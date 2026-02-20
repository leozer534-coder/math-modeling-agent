"""
LLM 模块测试
测试 LLM 调用、聊天功能等
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMInitialization:
    """测试 LLM 初始化"""

    def test_llm_class_exists(self):
        """测试 LLM 类存在"""
        from app.core.llm.llm import LLM
        assert LLM is not None

    def test_simple_chat_function_exists(self):
        """测试 simple_chat 函数存在"""
        from app.core.llm.llm import simple_chat
        assert callable(simple_chat)


class TestLLMConfiguration:
    """测试 LLM 配置"""

    @pytest.fixture
    def mock_settings(self):
        """模拟配置"""
        settings = MagicMock()
        settings.COORDINATOR_API_KEY = "test_key"
        settings.COORDINATOR_MODEL = "test_model"
        settings.COORDINATOR_BASE_URL = "https://api.test.com"
        return settings

    def test_llm_initialization_with_params(self):
        """测试带参数的 LLM 初始化"""
        from app.core.llm.llm import LLM

        llm = LLM(
            task_id="test_task",
            api_key="test_api_key",
            model="gpt-4",
            base_url="https://api.openai.com/v1"
        )

        assert llm.task_id == "test_task"
        assert llm.api_key == "test_api_key"
        # 模型名会自动添加 openai/ 前缀
        assert "gpt-4" in llm.model


class TestSimpleChat:
    """测试 simple_chat 函数"""

    @pytest.mark.skip(reason="需要真实 API 或完整 mock 环境")
    @pytest.mark.asyncio
    async def test_simple_chat_basic(self):
        """测试基本聊天功能"""
        from app.core.llm.llm import LLM, simple_chat

        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = "test_key"
        mock_llm.model = "test_model"
        mock_llm.base_url = "https://api.test.com"

        with patch('litellm.acompletion', new_callable=AsyncMock) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "测试响应"
            mock_completion.return_value = mock_response

            history = [{"role": "user", "content": "测试"}]
            result = await simple_chat(mock_llm, history)

            assert result == "测试响应"


class TestLLMChat:
    """测试 LLM chat 方法"""

    @pytest.fixture
    def llm_instance(self):
        """创建 LLM 实例"""
        from app.core.llm.llm import LLM

        return LLM(
            task_id="test_task",
            api_key="test_api_key",
            model="gpt-4",
            base_url="https://api.openai.com/v1"
        )

    @pytest.mark.skip(reason="需要真实 API 或完整 mock 环境")
    @pytest.mark.asyncio
    async def test_llm_chat_method(self, llm_instance):
        """测试 LLM chat 方法"""
        # Mock 需要放在实际调用位置
        with patch('app.core.llm.llm.litellm.acompletion', new_callable=AsyncMock) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "AI 响应"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            mock_completion.return_value = mock_response

            history = [
                {"role": "system", "content": "你是助手"},
                {"role": "user", "content": "你好"}
            ]

            result = await llm_instance.chat(
                history=history,
                agent_name="TestAgent",
                sub_title="测试"
            )

            assert result is not None
            assert result.choices[0].message.content == "AI 响应"
