from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.utils.log_util import logger

from app.core.agents.data_understanding_expert import DataInsight
from app.core.agents.experiment_designer import ExperimentPlan
from app.core.agents.expert_agent import QualityLevel
from app.core.agents.model_selector import ModelRecommendation
from app.core.agents.problem_analyzer import ProblemAnalysis
from app.core.agents.reviewer import QualityReview
from app.core.agents.smart_modeler_with_innovation import InnovativeModelPlan
from app.core.agents.validation_expert import ValidationReport
from app.schemas.A2A import CoordinatorToModeler


class WorkflowStage(Enum):
    """工作流阶段"""
    PROBLEM_ANALYSIS = "问题分析"
    MODEL_SELECTION = "模型选择"
    EXPERIMENT_DESIGN = "实验设计"
    CODE_IMPLEMENTATION = "代码实现"
    MODEL_VALIDATION = "模型验证"
    QUALITY_REVIEW = "质量评审"
    PAPER_WRITING = "论文写作"
    COMPLETED = "完成"
    FAILED = "失败"


class IterationDecision(Enum):
    """迭代决策"""
    CONTINUE = "继续下一阶段"
    ITERATE = "迭代优化当前阶段"
    ROLLBACK = "回退上一阶段"
    TERMINATE = "终止流程"


@dataclass
class WorkflowContext:
    """
    工作流上下文 - 跨阶段共享的纯数据对象

    设计原则: 只存储可序列化的阶段产物数据，
    不持有活跃服务对象 (CoderAgent / CodeInterpreter 等)。
    服务对象由 WorkflowServiceContainer 管理。
    """
    task_id: str
    coordinator_data: CoordinatorToModeler
    current_stage: WorkflowStage
    iteration_count: int = 0
    max_iterations: int = 3

    # 各阶段结果（纯数据）
    problem_analysis: Optional[ProblemAnalysis] = None
    data_insight: Optional[DataInsight] = None
    model_recommendation: Optional[ModelRecommendation] = None
    innovative_model_plan: Optional[InnovativeModelPlan] = None
    experiment_plan: Optional[ExperimentPlan] = None
    code_results: Optional[Dict[str, Any]] = None
    validation_report: Optional[ValidationReport] = None
    quality_review: Optional[QualityReview] = None
    paper_content: Optional[str] = None

    # 工作目录路径（纯数据，非服务对象）
    work_dir: Optional[str] = None

    # 质量指标跟踪
    stage_quality_metrics: Dict[str, QualityLevel] = field(default_factory=dict)
    improvement_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowServiceContainer:
    """
    工作流服务容器 - 持有活跃服务对象的引用

    与 WorkflowContext (纯数据) 分离，
    避免不可序列化的服务对象污染上下文快照。
    由 WorkflowEngine 在运行时创建和管理。
    """
    coder_agent: Optional[Any] = None       # CoderAgent 实例
    code_interpreter: Optional[Any] = None  # BaseCodeInterpreter 实例
    user_output: Optional[Any] = None       # UserOutput 实例
    flows: Optional[Any] = None             # Flows 实例

    async def cleanup(self) -> None:
        """释放服务资源，确保子进程和连接正确关闭"""
        # 优先清理代码解释器（可能持有 Jupyter kernel 子进程）
        if self.code_interpreter is not None:
            try:
                cleanup_fn = getattr(self.code_interpreter, "cleanup", None)
                if cleanup_fn is not None:
                    import asyncio
                    if asyncio.iscoroutinefunction(cleanup_fn):
                        await cleanup_fn()
                    else:
                        cleanup_fn()
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "代码解释器清理失败，可能存在残留进程", exc_info=True
                )
            finally:
                self.code_interpreter = None

        # 清理 CoderAgent（可能持有 LLM 连接）
        if self.coder_agent is not None:
            try:
                close_fn = getattr(self.coder_agent, "close", None)
                if close_fn is not None:
                    import asyncio
                    if asyncio.iscoroutinefunction(close_fn):
                        await close_fn()
                    else:
                        close_fn()
            except Exception as e:
                logger.debug("关闭 CoderAgent 失败: %s", e)
            finally:
                self.coder_agent = None

        self.user_output = None
        self.flows = None
