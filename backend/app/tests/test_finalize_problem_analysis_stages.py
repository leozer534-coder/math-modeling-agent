"""
FinalizeStage 和 ProblemAnalysisStage execute() 测试

覆盖:
  - FinalizeStage.execute(): 保存结果、LaTeX 生成、记忆系统、统计消息、评审结果
  - FinalizeStage._generate_latex(): LaTeX 生成逻辑、异常处理
  - FinalizeStage._save_modeling_experience(): 经验保存逻辑
  - ProblemAnalysisStage.execute(): 分析运行、artifacts 写入、异常处理（optional 模式）
"""

import sys
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.HumanMessage = MagicMock
        _mock.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock

import pytest  # noqa: E402

from app.core.workflow.stages.finalize_stage import FinalizeStage  # noqa: E402
from app.core.workflow.stages.problem_analysis_stage import ProblemAnalysisStage  # noqa: E402
from app.core.workflow.stages.artifact_keys import ArtifactKeys  # noqa: E402
from app.schemas.enums import FormatOutPut  # noqa: E402


# ================================================================
# 测试辅助: Mock PipelineContext
# ================================================================


class _MockPipelineContext:
    """轻量级 PipelineContext mock"""

    def __init__(
        self,
        *,
        task_id: str = "test_task_001",
        work_dir: str = "/tmp/test_work",
        problem=None,
        llms=None,
        agents=None,
        coordinator_response=None,
        modeler_response=None,
        solution_results=None,
        user_output=None,
        artifacts=None,
        start_time=None,
    ):
        self.task_id = task_id
        self.work_dir = work_dir
        self.problem = problem
        self.llms = llms or {}
        self.agents = agents if agents is not None else {}
        self.coordinator_response = coordinator_response
        self.modeler_response = modeler_response
        self.solution_results = solution_results or {}
        self.user_output = user_output
        self.artifacts = artifacts if artifacts is not None else {}
        self.send_progress = AsyncMock()
        self._start_time = start_time or 0

    def elapsed_minutes(self) -> float:
        return 5.0  # 固定返回 5 分钟


# ================================================================
# FinalizeStage 测试
# ================================================================


class TestFinalizeStageName:
    """FinalizeStage 基础属性测试"""

    @pytest.mark.unit
    def test_stage_name(self):
        """验证: Stage 名称正确"""
        stage = FinalizeStage()
        assert stage.name == "finalize"


class TestFinalizeStageExecute:
    """FinalizeStage.execute 测试"""

    def _make_problem(self, format_output=None, comp_template="cumcm"):
        """创建 mock Problem"""
        problem = MagicMock()
        problem.format_output = format_output or "Markdown"
        problem.comp_template = comp_template
        problem.ques_all = "这是一道线性规划问题..."
        problem.title = "论文标题"
        problem.team_control_number = "2024001"
        problem.problem_choice = "A"
        return problem

    def _make_user_output(self):
        """创建 mock UserOutput"""
        user_output = MagicMock()
        user_output.save_result = MagicMock()
        user_output.get_result_to_save = MagicMock(return_value="# 论文内容\n\n正文...")
        return user_output

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_basic_save_result(self, mock_settings, mock_redis):
        """验证: 基本流程 - save_result 被调用"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem()
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(problem=problem, user_output=user_output)

        stage = FinalizeStage()
        await stage.execute(ctx)

        # 断言: save_result 被调用
        user_output.save_result.assert_called_once()

        # 断言: 发送了完成消息
        mock_redis.publish_message.assert_called()

        # 断言: 进度消息
        assert ctx.send_progress.await_count >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_completion_message_includes_time(self, mock_settings, mock_redis):
        """验证: 完成消息包含用时信息"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem()
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(problem=problem, user_output=user_output)

        stage = FinalizeStage()
        await stage.execute(ctx)

        # 检查 redis 消息内容
        call_args = mock_redis.publish_message.call_args
        message = call_args.args[1]
        assert "5.0分钟" in message.content
        assert message.type == "success"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_review_result_included_in_message(self, mock_settings, mock_redis):
        """验证: 有评审结果时包含在完成消息中"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem()
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            artifacts={ArtifactKeys.REVIEW_RESULT: {"overall_rating": 4}},
        )

        stage = FinalizeStage()
        await stage.execute(ctx)

        call_args = mock_redis.publish_message.call_args
        message = call_args.args[1]
        assert "4/5" in message.content

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_review_result_zero_rating_excluded(self, mock_settings, mock_redis):
        """验证: 评审评分为 0 时不包含在完成消息中"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem()
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            artifacts={ArtifactKeys.REVIEW_RESULT: {"overall_rating": 0}},
        )

        stage = FinalizeStage()
        await stage.execute(ctx)

        call_args = mock_redis.publish_message.call_args
        message = call_args.args[1]
        assert "评审" not in message.content

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_no_review_result(self, mock_settings, mock_redis):
        """验证: 无评审结果时完成消息不含评审信息"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem()
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(problem=problem, user_output=user_output)

        stage = FinalizeStage()
        await stage.execute(ctx)

        call_args = mock_redis.publish_message.call_args
        message = call_args.args[1]
        assert "评审" not in message.content

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.generate_latex_from_markdown")
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_latex_generation_triggered(
        self, mock_settings, mock_redis, mock_gen_latex
    ):
        """验证: format_output 为 LaTeX 时触发 LaTeX 生成"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem(format_output=FormatOutPut.LaTeX)
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            artifacts={
                ArtifactKeys.ABSTRACT_CONTENT: "摘要文本",
                ArtifactKeys.KEYWORDS: ["关键词1", "关键词2"],
            },
        )

        stage = FinalizeStage()
        await stage.execute(ctx)

        # 断言: LaTeX 生成函数被调用
        mock_gen_latex.assert_called_once()
        call_kwargs = mock_gen_latex.call_args.kwargs
        assert call_kwargs["output_path"] == f"{ctx.work_dir}/paper.tex"
        assert call_kwargs["abstract"] == "摘要文本"
        assert call_kwargs["keywords"] == ["关键词1", "关键词2"]
        assert call_kwargs["title"] == "论文标题"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_latex_not_triggered_for_markdown(self, mock_settings, mock_redis):
        """验证: format_output 非 LaTeX 时不触发 LaTeX 生成"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem(format_output="Markdown")
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(problem=problem, user_output=user_output)

        with patch(
            "app.core.workflow.stages.finalize_stage.generate_latex_from_markdown"
        ) as mock_gen:
            stage = FinalizeStage()
            await stage.execute(ctx)
            mock_gen.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.generate_latex_from_markdown")
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_latex_failure_non_fatal(
        self, mock_settings, mock_redis, mock_gen_latex
    ):
        """验证: LaTeX 生成失败不中断主流程"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()
        mock_gen_latex.side_effect = Exception("LaTeX 编译失败")

        problem = self._make_problem(format_output=FormatOutPut.LaTeX)
        user_output = self._make_user_output()
        ctx = _MockPipelineContext(problem=problem, user_output=user_output)

        stage = FinalizeStage()
        # 不应抛出异常
        await stage.execute(ctx)

        # 断言: 发送了警告消息
        warning_calls = [
            call for call in mock_redis.publish_message.call_args_list
            if hasattr(call.args[1], 'type') and call.args[1].type == "warning"
        ]
        assert len(warning_calls) >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_save_result_failure_propagates(self, mock_settings, mock_redis):
        """验证: save_result 失败时异常向上传播"""
        mock_settings.ENABLE_MEMORY_SYSTEM = False
        mock_redis.publish_message = AsyncMock()

        problem = self._make_problem()
        user_output = self._make_user_output()
        user_output.save_result.side_effect = IOError("磁盘已满")
        ctx = _MockPipelineContext(problem=problem, user_output=user_output)

        stage = FinalizeStage()
        with pytest.raises(IOError, match="磁盘已满"):
            await stage.execute(ctx)


class TestFinalizeStageSaveExperience:
    """FinalizeStage._save_modeling_experience 测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_memory_system_called_when_enabled(self, mock_settings, mock_redis):
        """验证: ENABLE_MEMORY_SYSTEM=True 时调用保存经验"""
        mock_settings.ENABLE_MEMORY_SYSTEM = True
        mock_redis.publish_message = AsyncMock()

        modeler_agent = MagicMock()
        modeler_agent._memory_manager = MagicMock()
        modeler_agent.save_experience = AsyncMock()

        modeler_response = MagicMock()
        modeler_response.questions_solution = {"Q1": "线性规划"}

        problem = MagicMock()
        problem.format_output = "Markdown"
        problem.ques_all = "建模问题"

        user_output = MagicMock()
        user_output.save_result = MagicMock()

        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            agents={"modeler": modeler_agent},
            modeler_response=modeler_response,
            solution_results={"results": {"Q1": {"success": True}}},
        )

        stage = FinalizeStage()
        await stage.execute(ctx)

        # 断言: save_experience 被调用
        modeler_agent.save_experience.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_memory_skip_when_no_modeler(self, mock_settings, mock_redis):
        """验证: 无 modeler agent 时跳过经验保存"""
        mock_settings.ENABLE_MEMORY_SYSTEM = True
        mock_redis.publish_message = AsyncMock()

        problem = MagicMock()
        problem.format_output = "Markdown"

        user_output = MagicMock()
        user_output.save_result = MagicMock()

        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            agents={},
        )

        stage = FinalizeStage()
        # 不应抛出异常
        await stage.execute(ctx)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_memory_failure_non_fatal(self, mock_settings, mock_redis):
        """验证: 记忆系统保存失败不中断主流程"""
        mock_settings.ENABLE_MEMORY_SYSTEM = True
        mock_redis.publish_message = AsyncMock()

        modeler_agent = MagicMock()
        modeler_agent._memory_manager = MagicMock()
        modeler_agent.save_experience = AsyncMock(
            side_effect=RuntimeError("Redis 不可用")
        )

        problem = MagicMock()
        problem.format_output = "Markdown"
        problem.ques_all = "建模问题"

        user_output = MagicMock()
        user_output.save_result = MagicMock()

        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            agents={"modeler": modeler_agent},
            modeler_response=MagicMock(questions_solution={}),
            solution_results={"results": {}},
        )

        stage = FinalizeStage()
        # 不应抛出异常
        await stage.execute(ctx)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.finalize_stage.redis_manager")
    @patch("app.core.workflow.stages.finalize_stage.settings")
    async def test_failed_questions_detected(self, mock_settings, mock_redis):
        """验证: 失败的子问题被正确识别"""
        mock_settings.ENABLE_MEMORY_SYSTEM = True
        mock_redis.publish_message = AsyncMock()

        modeler_agent = MagicMock()
        modeler_agent._memory_manager = MagicMock()
        modeler_agent.save_experience = AsyncMock()

        problem = MagicMock()
        problem.format_output = "Markdown"
        problem.ques_all = "建模问题"

        user_output = MagicMock()
        user_output.save_result = MagicMock()

        ctx = _MockPipelineContext(
            problem=problem,
            user_output=user_output,
            agents={"modeler": modeler_agent},
            modeler_response=MagicMock(questions_solution={"Q1": "方法1", "Q2": "方法2"}),
            solution_results={
                "results": {
                    "Q1": {"success": True},
                    "Q2": {"success": False},
                }
            },
        )

        stage = FinalizeStage()
        await stage.execute(ctx)

        # 断言: save_experience 被调用，且 outcome 为 "partial"（50% 失败）
        call_kwargs = modeler_agent.save_experience.call_args.kwargs
        assert call_kwargs["outcome"] == "partial"
        assert any("Q2" in lesson for lesson in call_kwargs["lessons"])


# ================================================================
# ProblemAnalysisStage 测试
# ================================================================


class TestProblemAnalysisStageName:
    """ProblemAnalysisStage 基础属性测试"""

    @pytest.mark.unit
    def test_stage_name(self):
        """验证: Stage 名称正确"""
        stage = ProblemAnalysisStage()
        assert stage.name == "problem_analysis"


class TestProblemAnalysisStageExecute:
    """ProblemAnalysisStage.execute 测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.problem_analysis_stage.ProblemAnalyzer")
    async def test_success_flow(self, mock_analyzer_cls):
        """验证: 正常流程 - 分析结果写入 artifacts"""
        # 准备 mock 分析结果
        analysis_result = MagicMock()
        analysis_result.problem_type = "optimization"
        analysis_result.recommended_approaches = ["线性规划", "整数规划"]

        mock_analyzer = MagicMock()
        mock_analyzer.setup = AsyncMock()
        mock_analyzer.execute = AsyncMock(return_value=analysis_result)
        mock_analyzer.cleanup = AsyncMock()
        mock_analyzer_cls.return_value = mock_analyzer

        ctx = _MockPipelineContext(
            llms={"modeler": MagicMock()},
            coordinator_response="协调器分析结果",
        )

        stage = ProblemAnalysisStage()
        await stage.execute(ctx)

        # 断言: ProblemAnalyzer 正确创建
        mock_analyzer_cls.assert_called_once_with(
            task_id=ctx.task_id, model=ctx.llms["modeler"]
        )
        mock_analyzer.setup.assert_awaited_once()
        mock_analyzer.execute.assert_awaited_once_with(
            coordinator_data="协调器分析结果"
        )
        mock_analyzer.cleanup.assert_awaited_once()

        # 断言: artifacts 写入
        assert ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] is analysis_result
        assert ctx.artifacts[ArtifactKeys.PROBLEM_TYPE] == "optimization"
        assert ctx.artifacts[ArtifactKeys.RECOMMENDED_APPROACHES] == [
            "线性规划",
            "整数规划",
        ]

        # 断言: 进度消息
        assert ctx.send_progress.await_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.problem_analysis_stage.ProblemAnalyzer")
    async def test_exception_sets_analysis_to_none(self, mock_analyzer_cls):
        """验证: 异常时 PROBLEM_ANALYSIS 设为 None（optional 阶段模式）"""
        mock_analyzer = MagicMock()
        mock_analyzer.setup = AsyncMock(side_effect=RuntimeError("LLM 不可用"))
        mock_analyzer_cls.return_value = mock_analyzer

        ctx = _MockPipelineContext(
            llms={"modeler": MagicMock()},
            coordinator_response="协调器分析结果",
        )

        stage = ProblemAnalysisStage()
        # 不应抛出异常
        await stage.execute(ctx)

        # 断言: PROBLEM_ANALYSIS 设为 None
        assert ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.problem_analysis_stage.ProblemAnalyzer")
    async def test_no_problem_type_attribute(self, mock_analyzer_cls):
        """验证: 分析结果无 problem_type 属性时不写入该 artifact"""
        analysis_result = MagicMock(spec=[])  # 空 spec，无属性

        mock_analyzer = MagicMock()
        mock_analyzer.setup = AsyncMock()
        mock_analyzer.execute = AsyncMock(return_value=analysis_result)
        mock_analyzer.cleanup = AsyncMock()
        mock_analyzer_cls.return_value = mock_analyzer

        ctx = _MockPipelineContext(
            llms={"modeler": MagicMock()},
            coordinator_response="协调器分析结果",
        )

        stage = ProblemAnalysisStage()
        await stage.execute(ctx)

        # 断言: PROBLEM_ANALYSIS 写入，但 PROBLEM_TYPE 不存在
        assert ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] is analysis_result
        assert ArtifactKeys.PROBLEM_TYPE not in ctx.artifacts
        assert ArtifactKeys.RECOMMENDED_APPROACHES not in ctx.artifacts

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.problem_analysis_stage.ProblemAnalyzer")
    async def test_execute_failure_does_not_propagate(self, mock_analyzer_cls):
        """验证: execute 异常不向上传播"""
        mock_analyzer = MagicMock()
        mock_analyzer.setup = AsyncMock()
        mock_analyzer.execute = AsyncMock(
            side_effect=ValueError("分析数据格式异常")
        )
        mock_analyzer_cls.return_value = mock_analyzer

        ctx = _MockPipelineContext(
            llms={"modeler": MagicMock()},
            coordinator_response="协调器分析结果",
        )

        stage = ProblemAnalysisStage()
        # 不应抛出异常
        await stage.execute(ctx)

        # 断言: 正确设为 None
        assert ctx.artifacts[ArtifactKeys.PROBLEM_ANALYSIS] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.problem_analysis_stage.ProblemAnalyzer")
    async def test_progress_sent_even_on_failure(self, mock_analyzer_cls):
        """验证: 异常时仍发送完成进度"""
        mock_analyzer = MagicMock()
        mock_analyzer.setup = AsyncMock(side_effect=Exception("任意错误"))
        mock_analyzer_cls.return_value = mock_analyzer

        ctx = _MockPipelineContext(
            llms={"modeler": MagicMock()},
            coordinator_response="协调器分析结果",
        )

        stage = ProblemAnalysisStage()
        await stage.execute(ctx)

        # 断言: 至少发送了 2 次进度（开始 + 完成）
        assert ctx.send_progress.await_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.problem_analysis_stage.ProblemAnalyzer")
    async def test_uses_modeler_llm(self, mock_analyzer_cls):
        """验证: 使用 modeler LLM 实例"""
        analysis_result = MagicMock()
        analysis_result.problem_type = "prediction"
        analysis_result.recommended_approaches = ["ARIMA"]

        mock_analyzer = MagicMock()
        mock_analyzer.setup = AsyncMock()
        mock_analyzer.execute = AsyncMock(return_value=analysis_result)
        mock_analyzer.cleanup = AsyncMock()
        mock_analyzer_cls.return_value = mock_analyzer

        modeler_llm = MagicMock(name="modeler_llm_instance")
        ctx = _MockPipelineContext(
            llms={"modeler": modeler_llm, "coder": MagicMock()},
            coordinator_response="协调器分析结果",
        )

        stage = ProblemAnalysisStage()
        await stage.execute(ctx)

        # 断言: 使用的是 modeler LLM
        mock_analyzer_cls.assert_called_once_with(
            task_id=ctx.task_id, model=modeler_llm
        )
