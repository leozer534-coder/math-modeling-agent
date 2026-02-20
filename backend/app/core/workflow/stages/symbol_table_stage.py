"""
符号表提取阶段 - 自动从建模方案中提取数学符号

职责:
  1. 从 modeler_response 的建模方案中提取数学符号
  2. 从 coordinator_response 的问题分析中补充符号
  3. 输出结构化符号列表（符号、含义、单位、取值范围）
  4. 供 WriterStage 生成"符号说明"章节

设计原则:
  - 此阶段为可选阶段，失败仅 warning 不中断主工作流
  - 在 ModelerStage 之后、CoderStage 之前执行
  - 使用 LLM 进行语义级符号提取，比纯正则更准确
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


# 符号提取的系统提示词
_SYMBOL_EXTRACT_SYSTEM_PROMPT = """\
你是一位数学建模论文的符号整理专家。你的任务是从给定的建模方案文本中，
提取所有数学符号，并以结构化 JSON 格式输出。

要求:
1. 提取所有出现的数学符号（包括决策变量、参数、目标函数、约束条件、中间变量、评价指标）
2. 每个符号包含以下字段:
   - symbol: 符号的文本表示（如 x_i, alpha, R^2）
   - latex: 符号的 LaTeX 表示（如 x_i, \\alpha, R^2）
   - meaning: 符号的中文含义
   - unit: 单位（如无量纲则填"无量纲"）
   - range: 取值范围（如 x_i >= 0，无明确范围则填"-"）
   - category: 分类，仅限以下值之一: 决策变量、参数、目标函数、约束条件、中间变量、评价指标
3. 去重: 同一符号只出现一次
4. 排序: 按 category 分组，组内按 symbol 字母序排列

请严格以如下 JSON 格式输出，不要添加额外说明:
```json
{
  "symbols": [
    {
      "symbol": "x_i",
      "latex": "x_i",
      "meaning": "第i个决策变量",
      "unit": "无量纲",
      "range": "x_i >= 0",
      "category": "决策变量"
    }
  ]
}
```
"""

# 分类的展示顺序
_CATEGORY_ORDER = (
    "决策变量",
    "参数",
    "目标函数",
    "约束条件",
    "中间变量",
    "评价指标",
)


class SymbolTableStage:
    """符号表自动提取阶段

    从建模方案和问题分析中提取数学符号，输出结构化符号列表和
    Markdown 表格文本，供 WriterStage 生成"符号说明"章节使用。
    """

    @property
    def name(self) -> str:
        """阶段唯一标识符"""
        return "symbol_table"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行符号表提取

        从 ctx 收集建模方案文本，调用 LLM 提取符号，
        结果存入 ctx.artifacts["symbol_table"] 和
        ctx.artifacts["symbol_table_text"]。

        Args:
            ctx: 管线上下文，从中读取建模方案并写入符号表
        """
        try:
            await self._do_extract(ctx)
        except Exception as e:
            # 符号表提取失败仅 warning，不中断工作流
            logger.warning(
                "SymbolTableStage 执行失败（非关键）[task_id=%s]: %s",
                ctx.task_id,
                e,
            )

    async def _do_extract(self, ctx: PipelineContext) -> None:
        """符号提取核心逻辑

        Args:
            ctx: 管线上下文
        """
        logger.info("开始提取数学符号表")
        await ctx.send_progress("正在提取数学符号表...", 42)

        # 1. 收集建模方案文本
        input_text = self._collect_source_text(ctx)
        if not input_text.strip():
            logger.warning("未找到建模方案文本，跳过符号表提取")
            return

        # 2. 调用 LLM 提取符号
        model = ctx.llms.get("modeler")
        if model is None:
            logger.warning("未找到 modeler LLM 实例，跳过符号表提取")
            return

        messages = [
            SystemMessage(content=_SYMBOL_EXTRACT_SYSTEM_PROMPT),
            HumanMessage(content=f"请从以下建模方案中提取所有数学符号:\n\n{input_text}"),
        ]
        response = await model.ainvoke(messages)
        raw_output = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        # 3. 解析 JSON 结果
        symbols = self._parse_symbols_json(raw_output)
        if not symbols:
            logger.warning("LLM 未返回有效的符号列表")
            return

        # 4. 存入 artifacts
        ctx.artifacts[ArtifactKeys.SYMBOL_TABLE] = symbols
        logger.info("SymbolTableStage: 成功提取 %d 个数学符号", len(symbols))

        # 5. 格式化为 Markdown 表格
        table_text = self._format_markdown_table(symbols)
        ctx.artifacts[ArtifactKeys.SYMBOL_TABLE_TEXT] = table_text

        await ctx.send_progress(
            f"符号表提取完成，共 {len(symbols)} 个符号", 43
        )
        logger.info("SymbolTableStage 完成")

    def _collect_source_text(self, ctx: PipelineContext) -> str:
        """从 PipelineContext 收集建模方案和问题分析文本

        优先使用 modeler_response（主要来源），
        补充 coordinator_response 中可能提到的符号信息。

        Args:
            ctx: 管线上下文

        Returns:
            拼接后的源文本
        """
        parts: list[str] = []

        # 主要来源: 建模方案
        if ctx.modeler_response:
            modeler_text = self._extract_text(ctx.modeler_response)
            if modeler_text:
                parts.append(f"## 建模方案\n{modeler_text}")

        # 补充来源: 协调者的问题分析
        if ctx.coordinator_response:
            coordinator_text = self._extract_text(ctx.coordinator_response)
            if coordinator_text:
                # 截断过长的协调者文本，避免 context window 浪费
                truncated = coordinator_text[:3000]
                parts.append(f"## 问题分析\n{truncated}")

        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _extract_text(response: object) -> str:
        """从响应对象中提取纯文本

        兼容多种响应格式: str、dict、具有 content/response 属性的对象。

        Args:
            response: Agent 的响应对象

        Returns:
            提取的文本内容
        """
        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            # 尝试常见的键名
            for key in ("content", "response", "text", "result"):
                val = response.get(key)
                if val and isinstance(val, str):
                    return val
            # 兜底: JSON 序列化
            try:
                return json.dumps(response, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                return str(response)

        # 尝试属性访问
        for attr in ("content", "response", "text", "result"):
            val = getattr(response, attr, None)
            if val and isinstance(val, str):
                return val

        return str(response)

    @staticmethod
    def _parse_symbols_json(raw_output: str) -> list[dict]:
        """解析 LLM 输出中的符号 JSON

        LLM 可能在 JSON 外包裹 markdown 代码块，需要先剥离。
        对非标准 JSON 做容错处理。

        Args:
            raw_output: LLM 的原始输出文本

        Returns:
            符号字典列表，解析失败返回空列表
        """
        # 剥离 markdown 代码块标记
        json_str = raw_output.strip()
        code_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            json_str,
            re.DOTALL,
        )
        if code_block_match:
            json_str = code_block_match.group(1).strip()

        # 尝试直接解析
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "symbols" in data:
                symbols = data["symbols"]
                if isinstance(symbols, list):
                    return [s for s in symbols if isinstance(s, dict)]
            # 如果顶层直接是列表
            if isinstance(data, list):
                return [s for s in data if isinstance(s, dict)]
        except json.JSONDecodeError:
            pass

        # 容错: 尝试在整个文本中查找 JSON 对象
        json_obj_match = re.search(r"\{[\s\S]*\"symbols\"\s*:\s*\[[\s\S]*\][\s\S]*\}", json_str)
        if json_obj_match:
            try:
                data = json.loads(json_obj_match.group(0))
                if isinstance(data, dict) and isinstance(data.get("symbols"), list):
                    return [
                        s for s in data["symbols"] if isinstance(s, dict)
                    ]
            except json.JSONDecodeError:
                pass

        logger.warning("无法从 LLM 输出中解析符号 JSON")
        return []

    @staticmethod
    def _format_markdown_table(symbols: list[dict]) -> str:
        """将符号列表格式化为 Markdown 表格

        按 category 分组排序，输出规范的 Markdown 表格。

        Args:
            symbols: 符号字典列表

        Returns:
            Markdown 表格文本
        """
        if not symbols:
            return ""

        # 按 category 分组排序
        def sort_key(s: dict) -> tuple[int, str]:
            cat = s.get("category", "中间变量")
            order = (
                _CATEGORY_ORDER.index(cat)
                if cat in _CATEGORY_ORDER
                else len(_CATEGORY_ORDER)
            )
            return (order, s.get("symbol", ""))

        sorted_symbols = sorted(symbols, key=sort_key)

        # 构建表格
        lines: list[str] = [
            "| 符号 | 含义 | 单位 | 取值范围 |",
            "|------|------|------|----------|",
        ]

        for sym in sorted_symbols:
            latex = sym.get("latex", sym.get("symbol", ""))
            meaning = sym.get("meaning", "-")
            unit = sym.get("unit", "-")
            range_val = sym.get("range", "-")

            # 用 $ 包裹 LaTeX 符号
            latex_display = f"${latex}$" if latex else "-"
            # 取值范围中的数学表达式也用 $ 包裹
            range_display = (
                f"${range_val}$"
                if range_val and range_val != "-"
                else "-"
            )

            lines.append(
                f"| {latex_display} | {meaning} | {unit} | {range_display} |"
            )

        return "\n".join(lines)
