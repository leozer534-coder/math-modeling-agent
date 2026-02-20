"""
WorkflowPipeline 核心单元测试

覆盖目标:
  - StageConfig 数据类: 默认值、自定义赋值
  - StageResult 数据类: 成功/失败/跳过结果
  - PipelineContext: 创建、elapsed_minutes、configure_resume、_apply_resume_data
  - WorkflowPipeline: __init__、configure_resume、_apply_resume_data、
    get_execution_stats、create 工厂方法、Stage Protocol 合规性
"""

# ================== langchain_core Mock 注入 ==================
# 必须在所有 app.* 导入之前执行，防止缺少 langchain_core 依赖导致 ImportError
import sys
from unittest.mock import MagicMock

for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.HumanMessage = MagicMock
        _mock.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock

import time
from dataclasses import FrozenInstanceError, dataclass
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.workflow.pipeline import (
    PipelineContext,
    Stage,
    StageConfig,
    StageResult,
    WorkflowPipeline,
)


# ==================== 辅助: 符合 Stage Protocol 的 Fake 实现 ====================


class FakeStage:
    """符合 Stage Protocol 的测试替身。"""

    def __init__(self, **kwargs: Any) -> None:
        self._kwargs = kwargs

    @property
    def name(self) -> str:
        return self._kwargs.get("stage_name", "fake_stage")

    async def execute(self, ctx: PipelineContext) -> None:
        ctx.artifacts[self.name] = "done"


class FakeStageAlpha:
    """第二个 Fake Stage，用于多阶段场景。"""

    @property
    def name(self) -> str:
        return "alpha"

    async def execute(self, ctx: PipelineContext) -> None:
        ctx.artifacts["alpha"] = "alpha_done"


class FakeStageBeta:
    """第三个 Fake Stage，用于多阶段场景。"""

    @property
    def name(self) -> str:
        return "beta"

    async def execute(self, ctx: PipelineContext) -> None:
        ctx.artifacts["beta"] = "beta_done"


class FailingStage:
    """始终抛异常的 Stage，用于测试错误路径。"""

    @property
    def name(self) -> str:
        return "failing_stage"

    async def execute(self, ctx: PipelineContext) -> None:
        raise RuntimeError("模拟阶段失败")


class NotAStage:
    """不符合 Stage Protocol 的类（缺少 execute 方法）。"""

    @property
    def name(self) -> str:
        return "not_a_stage"


# ==================== TestStageConfig ====================


class TestStageConfig:
    """StageConfig 数据类单元测试。"""

    @pytest.mark.unit
    def test_default_values(self):
        """验证: StageConfig 使用默认值创建时各字段符合预期。"""
        config = StageConfig(stage_class=FakeStage)

        assert config.stage_class is FakeStage
        assert config.optional is False
        assert config.progress_start == 0.0
        assert config.progress_end == 100.0
        assert config.timeout == 0.0
        assert config.kwargs == {}

    @pytest.mark.unit
    def test_custom_values(self):
        """验证: StageConfig 支持自定义参数赋值。"""
        config = StageConfig(
            stage_class=FakeStage,
            optional=True,
            progress_start=10.0,
            progress_end=50.0,
            timeout=300.0,
            kwargs={"stage_name": "custom"},
        )

        assert config.stage_class is FakeStage
        assert config.optional is True
        assert config.progress_start == 10.0
        assert config.progress_end == 50.0
        assert config.timeout == 300.0
        assert config.kwargs == {"stage_name": "custom"}

    @pytest.mark.unit
    def test_kwargs_default_factory_independence(self):
        """验证: 不同 StageConfig 实例的 kwargs 互不影响（default_factory 隔离）。"""
        config_a = StageConfig(stage_class=FakeStage)
        config_b = StageConfig(stage_class=FakeStage)

        config_a.kwargs["key"] = "value_a"

        assert "key" not in config_b.kwargs

    @pytest.mark.unit
    def test_stage_class_stores_type(self):
        """验证: stage_class 存储的是类型对象而非实例。"""
        config = StageConfig(stage_class=FakeStage)
        assert isinstance(config.stage_class, type)

    @pytest.mark.unit
    def test_is_not_frozen(self):
        """验证: StageConfig 是普通 dataclass（非 frozen），字段可修改。"""
        config = StageConfig(stage_class=FakeStage)
        config.optional = True
        assert config.optional is True

        config.timeout = 600.0
        assert config.timeout == 600.0


# ==================== TestStageResult ====================


class TestStageResult:
    """StageResult 数据类单元测试。"""

    @pytest.mark.unit
    def test_success_result(self):
        """验证: 创建成功结果时各字段正确。"""
        result = StageResult(
            name="modeler",
            success=True,
            duration=12.5,
        )

        assert result.name == "modeler"
        assert result.success is True
        assert result.duration == 12.5
        assert result.error is None
        assert result.skipped is False

    @pytest.mark.unit
    def test_failure_result_with_error(self):
        """验证: 创建失败结果时包含错误信息。"""
        result = StageResult(
            name="coder",
            success=False,
            duration=5.0,
            error="LLM 调用超时",
        )

        assert result.name == "coder"
        assert result.success is False
        assert result.duration == 5.0
        assert result.error == "LLM 调用超时"
        assert result.skipped is False

    @pytest.mark.unit
    def test_skipped_result(self):
        """验证: 创建跳过结果时 skipped=True。"""
        result = StageResult(
            name="review",
            success=True,
            duration=0.0,
            skipped=True,
        )

        assert result.name == "review"
        assert result.success is True
        assert result.duration == 0.0
        assert result.skipped is True

    @pytest.mark.unit
    def test_default_values(self):
        """验证: StageResult 默认值符合预期。"""
        result = StageResult(name="test", success=True)

        assert result.duration == 0.0
        assert result.error is None
        assert result.skipped is False

    @pytest.mark.unit
    def test_failure_skipped_optional_stage(self):
        """验证: 可选阶段失败后的结果 (success=False, skipped=True)。"""
        result = StageResult(
            name="optional_stage",
            success=False,
            duration=2.3,
            error="可选阶段超时",
            skipped=True,
        )

        assert result.success is False
        assert result.skipped is True
        assert result.error == "可选阶段超时"


# ==================== TestPipelineContext ====================


class TestPipelineContext:
    """PipelineContext 单元测试。"""

    @pytest.mark.unit
    def test_default_values(self):
        """验证: PipelineContext 默认值正确初始化。"""
        ctx = PipelineContext()

        assert ctx.task_id == ""
        assert ctx.work_dir == ""
        assert ctx.problem is None
        assert ctx.llm_factory is None
        assert ctx.llms == {}
        assert ctx.agents == {}
        assert ctx.code_interpreter is None
        assert ctx.coordinator_response is None
        assert ctx.questions == {}
        assert ctx.ques_count == 0
        assert ctx.modeler_response is None
        assert ctx.solution_results == {}
        assert ctx.user_output is None
        assert ctx.artifacts == {}
        assert ctx.current_stage_name == ""
        assert ctx.agent_configs is None
        assert ctx.workflow_mode == "standard"

    @pytest.mark.unit
    def test_custom_initialization(self):
        """验证: PipelineContext 支持自定义参数初始化。"""
        mock_problem = MagicMock()
        mock_llm_factory = MagicMock()

        ctx = PipelineContext(
            task_id="task-001",
            work_dir="/tmp/work",
            problem=mock_problem,
            llm_factory=mock_llm_factory,
            workflow_mode="enhanced",
        )

        assert ctx.task_id == "task-001"
        assert ctx.work_dir == "/tmp/work"
        assert ctx.problem is mock_problem
        assert ctx.llm_factory is mock_llm_factory
        assert ctx.workflow_mode == "enhanced"

    @pytest.mark.unit
    def test_start_time_auto_set(self):
        """验证: start_time 自动设置为当前时间。"""
        before = time.time()
        ctx = PipelineContext()
        after = time.time()

        assert before <= ctx.start_time <= after

    @pytest.mark.unit
    def test_elapsed_minutes_calculation(self):
        """验证: elapsed_minutes() 正确计算已用时间（分钟）。"""
        ctx = PipelineContext()
        # 将 start_time 设为 120 秒前
        ctx.start_time = time.time() - 120.0

        elapsed = ctx.elapsed_minutes()
        # 应接近 2.0 分钟（允许少量误差）
        assert 1.9 <= elapsed <= 2.2

    @pytest.mark.unit
    def test_elapsed_minutes_zero_at_start(self):
        """验证: 刚创建的 context elapsed_minutes 接近 0。"""
        ctx = PipelineContext()
        elapsed = ctx.elapsed_minutes()
        assert elapsed < 0.1  # 不到 6 秒

    @pytest.mark.unit
    def test_elapsed_minutes_with_mocked_start_time(self):
        """验证: 通过 mock start_time 精确验证 elapsed_minutes 计算逻辑。"""
        ctx = PipelineContext()
        # 设置 start_time 为 300 秒前 (5 分钟)
        ctx.start_time = time.time() - 300.0

        result = ctx.elapsed_minutes()
        assert abs(result - 5.0) < 0.1

    @pytest.mark.unit
    def test_artifacts_isolation(self):
        """验证: 不同 PipelineContext 实例的 artifacts 互不影响。"""
        ctx_a = PipelineContext()
        ctx_b = PipelineContext()

        ctx_a.artifacts["key"] = "value_a"

        assert "key" not in ctx_b.artifacts

    @pytest.mark.unit
    def test_mutable_fields(self):
        """验证: PipelineContext 的可变字段可以正常修改。"""
        ctx = PipelineContext()

        ctx.task_id = "new-task"
        ctx.ques_count = 5
        ctx.questions = {"q1": "问题1"}
        ctx.solution_results = {"q1": {"result": "解答1"}}

        assert ctx.task_id == "new-task"
        assert ctx.ques_count == 5
        assert ctx.questions == {"q1": "问题1"}
        assert ctx.solution_results == {"q1": {"result": "解答1"}}

    @pytest.mark.unit
    def test_agent_configs_nullable(self):
        """验证: agent_configs 可以为 None 或 dict。"""
        ctx = PipelineContext()
        assert ctx.agent_configs is None

        ctx.agent_configs = {"coordinator": {"model": "gpt-4"}}
        assert ctx.agent_configs["coordinator"]["model"] == "gpt-4"


# ==================== TestWorkflowPipeline ====================


class TestWorkflowPipeline:
    """WorkflowPipeline 单元测试。"""

    @pytest.fixture
    def simple_configs(self) -> list[StageConfig]:
        """创建简单的阶段配置列表。"""
        return [
            StageConfig(
                stage_class=FakeStage,
                progress_start=0,
                progress_end=50,
                kwargs={"stage_name": "fake_stage"},
            ),
            StageConfig(
                stage_class=FakeStageAlpha,
                progress_start=50,
                progress_end=100,
            ),
        ]

    @pytest.fixture
    def pipeline(self, simple_configs) -> WorkflowPipeline:
        """创建基本的 WorkflowPipeline 实例。"""
        return WorkflowPipeline(
            stage_configs=simple_configs,
            agent_configs=None,
            workflow_mode="standard",
        )

    # ---- __init__ 测试 ----

    @pytest.mark.unit
    def test_init_default_values(self):
        """验证: WorkflowPipeline 初始化后默认状态正确。"""
        pipeline = WorkflowPipeline(stage_configs=[])

        assert pipeline.stage_configs == []
        assert pipeline._agent_configs is None
        assert pipeline._workflow_mode == "standard"
        assert pipeline.ctx is None
        assert pipeline.results == []
        assert pipeline._skip_stages == set()
        assert pipeline._resume_data is None

    @pytest.mark.unit
    def test_init_with_custom_params(self, simple_configs):
        """验证: WorkflowPipeline 支持自定义参数初始化。"""
        agent_configs = {"coordinator": {"model": "gpt-4"}}
        pipeline = WorkflowPipeline(
            stage_configs=simple_configs,
            agent_configs=agent_configs,
            workflow_mode="award",
        )

        assert len(pipeline.stage_configs) == 2
        assert pipeline._agent_configs == agent_configs
        assert pipeline._workflow_mode == "award"

    # ---- configure_resume 测试 ----

    @pytest.mark.unit
    def test_configure_resume_basic(self, pipeline):
        """验证: configure_resume 正确设置跳过阶段和恢复数据。"""
        pipeline.configure_resume(
            completed_stages=["coordinator", "modeler"],
            stage_outputs={"coordinator": "output1"},
            questions={"q1": "问题1"},
            ques_count=2,
        )

        assert "coordinator" in pipeline._skip_stages
        assert "modeler" in pipeline._skip_stages
        assert pipeline._resume_data is not None
        assert pipeline._resume_data["ques_count"] == 2
        assert pipeline._resume_data["questions"] == {"q1": "问题1"}

    @pytest.mark.unit
    def test_configure_resume_excludes_setup(self, pipeline):
        """验证: configure_resume 始终排除 setup 阶段（不可跳过）。"""
        pipeline.configure_resume(
            completed_stages=["setup", "coordinator", "modeler"],
        )

        assert "setup" not in pipeline._skip_stages
        assert "coordinator" in pipeline._skip_stages
        assert "modeler" in pipeline._skip_stages

    @pytest.mark.unit
    def test_configure_resume_default_values(self, pipeline):
        """验证: configure_resume 使用默认空值时的恢复数据。"""
        pipeline.configure_resume(completed_stages=["coordinator"])

        data = pipeline._resume_data
        assert data is not None
        assert data["stage_outputs"] == {}
        assert data["questions"] == {}
        assert data["ques_count"] == 0
        assert data["coordinator_response"] is None
        assert data["modeler_response"] is None
        assert data["user_output_res"] == {}

    @pytest.mark.unit
    def test_configure_resume_with_all_params(self, pipeline):
        """验证: configure_resume 所有参数都能正确存储。"""
        mock_coordinator = MagicMock()
        mock_modeler = MagicMock()

        pipeline.configure_resume(
            completed_stages=["coordinator", "modeler"],
            stage_outputs={"coord_out": "value1", "mod_out": "value2"},
            questions={"q1": "问题A", "q2": "问题B"},
            ques_count=2,
            coordinator_response=mock_coordinator,
            modeler_response=mock_modeler,
            user_output_res={"abstract": {"content": "摘要内容"}},
        )

        data = pipeline._resume_data
        assert data["stage_outputs"] == {"coord_out": "value1", "mod_out": "value2"}
        assert data["questions"] == {"q1": "问题A", "q2": "问题B"}
        assert data["ques_count"] == 2
        assert data["coordinator_response"] is mock_coordinator
        assert data["modeler_response"] is mock_modeler
        assert data["user_output_res"] == {"abstract": {"content": "摘要内容"}}

    # ---- _apply_resume_data 测试 ----

    @pytest.mark.unit
    def test_apply_resume_data_with_no_data(self, pipeline):
        """验证: _resume_data 为 None 时 _apply_resume_data 安全返回。"""
        pipeline.ctx = PipelineContext(task_id="test")
        pipeline._resume_data = None

        # 不应抛异常
        pipeline._apply_resume_data()

        assert pipeline.ctx.questions == {}
        assert pipeline.ctx.ques_count == 0

    @pytest.mark.unit
    def test_apply_resume_data_with_no_ctx(self, pipeline):
        """验证: ctx 为 None 时 _apply_resume_data 安全返回。"""
        pipeline.ctx = None
        pipeline._resume_data = {"questions": {"q1": "x"}}

        # 不应抛异常
        pipeline._apply_resume_data()

    @pytest.mark.unit
    def test_apply_resume_data_restores_questions(self, pipeline):
        """验证: _apply_resume_data 正确恢复 questions 到 ctx。"""
        pipeline.ctx = PipelineContext(task_id="test")
        pipeline._resume_data = {
            "questions": {"q1": "问题1", "q2": "问题2"},
            "ques_count": 2,
            "coordinator_response": None,
            "modeler_response": None,
            "stage_outputs": {},
            "user_output_res": {},
        }

        pipeline._apply_resume_data()

        assert pipeline.ctx.questions == {"q1": "问题1", "q2": "问题2"}
        assert pipeline.ctx.ques_count == 2

    @pytest.mark.unit
    def test_apply_resume_data_restores_coordinator(self, pipeline):
        """验证: _apply_resume_data 正确恢复 coordinator_response。"""
        mock_response = MagicMock()
        pipeline.ctx = PipelineContext(task_id="test")
        pipeline._resume_data = {
            "questions": {},
            "ques_count": 0,
            "coordinator_response": mock_response,
            "modeler_response": None,
            "stage_outputs": {},
            "user_output_res": {},
        }

        pipeline._apply_resume_data()

        assert pipeline.ctx.coordinator_response is mock_response

    @pytest.mark.unit
    def test_apply_resume_data_restores_modeler(self, pipeline):
        """验证: _apply_resume_data 正确恢复 modeler_response。"""
        mock_modeler = MagicMock()
        pipeline.ctx = PipelineContext(task_id="test")
        pipeline._resume_data = {
            "questions": {},
            "ques_count": 0,
            "coordinator_response": None,
            "modeler_response": mock_modeler,
            "stage_outputs": {},
            "user_output_res": {},
        }

        pipeline._apply_resume_data()

        assert pipeline.ctx.modeler_response is mock_modeler

    @pytest.mark.unit
    def test_apply_resume_data_restores_stage_outputs(self, pipeline):
        """验证: _apply_resume_data 将 stage_outputs 注入 artifacts。"""
        pipeline.ctx = PipelineContext(task_id="test")
        pipeline._resume_data = {
            "questions": {},
            "ques_count": 0,
            "coordinator_response": None,
            "modeler_response": None,
            "stage_outputs": {
                "eda_summary": "数据探索结论",
                "model_output": "建模结果",
            },
            "user_output_res": {},
        }

        pipeline._apply_resume_data()

        assert pipeline.ctx.artifacts["eda_summary"] == "数据探索结论"
        assert pipeline.ctx.artifacts["model_output"] == "建模结果"

    @pytest.mark.unit
    def test_apply_resume_data_restores_user_output_res(self, pipeline):
        """验证: _apply_resume_data 将 user_output_res 存入 artifacts 的特殊键。"""
        pipeline.ctx = PipelineContext(task_id="test")
        user_output = {"abstract": {"content": "摘要"}, "intro": {"content": "引言"}}
        pipeline._resume_data = {
            "questions": {},
            "ques_count": 0,
            "coordinator_response": None,
            "modeler_response": None,
            "stage_outputs": {},
            "user_output_res": user_output,
        }

        pipeline._apply_resume_data()

        assert pipeline.ctx.artifacts["_resume_user_output_res"] == user_output

    @pytest.mark.unit
    def test_apply_resume_data_empty_user_output_not_stored(self, pipeline):
        """验证: user_output_res 为空时不写入 artifacts。"""
        pipeline.ctx = PipelineContext(task_id="test")
        pipeline._resume_data = {
            "questions": {},
            "ques_count": 0,
            "coordinator_response": None,
            "modeler_response": None,
            "stage_outputs": {},
            "user_output_res": {},
        }

        pipeline._apply_resume_data()

        assert "_resume_user_output_res" not in pipeline.ctx.artifacts

    # ---- get_execution_stats 测试 ----

    @pytest.mark.unit
    def test_get_execution_stats_no_ctx(self):
        """验证: ctx 为 None 时 total_time 返回 0。"""
        pipeline = WorkflowPipeline(stage_configs=[])
        stats = pipeline.get_execution_stats()

        assert stats["total_time"] == 0.0
        assert stats["workflow_mode"] == "standard"
        assert stats["stages"] == {}

    @pytest.mark.unit
    def test_get_execution_stats_with_ctx(self):
        """验证: 有 ctx 时 total_time 反映实际耗时。"""
        pipeline = WorkflowPipeline(stage_configs=[], workflow_mode="enhanced")
        pipeline.ctx = PipelineContext()
        pipeline.ctx.start_time = time.time() - 60.0  # 60 秒前

        stats = pipeline.get_execution_stats()

        assert stats["workflow_mode"] == "enhanced"
        assert 59.0 <= stats["total_time"] <= 62.0

    @pytest.mark.unit
    def test_get_execution_stats_with_results(self):
        """验证: results 中的阶段信息正确映射到 stats。"""
        pipeline = WorkflowPipeline(stage_configs=[], workflow_mode="award")
        pipeline.ctx = PipelineContext()
        pipeline.results = [
            StageResult(name="coordinator", success=True, duration=10.5),
            StageResult(
                name="modeler", success=False, duration=5.0, error="超时"
            ),
            StageResult(
                name="review", success=True, duration=0.0, skipped=True
            ),
        ]

        stats = pipeline.get_execution_stats()

        assert "coordinator" in stats["stages"]
        assert stats["stages"]["coordinator"]["success"] is True
        assert stats["stages"]["coordinator"]["duration"] == 10.5
        assert stats["stages"]["coordinator"]["skipped"] is False
        assert stats["stages"]["coordinator"]["error"] is None

        assert stats["stages"]["modeler"]["success"] is False
        assert stats["stages"]["modeler"]["error"] == "超时"

        assert stats["stages"]["review"]["skipped"] is True

    @pytest.mark.unit
    def test_get_execution_stats_empty_results(self):
        """验证: results 为空列表时 stages 为空字典。"""
        pipeline = WorkflowPipeline(stage_configs=[])
        pipeline.ctx = PipelineContext()
        pipeline.results = []

        stats = pipeline.get_execution_stats()
        assert stats["stages"] == {}

    # ---- create 工厂方法测试 ----

    @pytest.mark.unit
    def test_create_standard_mode(self):
        """验证: create() 使用 standard 模式创建 pipeline。"""
        with patch(
            "app.core.workflow.configs.get_pipeline_config",
        ) as mock_get_config:
            mock_get_config.return_value = [
                StageConfig(stage_class=FakeStage),
            ]

            pipeline = WorkflowPipeline.create(
                workflow_mode="standard",
                agent_configs={"key": "value"},
            )

            mock_get_config.assert_called_once_with("standard")
            assert isinstance(pipeline, WorkflowPipeline)
            assert pipeline._workflow_mode == "standard"
            assert pipeline._agent_configs == {"key": "value"}
            assert len(pipeline.stage_configs) == 1

    @pytest.mark.unit
    def test_create_enhanced_mode(self):
        """验证: create() 使用 enhanced 模式。"""
        with patch(
            "app.core.workflow.configs.get_pipeline_config",
        ) as mock_get_config:
            mock_get_config.return_value = [
                StageConfig(stage_class=FakeStage),
                StageConfig(stage_class=FakeStageAlpha),
            ]

            pipeline = WorkflowPipeline.create(workflow_mode="enhanced")

            mock_get_config.assert_called_once_with("enhanced")
            assert pipeline._workflow_mode == "enhanced"
            assert len(pipeline.stage_configs) == 2

    @pytest.mark.unit
    def test_create_award_mode(self):
        """验证: create() 使用 award 模式。"""
        with patch(
            "app.core.workflow.configs.get_pipeline_config",
        ) as mock_get_config:
            mock_get_config.return_value = []

            pipeline = WorkflowPipeline.create(workflow_mode="award")

            mock_get_config.assert_called_once_with("award")
            assert pipeline._workflow_mode == "award"

    @pytest.mark.unit
    def test_create_passes_kwargs(self):
        """验证: create() 将 kwargs 传递给 get_pipeline_config。"""
        with patch(
            "app.core.workflow.configs.get_pipeline_config",
        ) as mock_get_config:
            mock_get_config.return_value = []

            WorkflowPipeline.create(
                workflow_mode="standard",
                stage_timeout=900.0,
            )

            mock_get_config.assert_called_once_with(
                "standard", stage_timeout=900.0
            )

    @pytest.mark.unit
    def test_create_with_none_agent_configs(self):
        """验证: create() 的 agent_configs 默认为 None。"""
        with patch(
            "app.core.workflow.configs.get_pipeline_config",
        ) as mock_get_config:
            mock_get_config.return_value = []

            pipeline = WorkflowPipeline.create(workflow_mode="standard")

            assert pipeline._agent_configs is None

    # ---- Stage Protocol 合规性测试 ----

    @pytest.mark.unit
    def test_fake_stage_is_stage_protocol(self):
        """验证: FakeStage 符合 Stage Protocol（runtime_checkable）。"""
        stage = FakeStage()
        assert isinstance(stage, Stage)

    @pytest.mark.unit
    def test_not_a_stage_fails_protocol(self):
        """验证: 缺少 execute 方法的类不满足 Stage Protocol。"""
        obj = NotAStage()
        assert not isinstance(obj, Stage)

    @pytest.mark.unit
    def test_multiple_fake_stages_comply(self):
        """验证: 所有 Fake Stage 实现类都符合 Protocol。"""
        assert isinstance(FakeStageAlpha(), Stage)
        assert isinstance(FakeStageBeta(), Stage)
        assert isinstance(FailingStage(), Stage)


# ==================== TestWorkflowPipelineIntegration ====================


class TestWorkflowPipelineConfigureAndApply:
    """WorkflowPipeline configure_resume + _apply_resume_data 集成场景测试。"""

    @pytest.mark.unit
    def test_configure_then_apply_full_cycle(self):
        """验证: configure_resume 后 _apply_resume_data 完整恢复上下文数据。"""
        pipeline = WorkflowPipeline(
            stage_configs=[StageConfig(stage_class=FakeStage)],
        )
        mock_coord = MagicMock()
        mock_modeler = MagicMock()

        # Step 1: 配置恢复
        pipeline.configure_resume(
            completed_stages=["coordinator", "setup", "eda"],
            stage_outputs={"eda_summary": "EDA 分析完成"},
            questions={"q1": "线性规划问题", "q2": "敏感性分析"},
            ques_count=2,
            coordinator_response=mock_coord,
            modeler_response=mock_modeler,
            user_output_res={"abstract": {"text": "摘要"}},
        )

        # Step 2: 创建 ctx 并注入
        pipeline.ctx = PipelineContext(task_id="resume-task")
        pipeline._apply_resume_data()

        # Step 3: 验证恢复结果
        ctx = pipeline.ctx
        assert ctx.questions == {"q1": "线性规划问题", "q2": "敏感性分析"}
        assert ctx.ques_count == 2
        assert ctx.coordinator_response is mock_coord
        assert ctx.modeler_response is mock_modeler
        assert ctx.artifacts["eda_summary"] == "EDA 分析完成"
        assert ctx.artifacts["_resume_user_output_res"] == {
            "abstract": {"text": "摘要"}
        }

        # Step 4: 验证 setup 不在跳过集合中
        assert "setup" not in pipeline._skip_stages
        assert "coordinator" in pipeline._skip_stages
        assert "eda" in pipeline._skip_stages

    @pytest.mark.unit
    def test_multiple_configure_resume_overwrites(self):
        """验证: 多次调用 configure_resume 后最后一次生效。"""
        pipeline = WorkflowPipeline(stage_configs=[])

        pipeline.configure_resume(
            completed_stages=["coordinator"],
            ques_count=1,
        )
        assert pipeline._resume_data["ques_count"] == 1

        pipeline.configure_resume(
            completed_stages=["coordinator", "modeler"],
            ques_count=3,
        )
        assert pipeline._resume_data["ques_count"] == 3
        assert "modeler" in pipeline._skip_stages

    @pytest.mark.unit
    def test_get_execution_stats_workflow_mode_preserved(self):
        """验证: 不同 workflow_mode 在 stats 中正确反映。"""
        for mode in ("standard", "enhanced", "award"):
            pipeline = WorkflowPipeline(
                stage_configs=[], workflow_mode=mode
            )
            pipeline.ctx = PipelineContext()
            stats = pipeline.get_execution_stats()
            assert stats["workflow_mode"] == mode


# ==================== TestStageResultEdgeCases ====================


class TestStageResultEdgeCases:
    """StageResult 边界条件测试。"""

    @pytest.mark.unit
    def test_very_long_error_message(self):
        """验证: 超长错误信息可以正常存储。"""
        long_error = "E" * 10000
        result = StageResult(name="test", success=False, error=long_error)
        assert len(result.error) == 10000

    @pytest.mark.unit
    def test_zero_duration(self):
        """验证: duration 为 0 的结果。"""
        result = StageResult(name="instant", success=True, duration=0.0)
        assert result.duration == 0.0

    @pytest.mark.unit
    def test_large_duration(self):
        """验证: 超大 duration 值。"""
        result = StageResult(
            name="slow", success=True, duration=86400.0
        )  # 24 小时
        assert result.duration == 86400.0

    @pytest.mark.unit
    def test_empty_name(self):
        """验证: 空名称的 StageResult。"""
        result = StageResult(name="", success=True)
        assert result.name == ""


# ==================== TestPipelineContextEdgeCases ====================


class TestPipelineContextEdgeCases:
    """PipelineContext 边界条件测试。"""

    @pytest.mark.unit
    def test_artifacts_nested_dict(self):
        """验证: artifacts 支持嵌套数据结构。"""
        ctx = PipelineContext()
        ctx.artifacts["nested"] = {
            "level1": {"level2": {"level3": [1, 2, 3]}}
        }
        assert ctx.artifacts["nested"]["level1"]["level2"]["level3"] == [
            1,
            2,
            3,
        ]

    @pytest.mark.unit
    def test_multiple_agents_and_llms(self):
        """验证: agents 和 llms 字典支持多个条目。"""
        ctx = PipelineContext()
        for name in ("coordinator", "modeler", "coder", "writer"):
            ctx.agents[name] = MagicMock(name=f"agent_{name}")
            ctx.llms[name] = MagicMock(name=f"llm_{name}")

        assert len(ctx.agents) == 4
        assert len(ctx.llms) == 4

    @pytest.mark.unit
    def test_current_stage_name_updates(self):
        """验证: current_stage_name 可以多次更新。"""
        ctx = PipelineContext()

        for stage in ("coordinator", "setup", "eda", "modeler", "coder"):
            ctx.current_stage_name = stage
            assert ctx.current_stage_name == stage

    @pytest.mark.unit
    def test_solution_results_complex_data(self):
        """验证: solution_results 支持复杂的结果数据。"""
        ctx = PipelineContext()
        ctx.solution_results = {
            "q1": {
                "code": "print('hello')",
                "output": "hello",
                "figures": ["fig1.png", "fig2.png"],
                "success": True,
            },
            "q2": {
                "code": "import numpy",
                "output": "array([1,2,3])",
                "figures": [],
                "success": True,
            },
        }

        assert len(ctx.solution_results) == 2
        assert ctx.solution_results["q1"]["success"] is True
        assert len(ctx.solution_results["q1"]["figures"]) == 2
