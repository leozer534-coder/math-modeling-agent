"""
改进循环阶段 - 验证驱动的迭代改进

职责:
  1. 读取 ctx.artifacts["validation_report"] 的验证结果
  2. 如果验证未通过，提取改进建议
  3. 构造反馈 prompt 给 CoderAgent 重新求解
  4. 重新验证改进后的结果
  5. 最多迭代 MAX_ITERATIONS 次
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.core.workflow.stages.stage_constants import IMPROVEMENT_MAX_ITERATIONS
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class ImprovementLoopStage:
    """验证驱动的改进循环（可选阶段）"""

    MAX_ITERATIONS: int = IMPROVEMENT_MAX_ITERATIONS

    @property
    def name(self) -> str:
        return "improvement_loop"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行改进循环"""
        validation_report = ctx.artifacts.get(ArtifactKeys.VALIDATION_REPORT)
        if not validation_report:
            logger.info("ImprovementLoopStage: 无验证报告，跳过")
            return

        overall = validation_report.get("overall_assessment", {})
        status = overall.get("validation_status", "")

        if status == "通过":
            logger.info("ImprovementLoopStage: 验证已通过，无需改进")
            return

        await ctx.send_progress("检测到验证未通过，启动改进循环...", 74)

        # 提取改进建议
        recommendations = validation_report.get(
            "improvement_recommendations", []
        )
        if not recommendations:
            logger.info("ImprovementLoopStage: 无改进建议，跳过")
            return

        coder_agent = ctx.agents.get("coder")
        if coder_agent is None:
            logger.warning("ImprovementLoopStage: CoderAgent 不可用，跳过")
            return

        for iteration in range(self.MAX_ITERATIONS):
            await ctx.send_progress(
                f"改进迭代 {iteration + 1}/{self.MAX_ITERATIONS}...",
                74 + iteration,
            )

            # 构造改进 prompt
            improvement_prompt = self._build_improvement_prompt(
                validation_report, recommendations, iteration
            )

            try:
                # 使用 CoderAgent 执行改进代码
                improvement_response = await coder_agent.run(
                    prompt=improvement_prompt,
                    subtask_title=f"improvement_iter_{iteration + 1}",
                )

                logger.info(
                    "改进迭代 %d 完成: needs_remodel=%s",
                    iteration + 1,
                    getattr(improvement_response, 'needs_remodel', False),
                )

                # 重新验证（简化版：使用 LLM 评估改进效果）
                new_status = await self._quick_validate(
                    ctx, improvement_response, iteration
                )

                if new_status == "通过":
                    logger.info(
                        "改进迭代 %d: 验证通过，退出循环",
                        iteration + 1,
                    )
                    validation_report["overall_assessment"][
                        "validation_status"
                    ] = "通过"
                    validation_report["overall_assessment"][
                        "improvement_iterations"
                    ] = iteration + 1
                    break

            except Exception as e:
                logger.warning(
                    "改进迭代 %d 失败 [task_id=%s]: %s",
                    iteration + 1,
                    ctx.task_id,
                    e,
                )
                # 失败不中断，继续下一次迭代或退出

        await ctx.send_progress("改进循环完成", 75)
        logger.info("ImprovementLoopStage 完成")

    @staticmethod
    def _build_improvement_prompt(
        validation_report: dict[str, Any],
        recommendations: list[dict[str, Any]],
        iteration: int,
    ) -> str:
        """构造改进 prompt"""
        # 提取高优先级建议
        high_priority = [
            r
            for r in recommendations
            if r.get("priority", "").lower() in ("高", "high")
        ]
        if not high_priority:
            high_priority = recommendations[:3]

        suggestions = "\n".join(
            f"- [{r.get('category', '未分类')}] "
            f"{r.get('recommendation', '无具体建议')}"
            for r in high_priority
        )

        # 提取验证问题
        error_analysis = validation_report.get("error_analysis", {})
        error_patterns = error_analysis.get("error_patterns", [])
        patterns_text = "\n".join(
            f"- {p.get('pattern_type', '')}: {p.get('description', '')}"
            for p in error_patterns[:3]
        )

        return (
            f"# 模型改进任务（第 {iteration + 1} 轮）\n"
            f"\n"
            f"## 验证发现的问题\n"
            f"{patterns_text if patterns_text else '验证报告未详细列出具体问题模式'}\n"
            f"\n"
            f"## 改进建议\n"
            f"{suggestions}\n"
            f"\n"
            f"## 要求\n"
            f"1. 根据以上改进建议，修改和优化模型代码\n"
            f"2. 重点关注高优先级的改进项\n"
            f"3. 确保改进后的代码仍然能正确运行\n"
            f"4. 打印改进前后的指标对比\n"
            f"\n"
            f"请基于以上建议改进模型实现。\n"
        )

    @staticmethod
    async def _quick_validate(
        ctx: PipelineContext,
        improvement_response: Any,
        iteration: int,
    ) -> str:
        """快速验证改进效果（使用 LLM 近似评估）

        Returns:
            验证状态: "通过" / "有条件通过" / "未通过"
        """
        try:
            llm = ctx.llms.get("modeler")
            if llm is None:
                return "有条件通过"

            code_output = ""
            if hasattr(improvement_response, "code_response"):
                code_output = str(
                    improvement_response.code_response
                )[:2000]

            if not code_output:
                return "有条件通过"

            validate_prompt = (
                "请评估以下改进代码的执行结果，"
                "判断模型是否达到可接受水平。\n\n"
                f"代码执行输出:\n{code_output}\n\n"
                "请仅回答以下三个选项之一（不要回答其他内容）:\n"
                "- 通过\n"
                "- 有条件通过\n"
                "- 未通过\n"
            )

            response = await llm.ainvoke([
                SystemMessage(
                    content=(
                        "你是一个模型验证专家，"
                        "根据代码输出判断模型质量。"
                    ),
                ),
                HumanMessage(content=validate_prompt),
            ])

            result_text = response.content.strip()
            if "通过" in result_text and "未通过" not in result_text:
                return "通过"
            elif "有条件" in result_text:
                return "有条件通过"
            else:
                return "未通过"

        except Exception as e:
            logger.warning("快速验证失败: %s", e)
            return "有条件通过"
