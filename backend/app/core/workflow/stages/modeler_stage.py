"""
建模阶段 - ModelerAgent 设计数学建模方案

职责:
  1. 创建 ModelerAgent 实例
  2. 注入 EDA 结果（含结构化摘要）、数据摘要、知识库上下文、记忆系统历史经验
  3. 运行 ModelerAgent 生成建模方案
  4. 将 modeler_response 写入 ctx.modeler_response
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.config.setting import settings
from app.core.agents import ModelerAgent
from app.core.knowledge_base import knowledge_base
from app.core.workflow.integration_helpers import (
    get_model_recommendations_context,
    query_knowledge_base_for_context,
)
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.schemas.tool_result import EDADataSummary
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


def _safe_get(obj: object, key: str, default: object = None) -> object:
    """统一取值辅助函数，兼容 dict 和具有属性的对象。"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class ModelerStage:
    """数学建模方案设计阶段"""

    @property
    def name(self) -> str:
        return "model"

    async def execute(self, ctx: PipelineContext) -> None:
        """运行 ModelerAgent 设计建模方案（错误处理层）"""
        try:
            await self._do_execute(ctx)
        except Exception:
            logger.error(
                "ModelerStage 执行失败, task_id=%s",
                ctx.task_id,
                exc_info=True,
            )
            raise

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """运行 ModelerAgent 设计建模方案（业务逻辑）"""
        await ctx.send_progress("正在设计建模方案...", 31)

        modeler_agent = ModelerAgent(
            ctx.task_id,
            ctx.llms["modeler"],
            enable_memory_system=settings.ENABLE_MEMORY_SYSTEM,
        )
        ctx.agents["modeler"] = modeler_agent

        # 记忆系统: 检索历史建模经验（失败不中断）
        memory_context = ""
        if settings.ENABLE_MEMORY_SYSTEM:
            try:
                problem_desc = ctx.problem.ques_all[:2000]
                memories = await modeler_agent.recall(problem_desc)
                memory_context = modeler_agent.format_recalled_memories(
                    memories
                )
                if memory_context:
                    logger.info(
                        "记忆系统: 检索到历史经验，长度: %d",
                        len(memory_context),
                    )
            except Exception as e:
                logger.warning("记忆系统检索失败（非关键）: %s", e)

        # 合并 EDA 结果和数据摘要
        eda_result = ctx.artifacts.get(ArtifactKeys.EDA_RESULT, "")
        data_summary = ctx.artifacts.get(ArtifactKeys.DATA_SUMMARY, "")
        combined_eda = eda_result or ""
        if data_summary:
            combined_eda = (
                f"## 原始数据文件信息\n{data_summary}\n\n"
                f"## EDA 代码执行结果\n{combined_eda}"
            )

        # 提取结构化 EDA 摘要（如果 EDA 阶段已提取则直接使用）
        eda_data_summary: EDADataSummary | None = ctx.artifacts.get(
            ArtifactKeys.EDA_DATA_SUMMARY
        )
        if eda_data_summary and not isinstance(eda_data_summary, EDADataSummary):
            # 防御性检查: 如果从检查点恢复时类型不匹配则忽略
            logger.warning(
                "eda_data_summary 类型不匹配，忽略结构化摘要"
            )
            eda_data_summary = None

        if eda_data_summary and not eda_data_summary.is_empty():
            # 将结构化摘要文本插入到 combined_eda 头部，让 Modeler 优先看到
            structured_text = eda_data_summary.to_prompt_text()
            combined_eda = (
                f"{structured_text}\n\n"
                f"---\n\n"
                f"{combined_eda}"
            )
            logger.info(
                "ModelerStage: 已注入结构化 EDA 摘要 (%d 字符)",
                len(structured_text),
            )

        # 查询知识库上下文（失败不中断）
        research_context = ""
        try:
            problem_desc = ctx.problem.ques_all
            problem_type = ""
            keywords: list[str] = []
            if hasattr(ctx.coordinator_response, "problem_type"):
                problem_type = ctx.coordinator_response.problem_type or ""
            if hasattr(ctx.coordinator_response, "recommended_methods"):
                keywords = ctx.coordinator_response.recommended_methods or []

            kb_context = query_knowledge_base_for_context(
                problem_description=problem_desc,
                problem_type=problem_type,
                keywords=keywords,
            )
            registry_context = get_model_recommendations_context(
                scenario=f"{problem_desc} {problem_type}".strip(),
                top_k=5,
            )
            context_parts = [p for p in [kb_context, registry_context] if p]
            if context_parts:
                research_context = "\n\n---\n\n".join(context_parts)
        except Exception as e:
            logger.warning("知识库查询失败（非关键）: %s", e)

        # NOTE: RESEARCH_REPORT 当前无生产者 Stage，预留给未来 ResearchStage 扩展。
        #       当 ResearchStage 上线后，在此处消费研究报告上下文。

        # 合并记忆系统历史经验
        if memory_context:
            if research_context:
                research_context += "\n\n---\n\n" + memory_context
            else:
                research_context = memory_context

        # 消费 ModelSelector 的模型推荐结果（失败不中断）
        try:
            model_recommendation = ctx.artifacts.get(
                ArtifactKeys.MODEL_RECOMMENDATION
            )
            if model_recommendation:
                rec_text = self._build_model_recommendation_text(
                    model_recommendation
                )
                if rec_text:
                    if research_context:
                        research_context += (
                            "\n\n---\n\n" + rec_text
                        )
                    else:
                        research_context = rec_text
                    logger.info(
                        "ModelerStage: 已注入 ModelSelector"
                        " 推荐结果 (%d 字符)",
                        len(rec_text),
                    )
        except Exception as e:
            logger.warning(
                "消费 ModelSelector 推荐结果失败（非关键）: %s", e
            )

        # 消费 SmartModeler 的创新方案建议（失败不中断）
        try:
            innovative_plan = ctx.artifacts.get(
                ArtifactKeys.INNOVATIVE_MODEL_PLAN
            )
            if innovative_plan:
                plan_text = self._build_innovative_plan_text(
                    innovative_plan
                )
                if plan_text:
                    if research_context:
                        research_context += (
                            "\n\n---\n\n" + plan_text
                        )
                    else:
                        research_context = plan_text
                    logger.info(
                        "ModelerStage: 已注入 SmartModeler"
                        " 创新方案 (%d 字符)",
                        len(plan_text),
                    )
        except Exception as e:
            logger.warning(
                "消费 SmartModeler 创新方案失败（非关键）: %s", e
            )

        # 消费上游推荐信息（来自 ProblemAnalysisStage 和 ModelSelectionStage）
        recommended_approaches = ctx.artifacts.get(
            ArtifactKeys.RECOMMENDED_APPROACHES
        )
        recommended_primary = ctx.artifacts.get(
            ArtifactKeys.RECOMMENDED_PRIMARY_MODEL
        )

        upstream_context = ""
        if recommended_approaches:
            if isinstance(recommended_approaches, list):
                approaches_text = ", ".join(
                    str(a) for a in recommended_approaches[:5]
                )
            else:
                approaches_text = str(recommended_approaches)[:500]
            upstream_context += f"\n\n【推荐建模方法】\n{approaches_text}"

        if recommended_primary:
            upstream_context += (
                f"\n\n【推荐首选模型】\n{str(recommended_primary)[:300]}"
            )

        if upstream_context:
            logger.info(
                "ModelerStage: 注入上游推荐上下文 (%d 字符)",
                len(upstream_context),
            )
            # 将上游推荐上下文追加到 research_context
            if research_context:
                research_context += "\n\n---\n\n" + upstream_context
            else:
                research_context = upstream_context

        # 运行 Modeler（传递结构化 EDA 摘要对象供精确建模参考）
        modeler_response = await modeler_agent.run(
            ctx.coordinator_response,
            eda_result=combined_eda,
            eda_data_summary=eda_data_summary,
            research_context=research_context if research_context else None,
        )
        ctx.modeler_response = modeler_response

        # 知识库推荐验证方法和评价指标（失败不中断）
        try:
            # 获取问题类型
            problem_type = ctx.artifacts.get(ArtifactKeys.PROBLEM_TYPE, "")
            if not problem_type and hasattr(ctx.coordinator_response, "problem_type"):
                problem_type = ctx.coordinator_response.problem_type or ""

            # 推荐验证方法
            validation_methods = knowledge_base.get_validation_method(problem_type)
            if validation_methods:
                ctx.artifacts[ArtifactKeys.RECOMMENDED_VALIDATION] = [
                    {"name": v.name, "description": v.description, "steps": v.implementation_steps}
                    for v in validation_methods
                ]

            # 推荐评价指标
            eval_metrics = knowledge_base.get_evaluation_metrics(problem_type)
            if eval_metrics:
                ctx.artifacts[ArtifactKeys.RECOMMENDED_METRICS] = [
                    {"name": m.name, "description": m.description, "formula": m.formula}
                    for m in eval_metrics
                ]

            logger.info(
                "ModelerStage: 推荐 %d 个验证方法, %d 个评价指标",
                len(validation_methods),
                len(eval_metrics),
            )
        except Exception as e:
            logger.warning("知识库推荐失败（非关键）: %s", e)

        await ctx.send_progress("建模方案设计完成", 38)
        logger.info("ModelerStage 完成")

    # ------------------------------------------------------------------
    # 辅助方法: 构造上游 Agent 推荐结果的文本表示
    # ------------------------------------------------------------------

    @staticmethod
    def _build_model_recommendation_text(
        recommendation: object,
    ) -> str:
        """将 ModelSelector 的推荐结果转为可注入 prompt 的文本。

        支持 dict 和具有属性的对象两种形式，兼容检查点恢复
        后的反序列化场景。失败时返回空字符串，由调用方决定
        是否跳过。

        Args:
            recommendation: ModelSelector 写入 artifacts 的
                推荐结果，通常包含 primary_model、
                alternative_models、selection_justification、
                parameter_suggestions 等字段。

        Returns:
            格式化后的 Markdown 文本，或空字符串。
        """
        parts: list[str] = []
        parts.append("## ModelSelector 模型推荐")

        # 1. 推荐的主模型
        primary = _safe_get(recommendation, "primary_model")
        if primary:
            name = _safe_get(primary, "name", "") or str(primary)
            desc = _safe_get(primary, "description", "")
            parts.append(f"### 推荐主模型\n- **名称**: {name}")
            if desc:
                parts.append(f"- **描述**: {desc}")

        # 2. 备选模型列表
        alternatives = _safe_get(recommendation, "alternative_models")
        if alternatives and isinstance(alternatives, (list, tuple)):
            alt_lines: list[str] = []
            for alt in alternatives[:5]:
                alt_name = (
                    _safe_get(alt, "name", "") or str(alt)
                )
                alt_desc = _safe_get(alt, "description", "")
                line = f"- {alt_name}"
                if alt_desc:
                    line += f": {alt_desc}"
                alt_lines.append(line)
            if alt_lines:
                parts.append(
                    "### 备选模型\n" + "\n".join(alt_lines)
                )

        # 3. 选择理由
        justification = _safe_get(
            recommendation, "selection_justification"
        )
        if justification:
            parts.append(f"### 选择理由\n{justification}")

        # 4. 参数建议
        param_suggestions = _safe_get(
            recommendation, "parameter_suggestions"
        )
        if param_suggestions:
            if isinstance(param_suggestions, dict):
                param_lines = [
                    f"- **{k}**: {v}"
                    for k, v in param_suggestions.items()
                ]
                parts.append(
                    "### 参数建议\n" + "\n".join(param_lines)
                )
            elif isinstance(param_suggestions, str):
                parts.append(f"### 参数建议\n{param_suggestions}")

        # 只有标题没有实际内容时返回空
        if len(parts) <= 1:
            return ""
        return "\n\n".join(parts)

    @staticmethod
    def _build_innovative_plan_text(
        plan: object,
    ) -> str:
        """将 SmartModeler 的创新方案转为可注入 prompt 的文本。

        支持 dict 和具有属性的对象两种形式。失败时返回空
        字符串，由调用方决定是否跳过。

        Args:
            plan: SmartModeler 写入 artifacts 的创新方案，
                通常包含 innovation_points、approach、
                advantages、implementation_notes 等字段。

        Returns:
            格式化后的 Markdown 文本，或空字符串。
        """
        parts: list[str] = []
        parts.append("## SmartModeler 创新方案建议")

        # 如果 plan 是纯字符串，直接作为正文
        if isinstance(plan, str):
            if plan.strip():
                parts.append(plan.strip())
                return "\n\n".join(parts)
            return ""

        # 1. 创新点
        innovations = _safe_get(plan, "innovation_points")
        if innovations:
            if isinstance(innovations, (list, tuple)):
                items = "\n".join(
                    f"- {p}" for p in innovations[:10]
                )
                parts.append(f"### 创新点\n{items}")
            elif isinstance(innovations, str):
                parts.append(f"### 创新点\n{innovations}")

        # 2. 方法路径
        approach = _safe_get(plan, "approach")
        if approach:
            parts.append(f"### 方法路径\n{approach}")

        # 3. 方案优势
        advantages = _safe_get(plan, "advantages")
        if advantages:
            if isinstance(advantages, (list, tuple)):
                items = "\n".join(
                    f"- {a}" for a in advantages[:10]
                )
                parts.append(f"### 方案优势\n{items}")
            elif isinstance(advantages, str):
                parts.append(f"### 方案优势\n{advantages}")

        # 4. 实现注意事项
        impl_notes = _safe_get(plan, "implementation_notes")
        if impl_notes:
            parts.append(f"### 实现注意事项\n{impl_notes}")

        # 兜底: 如果上述字段都没命中，尝试 JSON 序列化
        if len(parts) <= 1:
            try:
                raw = (
                    plan
                    if isinstance(plan, dict)
                    else vars(plan)
                )
                fallback = json.dumps(
                    raw, ensure_ascii=False, indent=2
                )
                parts.append(f"### 方案详情\n```json\n{fallback}\n```")
            except Exception as e:
                logger.warning(
                    "_build_innovative_plan_text JSON 序列化失败: %s",
                    str(e),
                )
                return ""

        if len(parts) <= 1:
            return ""
        return "\n\n".join(parts)
