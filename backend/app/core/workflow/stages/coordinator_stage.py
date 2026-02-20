"""
协调者阶段 - 分析问题并拆分子问题

职责:
  1. 创建 LLMFactory 和所有 LLM 实例
  2. 运行 CoordinatorAgent 解析用户问题
  3. 将 questions / ques_count / coordinator_response 写入上下文
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.agents import CoordinatorAgent
from app.core.llm.llm_factory import LLMFactory
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class CoordinatorStage:
    """任务分析阶段"""

    @property
    def name(self) -> str:
        return "coordinate"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行协调者分析

        创建 LLM 实例并运行 CoordinatorAgent，
        将分析结果写入 PipelineContext。
        """
        try:
            await ctx.send_progress("正在分析问题...", 5)

            # 创建 LLM 工厂和所有实例
            llm_factory = LLMFactory(ctx.task_id, ctx.agent_configs)
            ctx.llm_factory = llm_factory

            coordinator_llm, modeler_llm, coder_llm, writer_llm = (
                llm_factory.get_all_llms()
            )
            ctx.llms = {
                "coordinator": coordinator_llm,
                "modeler": modeler_llm,
                "coder": coder_llm,
                "writer": writer_llm,
            }

            # 构建问题输入
            problem_input = ctx.problem.ques_all
            # NOTE: RESEARCH_REPORT 当前无生产者 Stage，预留给未来 ResearchStage 扩展。
            #       当 ResearchStage 上线后，在此处消费 ctx.artifacts[ArtifactKeys.RESEARCH_REPORT]。

            # 运行协调者
            coordinator = CoordinatorAgent(ctx.task_id, coordinator_llm)
            ctx.agents["coordinator"] = coordinator

            response = await coordinator.run(problem_input)

            ctx.coordinator_response = response
            ctx.questions = response.questions
            ctx.ques_count = response.ques_count

            await ctx.send_progress(
                f"问题分析完成，共 {ctx.ques_count} 个子问题", 15
            )
            logger.info(
                "CoordinatorStage 完成 [task_id=%s]: %s 个子问题",
                ctx.task_id,
                ctx.ques_count,
            )
        except Exception as e:
            logger.error(
                "CoordinatorStage 执行失败 [task_id=%s]: %s",
                ctx.task_id,
                e,
                exc_info=True,
            )
            await ctx.send_progress(
                f"问题分析失败: {type(e).__name__}", 0
            )
            raise
