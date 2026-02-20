"""
问题分析阶段 - 使用 ProblemAnalyzer 深度分析问题

职责:
  1. 使用 ProblemAnalyzer 对问题进行深度分析
  2. 输出问题类型、难度、建模目标等结构化信息
  3. 将分析结果写入 ctx.artifacts["problem_analysis"]
  4. 供后续 ModelerStage 使用
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.agents.problem_analyzer import ProblemAnalyzer
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.log_util import logger

if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class ProblemAnalysisStage:
    """问题深度分析阶段（Pipeline 架构）"""

    @property
    def name(self) -> str:
        return "problem_analysis"

    async def execute(self, ctx: PipelineContext) -> None:
        """运行 ProblemAnalyzer 分析问题"""
        await ctx.send_progress("正在深度分析问题...", 29)

        try:
            # 复用 modeler LLM 实例（节省资源）
            analyzer = ProblemAnalyzer(
                task_id=ctx.task_id,
                model=ctx.llms["modeler"],
            )
            await analyzer.setup()

            # 执行分析
            problem_analysis = await analyzer.execute(
                coordinator_data=ctx.coordinator_response
            )

            # 将分析结果存入 artifacts
            ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = problem_analysis

            # 提取关键信息供下游使用
            if hasattr(problem_analysis, "problem_type"):
                ctx.artifacts[ArtifactKeys.PROBLEM_TYPE] = problem_analysis.problem_type
            if hasattr(problem_analysis, "recommended_approaches"):
                ctx.artifacts[ArtifactKeys.RECOMMENDED_APPROACHES] = (
                    problem_analysis.recommended_approaches
                )

            await analyzer.cleanup()
            logger.info(
                "ProblemAnalysisStage 完成: 问题类型=%s",
                getattr(problem_analysis, 'problem_type', 'unknown'),
            )

        except Exception as e:
            logger.warning(
                "ProblemAnalysisStage 失败（非关键）[task_id=%s]: %s",
                ctx.task_id,
                e,
            )
            # 设为 optional 阶段，失败不中断
            ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = None

        await ctx.send_progress("问题分析完成", 30)
