"""
模型选择阶段 - ModelSelector 智能推荐最优模型

职责:
  1. 读取问题分析结果 (ProblemAnalysis)
  2. 使用 ModelSelector 分析问题特征并推荐模型
  3. 将推荐结果写入 ctx.artifacts 供后续 ModelerStage 参考
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.agents.model_selector import ModelSelector
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.log_util import logger

if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class ModelSelectionStage:
    """模型智能选择阶段（可选，失败不中断主工作流）"""

    @property
    def name(self) -> str:
        return "model_selection"

    async def execute(self, ctx: PipelineContext) -> None:
        """运行 ModelSelector 推荐最优数学模型"""
        await ctx.send_progress("正在智能选择最优模型...", 31)

        try:
            # 读取上游问题分析结果
            problem_analysis = ctx.artifacts.get(ArtifactKeys.PROBLEM_ANALYSIS)
            if problem_analysis is None:
                logger.info(
                    "ModelSelectionStage 跳过: "
                    "上游 problem_analysis 为空"
                )
                await ctx.send_progress("跳过模型选择（无问题分析）", 33)
                return

            # 复用 modeler LLM 实例
            selector = ModelSelector(
                task_id=ctx.task_id,
                model=ctx.llms["modeler"],
            )
            await selector.setup()

            # 执行模型选择（接受 ProblemAnalysis dataclass）
            recommendation = await selector.execute(problem_analysis)

            # 防御性检查: selector.execute() 应返回 ModelRecommendation,
            # 但 LLM 数据链路不可控，需要验证返回值
            if recommendation is None:
                logger.warning(
                    "ModelSelector 返回 None [task_id=%s]",
                    ctx.task_id,
                )
                ctx.artifacts[ArtifactKeys.MODEL_RECOMMENDATION] = None
                ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL] = None
                await ctx.send_progress("模型选择完成（无推荐结果）", 33)
                return

            # 将完整推荐结果存入 artifacts
            ctx.artifacts[ArtifactKeys.MODEL_RECOMMENDATION] = recommendation

            # 提取主推荐模型名称供下游快速访问
            # primary_model 来自 LLM JSON 解析，可能不是 dict 或为 None
            primary_model = getattr(recommendation, "primary_model", None)
            if isinstance(primary_model, dict):
                primary_name = primary_model.get("name", "未知模型")
            elif primary_model is not None:
                # primary_model 存在但不是 dict（如 str），尝试提取可用信息
                logger.warning(
                    "primary_model 类型异常: expected dict, got %s "
                    "[task_id=%s]",
                    type(primary_model).__name__,
                    ctx.task_id,
                )
                primary_name = str(primary_model) if primary_model else "未知模型"
            else:
                primary_name = "未知模型"

            ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL] = primary_name

            logger.info(
                "ModelSelectionStage 完成: 主推荐模型=%s [task_id=%s]",
                primary_name,
                ctx.task_id,
            )

        except Exception as e:
            logger.error(
                "ModelSelectionStage 执行失败: %s [task_id=%s]",
                e,
                ctx.task_id,
            )
            # award 模式下此 Stage 是必选的，必须传播异常
            if ctx.workflow_mode == "award":
                raise
            # 其他模式下是可选的，记录警告并继续
            logger.warning(
                "ModelSelectionStage 为可选阶段，跳过失败继续执行"
            )
            ctx.artifacts[ArtifactKeys.MODEL_RECOMMENDATION] = None
            ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL] = None

        await ctx.send_progress("模型选择完成", 33)
