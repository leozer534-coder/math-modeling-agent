"""
Stage 集成测试 - 覆盖 ValidationStage, ModelSelectionStage, ReviewStage 的关键分支

测试目标:
  1. ValidationStage: 静态方法纯函数 + execute 正常/异常路径
  2. ModelSelectionStage: execute 正常/异常路径 + primary_model 多类型处理
  3. ReviewStage: 静态方法 + 实例方法 + execute 异常处理策略

所有测试均不依赖 LLM、Redis、文件系统等外部资源。
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
# validation_stage.py 依赖 langchain_core (可选依赖, 测试环境可能未安装)
# 必须在任何 app.core.workflow.* 导入前注入 mock, 避免 ModuleNotFoundError
for _mod in ("langchain_core", "langchain_core.messages"):
    if _mod not in sys.modules:
        _m = MagicMock()
        _m.HumanMessage = MagicMock
        _m.SystemMessage = MagicMock
        sys.modules[_mod] = _m

import pytest  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from app.core.workflow.stages.artifact_keys import ArtifactKeys  # noqa: E402
from app.core.workflow.stages.model_selection_stage import (  # noqa: E402
    ModelSelectionStage,
)
from app.core.workflow.stages.review_stage import ReviewStage  # noqa: E402
from app.core.workflow.stages.stage_constants import (  # noqa: E402
    REVIEW_WEAK_THRESHOLD,
)
from app.core.workflow.stages.validation_stage import ValidationStage  # noqa: E402


# ================================================================
# 共享 Fixture
# ================================================================


@pytest.fixture
def mock_ctx():
    """构造通用的 PipelineContext mock 对象。

    提供所有 Stage 所需的最小属性集:
    task_id, workflow_mode, artifacts, solution_results,
    modeler_response, llms, agents, user_output, problem, ques_count,
    send_progress.
    """
    ctx = MagicMock()
    ctx.task_id = "test-task-001"
    ctx.workflow_mode = "standard"
    ctx.artifacts = {}
    ctx.solution_results = None
    # 设置为 None, 使 _run_sensitivity_analysis 提前返回
    ctx.modeler_response = None
    ctx.llms = {"modeler": MagicMock(), "writer": MagicMock()}
    ctx.agents = {"writer": AsyncMock()}
    ctx.ques_count = 2
    ctx.send_progress = AsyncMock()

    # user_output mock
    ctx.user_output = MagicMock()
    ctx.user_output.res = {}
    ctx.user_output.set_res = MagicMock()
    ctx.user_output.get_result_to_save = MagicMock(return_value="mock paper content")

    # problem mock
    ctx.problem = MagicMock()
    ctx.problem.ques_all = "mock problem description"

    return ctx


# ================================================================
# TestValidationStageCollectModelResults
# ================================================================


class TestValidationStageCollectModelResults:
    """ValidationStage._collect_model_results 静态方法测试。"""

    def test_empty_solution_results_returns_empty(self, mock_ctx):
        """验证: solution_results 为 None 时返回空 dict。"""
        mock_ctx.solution_results = None
        result = ValidationStage._collect_model_results(mock_ctx)
        assert result == {}

    def test_empty_dict_solution_results_returns_empty(self, mock_ctx):
        """验证: solution_results 为空 dict 时返回空 dict。"""
        mock_ctx.solution_results = {}
        result = ValidationStage._collect_model_results(mock_ctx)
        assert result == {}

    def test_collects_dict_values_correctly(self, mock_ctx):
        """验证: 有求解结果时正确收集, 并跳过 'flows' / 'config_template' 键。"""
        mock_ctx.solution_results = {
            "ques1": {
                "success": True,
                "code_output": "x = 42",
                "remodel_attempts": 1,
            },
            "ques2": {
                "success": False,
                "code_output": "Error occurred",
            },
            "flows": {"internal": "data"},
            "config_template": {"template": "data"},
        }
        result = ValidationStage._collect_model_results(mock_ctx)

        # 不应包含 flows 和 config_template
        assert "flows" not in result
        assert "config_template" not in result

        # 应包含 ques1, ques2
        assert "ques1" in result
        assert result["ques1"]["success"] is True
        assert result["ques1"]["code_output"] == "x = 42"
        assert result["ques1"]["remodel_attempts"] == 1

        assert "ques2" in result
        assert result["ques2"]["success"] is False

    def test_non_dict_value_fallback_to_str(self, mock_ctx):
        """验证: value 为非 dict 类型时, 截断为 str[:1000] 作为 fallback。"""
        long_text = "A" * 2000
        mock_ctx.solution_results = {
            "ques1": long_text,
        }
        result = ValidationStage._collect_model_results(mock_ctx)

        assert "ques1" in result
        assert isinstance(result["ques1"], str)
        assert len(result["ques1"]) == 1000  # 截断到 1000 字符


# ================================================================
# TestValidationStageCollectExperimentData
# ================================================================


class TestValidationStageCollectExperimentData:
    """ValidationStage._collect_experiment_data 静态方法测试。"""

    def test_empty_artifacts_returns_empty(self, mock_ctx):
        """验证: artifacts 为空时返回空 dict。"""
        mock_ctx.artifacts = {}
        result = ValidationStage._collect_experiment_data(mock_ctx)
        assert result == {}

    def test_collects_eda_and_data_summary(self, mock_ctx):
        """验证: 有 EDA_RESULT + DATA_SUMMARY 时正确收集。"""
        mock_ctx.artifacts = {
            ArtifactKeys.EDA_RESULT: "EDA analysis result text",
            ArtifactKeys.DATA_SUMMARY: "Data summary text",
        }
        result = ValidationStage._collect_experiment_data(mock_ctx)

        assert "eda_summary" in result
        assert result["eda_summary"] == "EDA analysis result text"
        assert "data_summary" in result
        assert result["data_summary"] == "Data summary text"

    def test_problem_analysis_with_dict_attr(self, mock_ctx):
        """验证: problem_analysis 有 __dict__ 属性时正确转换为字符串。"""
        analysis_obj = SimpleNamespace(
            problem_type="optimization",
            difficulty="medium",
        )
        mock_ctx.artifacts = {
            ArtifactKeys.PROBLEM_ANALYSIS: analysis_obj,
        }
        result = ValidationStage._collect_experiment_data(mock_ctx)

        assert "problem_analysis" in result
        # SimpleNamespace.__dict__ 转为 str 后应包含关键信息
        assert "optimization" in result["problem_analysis"]

    def test_problem_analysis_without_dict_attr(self, mock_ctx):
        """验证: problem_analysis 为普通字符串时直接截断。"""
        mock_ctx.artifacts = {
            ArtifactKeys.PROBLEM_ANALYSIS: "plain analysis text",
        }
        result = ValidationStage._collect_experiment_data(mock_ctx)

        assert "problem_analysis" in result
        assert result["problem_analysis"] == "plain analysis text"

    def test_recommended_validation_injected(self, mock_ctx):
        """验证: RECOMMENDED_VALIDATION 有值时注入到结果中。"""
        mock_ctx.artifacts = {
            ArtifactKeys.RECOMMENDED_VALIDATION: ["cross_validation", "holdout"],
        }
        result = ValidationStage._collect_experiment_data(mock_ctx)

        assert "recommended_validation" in result
        assert result["recommended_validation"] == [
            "cross_validation",
            "holdout",
        ]

    def test_recommended_validation_empty_not_injected(self, mock_ctx):
        """验证: RECOMMENDED_VALIDATION 为空列表时不注入。"""
        mock_ctx.artifacts = {
            ArtifactKeys.RECOMMENDED_VALIDATION: [],
        }
        result = ValidationStage._collect_experiment_data(mock_ctx)
        assert "recommended_validation" not in result


# ================================================================
# TestValidationStageExecute
# ================================================================


class TestValidationStageExecute:
    """ValidationStage.execute 异步方法测试。"""

    @pytest.mark.asyncio
    async def test_early_return_no_solution_results(self, mock_ctx):
        """验证: 无求解结果时 early return, 不调用 ValidationExpert。"""
        mock_ctx.solution_results = None

        stage = ValidationStage()
        with patch(
            "app.core.workflow.stages.validation_stage.ValidationExpert"
        ) as MockVE:
            await stage.execute(mock_ctx)
            # ValidationExpert 应被构造 (在 early return 检查之前)
            # 但 validator.execute 不应被调用
            # 实际上, _collect_model_results 返回空 -> return
            # ValidationExpert 已被实例化, 但 execute 不会被调用
            if MockVE.return_value.execute.called:
                pytest.fail(
                    "无求解结果时不应调用 validator.execute"
                )

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.validation_stage.ValidationExpert")
    async def test_execute_success_writes_artifact(
        self, MockValidationExpert, mock_ctx
    ):
        """验证: 验证成功时应写入 validation_report artifact。"""
        # 准备求解结果
        mock_ctx.solution_results = {
            "ques1": {"success": True, "code_output": "x = 42"},
        }

        # 准备 mock 验证报告 (使用 SimpleNamespace 使 __dict__ 可用)
        mock_report = SimpleNamespace(
            overall_assessment={"validation_status": "通过"},
            details="all checks passed",
        )
        mock_validator_instance = AsyncMock()
        mock_validator_instance.execute = AsyncMock(return_value=mock_report)
        MockValidationExpert.return_value = mock_validator_instance

        stage = ValidationStage()
        await stage.execute(mock_ctx)

        # 验证 artifact 已写入
        assert ArtifactKeys.VALIDATION_REPORT in mock_ctx.artifacts
        report = mock_ctx.artifacts[ArtifactKeys.VALIDATION_REPORT]
        assert report["overall_assessment"]["validation_status"] == "通过"

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.validation_stage.ValidationExpert")
    async def test_execute_fail_award_mode_raises(
        self, MockValidationExpert, mock_ctx
    ):
        """验证: 验证失败 + award 模式 -> 应 raise 异常。"""
        mock_ctx.solution_results = {
            "ques1": {"success": True, "code_output": "result"},
        }
        mock_ctx.workflow_mode = "award"

        # 让 validator.execute 抛出异常
        mock_validator_instance = AsyncMock()
        mock_validator_instance.execute = AsyncMock(
            side_effect=RuntimeError("LLM call failed")
        )
        MockValidationExpert.return_value = mock_validator_instance

        stage = ValidationStage()
        with pytest.raises(RuntimeError, match="LLM call failed"):
            await stage.execute(mock_ctx)

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.validation_stage.ValidationExpert")
    async def test_execute_fail_standard_mode_no_raise(
        self, MockValidationExpert, mock_ctx
    ):
        """验证: 验证失败 + standard 模式 -> 写入错误 artifact 但不 raise。"""
        mock_ctx.solution_results = {
            "ques1": {"success": True, "code_output": "result"},
        }
        mock_ctx.workflow_mode = "standard"

        mock_validator_instance = AsyncMock()
        mock_validator_instance.execute = AsyncMock(
            side_effect=RuntimeError("validation error")
        )
        MockValidationExpert.return_value = mock_validator_instance

        stage = ValidationStage()
        # 不应抛出异常
        await stage.execute(mock_ctx)

        # 应写入包含错误信息的 artifact
        assert ArtifactKeys.VALIDATION_REPORT in mock_ctx.artifacts
        report = mock_ctx.artifacts[ArtifactKeys.VALIDATION_REPORT]
        assert report["overall_assessment"]["validation_status"] == "验证异常"
        assert "validation error" in report["overall_assessment"]["error"]


# ================================================================
# TestModelSelectionStageExecute
# ================================================================


class TestModelSelectionStageExecute:
    """ModelSelectionStage.execute 异步方法测试。"""

    @pytest.mark.asyncio
    async def test_no_problem_analysis_early_return(self, mock_ctx):
        """验证: 无 problem_analysis -> early return, 不创建 ModelSelector。"""
        mock_ctx.artifacts = {}  # 无 PROBLEM_ANALYSIS

        stage = ModelSelectionStage()
        with patch(
            "app.core.workflow.stages.model_selection_stage.ModelSelector"
        ) as MockMS:
            await stage.execute(mock_ctx)
            # ModelSelector 不应被构造
            MockMS.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.model_selection_stage.ModelSelector")
    async def test_selector_returns_none(self, MockSelector, mock_ctx):
        """验证: selector 返回 None -> 写入 None artifact。"""
        mock_ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = {
            "type": "optimization"
        }

        mock_selector_instance = AsyncMock()
        mock_selector_instance.setup = AsyncMock()
        mock_selector_instance.execute = AsyncMock(return_value=None)
        MockSelector.return_value = mock_selector_instance

        stage = ModelSelectionStage()
        await stage.execute(mock_ctx)

        assert mock_ctx.artifacts[ArtifactKeys.MODEL_RECOMMENDATION] is None
        assert (
            mock_ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL] is None
        )

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.model_selection_stage.ModelSelector")
    async def test_primary_model_dict_extracts_name(
        self, MockSelector, mock_ctx
    ):
        """验证: primary_model 为 dict 时提取 name 字段。"""
        mock_ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = {
            "type": "optimization"
        }

        mock_recommendation = SimpleNamespace(
            primary_model={"name": "线性规划", "type": "optimization"},
        )
        mock_selector_instance = AsyncMock()
        mock_selector_instance.setup = AsyncMock()
        mock_selector_instance.execute = AsyncMock(
            return_value=mock_recommendation
        )
        MockSelector.return_value = mock_selector_instance

        stage = ModelSelectionStage()
        await stage.execute(mock_ctx)

        assert (
            mock_ctx.artifacts[ArtifactKeys.MODEL_RECOMMENDATION]
            == mock_recommendation
        )
        assert (
            mock_ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL]
            == "线性规划"
        )

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.model_selection_stage.ModelSelector")
    async def test_primary_model_str_fallback(self, MockSelector, mock_ctx):
        """验证: primary_model 为 str 时使用 str() fallback。"""
        mock_ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = {
            "type": "prediction"
        }

        mock_recommendation = SimpleNamespace(
            primary_model="ARIMA",
        )
        mock_selector_instance = AsyncMock()
        mock_selector_instance.setup = AsyncMock()
        mock_selector_instance.execute = AsyncMock(
            return_value=mock_recommendation
        )
        MockSelector.return_value = mock_selector_instance

        stage = ModelSelectionStage()
        await stage.execute(mock_ctx)

        assert (
            mock_ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL]
            == "ARIMA"
        )

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.model_selection_stage.ModelSelector")
    async def test_primary_model_none_uses_default(
        self, MockSelector, mock_ctx
    ):
        """验证: primary_model 为 None 时使用默认值 '未知模型'。"""
        mock_ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = {
            "type": "evaluation"
        }

        mock_recommendation = SimpleNamespace(
            primary_model=None,
        )
        mock_selector_instance = AsyncMock()
        mock_selector_instance.setup = AsyncMock()
        mock_selector_instance.execute = AsyncMock(
            return_value=mock_recommendation
        )
        MockSelector.return_value = mock_selector_instance

        stage = ModelSelectionStage()
        await stage.execute(mock_ctx)

        assert (
            mock_ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL]
            == "未知模型"
        )

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.model_selection_stage.ModelSelector")
    async def test_execute_error_award_mode_raises(
        self, MockSelector, mock_ctx
    ):
        """验证: 执行异常 + award 模式 -> raise 异常。"""
        mock_ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = {
            "type": "optimization"
        }
        mock_ctx.workflow_mode = "award"

        mock_selector_instance = AsyncMock()
        mock_selector_instance.setup = AsyncMock()
        mock_selector_instance.execute = AsyncMock(
            side_effect=RuntimeError("selector crashed")
        )
        MockSelector.return_value = mock_selector_instance

        stage = ModelSelectionStage()
        with pytest.raises(RuntimeError, match="selector crashed"):
            await stage.execute(mock_ctx)

    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.model_selection_stage.ModelSelector")
    async def test_execute_error_standard_mode_no_raise(
        self, MockSelector, mock_ctx
    ):
        """验证: 执行异常 + standard 模式 -> 写入 None 不 raise。"""
        mock_ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] = {
            "type": "optimization"
        }
        mock_ctx.workflow_mode = "standard"

        mock_selector_instance = AsyncMock()
        mock_selector_instance.setup = AsyncMock()
        mock_selector_instance.execute = AsyncMock(
            side_effect=RuntimeError("selector crashed")
        )
        MockSelector.return_value = mock_selector_instance

        stage = ModelSelectionStage()
        # 不应抛出异常
        await stage.execute(mock_ctx)

        assert mock_ctx.artifacts[ArtifactKeys.MODEL_RECOMMENDATION] is None
        assert (
            mock_ctx.artifacts[ArtifactKeys.RECOMMENDED_PRIMARY_MODEL] is None
        )


# ================================================================
# TestReviewStageWriteDefaultArtifacts
# ================================================================


class TestReviewStageWriteDefaultArtifacts:
    """ReviewStage._write_default_artifacts 静态方法测试。"""

    def test_empty_artifacts_writes_defaults(self, mock_ctx):
        """验证: 空 artifacts 时写入默认 REVIEW_RESULT 和 REVIEW_FEEDBACK。"""
        mock_ctx.artifacts = {}
        ReviewStage._write_default_artifacts(mock_ctx)

        # 应写入 REVIEW_RESULT
        assert ArtifactKeys.REVIEW_RESULT in mock_ctx.artifacts
        review = mock_ctx.artifacts[ArtifactKeys.REVIEW_RESULT]
        assert review["overall_rating"] == 0
        assert review["review_status"] == "error"

        # 应写入 REVIEW_FEEDBACK
        assert ArtifactKeys.REVIEW_FEEDBACK in mock_ctx.artifacts
        feedback = mock_ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK]
        assert feedback["overall_rating"] == 0
        assert feedback["suggestions"] == []

    def test_existing_review_result_not_overwritten(self, mock_ctx):
        """验证: 已有 REVIEW_RESULT 时不覆盖, 但补充缺失的 REVIEW_FEEDBACK。"""
        existing_review = {
            "overall_rating": 4,
            "review_status": "pass",
        }
        mock_ctx.artifacts = {
            ArtifactKeys.REVIEW_RESULT: existing_review,
        }

        ReviewStage._write_default_artifacts(mock_ctx)

        # REVIEW_RESULT 不应被覆盖
        assert mock_ctx.artifacts[ArtifactKeys.REVIEW_RESULT] is existing_review
        assert (
            mock_ctx.artifacts[ArtifactKeys.REVIEW_RESULT]["overall_rating"]
            == 4
        )

        # REVIEW_FEEDBACK 应被补充写入
        assert ArtifactKeys.REVIEW_FEEDBACK in mock_ctx.artifacts
        assert (
            mock_ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK]["review_status"]
            == "error"
        )

    def test_existing_feedback_not_overwritten(self, mock_ctx):
        """验证: 已有 REVIEW_FEEDBACK 时也不覆盖。"""
        existing_feedback = {
            "overall_rating": 3,
            "suggestions": ["improve intro"],
            "review_status": "needs_revision",
        }
        mock_ctx.artifacts = {
            ArtifactKeys.REVIEW_FEEDBACK: existing_feedback,
        }

        ReviewStage._write_default_artifacts(mock_ctx)

        # REVIEW_FEEDBACK 不应被覆盖
        assert (
            mock_ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK]
            is existing_feedback
        )
        # REVIEW_RESULT 应被补充写入
        assert ArtifactKeys.REVIEW_RESULT in mock_ctx.artifacts


# ================================================================
# TestReviewStageIdentifyWeakestSections
# ================================================================


class TestReviewStageIdentifyWeakestSections:
    """ReviewStage._identify_weakest_sections 实例方法测试。"""

    def test_identifies_low_score_sections_max_3(self, mock_ctx):
        """验证: 识别低分章节, 最多返回 3 个, 按分数升序排列。"""
        # 构造 user_output.res 包含多个章节
        mock_ctx.user_output.res = {
            "analysisQues": {"response_content": "..."},
            "conclusion": {"response_content": "..."},
            "judge": {"response_content": "..."},
            "ques1": {"response_content": "..."},
            "ques2": {"response_content": "..."},
        }

        review_result = {
            # writing_avg = 2.0 (低于 3.5 阈值)
            "writing_quality": {"average_score": 2.0},
            # content_avg = 4.0 (高于 3.5 阈值, 不弱)
            "content_quality": {"average_score": 4.0},
            # methodology_avg = 3.0 (低于 3.5 阈值)
            "methodology_quality": {"average_score": 3.0},
            # innovation_avg = 5.0 (高于 3.5 阈值, 不弱)
            "innovation_assessment": {"average_score": 5.0},
        }

        stage = ReviewStage()
        result = stage._identify_weakest_sections(mock_ctx, review_result)

        # 弱章节 (score < 3.5 且在 user_output.res 中):
        # - conclusion: writing_avg=2.0
        # - judge: methodology_avg=3.0
        # - ques1: methodology_avg=3.0
        # - ques2: methodology_avg=3.0
        # 共 4 个弱章节, 最多返回 3 个
        assert len(result) == 3
        # 最低分的 conclusion (2.0) 应排在第一
        assert result[0] == "conclusion"
        # 其余 2 个应来自 methodology 相关章节 (judge, ques1, ques2)
        for section in result[1:]:
            assert section in ("judge", "ques1", "ques2")

    def test_no_low_score_returns_empty(self, mock_ctx):
        """验证: 所有章节分数均高于阈值时返回空列表。"""
        mock_ctx.user_output.res = {
            "analysisQues": {"response_content": "..."},
            "conclusion": {"response_content": "..."},
            "judge": {"response_content": "..."},
        }

        review_result = {
            "writing_quality": {"average_score": 4.5},
            "content_quality": {"average_score": 4.0},
            "methodology_quality": {"average_score": 4.0},
            "innovation_assessment": {"average_score": 4.0},
        }

        stage = ReviewStage()
        result = stage._identify_weakest_sections(mock_ctx, review_result)
        assert result == []

    def test_threshold_boundary(self, mock_ctx):
        """验证: 分数恰好等于阈值时不被视为弱章节 (严格小于才弱)。"""
        mock_ctx.user_output.res = {
            "conclusion": {"response_content": "..."},
        }

        review_result = {
            # writing_avg 恰好等于 REVIEW_WEAK_THRESHOLD (3.5)
            "writing_quality": {"average_score": REVIEW_WEAK_THRESHOLD},
            "content_quality": {"average_score": 5.0},
            "methodology_quality": {"average_score": 5.0},
            "innovation_assessment": {"average_score": 5.0},
        }

        stage = ReviewStage()
        result = stage._identify_weakest_sections(mock_ctx, review_result)
        # score == 3.5 不满足 score < 3.5, 不应被识别为弱章节
        assert result == []

    def test_missing_review_keys_defaults_to_5(self, mock_ctx):
        """验证: review_result 中缺少某个维度时, 该维度默认分数为 5 (不弱)。"""
        mock_ctx.user_output.res = {
            "analysisQues": {"response_content": "..."},
            "conclusion": {"response_content": "..."},
        }

        # 只提供部分维度
        review_result = {}

        stage = ReviewStage()
        result = stage._identify_weakest_sections(mock_ctx, review_result)
        # 所有维度 default 为 5.0, 不低于 3.5
        assert result == []


# ================================================================
# TestReviewStageExecute
# ================================================================


class TestReviewStageExecute:
    """ReviewStage.execute 异步方法测试。"""

    @pytest.mark.asyncio
    async def test_execute_fail_award_mode_raises(self, mock_ctx):
        """验证: 执行失败 + award 模式 -> raise 异常。"""
        mock_ctx.workflow_mode = "award"

        stage = ReviewStage()
        with patch.object(
            stage,
            "_do_execute",
            new_callable=AsyncMock,
            side_effect=RuntimeError("reviewer crashed"),
        ):
            with pytest.raises(RuntimeError, match="reviewer crashed"):
                await stage.execute(mock_ctx)

        # 异常前应已写入默认 artifact
        assert ArtifactKeys.REVIEW_RESULT in mock_ctx.artifacts
        assert ArtifactKeys.REVIEW_FEEDBACK in mock_ctx.artifacts
        # send_progress 应被调用 (报告错误)
        mock_ctx.send_progress.assert_called()

    @pytest.mark.asyncio
    async def test_execute_fail_standard_mode_no_raise(self, mock_ctx):
        """验证: 执行失败 + standard 模式 -> 写入默认 artifact 不 raise。"""
        mock_ctx.workflow_mode = "standard"

        stage = ReviewStage()
        with patch.object(
            stage,
            "_do_execute",
            new_callable=AsyncMock,
            side_effect=RuntimeError("reviewer crashed"),
        ):
            # 不应抛出异常
            await stage.execute(mock_ctx)

        # 应写入默认 artifact
        assert ArtifactKeys.REVIEW_RESULT in mock_ctx.artifacts
        review = mock_ctx.artifacts[ArtifactKeys.REVIEW_RESULT]
        assert review["review_status"] == "error"

        assert ArtifactKeys.REVIEW_FEEDBACK in mock_ctx.artifacts
        feedback = mock_ctx.artifacts[ArtifactKeys.REVIEW_FEEDBACK]
        assert feedback["suggestions"] == []

    @pytest.mark.asyncio
    async def test_execute_fail_enhanced_mode_no_raise(self, mock_ctx):
        """验证: 执行失败 + enhanced 模式 -> 同 standard, 不 raise。"""
        mock_ctx.workflow_mode = "enhanced"

        stage = ReviewStage()
        with patch.object(
            stage,
            "_do_execute",
            new_callable=AsyncMock,
            side_effect=ValueError("unexpected error"),
        ):
            # enhanced 模式下不应抛出
            await stage.execute(mock_ctx)

        assert ArtifactKeys.REVIEW_RESULT in mock_ctx.artifacts
        assert ArtifactKeys.REVIEW_FEEDBACK in mock_ctx.artifacts

    @pytest.mark.asyncio
    async def test_execute_success_no_exception(self, mock_ctx):
        """验证: 执行成功时不写入默认 artifact (由 _do_execute 正常写入)。"""
        stage = ReviewStage()
        with patch.object(
            stage,
            "_do_execute",
            new_callable=AsyncMock,
        ) as mock_do:
            await stage.execute(mock_ctx)
            mock_do.assert_awaited_once_with(mock_ctx)

        # _do_execute 正常完成, 不应触发 _write_default_artifacts
        # artifacts 保持为空 (因为 mock 的 _do_execute 什么都没写)
        assert ArtifactKeys.REVIEW_RESULT not in mock_ctx.artifacts
