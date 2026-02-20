"""
EDA 数据探索阶段 - 独立 EDA 分析（在建模之前执行）

职责:
  1. 使用 CoderAgent 执行 EDA 代码（数据清洗、可视化）
  2. 收集 EDA 的代码输出，供 Modeler 参考
  3. 使用 WriterAgent 将 EDA 结果写入论文
  4. 将 EDA 代码输出写入 ctx.artifacts["eda_result"]
  5. 从代码输出中提取结构化 EDA 摘要，写入 ctx.artifacts["eda_data_summary"]
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.core.flows import Flows
from app.core.prompts import INDEPENDENT_EDA_PROMPT
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.core.workflow.stages.stage_constants import (
    EDA_CORRELATION_THRESHOLD,
    EDA_HIGH_MISSING_RATE,
)
from app.schemas.tool_result import EDADataSummary
from app.utils.common_utils import get_config_template
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class EDAStage:
    """EDA 数据探索阶段"""

    @property
    def name(self) -> str:
        return "eda"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行独立 EDA 分析（含错误处理层）"""
        try:
            await self._do_execute(ctx)
        except Exception:
            logger.error(
                "EDAStage 执行失败 [task_id=%s]",
                ctx.task_id,
                exc_info=True,
            )
            try:
                await ctx.send_progress("数据探索分析阶段执行失败", -1)
            except Exception:
                logger.warning("EDAStage: 发送错误进度通知失败")
            raise

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """EDAStage 核心业务逻辑"""
        await ctx.send_progress("正在进行数据探索分析（EDA）...", 21)

        coder_agent = ctx.agents["coder"]
        flows = Flows(ctx.questions)

        # 构建 EDA prompt，注入数据预览摘要
        eda_prompt = INDEPENDENT_EDA_PROMPT
        data_summary = ctx.artifacts.get(ArtifactKeys.DATA_SUMMARY, "")
        if data_summary:
            eda_prompt += (
                "\n\n## 已知数据文件信息（预览）\n"
                "以下是对工作目录中数据文件的预扫描结果，"
                "请基于这些信息进行更有针对性的 EDA：\n\n"
                f"{data_summary}\n"
            )

        # 执行 EDA
        eda_coder_response = await coder_agent.run(
            prompt=eda_prompt,
            subtask_title="eda",
        )

        # 收集 EDA 的代码执行输出
        eda_code_output = ctx.code_interpreter.get_code_output("eda")

        # EDA 结果写入论文
        config_template = get_config_template(ctx.problem.comp_template, ctx.problem.format_output)
        writer_prompt = flows.get_writer_prompt(
            "eda",
            eda_coder_response.code_response,
            ctx.code_interpreter,
            config_template,
        )
        writer_agent = ctx.agents["writer"]
        writer_response = await writer_agent.run(
            writer_prompt,
            available_images=eda_coder_response.created_images,
            sub_title="eda",
        )
        ctx.user_output.set_res("eda", writer_response)

        # 保存 EDA 原始文本结果供 Modeler 使用（向后兼容）
        ctx.artifacts[ArtifactKeys.EDA_RESULT] = eda_code_output

        # 从代码输出中提取结构化 EDA 摘要
        eda_data_summary = self._extract_eda_summary(eda_code_output)
        if not eda_data_summary.is_empty():
            ctx.artifacts[ArtifactKeys.EDA_DATA_SUMMARY] = eda_data_summary
            logger.info(
                "EDAStage: 已提取结构化 EDA 摘要 "
                "(shape=%s, 数值列=%d, 分类列=%d, 缺失率条目=%d)",
                eda_data_summary.dataset_shape,
                len(eda_data_summary.numeric_columns),
                len(eda_data_summary.categorical_columns),
                len(eda_data_summary.missing_ratio),
            )
        else:
            logger.info("EDAStage: 未能从代码输出中提取结构化摘要，将使用纯文本传递")

        await ctx.send_progress("数据探索分析完成", 30)
        logger.info("EDAStage 完成: 代码输出长度 %d 字符", len(eda_code_output))

    @staticmethod
    def _extract_eda_summary(code_output: str) -> EDADataSummary:
        """从 EDA 代码执行输出中提取结构化摘要信息。

        使用正则匹配从 pandas/numpy 的常见输出格式中提取数据特征。
        该方法采用"尽力提取"策略：每个字段独立提取，单个字段解析失败
        不影响其他字段。

        Args:
            code_output: EDA 阶段的代码执行原始输出文本

        Returns:
            EDADataSummary 结构化摘要对象（可能为空）
        """
        summary = EDADataSummary()

        if not code_output or not code_output.strip():
            return summary

        # --- 提取数据维度 (行数, 列数) ---
        summary.dataset_shape = _extract_dataset_shape(code_output)

        # --- 提取数值型列名 ---
        summary.numeric_columns = _extract_column_list(
            code_output,
            patterns=[
                r"(?:数值[型类]?|numeric|float|int)\s*(?:列|columns?|变量|features?)\s*[:：]\s*(.+)",
                r"(?:float64|int64|float32|int32)\s*(?:列|columns?)\s*[:：]?\s*(.+)",
            ],
        )

        # --- 提取分类型列名 ---
        summary.categorical_columns = _extract_column_list(
            code_output,
            patterns=[
                r"(?:分类[型类]?|categorical|object|string|类别)\s*(?:列|columns?|变量|features?)\s*[:：]\s*(.+)",
                r"(?:object)\s*(?:列|columns?)\s*[:：]?\s*(.+)",
            ],
        )

        # --- 从 dtypes 输出中补充提取列类型 ---
        if not summary.numeric_columns and not summary.categorical_columns:
            numeric, categorical = _extract_columns_from_dtypes(code_output)
            summary.numeric_columns = numeric
            summary.categorical_columns = categorical

        # --- 提取缺失率 ---
        summary.missing_ratio = _extract_missing_ratio(code_output)

        # --- 提取相关性信息 ---
        summary.correlation_highlights = _extract_correlation(code_output)

        # --- 提取数据质量问题 ---
        summary.data_quality_issues = _extract_quality_issues(code_output)

        # --- 提取关键统计摘要（截取 describe() 输出等） ---
        summary.key_statistics = _extract_key_statistics(code_output)

        # --- 基于数据特征推荐模型类型 ---
        summary.suggested_models = _suggest_models(summary)

        return summary


# ==================== 内部提取辅助函数 ====================


def _extract_dataset_shape(text: str) -> tuple[int, int] | None:
    """从输出中提取数据集的行列数。

    支持多种常见输出格式：
    - pandas shape: (1000, 15)
    - 中文描述: 1000 行 15 列
    - RangeIndex / columns 信息
    """
    # 匹配 shape 输出: (行数, 列数)
    shape_patterns = [
        r"(?:shape|形状)\s*[:：]?\s*\((\d+),\s*(\d+)\)",
        r"(\d+)\s*(?:行|rows?)\s*[,x×]\s*(\d+)\s*(?:列|columns?)",
        r"(\d+)\s*(?:rows?|entries)\s*[,x×]\s*(\d+)\s*(?:columns?)",
        r"RangeIndex:\s*(\d+)\s*entries.*?(\d+)\s*columns",
    ]
    for pattern in shape_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                rows = int(match.group(1))
                cols = int(match.group(2))
                if rows > 0 and cols > 0:
                    return (rows, cols)
            except (ValueError, IndexError):
                continue
    return None


def _extract_column_list(text: str, patterns: list[str]) -> list[str]:
    """通过正则模式提取列名列表。

    Args:
        text: 输出文本
        patterns: 待匹配的正则模式列表（每个模式的 group(1) 应为列名字符串）

    Returns:
        提取到的列名列表
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            # 清理常见格式: ['col1', 'col2'] 或 col1, col2
            raw = re.sub(r"[\[\]\"']", "", raw)
            cols = [c.strip() for c in re.split(r"[,，\s]+", raw) if c.strip()]
            if cols:
                return cols
    return []


def _extract_columns_from_dtypes(text: str) -> tuple[list[str], list[str]]:
    """从 pandas dtypes 输出中提取数值列和分类列。

    典型格式:
        col_name    float64
        col_name    object
        col_name    int64
    """
    numeric: list[str] = []
    categorical: list[str] = []

    # 匹配 dtypes 输出块
    dtype_pattern = re.compile(
        r"^(\w[\w\s]*?)\s+(float\d*|int\d*|bool|datetime\d*|object|string|category)\s*$",
        re.MULTILINE,
    )
    for match in dtype_pattern.finditer(text):
        col_name = match.group(1).strip()
        dtype = match.group(2).lower()
        if dtype in ("object", "string", "category"):
            categorical.append(col_name)
        elif dtype.startswith(("float", "int", "bool")):
            numeric.append(col_name)

    return numeric, categorical


def _extract_missing_ratio(text: str) -> dict[str, float]:
    """从输出中提取各列的缺失率。

    支持多种格式:
    - col_name: 15.2% / 0.152
    - col_name    15.20%
    - 缺失值统计表格输出
    """
    missing: dict[str, float] = {}

    # 匹配 "列名 缺失率" 模式（百分比格式）
    pct_pattern = re.compile(
        r"(\w[\w\s]*?)\s+(\d+\.?\d*)\s*%",
        re.MULTILINE,
    )

    # 查找缺失值相关区域
    missing_section_patterns = [
        r"(?:缺失|missing|null|nan|isnull|isna).*?(?:\n(?:.*\n){0,30})",
    ]

    for section_pat in missing_section_patterns:
        section_match = re.search(
            section_pat, text, re.IGNORECASE | re.DOTALL
        )
        if not section_match:
            continue
        section_text = section_match.group(0)
        for m in pct_pattern.finditer(section_text):
            col_name = m.group(1).strip()
            # 过滤掉非列名的关键词
            if col_name.lower() in (
                "dtype",
                "type",
                "count",
                "total",
                "sum",
                "mean",
            ):
                continue
            try:
                ratio = float(m.group(2)) / 100.0
                if 0.0 < ratio <= 1.0:
                    missing[col_name] = round(ratio, 4)
            except ValueError:
                continue

    return missing


def _extract_correlation(text: str) -> str | None:
    """从输出中提取相关性分析的关键发现。

    提取高相关性变量对和相关系数。
    """
    highlights: list[str] = []

    # 匹配 "变量A 与 变量B 相关系数: 0.85" 格式
    corr_patterns = [
        r"(\w+)\s*(?:与|and|vs|&)\s*(\w+)\s*[:：]?\s*(?:相关系数|corr|correlation)?\s*[:=]?\s*([+-]?0\.\d+)",
        r"(?:相关系数|corr|correlation)\s*[:：]?\s*(\w+)\s*(?:与|and|vs)\s*(\w+)\s*[:=]?\s*([+-]?0\.\d+)",
        r"(\w+)\s*[-–]\s*(\w+)\s*[:：]?\s*([+-]?0\.\d+)",
    ]

    for pattern in corr_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                var1 = match.group(1).strip()
                var2 = match.group(2).strip()
                coeff = float(match.group(3))
                if abs(coeff) >= EDA_CORRELATION_THRESHOLD:  # 只记录中等以上相关性
                    highlights.append(f"{var1}-{var2}: {coeff:.2f}")
            except (ValueError, IndexError):
                continue

    # 匹配整段相关性描述
    if not highlights:
        desc_pattern = re.search(
            r"(?:高度?相关|强相关|highly correlated|strong correlation)"
            r"\s*[:：]?\s*(.+?)(?:\n|$)",
            text,
            re.IGNORECASE,
        )
        if desc_pattern:
            return desc_pattern.group(1).strip()[:500]

    return "; ".join(highlights[:10]) if highlights else None


def _extract_quality_issues(text: str) -> list[str]:
    """从输出中提取数据质量问题。

    检测常见的数据质量关键词和模式。
    """
    issues: list[str] = []
    issue_keywords = [
        (r"(?:异常值|outlier|离群)[^。\n]{0,100}", "异常值"),
        (r"(?:重复[值行数据]|duplicate)[^。\n]{0,100}", "重复数据"),
        (r"(?:数据倾斜|skew|偏态)[^。\n]{0,100}", "数据分布偏斜"),
        (r"(?:不平衡|imbalance|类别不均)[^。\n]{0,100}", "类别不平衡"),
        (r"(?:多重共线|multicollinear)[^。\n]{0,100}", "多重共线性"),
        (r"(?:零方差|constant|常量列)[^。\n]{0,100}", "零方差/常量列"),
    ]

    for pattern, label in issue_keywords:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            detail = match.group(0).strip()
            # 截断过长的描述
            if len(detail) > 80:
                detail = detail[:80] + "..."
            issues.append(f"{label}: {detail}")

    return issues[:10]  # 最多保留 10 条


def _extract_key_statistics(text: str) -> str | None:
    """从输出中提取关键统计信息（如 describe() 输出）。

    Returns:
        截取的关键统计文本，最多 1500 字符
    """
    # 匹配 pandas describe() 的输出格式
    describe_patterns = [
        r"((?:count|mean|std|min|max|25%|50%|75%).*?(?:\n.*?){3,15})",
        r"((?:统计[描量述]|describe|基本统计|descriptive statistics).*?(?:\n.*?){3,20})",
    ]

    for pattern in describe_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            stats_text = match.group(0).strip()
            if len(stats_text) > 1500:
                stats_text = stats_text[:1500] + "\n... (已截断)"
            return stats_text

    return None


def _suggest_models(summary: EDADataSummary) -> list[str]:
    """基于 EDA 数据特征给出初步的模型类型建议。

    这只是辅助性建议，最终建模决策由 ModelerAgent 做出。

    Args:
        summary: 已提取的 EDA 摘要

    Returns:
        建议的模型类型列表
    """
    suggestions: list[str] = []

    if summary.dataset_shape is None:
        return suggestions

    rows, cols = summary.dataset_shape
    has_numeric = bool(summary.numeric_columns)
    has_categorical = bool(summary.categorical_columns)
    has_high_missing = any(
        v > EDA_HIGH_MISSING_RATE for v in summary.missing_ratio.values()
    )

    # 数据量建议
    if rows < 100:
        suggestions.append("小样本方法（参数检验、贝叶斯方法）")
    elif rows > 10000:
        suggestions.append("适合机器学习/深度学习方法")

    # 变量类型建议
    if has_numeric and not has_categorical:
        suggestions.append("回归分析、时间序列")
    elif has_categorical and not has_numeric:
        suggestions.append("分类模型、关联分析")
    elif has_numeric and has_categorical:
        suggestions.append("混合型建模（回归+分类）")

    # 高维度建议
    if cols > 30:
        suggestions.append("建议降维（PCA/特征选择）")

    # 缺失值建议
    if has_high_missing:
        suggestions.append("需要缺失值处理（多重插补/KNN填充）")

    return suggestions
