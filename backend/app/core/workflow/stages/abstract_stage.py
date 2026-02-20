"""
摘要生成阶段 - 独立生成高质量学术摘要

职责:
  1. 基于完整建模结果和论文内容，生成结构化学术摘要
  2. 包含问题描述、方法概述、主要结论、关键词
  3. 确保摘要满足数学建模竞赛评审标准
  4. 此阶段为可选阶段，失败不中断主工作流
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.agents.abstract_generator import AbstractGenerator
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class AbstractStage:
    """摘要生成阶段（可选）

    在 WriterStage 完成论文主体撰写后，利用完整的建模结果、
    求解数据和论文内容，生成符合数学建模竞赛评审标准的高质量摘要。
    """

    @property
    def name(self) -> str:
        return "abstract_generation"

    async def execute(self, ctx: PipelineContext) -> None:
        """基于建模全流程结果，生成高质量学术摘要"""
        await ctx.send_progress("正在生成论文摘要...", 89)

        try:
            # 1. 收集摘要生成所需的上下文信息
            abstract_input = self._collect_abstract_context(ctx)

            if not abstract_input.get("problem_description"):
                logger.warning("AbstractStage: 无问题描述，跳过摘要生成")
                return

            # 2. 使用 AbstractGenerator 生成杀手级摘要
            generator = AbstractGenerator(
                task_id=ctx.task_id,
                model=ctx.llms["writer"],
            )

            result = await generator.execute(
                problem_description=abstract_input["problem_description"],
                modeling_results=abstract_input["modeling_results"],
                code_results=abstract_input.get("code_results"),
                innovation_points=abstract_input.get("innovation_points"),
                validation_results=abstract_input.get("validation_results"),
            )

            # 3. 将摘要文本和关键词存入 artifacts
            abstract_text = result.abstract_text
            ctx.artifacts[ArtifactKeys.ABSTRACT_CONTENT] = abstract_text

            keywords = self._extract_keywords(result)
            ctx.artifacts[ArtifactKeys.KEYWORDS] = keywords

            # 4. 写入 UserOutput（如果可用）
            if ctx.user_output and hasattr(ctx.user_output, "set_res"):
                from app.schemas.A2A import WriterResponse

                writer_resp = WriterResponse(
                    response_content=abstract_text,
                    footnotes=None,
                )
                ctx.user_output.set_res("abstract", writer_resp)

            # 5. 报告完成状态
            score = result.quality_assessment.overall_score
            await ctx.send_progress(
                f"摘要生成完成，质量评分: {score:.0f}/100", 91
            )
            logger.info(
                "AbstractStage 完成: "
                "字数=%s, 评分=%.0f, 迭代=%d次",
                result.word_count,
                score,
                result.iteration_count,
            )

        except Exception as e:
            logger.warning(
                "AbstractStage 摘要生成失败（不影响主流程）[task_id=%s]: %s",
                ctx.task_id,
                e,
            )
            await ctx.send_progress("摘要生成跳过", 91)

    @staticmethod
    def _extract_keywords(result: Any) -> list[str]:
        """从摘要生成结果中提取关键词（3-5个）"""
        keywords: list[str] = []

        if result.components:
            # 优先使用关键贡献作为关键词来源
            contributions = getattr(
                result.components, "key_contributions", []
            )
            if contributions:
                keywords.extend(contributions)

            # 补充核心方法
            key_approach = getattr(result.components, "key_approach", "")
            if key_approach and len(keywords) < 5:
                # key_approach 是逗号分隔的字符串
                methods = [
                    m.strip()
                    for m in key_approach.split(",")
                    if m.strip()
                ]
                for method in methods:
                    if method not in keywords and len(keywords) < 5:
                        keywords.append(method)

        return keywords[:5]

    @staticmethod
    def _collect_abstract_context(
        ctx: PipelineContext,
    ) -> dict[str, Any]:
        """从 PipelineContext 收集摘要生成所需的全部上下文

        收集范围:
          - 问题描述（来自 Problem 或 CoordinatorResponse）
          - 建模方案（来自 ModelerResponse）
          - 求解结果（来自 solution_results）
          - 验证报告（来自 artifacts）
          - 创新点（来自 artifacts）
        """
        context: dict[str, Any] = {}

        # ---- 问题描述 ----
        if ctx.problem:
            context["problem_description"] = getattr(
                ctx.problem, "ques_all", str(ctx.problem)
            )
        elif ctx.coordinator_response:
            context["problem_description"] = str(
                ctx.coordinator_response
            )[:3000]
        else:
            context["problem_description"] = ""

        # ---- 建模结果 ----
        modeling_results: dict[str, Any] = {}

        if ctx.modeler_response:
            if hasattr(ctx.modeler_response, "__dict__"):
                modeling_results["modeler"] = str(
                    ctx.modeler_response.__dict__
                )[:3000]
            else:
                modeling_results["modeler"] = str(
                    ctx.modeler_response
                )[:3000]

        if ctx.coordinator_response:
            if hasattr(ctx.coordinator_response, "__dict__"):
                modeling_results["coordinator"] = str(
                    ctx.coordinator_response.__dict__
                )[:2000]
            else:
                modeling_results["coordinator"] = str(
                    ctx.coordinator_response
                )[:2000]

        # 已写论文章节列表（辅助信息）
        if ctx.user_output and hasattr(ctx.user_output, "res"):
            paper_sections = list(ctx.user_output.res.keys())
            if paper_sections:
                modeling_results["paper_sections"] = paper_sections

        context["modeling_results"] = modeling_results

        # ---- 求解结果（代码执行） ----
        if ctx.solution_results:
            code_results: dict[str, Any] = {}
            for key, value in ctx.solution_results.items():
                if key in ("flows", "config_template"):
                    continue
                if isinstance(value, dict):
                    code_results[key] = {
                        "success": value.get("success", False),
                        "code_output": str(
                            value.get("code_output", "")
                        )[:1500],
                    }
                else:
                    code_results[key] = str(value)[:1000]
            if code_results:
                context["code_results"] = code_results

        # ---- 验证报告 ----
        validation_report = ctx.artifacts.get(ArtifactKeys.VALIDATION_REPORT)
        if validation_report:
            context["validation_results"] = validation_report

        # ---- 创新点（来自 SmartModelerStage 的 InnovativeModelPlan） ----
        innovation = ctx.artifacts.get(ArtifactKeys.INNOVATIVE_MODEL_PLAN)
        if innovation:
            if isinstance(innovation, list):
                context["innovation_points"] = innovation
            elif isinstance(innovation, str):
                context["innovation_points"] = [innovation]
            else:
                # InnovativeModelPlan dataclass 或其他结构化对象：
                # 提取各类创新方案的描述信息
                points: list[str] = []
                for attr in (
                    "model_innovations",
                    "methodology_innovations",
                    "hybrid_approaches",
                ):
                    items = getattr(innovation, attr, None)
                    if isinstance(items, list):
                        points.extend(str(item) for item in items)
                if points:
                    context["innovation_points"] = points
                else:
                    # 兜底：将整个对象序列化为字符串
                    context["innovation_points"] = [
                        str(innovation)[:3000]
                    ]

        return context
