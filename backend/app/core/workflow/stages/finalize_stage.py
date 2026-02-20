"""
完成阶段 - 保存结果、生成 LaTeX、保存建模经验

职责:
  1. 保存 Markdown 结果到文件
  2. 如果用户选择 LaTeX 输出，生成 paper.tex
  3. 保存建模经验到记忆系统（可选）
  4. 发送完成统计消息
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.setting import settings
from app.core.paper.latex_export import generate_latex_from_markdown
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.schemas.enums import FormatOutPut
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class FinalizeStage:
    """完成阶段 - 保存结果"""

    @property
    def name(self) -> str:
        return "finalize"

    async def execute(self, ctx: PipelineContext) -> None:
        """保存结果并输出统计（错误处理层）"""
        try:
            await self._do_execute(ctx)
        except Exception:
            logger.error(
                "FinalizeStage 执行失败 [task_id=%s]",
                ctx.task_id,
                exc_info=True,
            )
            raise

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """保存结果并输出统计（业务逻辑）"""
        await ctx.send_progress("正在保存结果...", 96)

        # 保存 Markdown 结果
        ctx.user_output.save_result()

        # LaTeX 生成（条件触发）
        if (
            ctx.problem is not None
            and ctx.problem.format_output == FormatOutPut.LaTeX
        ):
            await self._generate_latex(ctx)

        # 记忆系统保存（可选，失败不中断）
        if settings.ENABLE_MEMORY_SYSTEM:
            await self._save_modeling_experience(ctx)

        # 输出统计
        elapsed = ctx.elapsed_minutes()

        # 包含评审结果（如果有）
        review_result = ctx.artifacts.get(ArtifactKeys.REVIEW_RESULT)
        review_info = ""
        if review_result and isinstance(review_result, dict):
            rating = review_result.get("overall_rating")
            if rating and rating > 0:
                review_info = f"，论文评审评分: {rating}/5"

        await redis_manager.publish_message(
            ctx.task_id,
            SystemMessage(
                content=f"任务完成! 总用时: {elapsed:.1f}分钟{review_info}",
                type="success",
            ),
        )
        logger.info("FinalizeStage 完成: 总用时 %.1f 分钟%s", elapsed, review_info)

    async def _generate_latex(self, ctx: PipelineContext) -> None:
        """生成 LaTeX 论文"""
        await ctx.send_progress("正在生成 LaTeX 论文...", 97)
        try:
            markdown_content = ctx.user_output.get_result_to_save()
            latex_path = f"{ctx.work_dir}/paper.tex"

            # 提取摘要和关键词（由 AbstractStage 写入 artifacts）
            abstract_text = ctx.artifacts.get(ArtifactKeys.ABSTRACT_CONTENT, "")
            keywords = ctx.artifacts.get(ArtifactKeys.KEYWORDS)

            generate_latex_from_markdown(
                markdown_content=markdown_content,
                output_path=latex_path,
                comp_template=ctx.problem.comp_template,
                title=ctx.problem.title,
                abstract=abstract_text,
                keywords=keywords,
                team_control_number=ctx.problem.team_control_number,
                problem_choice=ctx.problem.problem_choice,
            )
            await ctx.send_progress("LaTeX 论文生成完成", 98)
        except Exception as e:
            logger.error("[task_id=%s] LaTeX 生成失败: %s", ctx.task_id, e, exc_info=True)
            await redis_manager.publish_message(
                ctx.task_id,
                SystemMessage(
                    content=(
                        f"警告: LaTeX 生成失败，Markdown 结果已保存: "
                        f"{str(e)[:100]}"
                    ),
                    type="warning",
                ),
            )

    async def _save_modeling_experience(self, ctx: PipelineContext) -> None:
        """保存本次建模经验到记忆系统"""
        try:
            modeler_agent = ctx.agents.get("modeler")
            if not modeler_agent:
                return

            if not getattr(modeler_agent, "_memory_manager", None):
                return

            problem_desc = ctx.problem.ques_all[:1000] if ctx.problem else ""

            # 收集使用的模型方法
            models_used: list[str] = []
            if ctx.modeler_response:
                solutions = getattr(
                    ctx.modeler_response, "questions_solution", {}
                )
                if isinstance(solutions, dict):
                    models_used = list(solutions.keys())

            # 收集经验教训
            lessons: list[str] = []
            results = ctx.solution_results.get("results", {})
            failed = [k for k, v in results.items() if not v.get("success")]
            if failed:
                lessons.append(f"失败的子问题: {', '.join(failed)}")

            outcome = (
                "success" if len(failed) < len(results) * 0.3 else "partial"
            )

            # 构建解决方案摘要
            solution_approach = ""
            if ctx.modeler_response:
                solutions = getattr(
                    ctx.modeler_response, "questions_solution", {}
                )
                if isinstance(solutions, dict):
                    approach_parts = []
                    for key, val in solutions.items():
                        if isinstance(val, str):
                            approach_parts.append(f"{key}: {val[:200]}")
                    solution_approach = "; ".join(approach_parts)[:2000]

            await modeler_agent.save_experience(
                problem_type="math_modeling",
                problem_description=problem_desc,
                solution_approach=solution_approach,
                models_used=models_used,
                outcome=outcome,
                lessons=lessons,
            )
            logger.info(
                "记忆系统: 建模经验已保存 (outcome=%s)", outcome
            )

        except Exception as e:
            logger.warning("记忆系统: 保存建模经验失败（非关键）: %s", e)
