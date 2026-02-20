"""Workflow stages for mathematical modeling.

Pipeline 架构阶段 — 遵循 Stage Protocol，接收 PipelineContext 作为 execute 参数。
由 WorkflowPipeline + configs.py 组装使用。

NOTE: 旧架构 Stage（继承 BaseStage，被 WorkflowEngine 使用）的源文件仍保留在目录中
      （analysis.py / coding.py / modeling.py / validation.py / writing.py），
      但不再从包级别导出。如需使用请直接 import 对应文件。
"""

# ---- Pipeline 架构阶段 ----
from app.core.workflow.stages.abstract_stage import AbstractStage
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
from app.core.workflow.stages.review_stage import ReviewStage
from app.core.workflow.stages.setup_stage import SetupStage
from app.core.workflow.stages.smart_modeler_stage import SmartModelerStage
from app.core.workflow.stages.symbol_table_stage import SymbolTableStage
from app.core.workflow.stages.validation_stage import ValidationStage
from app.core.workflow.stages.writer_stage import WriterStage


__all__ = [
    'AbstractStage',
    'CoderStage',
    'ConsistencyCheckStage',
    'CoordinatorStage',
    'DataPreviewStage',
    'EDAStage',
    'FinalizeStage',
    'ImprovementLoopStage',
    'ModelSelectionStage',
    'ModelerStage',
    'ProblemAnalysisStage',
    'ReviewStage',
    'SetupStage',
    'SmartModelerStage',
    'SymbolTableStage',
    'ValidationStage',
    'WriterStage',
]
