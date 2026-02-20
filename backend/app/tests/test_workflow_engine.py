"""工作流状态管理单元测试

覆盖: WorkflowContext / WorkflowServiceContainer (数据/服务分离)
       WorkflowStage / IterationDecision (枚举)

NOTE: 旧架构 BaseStage / dataclass_to_dict / WorkflowEngine 已在 Batch 22A 中移除。
"""

from unittest.mock import MagicMock

import pytest


# ============================================================
# WorkflowContext 测试
# ============================================================

class TestWorkflowContext:
    """工作流上下文测试"""

    def test_creation_with_defaults(self):
        """测试默认值创建"""
        from app.core.workflow.state import WorkflowContext, WorkflowStage
        coordinator_data = MagicMock()
        ctx = WorkflowContext(
            task_id="test-001",
            coordinator_data=coordinator_data,
            current_stage=WorkflowStage.PROBLEM_ANALYSIS,
        )
        assert ctx.task_id == "test-001"
        assert ctx.iteration_count == 0
        assert ctx.max_iterations == 3
        assert ctx.problem_analysis is None
        assert ctx.code_results is None
        assert isinstance(ctx.stage_quality_metrics, dict)
        assert isinstance(ctx.improvement_history, list)

    def test_pure_data_no_service_objects(self):
        """测试 WorkflowContext 不包含服务对象"""
        from app.core.workflow.state import WorkflowContext, WorkflowStage
        coordinator_data = MagicMock()
        ctx = WorkflowContext(
            task_id="test-001",
            coordinator_data=coordinator_data,
            current_stage=WorkflowStage.PROBLEM_ANALYSIS,
        )
        # 确认没有 coder_agent, code_interpreter 等服务对象字段
        assert not hasattr(ctx, "coder_agent")
        assert not hasattr(ctx, "code_interpreter")


# ============================================================
# WorkflowServiceContainer 测试
# ============================================================

class TestWorkflowServiceContainer:
    """工作流服务容器测试"""

    def test_creation_with_defaults(self):
        """测试默认值创建"""
        from app.core.workflow.state import WorkflowServiceContainer
        svc = WorkflowServiceContainer()
        assert svc.coder_agent is None
        assert svc.code_interpreter is None
        assert svc.user_output is None
        assert svc.flows is None

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """测试 cleanup 将所有服务置 None"""
        from app.core.workflow.state import WorkflowServiceContainer
        svc = WorkflowServiceContainer(
            coder_agent=MagicMock(),
            code_interpreter=MagicMock(),
            user_output=MagicMock(),
            flows=MagicMock(),
        )
        await svc.cleanup()
        assert svc.coder_agent is None
        assert svc.code_interpreter is None
        assert svc.user_output is None
        assert svc.flows is None

    def test_holds_service_references(self):
        """测试可以持有服务对象引用"""
        from app.core.workflow.state import WorkflowServiceContainer
        mock_coder = MagicMock()
        mock_interpreter = MagicMock()
        svc = WorkflowServiceContainer(
            coder_agent=mock_coder,
            code_interpreter=mock_interpreter,
        )
        assert svc.coder_agent is mock_coder
        assert svc.code_interpreter is mock_interpreter


# ============================================================
# WorkflowStage 枚举测试
# ============================================================

class TestWorkflowStage:
    """工作流阶段枚举测试"""

    def test_all_stages_exist(self):
        """测试所有阶段枚举值存在"""
        from app.core.workflow.state import WorkflowStage
        expected = [
            "PROBLEM_ANALYSIS", "MODEL_SELECTION", "EXPERIMENT_DESIGN",
            "CODE_IMPLEMENTATION", "MODEL_VALIDATION", "QUALITY_REVIEW",
            "PAPER_WRITING", "COMPLETED", "FAILED",
        ]
        for stage_name in expected:
            assert hasattr(WorkflowStage, stage_name), f"缺少阶段: {stage_name}"

    def test_terminal_stages(self):
        """测试终态阶段"""
        from app.core.workflow.state import WorkflowStage
        assert WorkflowStage.COMPLETED is not None
        assert WorkflowStage.FAILED is not None


# ============================================================
# IterationDecision 枚举测试
# ============================================================

class TestIterationDecision:
    """迭代决策枚举测试"""

    def test_all_decisions_exist(self):
        """测试所有决策枚举值存在"""
        from app.core.workflow.state import IterationDecision
        expected = ["CONTINUE", "ITERATE", "ROLLBACK", "TERMINATE"]
        for decision_name in expected:
            assert hasattr(IterationDecision, decision_name), f"缺少决策: {decision_name}"
