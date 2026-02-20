"""
CoordinatorStage 和 SetupStage execute() 测试

覆盖:
  - CoordinatorStage.execute(): LLM 创建、CoordinatorAgent 运行、上下文写入、异常处理
  - SetupStage.execute(): 代码解释器创建、Agent 实例创建、UserOutput 创建、异常处理
"""

import sys
from unittest.mock import MagicMock, AsyncMock, patch

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.HumanMessage = MagicMock
        _mock.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock

import pytest  # noqa: E402

from app.core.workflow.stages.coordinator_stage import CoordinatorStage  # noqa: E402
from app.core.workflow.stages.setup_stage import SetupStage  # noqa: E402


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
        agent_configs=None,
        ques_count: int = 0,
    ):
        self.task_id = task_id
        self.work_dir = work_dir
        self.problem = problem
        self.llms = llms or {}
        self.agents = agents if agents is not None else {}
        self.agent_configs = agent_configs
        self.ques_count = ques_count
        self.coordinator_response = None
        self.questions = None
        self.llm_factory = None
        self.code_interpreter = None
        self.user_output = None
        self.artifacts = {}
        self.send_progress = AsyncMock()


# ================================================================
# CoordinatorStage 测试
# ================================================================


class TestCoordinatorStageName:
    """CoordinatorStage 基础属性测试"""

    @pytest.mark.unit
    def test_stage_name(self):
        """验证: Stage 名称正确"""
        stage = CoordinatorStage()
        assert stage.name == "coordinate"


class TestCoordinatorStageExecute:
    """CoordinatorStage.execute 测试"""

    def _make_problem(self, ques_all: str = "请建立线性规划模型") -> MagicMock:
        """创建 mock Problem"""
        problem = MagicMock()
        problem.ques_all = ques_all
        return problem

    def _make_coordinator_response(
        self, questions: dict | None = None, ques_count: int = 3
    ) -> MagicMock:
        """创建 mock CoordinatorAgent 响应"""
        response = MagicMock()
        response.questions = questions or {"Q1": "子问题1", "Q2": "子问题2", "Q3": "子问题3"}
        response.ques_count = ques_count
        return response

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.coordinator_stage.CoordinatorAgent")
    @patch("app.core.workflow.stages.coordinator_stage.LLMFactory")
    async def test_success_flow(self, mock_factory_cls, mock_agent_cls):
        """验证: 正常流程 - LLM 创建、Agent 运行、上下文写入"""
        # 准备
        mock_llms = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
        mock_factory = MagicMock()
        mock_factory.get_all_llms.return_value = mock_llms
        mock_factory_cls.return_value = mock_factory

        response = self._make_coordinator_response()
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=response)
        mock_agent_cls.return_value = mock_agent

        problem = self._make_problem()
        ctx = _MockPipelineContext(problem=problem)

        # 执行
        stage = CoordinatorStage()
        await stage.execute(ctx)

        # 断言: LLMFactory 被创建
        mock_factory_cls.assert_called_once_with(ctx.task_id, ctx.agent_configs)
        assert ctx.llm_factory is mock_factory

        # 断言: 4 个 LLM 写入 ctx.llms
        assert len(ctx.llms) == 4
        assert ctx.llms["coordinator"] is mock_llms[0]
        assert ctx.llms["modeler"] is mock_llms[1]
        assert ctx.llms["coder"] is mock_llms[2]
        assert ctx.llms["writer"] is mock_llms[3]

        # 断言: CoordinatorAgent 创建和运行
        mock_agent_cls.assert_called_once_with(ctx.task_id, mock_llms[0])
        mock_agent.run.assert_awaited_once_with(problem.ques_all)

        # 断言: 上下文写入
        assert ctx.coordinator_response is response
        assert ctx.questions == response.questions
        assert ctx.ques_count == 3

        # 断言: Agent 存储
        assert ctx.agents["coordinator"] is mock_agent

        # 断言: 进度消息
        assert ctx.send_progress.await_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.coordinator_stage.CoordinatorAgent")
    @patch("app.core.workflow.stages.coordinator_stage.LLMFactory")
    async def test_llm_factory_failure_propagates(self, mock_factory_cls, mock_agent_cls):
        """验证: LLMFactory 创建失败时异常向上传播"""
        mock_factory_cls.side_effect = ValueError("API Key 无效")

        problem = self._make_problem()
        ctx = _MockPipelineContext(problem=problem)

        stage = CoordinatorStage()
        with pytest.raises(ValueError, match="API Key 无效"):
            await stage.execute(ctx)

        # 断言: 发送了失败进度
        calls = [
            call for call in ctx.send_progress.call_args_list
            if "失败" in str(call)
        ]
        assert len(calls) >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.coordinator_stage.CoordinatorAgent")
    @patch("app.core.workflow.stages.coordinator_stage.LLMFactory")
    async def test_coordinator_agent_failure_propagates(self, mock_factory_cls, mock_agent_cls):
        """验证: CoordinatorAgent.run() 失败时异常向上传播"""
        mock_factory = MagicMock()
        mock_factory.get_all_llms.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
        mock_factory_cls.return_value = mock_factory

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM 调用超时"))
        mock_agent_cls.return_value = mock_agent

        problem = self._make_problem()
        ctx = _MockPipelineContext(problem=problem)

        stage = CoordinatorStage()
        with pytest.raises(RuntimeError, match="LLM 调用超时"):
            await stage.execute(ctx)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.coordinator_stage.CoordinatorAgent")
    @patch("app.core.workflow.stages.coordinator_stage.LLMFactory")
    async def test_agent_configs_forwarded(self, mock_factory_cls, mock_agent_cls):
        """验证: agent_configs 被正确传递给 LLMFactory"""
        mock_factory = MagicMock()
        mock_factory.get_all_llms.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
        mock_factory_cls.return_value = mock_factory

        response = self._make_coordinator_response()
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=response)
        mock_agent_cls.return_value = mock_agent

        custom_configs = {"coordinator": {"model": "gpt-4"}}
        problem = self._make_problem()
        ctx = _MockPipelineContext(problem=problem, agent_configs=custom_configs)

        stage = CoordinatorStage()
        await stage.execute(ctx)

        # 断言: agent_configs 被传递
        mock_factory_cls.assert_called_once_with(ctx.task_id, custom_configs)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.coordinator_stage.CoordinatorAgent")
    @patch("app.core.workflow.stages.coordinator_stage.LLMFactory")
    async def test_ques_count_written(self, mock_factory_cls, mock_agent_cls):
        """验证: 单问题场景下 ques_count 正确写入"""
        mock_factory = MagicMock()
        mock_factory.get_all_llms.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
        mock_factory_cls.return_value = mock_factory

        response = self._make_coordinator_response(
            questions={"Q1": "唯一子问题"}, ques_count=1
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=response)
        mock_agent_cls.return_value = mock_agent

        problem = self._make_problem()
        ctx = _MockPipelineContext(problem=problem)

        stage = CoordinatorStage()
        await stage.execute(ctx)

        assert ctx.ques_count == 1
        assert len(ctx.questions) == 1


# ================================================================
# SetupStage 测试
# ================================================================


class TestSetupStageName:
    """SetupStage 基础属性测试"""

    @pytest.mark.unit
    def test_stage_name(self):
        """验证: Stage 名称正确"""
        stage = SetupStage()
        assert stage.name == "setup"


class TestSetupStageExecute:
    """SetupStage.execute 测试"""

    def _make_ctx(self, **kwargs) -> _MockPipelineContext:
        """创建含必要 llms 的 mock ctx"""
        problem = MagicMock()
        problem.comp_template = "cumcm"
        problem.format_output = "Markdown"
        ctx = _MockPipelineContext(
            problem=problem,
            llms={
                "coordinator": MagicMock(),
                "modeler": MagicMock(),
                "coder": MagicMock(),
                "writer": MagicMock(),
            },
            ques_count=3,
            **kwargs,
        )
        return ctx

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.setup_stage.settings")
    @patch("app.core.workflow.stages.setup_stage.UserOutput")
    @patch("app.core.workflow.stages.setup_stage.WriterAgent")
    @patch("app.core.workflow.stages.setup_stage.CoderAgent")
    @patch("app.core.workflow.stages.setup_stage.OpenAlexScholar")
    @patch("app.core.workflow.stages.setup_stage.NotebookSerializer")
    @patch("app.core.workflow.stages.setup_stage.create_interpreter")
    async def test_success_flow(
        self,
        mock_create_interp,
        mock_nb_serializer_cls,
        mock_scholar_cls,
        mock_coder_cls,
        mock_writer_cls,
        mock_user_output_cls,
        mock_settings,
    ):
        """验证: 正常流程 - 所有组件被创建并写入上下文"""
        mock_settings.CODE_EXECUTION_TIMEOUT = 30
        mock_settings.OPENALEX_EMAIL = "test@example.com"
        mock_settings.MAX_CHAT_TURNS = 10
        mock_settings.MAX_RETRIES = 3
        mock_settings.ENABLE_MEMORY_SYSTEM = False

        mock_interpreter = MagicMock()
        mock_create_interp.return_value = mock_interpreter
        mock_coder = MagicMock()
        mock_coder_cls.return_value = mock_coder
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer
        mock_user_output = MagicMock()
        mock_user_output_cls.return_value = mock_user_output

        ctx = self._make_ctx()

        stage = SetupStage()
        await stage.execute(ctx)

        # 断言: 代码解释器创建
        mock_create_interp.assert_awaited_once()
        assert ctx.code_interpreter is mock_interpreter

        # 断言: Agent 创建和存储
        assert ctx.agents["coder"] is mock_coder
        assert ctx.agents["writer"] is mock_writer

        # 断言: UserOutput 创建
        mock_user_output_cls.assert_called_once_with(
            work_dir=ctx.work_dir,
            ques_count=ctx.ques_count,
            comp_template=ctx.problem.comp_template,
        )
        assert ctx.user_output is mock_user_output

        # 断言: 进度消息
        assert ctx.send_progress.await_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.setup_stage.create_interpreter")
    async def test_interpreter_failure_propagates(self, mock_create_interp):
        """验证: 代码解释器创建失败时异常向上传播"""
        mock_create_interp.side_effect = RuntimeError("Docker 不可用")

        ctx = self._make_ctx()

        stage = SetupStage()
        with pytest.raises(RuntimeError, match="Docker 不可用"):
            await stage.execute(ctx)

        # 断言: 发送了失败进度
        fail_calls = [
            call for call in ctx.send_progress.call_args_list
            if "失败" in str(call)
        ]
        assert len(fail_calls) >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.setup_stage.settings")
    @patch("app.core.workflow.stages.setup_stage.UserOutput")
    @patch("app.core.workflow.stages.setup_stage.WriterAgent")
    @patch("app.core.workflow.stages.setup_stage.CoderAgent")
    @patch("app.core.workflow.stages.setup_stage.OpenAlexScholar")
    @patch("app.core.workflow.stages.setup_stage.NotebookSerializer")
    @patch("app.core.workflow.stages.setup_stage.create_interpreter")
    async def test_coder_agent_receives_correct_params(
        self,
        mock_create_interp,
        mock_nb_serializer_cls,
        mock_scholar_cls,
        mock_coder_cls,
        mock_writer_cls,
        mock_user_output_cls,
        mock_settings,
    ):
        """验证: CoderAgent 接收到正确的参数"""
        mock_settings.CODE_EXECUTION_TIMEOUT = 30
        mock_settings.OPENALEX_EMAIL = "test@example.com"
        mock_settings.MAX_CHAT_TURNS = 10
        mock_settings.MAX_RETRIES = 3
        mock_settings.ENABLE_MEMORY_SYSTEM = False

        mock_interpreter = MagicMock()
        mock_create_interp.return_value = mock_interpreter

        ctx = self._make_ctx()

        stage = SetupStage()
        await stage.execute(ctx)

        # 断言: CoderAgent 的关键参数
        call_kwargs = mock_coder_cls.call_args
        assert call_kwargs.kwargs["task_id"] == ctx.task_id
        assert call_kwargs.kwargs["model"] is ctx.llms["coder"]
        assert call_kwargs.kwargs["work_dir"] == ctx.work_dir
        assert call_kwargs.kwargs["code_interpreter"] is mock_interpreter
        assert call_kwargs.kwargs["comp_template"] == "cumcm"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.setup_stage.settings")
    @patch("app.core.workflow.stages.setup_stage.UserOutput")
    @patch("app.core.workflow.stages.setup_stage.WriterAgent")
    @patch("app.core.workflow.stages.setup_stage.CoderAgent")
    @patch("app.core.workflow.stages.setup_stage.OpenAlexScholar")
    @patch("app.core.workflow.stages.setup_stage.NotebookSerializer")
    @patch("app.core.workflow.stages.setup_stage.create_interpreter")
    async def test_writer_agent_receives_correct_params(
        self,
        mock_create_interp,
        mock_nb_serializer_cls,
        mock_scholar_cls,
        mock_coder_cls,
        mock_writer_cls,
        mock_user_output_cls,
        mock_settings,
    ):
        """验证: WriterAgent 接收到正确的参数"""
        mock_settings.CODE_EXECUTION_TIMEOUT = 30
        mock_settings.OPENALEX_EMAIL = "test@example.com"
        mock_settings.MAX_CHAT_TURNS = 10
        mock_settings.MAX_RETRIES = 3
        mock_settings.ENABLE_MEMORY_SYSTEM = False

        mock_create_interp.return_value = MagicMock()

        ctx = self._make_ctx()

        stage = SetupStage()
        await stage.execute(ctx)

        # 断言: WriterAgent 的关键参数
        call_kwargs = mock_writer_cls.call_args
        assert call_kwargs.kwargs["task_id"] == ctx.task_id
        assert call_kwargs.kwargs["model"] is ctx.llms["writer"]
        assert call_kwargs.kwargs["comp_template"] == "cumcm"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.setup_stage.settings")
    @patch("app.core.workflow.stages.setup_stage.UserOutput")
    @patch("app.core.workflow.stages.setup_stage.WriterAgent")
    @patch("app.core.workflow.stages.setup_stage.CoderAgent")
    @patch("app.core.workflow.stages.setup_stage.OpenAlexScholar")
    @patch("app.core.workflow.stages.setup_stage.NotebookSerializer")
    @patch("app.core.workflow.stages.setup_stage.create_interpreter")
    async def test_notebook_serializer_uses_work_dir(
        self,
        mock_create_interp,
        mock_nb_serializer_cls,
        mock_scholar_cls,
        mock_coder_cls,
        mock_writer_cls,
        mock_user_output_cls,
        mock_settings,
    ):
        """验证: NotebookSerializer 使用 ctx.work_dir"""
        mock_settings.CODE_EXECUTION_TIMEOUT = 30
        mock_settings.OPENALEX_EMAIL = "test@example.com"
        mock_settings.MAX_CHAT_TURNS = 10
        mock_settings.MAX_RETRIES = 3
        mock_settings.ENABLE_MEMORY_SYSTEM = False

        mock_create_interp.return_value = MagicMock()

        ctx = self._make_ctx(work_dir="/custom/work/dir")

        stage = SetupStage()
        await stage.execute(ctx)

        mock_nb_serializer_cls.assert_called_once_with(work_dir="/custom/work/dir")

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.core.workflow.stages.setup_stage.settings")
    @patch("app.core.workflow.stages.setup_stage.UserOutput")
    @patch("app.core.workflow.stages.setup_stage.WriterAgent")
    @patch("app.core.workflow.stages.setup_stage.CoderAgent", side_effect=TypeError("参数错误"))
    @patch("app.core.workflow.stages.setup_stage.OpenAlexScholar")
    @patch("app.core.workflow.stages.setup_stage.NotebookSerializer")
    @patch("app.core.workflow.stages.setup_stage.create_interpreter")
    async def test_coder_creation_failure_propagates(
        self,
        mock_create_interp,
        mock_nb_serializer_cls,
        mock_scholar_cls,
        mock_coder_cls,
        mock_writer_cls,
        mock_user_output_cls,
        mock_settings,
    ):
        """验证: CoderAgent 创建失败时异常向上传播"""
        mock_settings.CODE_EXECUTION_TIMEOUT = 30
        mock_settings.OPENALEX_EMAIL = "test@example.com"
        mock_settings.MAX_CHAT_TURNS = 10
        mock_settings.MAX_RETRIES = 3
        mock_settings.ENABLE_MEMORY_SYSTEM = False

        mock_create_interp.return_value = MagicMock()

        ctx = self._make_ctx()

        stage = SetupStage()
        with pytest.raises(TypeError, match="参数错误"):
            await stage.execute(ctx)
