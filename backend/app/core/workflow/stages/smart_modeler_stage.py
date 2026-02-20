"""
创新建模阶段 - SmartModelerWithInnovation 增强建模方案

职责:
  1. 仅在 award 模式下执行
  2. 基于问题分析和模型推荐，设计创新性建模方案
  3. 输出模型改进、混合策略和方法论创新建议
  4. 供后续 ModelerStage 参考以提升方案质量
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from app.core.agents.smart_modeler_with_innovation import (
    SmartModelerWithInnovation,
)
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.log_util import logger

if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class SmartModelerStage:
    """创新建模方案设计阶段（仅 award 模式）"""

    @property
    def name(self) -> str:
        return "smart_modeler"

    async def execute(self, ctx: PipelineContext) -> None:
        """基于问题分析和模型推荐，设计创新性建模方案。

        仅在 award 模式下执行；其他模式直接跳过。
        整个阶段用 try/except 包裹，失败时仅打印警告日志并跳过，
        不中断主工作流。
        """
        # ---- 模式检查: 仅 award 模式执行 ----
        if ctx.workflow_mode != "award":
            logger.info(
                "SmartModelerStage 跳过: 当前模式为 %s，非 award 模式",
                ctx.workflow_mode,
            )
            return

        await ctx.send_progress("正在设计创新建模方案...", 34)

        try:
            # ---- 组装 problem_analysis ----
            problem_analysis = self._to_dict(
                ctx.artifacts.get(ArtifactKeys.PROBLEM_ANALYSIS)
            )

            # ---- 组装 data_insight ----
            data_insight = self._build_data_insight(ctx)

            # ---- 组装 model_recommendation ----
            model_recommendation = self._to_dict(
                ctx.artifacts.get(ArtifactKeys.MODEL_RECOMMENDATION)
            )

            # ---- 创建 SmartModeler 并执行 ----
            smart_modeler = SmartModelerWithInnovation(
                task_id=ctx.task_id,
                model=ctx.llms["modeler"],
            )

            innovative_plan = await smart_modeler.execute(
                problem_analysis=problem_analysis,
                data_insight=data_insight,
                model_recommendation=model_recommendation,
            )

            # 将结果写入 artifacts 供后续 ModelerStage 参考
            ctx.artifacts[ArtifactKeys.INNOVATIVE_MODEL_PLAN] = innovative_plan

            innovations_count = len(
                getattr(innovative_plan, "model_innovations", [])
            )
            logger.info(
                "SmartModelerStage 完成 [task_id=%s]: 创新方案数=%d",
                ctx.task_id,
                innovations_count,
            )
            await ctx.send_progress(
                f"创新建模方案设计完成（{innovations_count} 个创新方向）",
                36,
            )

        except Exception as e:
            logger.warning(
                "SmartModelerStage 失败（非关键，跳过）[task_id=%s]: %s",
                ctx.task_id,
                e,
            )
            await ctx.send_progress("创新建模方案设计跳过", 36)

    # ------------------------------------------------------------------ #
    #                         私有辅助方法                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        """将对象安全转换为 dict。

        支持 dataclass、具有 __dict__ 的普通对象以及已经是 dict 的情况。
        如果传入 None 或不可转换的类型，返回空字典。
        """
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if hasattr(obj, "__dict__"):
            return dict(obj.__dict__)
        return {}

    @staticmethod
    def _build_data_insight(ctx: PipelineContext) -> dict[str, Any]:
        """从 ctx.artifacts 中组装 data_insight 字典。

        优先使用结构化的 eda_data_summary，兜底使用 eda_result 文本。
        """
        data_insight: dict[str, Any] = {}

        # 结构化 EDA 摘要
        eda_data_summary = ctx.artifacts.get(ArtifactKeys.EDA_DATA_SUMMARY)
        if eda_data_summary is not None:
            if dataclasses.is_dataclass(eda_data_summary) and not isinstance(
                eda_data_summary, type
            ):
                data_insight["eda_data_summary"] = dataclasses.asdict(
                    eda_data_summary
                )
            elif isinstance(eda_data_summary, dict):
                data_insight["eda_data_summary"] = eda_data_summary
            elif hasattr(eda_data_summary, "__dict__"):
                data_insight["eda_data_summary"] = dict(
                    eda_data_summary.__dict__
                )

        # EDA 执行结果文本
        eda_result = ctx.artifacts.get(ArtifactKeys.EDA_RESULT)
        if eda_result:
            data_insight["eda_result"] = (
                str(eda_result)[:3000] if eda_result else ""
            )

        # 原始数据文件摘要
        data_summary = ctx.artifacts.get(ArtifactKeys.DATA_SUMMARY)
        if data_summary:
            data_insight["data_summary"] = (
                str(data_summary)[:2000] if data_summary else ""
            )

        return data_insight
