"""
质量评审阶段 - Reviewer 对论文进行多维度评审

职责:
  1. 使用 Reviewer 对论文进行 5 维度评审
  2. 如果评分低于阈值，自动触发论文修订
  3. 将评审结果写入 ctx.artifacts["review_result"]
  4. 在 standard/enhanced 模式下为可选阶段，失败不中断主工作流
  5. 在 award 模式下为必选阶段，关键异常会向上传播
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from app.core.agents.reviewer import Reviewer
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.core.workflow.stages.stage_constants import (
    MAX_REVISE_ITERATIONS,
    REVIEW_QUALITY_THRESHOLD,
    REVIEW_WEAK_THRESHOLD,
)
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class ReviewStage:
    """质量评审阶段（可选/必选取决于工作流模式）"""

    QUALITY_THRESHOLD: int = REVIEW_QUALITY_THRESHOLD  # 评分阈值（1-5 分制）
    MAX_REVISE_ITERATIONS: int = MAX_REVISE_ITERATIONS

    @property
    def name(self) -> str:
        return "review"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行论文质量评审和条件修订。

        异常处理策略:
        - award 模式: 评审为必选阶段，异常记录后 re-raise，由 Pipeline 中断
        - 其他模式: 评审为可选阶段，异常时写入默认空反馈，Pipeline 可继续
        """
        try:
            await self._do_execute(ctx)
        except Exception as e:
            logger.error(
                "[task_id=%s] ReviewStage 执行失败: %s",
                ctx.task_id,
                e,
                exc_info=True,
            )
            logger.debug(
                "ReviewStage 异常堆栈:\n%s", traceback.format_exc()
            )

            # 发送错误进度消息，让前端感知
            await ctx.send_progress(
                f"论文质量评审异常: {str(e)[:100]}", 96
            )

            # 写入默认空 artifact，确保下游阶段不会因缺少键而崩溃
            self._write_default_artifacts(ctx)

            # award 模式下评审为必选阶段，异常不可吞掉
            if ctx.workflow_mode == "award":
                logger.error(
                    "Award 模式下评审阶段失败，中断 Pipeline",
                    extra={"task_id": ctx.task_id},
                )
                raise
            else:
                logger.warning(
                    "非 award 模式下评审失败，已写入默认空反馈，"
                    "Pipeline 继续执行 (task_id=%s)",
                    ctx.task_id,
                )

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """评审核心逻辑（从 execute 中拆出，便于统一异常包裹）。"""
        await ctx.send_progress("正在进行论文质量评审...", 95)

        reviewer = Reviewer(
            task_id=ctx.task_id,
            model=ctx.llms["writer"],
        )
        await reviewer.setup()

        # 收集论文内容作为评审输入
        paper_content = ctx.user_output.get_result_to_save()
        modeling_results = {
            "paper_content": paper_content[:6000],
            "sections": list(ctx.user_output.res.keys()),
            "ques_count": ctx.ques_count,
        }

        # 注入一致性检查结果（如果有，来自 ConsistencyCheckStage）
        consistency_issues = ctx.artifacts.get(ArtifactKeys.CONSISTENCY_ISSUES)
        if consistency_issues:
            issues_list = consistency_issues.get("issues", [])
            if issues_list:
                modeling_results["consistency_issues"] = issues_list[:10]
                logger.info(
                    "ReviewStage: 注入 %d 条一致性检查问题", len(issues_list)
                )

        quality_review = await reviewer.execute(
            modeling_results=modeling_results
        )

        # 转为字典
        review_dict = quality_review.__dict__
        review_status = review_dict.get("review_status")
        if hasattr(review_status, "value"):
            review_dict["review_status"] = review_status.value

        overall_rating = review_dict.get("overall_rating", 3)

        await ctx.send_progress(
            f"论文质量评审完成，综合评分: {overall_rating}/5", 96
        )
        logger.info(
            "论文评审完成: 评分=%s, 状态=%s",
            overall_rating,
            review_dict.get('review_status'),
        )

        ctx.artifacts[ArtifactKeys.REVIEW_RESULT] = review_dict

        # 提取改进建议供 WriterStage 使用
        improvement_suggestions = []
        for key in ("writing_quality", "content_quality", "methodology_quality"):
            section = review_dict.get(key, {})
            if isinstance(section, dict):
                suggestions = section.get("suggestions", [])
                if suggestions:
                    improvement_suggestions.extend(suggestions)

        if improvement_suggestions or overall_rating < self.QUALITY_THRESHOLD:
            ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK] = {
                "overall_rating": overall_rating,
                "suggestions": improvement_suggestions,
                "review_status": review_dict.get("review_status", ""),
            }

            # award 模式下低分触发全面重写标记
            if (
                ctx.workflow_mode == "award"
                and overall_rating < self.QUALITY_THRESHOLD - 1
            ):
                ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK]["needs_full_rewrite"] = True
                logger.warning(
                    "Award 模式下评分过低 (%s/5)，标记需要全面重写",
                    overall_rating,
                )

        # 条件触发修订
        if overall_rating < self.QUALITY_THRESHOLD:
            await self._revise_paper(ctx, review_dict)

    @staticmethod
    def _write_default_artifacts(ctx: PipelineContext) -> None:
        """写入默认的空评审 artifact，防止下游阶段因缺少键而崩溃。"""
        if ArtifactKeys.REVIEW_RESULT not in ctx.artifacts:
            ctx.artifacts[ArtifactKeys.REVIEW_RESULT] = {
                "overall_rating": 0,
                "review_status": "error",
                "error": "评审阶段执行异常，未能完成评审",
            }
        if ArtifactKeys.REVIEW_FEEDBACK not in ctx.artifacts:
            ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK] = {
                "overall_rating": 0,
                "suggestions": [],
                "review_status": "error",
            }

    async def _revise_paper(
        self, ctx: PipelineContext, review_result: dict
    ) -> None:
        """根据评审反馈修订薄弱章节"""
        overall_rating = review_result.get("overall_rating", 5)
        review_status = review_result.get("review_status", "")

        await ctx.send_progress(
            f"论文评分 {overall_rating}/5（{review_status}），"
            f"正在自动修订...",
            96,
        )

        writer_agent = ctx.agents["writer"]
        weakest_sections = self._identify_weakest_sections(
            ctx, review_result
        )

        if not weakest_sections:
            logger.info("未识别到需要修订的具体章节，跳过修订")
            return

        for iteration in range(self.MAX_REVISE_ITERATIONS):
            logger.info(
                "修订迭代 %d/%d，修订章节: %s",
                iteration + 1,
                self.MAX_REVISE_ITERATIONS,
                weakest_sections,
            )

            revised_count = 0
            for section_key in weakest_sections:
                if section_key not in ctx.user_output.res:
                    continue

                original = ctx.user_output.res[section_key]
                original_content = original.get("response_content", "")
                if not original_content:
                    continue

                try:
                    await ctx.send_progress(
                        f"正在修订章节: {section_key} "
                        f"(迭代 {iteration + 1}/{self.MAX_REVISE_ITERATIONS})",
                        96,
                    )

                    revised_response = await writer_agent.revise(
                        original_content=original_content,
                        review_feedback=review_result,
                        section_key=section_key,
                    )
                    ctx.user_output.set_res(section_key, revised_response)
                    revised_count += 1
                    logger.info("章节 %s 修订完成", section_key)

                except Exception as e:
                    logger.warning("修订章节 %s 失败: %s", section_key, e)

            if revised_count == 0:
                logger.info("没有章节被成功修订，停止迭代")
                break

        await ctx.send_progress("论文修订完成", 97)

    def _identify_weakest_sections(
        self, ctx: PipelineContext, review_result: dict
    ) -> list[str]:
        """根据评审结果识别最弱的章节（最多 3 个）"""
        section_scores: dict[str, float] = {}

        writing_avg = review_result.get("writing_quality", {}).get(
            "average_score", 5
        )
        content_avg = review_result.get("content_quality", {}).get(
            "average_score", 5
        )
        methodology_avg = review_result.get("methodology_quality", {}).get(
            "average_score", 5
        )
        innovation_avg = review_result.get("innovation_assessment", {}).get(
            "average_score", 5
        )

        section_mapping: dict[str, float] = {
            "analysisQues": content_avg,
            "modelAssumption": content_avg,
            "RepeatQues": writing_avg,
            "firstPage": writing_avg,
            "judge": max(methodology_avg, innovation_avg),
            "conclusion": writing_avg,
        }

        for key in ctx.user_output.res:
            if key.startswith("ques") and key != "ques_count":
                section_mapping[key] = methodology_avg

        weak_threshold = REVIEW_WEAK_THRESHOLD
        for section, score in section_mapping.items():
            if score < weak_threshold and section in ctx.user_output.res:
                section_scores[section] = score

        sorted_sections = sorted(
            section_scores.keys(),
            key=lambda k: section_scores[k],
        )
        return sorted_sections[:3]
