"""
全文一致性检查阶段 - 检查论文各章节间的一致性问题

职责:
  1. 从 PipelineContext 收集所有已生成的论文章节内容
  2. 检查图片编号连续性（缺失、重复）
  3. 检查表格编号连续性（缺失、重复）
  4. 检查数值引用一致性（摘要 vs 正文的数值矛盾）
  5. 检查符号定义一致性（同一变量在不同章节的定义冲突）
  6. 检查术语统一性（同一概念使用不同名称）
  7. 将发现的问题存入 ctx.artifacts["consistency_issues"]

设计原则:
  - 此阶段为可选阶段，失败不中断主工作流
  - 在 WriterStage 之后、ReviewStage / FinalizeStage 之前执行
  - 仅做静态文本分析，不调用 LLM，执行速度快
"""

from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING

from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class ConsistencyCheckStage:
    """全文一致性检查阶段

    在 WriterStage 完成后执行，对论文各章节间的一致性进行静态检查。
    检查项包括：图表编号连续性、数值引用一致性、符号定义一致性、术语统一性。
    """

    # 图片编号正则：匹配 "图1"、"图 1"、"Figure 1"、"Fig. 1"、"Fig 1" 等
    _FIG_PATTERN: str = r"(?:图|Figure|Fig\.?)\s*(\d+)"

    # 表格编号正则：匹配 "表1"、"表 1"、"Table 1" 等
    _TABLE_PATTERN: str = r"(?:表|Table)\s*(\d+)"

    # 百分比数值正则：匹配 "3.2%"、"95.5%" 等
    _PERCENT_PATTERN: str = r"(\d+(?:\.\d+)?)\s*%"

    # 数学符号定义正则：匹配 "$x$"、"$\alpha$" 等 LaTeX 行内公式
    _SYMBOL_PATTERN: str = r"\$([a-zA-Z_\\]+(?:\{[^}]*\})?)\$"

    @property
    def name(self) -> str:
        """阶段唯一标识符"""
        return "consistency_check"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行全文一致性检查

        Args:
            ctx: 管线上下文，从中读取论文内容并写入检查结果
        """
        logger.info("开始全文一致性检查")

        # 从 ctx.user_output 收集所有已生成的论文内容
        full_text, section_texts = self._collect_full_text(ctx)
        if not full_text:
            logger.warning("未找到论文内容，跳过一致性检查")
            return

        issues: list[dict] = []

        # 1. 图片编号连续性检查
        issues.extend(self._check_figure_numbering(full_text))

        # 2. 表格编号连续性检查
        issues.extend(self._check_table_numbering(full_text))

        # 3. 数值引用一致性检查（摘要 vs 正文）
        issues.extend(self._check_numerical_consistency(section_texts))

        # 4. 符号定义一致性检查
        issues.extend(self._check_symbol_consistency(section_texts))

        # 5. 术语统一性检查
        issues.extend(self._check_terminology_consistency(full_text))

        if issues:
            logger.warning("一致性检查发现 %d 个问题", len(issues))
            for issue in issues:
                logger.info(
                    "  [%s] %s: %s",
                    issue['severity'],
                    issue['type'],
                    issue['message'],
                )

            # 将问题存入 ctx.artifacts 供后续阶段（如 ReviewStage）使用
            ctx.artifacts[ArtifactKeys.CONSISTENCY_ISSUES] = issues

            # 按严重程度统计
            critical_count = sum(
                1 for i in issues if i.get("severity") == "critical"
            )

            summary = f"一致性检查发现 {len(issues)} 个问题"
            if critical_count > 0:
                summary += f"（{critical_count} 个严重）"

            await ctx.send_progress(f"!! {summary}", 92)
        else:
            logger.info("一致性检查通过，未发现问题")
            ctx.artifacts[ArtifactKeys.CONSISTENCY_ISSUES] = []
            await ctx.send_progress("全文一致性检查通过", 92)

    def _collect_full_text(
        self, ctx: PipelineContext
    ) -> tuple[str, dict[str, str]]:
        """从 PipelineContext 收集完整论文文本

        按照 UserOutput.seq 的顺序拼接各章节内容，同时返回按章节键
        索引的字典，方便后续做跨章节对比。

        Args:
            ctx: 管线上下文

        Returns:
            (full_text, section_texts) 元组:
              - full_text: 全文拼接字符串
              - section_texts: {章节键: 章节内容} 字典
        """
        if ctx.user_output is None:
            return "", {}

        section_texts: dict[str, str] = {}
        ordered_parts: list[str] = []

        # 按 seq 顺序遍历，确保拼接顺序与最终论文一致
        for section_key in ctx.user_output.seq:
            section_data = ctx.user_output.res.get(section_key)
            if not section_data:
                continue

            content = section_data.get("response_content", "")
            if content:
                section_texts[section_key] = content
                ordered_parts.append(content)

        full_text = "\n\n".join(ordered_parts)
        return full_text, section_texts

    def _check_figure_numbering(self, text: str) -> list[dict]:
        """检查图片编号是否连续

        规则:
          - 编号应从 1 开始，连续递增
          - 不允许编号缺失（跳跃）
          - 不允许编号重复

        Args:
            text: 论文全文

        Returns:
            问题列表
        """
        numbers = [int(m) for m in re.findall(self._FIG_PATTERN, text)]
        return self._check_numbering_sequence(numbers, "图片", "figure_numbering")

    def _check_table_numbering(self, text: str) -> list[dict]:
        """检查表格编号是否连续

        规则与图片编号检查相同。

        Args:
            text: 论文全文

        Returns:
            问题列表
        """
        numbers = [int(m) for m in re.findall(self._TABLE_PATTERN, text)]
        return self._check_numbering_sequence(numbers, "表格", "table_numbering")

    def _check_numbering_sequence(
        self,
        numbers: list[int],
        label: str,
        issue_type: str,
    ) -> list[dict]:
        """通用编号连续性检查

        Args:
            numbers: 从文本中提取的编号列表（可能乱序、重复）
            label: 中文标签（"图片" 或 "表格"）
            issue_type: 问题类型标识符

        Returns:
            问题列表
        """
        issues: list[dict] = []
        if not numbers:
            return issues

        max_num = max(numbers)
        expected = set(range(1, max_num + 1))
        actual = set(numbers)
        counter = Counter(numbers)

        # 检查缺失编号
        missing = sorted(expected - actual)
        if missing:
            missing_str = ", ".join(str(n) for n in missing)
            issues.append({
                "type": issue_type,
                "severity": "warning",
                "message": (
                    f"{label}编号不连续，缺少: "
                    f"{label}{missing_str}"
                ),
            })

        # 检查重复编号
        duplicates = sorted(n for n, cnt in counter.items() if cnt > 1)
        if duplicates:
            dup_str = ", ".join(str(n) for n in duplicates)
            issues.append({
                "type": issue_type,
                "severity": "critical",
                "message": (
                    f"{label}编号重复: "
                    f"{label}{dup_str}"
                ),
            })

        return issues

    def _check_numerical_consistency(
        self, section_texts: dict[str, str]
    ) -> list[dict]:
        """检查数值引用一致性（摘要 vs 正文）

        对比摘要/首页中出现的百分比数值与正文中的百分比数值，
        检测是否存在矛盾引用（如摘要说"误差小于5%"但正文说"误差为3.2%"
        时不算矛盾，但摘要写"准确率为98%"而正文中从未出现"98%"则需警告）。

        Args:
            section_texts: {章节键: 章节内容} 字典

        Returns:
            问题列表
        """
        issues: list[dict] = []

        # 提取摘要/首页中的百分比数值
        abstract_text = section_texts.get("firstPage", "")
        if not abstract_text:
            return issues

        abstract_percents = set(re.findall(self._PERCENT_PATTERN, abstract_text))
        if not abstract_percents:
            return issues

        # 收集正文中所有百分比数值（排除摘要本身）
        body_percents: set[str] = set()
        for key, content in section_texts.items():
            if key == "firstPage":
                continue
            body_percents.update(re.findall(self._PERCENT_PATTERN, content))

        # 找出摘要中提到但正文中从未出现的数值
        orphan_values = abstract_percents - body_percents
        if orphan_values:
            orphan_str = ", ".join(f"{v}%" for v in sorted(orphan_values))
            issues.append({
                "type": "numerical_consistency",
                "severity": "warning",
                "message": (
                    f"摘要中出现的数值在正文中未找到对应来源: "
                    f"{orphan_str}（可能是数值引用不一致）"
                ),
            })

        return issues

    def _check_symbol_consistency(
        self, section_texts: dict[str, str]
    ) -> list[dict]:
        """检查符号定义一致性

        检测在「符号说明」章节中定义的数学符号是否在正文中被使用，
        以及正文中使用的高频符号是否在符号说明中有定义。

        Args:
            section_texts: {章节键: 章节内容} 字典

        Returns:
            问题列表
        """
        issues: list[dict] = []

        # 提取符号说明章节中定义的符号
        symbol_section = section_texts.get("symbol", "")
        if not symbol_section:
            return issues

        defined_symbols = set(re.findall(self._SYMBOL_PATTERN, symbol_section))
        if not defined_symbols:
            return issues

        # 收集正文中使用的符号（排除符号说明章节本身）
        body_symbols: set[str] = set()
        for key, content in section_texts.items():
            if key == "symbol":
                continue
            body_symbols.update(re.findall(self._SYMBOL_PATTERN, content))

        # 符号说明中定义但正文未使用的符号
        unused_symbols = defined_symbols - body_symbols
        # 过滤掉过于简短的单字母符号（可能是误匹配）
        unused_significant = {
            s for s in unused_symbols if len(s) > 1 or s.startswith("\\")
        }
        if unused_significant:
            symbols_str = ", ".join(
                f"${s}$" for s in sorted(unused_significant)[:10]
            )
            issues.append({
                "type": "symbol_consistency",
                "severity": "info",
                "message": (
                    f"符号说明中定义但正文未使用的符号: "
                    f"{symbols_str}"
                ),
            })

        # 正文中高频使用但符号说明中未定义的符号
        # 只关注非单字母的复杂符号（单字母变量如 x, y 可能是常见变量不需特别定义）
        undefined_symbols = body_symbols - defined_symbols
        undefined_complex = {
            s for s in undefined_symbols
            if len(s) > 1 or s.startswith("\\")
        }
        if undefined_complex:
            # 统计出现频次，只报告高频未定义符号
            symbol_freq: Counter = Counter()
            for key, content in section_texts.items():
                if key == "symbol":
                    continue
                for sym in re.findall(self._SYMBOL_PATTERN, content):
                    if sym in undefined_complex:
                        symbol_freq[sym] += 1

            # 出现 3 次及以上的未定义符号才报告
            frequent_undefined = [
                sym for sym, cnt in symbol_freq.most_common()
                if cnt >= 3
            ]
            if frequent_undefined:
                symbols_str = ", ".join(
                    f"${s}$" for s in frequent_undefined[:10]
                )
                issues.append({
                    "type": "symbol_consistency",
                    "severity": "warning",
                    "message": (
                        f"正文中频繁使用但符号说明中未定义的符号: "
                        f"{symbols_str}"
                    ),
                })

        return issues

    def _check_terminology_consistency(self, text: str) -> list[dict]:
        """检查术语统一性

        检测同一概念是否使用了不同的名称。例如：
        - "随机森林" vs "Random Forest"（中英混用）
        - "目标函数" vs "适应度函数"（同义词混用）

        目前采用预定义的常见混用术语对进行检查。

        Args:
            text: 论文全文

        Returns:
            问题列表
        """
        issues: list[dict] = []

        # 常见的术语混用对：(术语A, 术语B, 描述)
        # 如果同一篇论文中同时出现 A 和 B，则提醒用户统一
        _TERM_PAIRS: tuple[tuple[str, str, str], ...] = (
            ("随机森林", "Random Forest", "建议统一使用中文或英文"),
            ("支持向量机", "SVM", "建议首次出现时标注全称"),
            ("神经网络", "Neural Network", "建议统一使用中文或英文"),
            ("遗传算法", "Genetic Algorithm", "建议统一使用中文或英文"),
            ("目标函数", "适应度函数", "建议统一术语"),
            ("损失函数", "代价函数", "建议统一术语"),
            ("特征", "属性", "在同一语境下建议统一术语"),
            ("训练集", "训练数据集", "建议统一术语"),
            ("预测值", "估计值", "在同一语境下建议统一术语"),
        )

        for term_a, term_b, suggestion in _TERM_PAIRS:
            has_a = term_a in text
            has_b = term_b in text
            if has_a and has_b:
                issues.append({
                    "type": "terminology_consistency",
                    "severity": "info",
                    "message": (
                        f"术语混用: 同时出现「{term_a}」和「{term_b}」，"
                        f"{suggestion}"
                    ),
                })

        return issues
