"""
工作流管线配置模块

根据不同的工作流模式 (standard / enhanced / award)
返回对应的 StageConfig 列表，供 WorkflowPipeline.create() 使用。

设计原则:
  - 每种模式是一个独立函数，返回 StageConfig 列表
  - 增强模式在标准模式基础上叠加，避免重复定义
  - 获奖模式在增强模式基础上调整参数
  - 所有阶段的进度区间、超时、是否可选在此集中配置
"""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from app.core.workflow.pipeline import StageConfig
from app.core.workflow.stages.coder_stage import CoderStage
from app.core.workflow.stages.consistency_check_stage import ConsistencyCheckStage
from app.core.workflow.stages.coordinator_stage import CoordinatorStage
from app.core.workflow.stages.data_preview_stage import DataPreviewStage
from app.core.workflow.stages.eda_stage import EDAStage
from app.core.workflow.stages.finalize_stage import FinalizeStage
from app.core.workflow.stages.improvement_loop_stage import ImprovementLoopStage
from app.core.workflow.stages.model_selection_stage import ModelSelectionStage
from app.core.workflow.stages.modeler_stage import ModelerStage
from app.core.workflow.stages.problem_analysis_stage import ProblemAnalysisStage
from app.core.workflow.stages.smart_modeler_stage import SmartModelerStage
from app.core.workflow.stages.symbol_table_stage import SymbolTableStage
from app.core.workflow.stages.abstract_stage import AbstractStage
from app.core.workflow.stages.review_stage import ReviewStage
from app.core.workflow.stages.setup_stage import SetupStage
from app.core.workflow.stages.validation_stage import ValidationStage
from app.core.workflow.stages.writer_stage import WriterStage


# 默认单阶段超时（秒）
_DEFAULT_STAGE_TIMEOUT: float = 600.0
# DataPreview 阶段超时（较短，因为只是文件扫描）
_DATA_PREVIEW_TIMEOUT: float = 120.0
# ConsistencyCheck 阶段超时（纯文本分析，不调用 LLM，较短）
_CONSISTENCY_CHECK_TIMEOUT: float = 60.0


def get_pipeline_config(
    workflow_mode: str,
    **kwargs,
) -> list[StageConfig]:
    """根据工作流模式返回阶段配置列表

    这是 WorkflowPipeline.create() 调用的唯一入口。
    新增工作流模式时，只需在此添加对应的配置函数。

    Args:
        workflow_mode: 工作流模式 (standard / enhanced / award)
        **kwargs: 可选参数
            - stage_timeout: 覆盖默认的单阶段超时（秒）

    Returns:
        StageConfig 列表，WorkflowPipeline 将按顺序执行
    """
    builders: dict[str, Callable[..., list[StageConfig]]] = {
        "standard": _standard_config,
        "enhanced": _enhanced_config,
        "award": _award_config,
    }
    builder = builders.get(workflow_mode, _standard_config)
    return builder(**kwargs)


# ==================== 标准模式 ====================


def _standard_config(**kwargs) -> list[StageConfig]:
    """标准工作流配置

    流程:
      Coordinator -> Setup -> DataPreview(可选) -> EDA
      -> ProblemAnalysis(可选) -> Modeler -> Coder -> Writer
      -> Review(可选) -> Finalize

    这是最基础的工作流，对应原 MathModelWorkFlow 的核心路径。
    """
    timeout = kwargs.get("stage_timeout", _DEFAULT_STAGE_TIMEOUT)

    return [
        # 1. 协调者分析问题、创建 LLM
        StageConfig(
            stage_class=CoordinatorStage,
            progress_start=0,
            progress_end=15,
            timeout=timeout,
        ),
        # 2. 环境设置（CodeInterpreter、Agent 实例、UserOutput）
        StageConfig(
            stage_class=SetupStage,
            progress_start=16,
            progress_end=20,
            timeout=timeout,
        ),
        # 3. 数据预览（可选，失败不中断）
        StageConfig(
            stage_class=DataPreviewStage,
            optional=True,
            progress_start=18,
            progress_end=19,
            timeout=_DATA_PREVIEW_TIMEOUT,
        ),
        # 4. EDA 数据探索
        StageConfig(
            stage_class=EDAStage,
            progress_start=21,
            progress_end=28,
            timeout=timeout,
        ),
        # 4.5 问题深度分析（可选，失败不中断）
        StageConfig(
            stage_class=ProblemAnalysisStage,
            optional=True,
            progress_start=29,
            progress_end=30,
            timeout=timeout,
        ),
        # 4.6 模型智能选择（可选，失败不中断）
        StageConfig(
            stage_class=ModelSelectionStage,
            optional=True,
            progress_start=31,
            progress_end=33,
            timeout=timeout,
        ),
        # 4.7 创新建模方案（可选，仅 award 模式实际执行）
        StageConfig(
            stage_class=SmartModelerStage,
            optional=True,
            progress_start=34,
            progress_end=36,
            timeout=timeout,
        ),
        # 5. 建模方案设计
        StageConfig(
            stage_class=ModelerStage,
            progress_start=37,
            progress_end=42,
            timeout=timeout,
        ),
        # 5.5 符号表自动提取（可选，失败不中断）
        StageConfig(
            stage_class=SymbolTableStage,
            optional=True,
            progress_start=42,
            progress_end=43,
            timeout=timeout,
        ),
        # 6. 代码求解（含反馈环路，内部有子任务超时控制，不设整体超时）
        StageConfig(
            stage_class=CoderStage,
            progress_start=43,
            progress_end=68,
            timeout=0,
        ),
        # 6.5 结果验证（可选，失败不中断）
        StageConfig(
            stage_class=ValidationStage,
            optional=True,
            progress_start=69,
            progress_end=72,
            timeout=timeout,
        ),
        # 6.6 改进循环（可选，失败不中断）
        StageConfig(
            stage_class=ImprovementLoopStage,
            optional=True,
            progress_start=73,
            progress_end=75,
            timeout=timeout,
        ),
        # 7. 论文写作（非求解部分）
        StageConfig(
            stage_class=WriterStage,
            progress_start=76,
            progress_end=89,
            timeout=timeout,
        ),
        # 7.5 摘要独立生成（可选，失败不中断）
        StageConfig(
            stage_class=AbstractStage,
            optional=True,
            progress_start=89,
            progress_end=91,
            timeout=timeout,
        ),
        # 7.6 质量评审（可选，失败不中断）
        StageConfig(
            stage_class=ReviewStage,
            optional=True,
            progress_start=91,
            progress_end=96,
            timeout=timeout,
        ),
        # 8. 保存结果、LaTeX 生成、记忆系统
        StageConfig(
            stage_class=FinalizeStage,
            progress_start=97,
            progress_end=100,
            timeout=timeout,
        ),
    ]


# ==================== 增强模式 ====================


def _enhanced_config(**kwargs) -> list[StageConfig]:
    """增强工作流配置

    在标准配置基础上增加:
      - ConsistencyCheckStage: 全文一致性检查（ReviewStage 之前）

    标准配置已包含 ReviewStage（可选），增强模式在其前插入一致性检查。
    插入后顺序: Writer -> ConsistencyCheck -> Review -> Finalize

    对应原 EnhancedMathModelWorkFlow 的核心路径。
    """
    stages = _standard_config(**kwargs)

    # 找到 ReviewStage 的位置，在其前插入 ConsistencyCheckStage
    review_idx = next(
        i for i, s in enumerate(stages) if s.stage_class is ReviewStage
    )

    consistency_config = StageConfig(
        stage_class=ConsistencyCheckStage,
        optional=True,
        progress_start=91,
        progress_end=93,
        timeout=_CONSISTENCY_CHECK_TIMEOUT,
    )
    stages.insert(review_idx, consistency_config)

    # 调整后续阶段的进度区间（ConsistencyCheck 插入后各阶段后移一位）
    # 使用 replace() 创建副本，避免污染 _standard_config 返回的原始对象
    # ReviewStage 现在在 review_idx + 1
    stages[review_idx + 1] = replace(
        stages[review_idx + 1], progress_start=93, progress_end=96
    )
    # FinalizeStage 现在在 review_idx + 2
    stages[review_idx + 2] = replace(
        stages[review_idx + 2], progress_start=97, progress_end=100
    )

    return stages


# ==================== 获奖模式 ====================


def _award_config(**kwargs) -> list[StageConfig]:
    """获奖级工作流配置

    在增强配置基础上:
      - ReviewStage 设为必选（获奖级论文必须通过质量评审）
      - 使用更宽松的超时以允许更深入的分析

    对应原 AwardWinningWorkflow 的核心路径。
    未来可在此扩展 ResearchStage、AssumptionStage 等获奖级专属阶段。
    """
    # 获奖模式默认使用更长的超时
    if "stage_timeout" not in kwargs:
        kwargs["stage_timeout"] = 900.0

    stages = _enhanced_config(**kwargs)

    # 获奖模式下以下阶段设为必选
    # 使用 replace() 创建副本，避免直接变异 StageConfig 实例
    _award_required_stages = (
        ReviewStage,
        ValidationStage,
        ModelSelectionStage,
        SmartModelerStage,  # 创新建模方案是获奖关键
    )
    for i, config in enumerate(stages):
        if config.stage_class in _award_required_stages:
            stages[i] = replace(config, optional=False)

    return stages
