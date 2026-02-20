"""
论文写作阶段 - WriterAgent 撰写论文非求解部分

职责:
  1. 生成写作流程 (firstPage, RepeatQues, analysisQues 等)
  2. 按顺序让 WriterAgent 撰写每个章节
  3. 将撰写结果写入 UserOutput
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


def _format_sensitivity(sensitivity: dict) -> str:
    """格式化灵敏度分析结果为可读文本。"""
    parts: list[str] = []
    params = sensitivity.get("sensitive_parameters", [])
    if params:
        parts.append("敏感参数:")
        for p in params:
            if isinstance(p, dict):
                parts.append(
                    f"  - {p.get('name', '未知')}: {p.get('description', '')}"
                )
            else:
                parts.append(f"  - {p}")
    assessment = sensitivity.get("stability_assessment", "")
    if assessment:
        parts.append(f"稳定性评估: {assessment}")
    recommendations = sensitivity.get("recommendations", [])
    if recommendations:
        parts.append("建议:")
        for r in recommendations:
            parts.append(f"  - {r}")
    return "\n".join(parts) if parts else "灵敏度分析结果暂无详细内容"


class WriterStage:
    """论文写作阶段"""

    @property
    def name(self) -> str:
        return "write"

    async def execute(self, ctx: PipelineContext) -> None:
        """撰写论文非求解部分（错误处理层）"""
        try:
            await self._do_execute(ctx)
        except Exception:
            logger.error(
                "WriterStage 执行失败 [task_id=%s]",
                ctx.task_id,
                exc_info=True,
            )
            raise

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """撰写论文非求解部分（业务逻辑）"""
        await ctx.send_progress("正在撰写论文其他部分...", 75)

        solution_data = ctx.solution_results
        flows = solution_data["flows"]
        config_template = solution_data["config_template"]

        # NOTE: AWARD_CONTEXT 当前无生产者 Stage，预留给未来 AwardContextStage 扩展。
        #       当 AwardContextStage 上线后，在此处注入获奖补充要求到 write_flows。

        write_flows = flows.get_write_flows(
            ctx.user_output,
            config_template,
            ctx.problem.ques_all,
            comp_template=ctx.problem.comp_template,
        )

        # 注入评审反馈（如果有，来自上一轮评审）
        review_feedback = ctx.artifacts.get(ArtifactKeys.REVIEW_FEEDBACK)
        review_context = ""
        if review_feedback:
            suggestions = review_feedback.get("suggestions", [])
            if suggestions:
                suggestions_text = "\n".join(f"- {s}" for s in suggestions[:10])
                review_context = (
                    f"\n\n【评审改进建议】\n"
                    f"上一轮评审评分: {review_feedback.get('overall_rating', '未知')}/5\n"
                    f"改进建议:\n{suggestions_text}\n"
                    f"请在撰写时特别注意以上改进建议。\n"
                )
            logger.info(
                "WriterStage: 注入评审反馈 (评分=%s, %d 条建议)",
                review_feedback.get('overall_rating'),
                len(suggestions),
            )

        # 注入符号说明表（如果有，来自 SymbolTableStage）
        symbol_table_text = ctx.artifacts.get(ArtifactKeys.SYMBOL_TABLE_TEXT)
        if symbol_table_text and "symbolExplain" in write_flows:
            write_flows["symbolExplain"] += (
                f"\n\n【符号定义参考】\n"
                f"以下是从建模方案中提取的符号定义，请据此撰写符号说明章节：\n"
                f"{symbol_table_text}\n"
            )
            logger.info(
                "WriterStage: 注入符号说明表 (%d 字符)", len(symbol_table_text)
            )

        # 注入灵敏度分析结果（如果有，来自 ValidationStage）
        sensitivity = ctx.artifacts.get(ArtifactKeys.SENSITIVITY_ANALYSIS)
        if sensitivity:
            sensitivity_text = _format_sensitivity(sensitivity)
            # 尝试注入到模型检验相关章节
            for candidate_key in ("modelTest", "analysisQues", "judge"):
                if candidate_key in write_flows:
                    write_flows[candidate_key] += (
                        f"\n\n【灵敏度分析结果】\n{sensitivity_text}\n"
                        f"请在论文中体现灵敏度分析内容。\n"
                    )
                    logger.info(
                        "WriterStage: 注入灵敏度分析到 %s", candidate_key
                    )
                    break

        # 注入代码求解的结构化结果（如果有，来自 CoderStage）
        code_metrics = ctx.artifacts.get(ArtifactKeys.CODE_METRICS)
        code_figures = ctx.artifacts.get(ArtifactKeys.CODE_FIGURES)
        result_summaries = ctx.artifacts.get(ArtifactKeys.RESULT_SUMMARIES)

        if code_metrics or code_figures or result_summaries:
            # 构建聚合文本，注入到 judge（模型评价）和 firstPage（摘要）章节
            structured_text_parts: list[str] = []

            if code_metrics:
                structured_text_parts.append("各子问题模型评估指标:")
                for q_key, metrics in code_metrics.items():
                    metrics_str = ", ".join(
                        f"{k}={v:.4f}" for k, v in metrics.items()
                    )
                    structured_text_parts.append(f"  - {q_key}: {metrics_str}")

            if result_summaries:
                structured_text_parts.append("各子问题求解结论:")
                for q_key, summaries in result_summaries.items():
                    for s in summaries:
                        model = s.get("model", "未知")
                        conclusion = s.get("conclusion", "")
                        if conclusion:
                            structured_text_parts.append(
                                f"  - {q_key} (模型: {model}): {conclusion}"
                            )

            if code_figures:
                structured_text_parts.append("生成图表清单:")
                for q_key, figures in code_figures.items():
                    for fig in figures:
                        structured_text_parts.append(
                            f"  - {q_key}: {fig.get('filename', '')} "
                            f"({fig.get('description', '')})"
                        )

            structured_context = "\n".join(structured_text_parts)

            # 注入到 judge（模型评价）章节
            if "judge" in write_flows:
                write_flows["judge"] += (
                    f"\n\n【求解结果汇总】\n{structured_context}\n"
                    f"请在评价部分引用以上指标数据，给出客观的模型评价。\n"
                )

            # 注入到 firstPage（摘要）章节——提供关键结论供摘要参考
            if "firstPage" in write_flows and result_summaries:
                conclusions_text = "\n".join(
                    f"  - {q_key}: {s.get('conclusion', '')}"
                    for q_key, summaries in result_summaries.items()
                    for s in summaries
                    if s.get("conclusion")
                )
                if conclusions_text:
                    write_flows["firstPage"] += (
                        f"\n\n【各问题关键结论（供摘要参考）】\n{conclusions_text}\n"
                    )

            # 注入到 model_comparison（多模型对比）章节
            if "model_comparison" in write_flows and code_metrics:
                write_flows["model_comparison"] += (
                    "\n\n【模型评估指标汇总】\n"
                    + "\n".join(
                        f"  - {q_key}: "
                        + ", ".join(f"{k}={v:.4f}" for k, v in m.items())
                        for q_key, m in code_metrics.items()
                    )
                    + "\n请基于以上指标进行多模型对比分析。\n"
                )

            logger.info(
                "WriterStage: 注入结构化求解结果 "
                "(指标=%d题, 图表=%d题, 结论=%d题)",
                len(code_metrics) if code_metrics else 0,
                len(code_figures) if code_figures else 0,
                len(result_summaries) if result_summaries else 0,
            )

        # 注入验证报告摘要（如果有，来自 ValidationStage）
        validation_report = ctx.artifacts.get(ArtifactKeys.VALIDATION_REPORT)
        if validation_report:
            val_summary = validation_report.get("summary", "")
            val_metrics = validation_report.get("metrics", {})
            if val_summary or val_metrics:
                val_text = f"验证结论: {val_summary}\n"
                if val_metrics:
                    val_text += "关键指标:\n" + "\n".join(
                        f"  - {k}: {v}" for k, v in val_metrics.items()
                    )
                for candidate_key in ("modelTest", "judge"):
                    if candidate_key in write_flows:
                        write_flows[candidate_key] += (
                            f"\n\n【模型验证报告】\n{val_text}\n"
                        )
                        logger.info(
                            "WriterStage: 注入验证报告到 %s", candidate_key
                        )
                        break

        writer_agent = ctx.agents["writer"]
        total_write_steps = len(write_flows)
        step_idx = 0

        for key, value in write_flows.items():
            step_idx += 1
            progress = 75 + (step_idx / total_write_steps) * 20

            await ctx.send_progress(f"正在撰写: {key}", progress)

            try:
                # 如果有评审反馈，注入到每个写作 prompt 中
                if review_context:
                    value = value + review_context

                writer_response = await writer_agent.run(
                    prompt=value, sub_title=key
                )
                ctx.user_output.set_res(key, writer_response)
            except Exception as e:
                logger.error("[task_id=%s] 写作 %s 失败: %s", ctx.task_id, key, e, exc_info=True)
                await redis_manager.publish_message(
                    ctx.task_id,
                    SystemMessage(
                        content=f"警告: {key} 写作遇到问题",
                        type="warning",
                    ),
                )

        await ctx.send_progress("论文撰写完成", 95)
        logger.info("WriterStage 完成")
