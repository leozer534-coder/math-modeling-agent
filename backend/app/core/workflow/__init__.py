"""Workflow module for mathematical modeling.

WorkflowPipeline (统一架构) - Pipeline + Stage 统一管线，使用 PipelineContext。
推荐使用 WorkflowPipeline.create(mode) 作为统一入口。

NOTE: WorkflowEngine（旧架构）源文件仍保留在 engine.py 中，
      但不再从包级别导出。如需使用请直接 import。
"""

from app.core.workflow.checkpoints import CheckpointManager, get_checkpoint_manager

# 向后兼容: modeling_router 等模块通过 app.core.workflow 导入 MathModelWorkFlow
from app.core.math_model_workflow import MathModelWorkFlow

# Pipeline 统一架构
from app.core.workflow.pipeline import (
    PipelineContext,
    Stage,
    StageConfig,
    StageResult,
    WorkflowPipeline,
)
from app.core.workflow.state import (
    IterationDecision,
    WorkflowContext,
    WorkflowServiceContainer,
    WorkflowStage,
)
from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType


__all__ = [
    # 向后兼容
    'MathModelWorkFlow',
    # Pipeline 统一架构
    'WorkflowPipeline',
    'PipelineContext',
    'Stage',
    'StageConfig',
    'StageResult',
    # 状态管理
    'WorkflowContext',
    'WorkflowServiceContainer',
    'WorkflowStage',
    'IterationDecision',
    # 检查点
    'CheckpointManager',
    'get_checkpoint_manager',
    # 工作流选择
    'WorkflowSelector',
    'WorkflowType',
]
