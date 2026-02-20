"""
Agent 基类测试模块
测试 Agent 基类的核心功能：对话管理、记忆清理、历史记录处理
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAgentBase:
    """测试 Agent 基类"""

    @pytest.fixture
    def mock_llm(self):
        """模拟 LLM 实例"""
        llm = MagicMock()
        llm.chat = AsyncMock()

        # 模拟响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "测试响应内容"
        llm.chat.return_value = mock_response

        return llm

    @pytest.fixture
    def agent(self, mock_llm):
        """创建测试用 Agent 实例"""
        from app.core.agents.agent import Agent

        return Agent(
            task_id="test_task_001",
            model=mock_llm,
            max_chat_turns=30,
            max_memory=12
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        assert agent.task_id == "test_task_001"
        assert agent.max_chat_turns == 30
        assert agent.max_memory == 12
        assert agent.chat_history == []
        assert agent.current_chat_turns == 0

    @pytest.mark.asyncio
    async def test_append_chat_history(self, agent):
        """测试添加聊天历史"""
        msg = {"role": "user", "content": "测试消息"}
        await agent.append_chat_history(msg)

        assert len(agent.chat_history) == 1
        assert agent.chat_history[0] == msg

    @pytest.mark.asyncio
    async def test_run_raises_not_implemented(self, agent):
        """测试基类 run() 抛出 NotImplementedError，子类必须覆写"""
        with pytest.raises(NotImplementedError, match="子类必须实现 run\\(\\) 方法"):
            await agent.run(
                prompt="测试提示",
                system_prompt="系统提示",
                sub_title="测试"
            )

    def test_format_history_for_summary(self, agent):
        """测试历史记录格式化"""
        history = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"}
        ]

        formatted = agent._format_history_for_summary(history)

        assert "user: 问题1" in formatted
        assert "assistant: 回答1" in formatted

    def test_format_history_truncates_long_content(self, agent):
        """测试长内容截断"""
        long_content = "a" * 1000
        history = [{"role": "user", "content": long_content}]

        formatted = agent._format_history_for_summary(history)

        assert len(formatted) < 1000
        assert "..." in formatted

    def test_is_safe_cut_point_empty_history(self, agent):
        """测试空历史的安全切割点检查"""
        result = agent._is_safe_cut_point(0)
        assert result is True

    def test_is_safe_cut_point_with_messages(self, agent):
        """测试有消息时的安全切割点检查"""
        agent.chat_history = [
            {"role": "system", "content": "系统"},
            {"role": "user", "content": "用户"},
            {"role": "assistant", "content": "助手"}
        ]

        result = agent._is_safe_cut_point(1)
        assert result is True

    def test_is_safe_cut_point_with_tool_calls(self, agent):
        """测试工具调用时的安全切割点检查"""
        agent.chat_history = [
            {"role": "system", "content": "系统"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1"}]},
            {"role": "tool", "content": "结果", "tool_call_id": "call_1"}
        ]

        # 从索引 1 开始切割应该是安全的（包含完整的工具调用）
        result = agent._is_safe_cut_point(1)
        assert result is True

        # 从索引 2 开始切割不安全（孤立的 tool 消息）
        result = agent._is_safe_cut_point(2)
        assert result is False

    def test_find_safe_preserve_point(self, agent):
        """测试查找安全保留点"""
        agent.chat_history = [
            {"role": "system", "content": "系统"},
            {"role": "user", "content": "用户1"},
            {"role": "assistant", "content": "助手1"},
            {"role": "user", "content": "用户2"},
            {"role": "assistant", "content": "助手2"}
        ]

        preserve_point = agent._find_safe_preserve_point()

        # 应该保留最后几条消息
        assert preserve_point >= 2

    def test_get_safe_fallback_history(self, agent):
        """测试安全回退历史"""
        agent.chat_history = [
            {"role": "system", "content": "系统"},
            {"role": "user", "content": "用户"},
            {"role": "assistant", "content": "助手"}
        ]

        safe_history = agent._get_safe_fallback_history()

        assert len(safe_history) >= 1
        # 应该保留系统消息
        assert safe_history[0]["role"] == "system"

    def test_find_last_unmatched_tool_call_none(self, agent):
        """测试没有未匹配工具调用"""
        agent.chat_history = [
            {"role": "user", "content": "用户"},
            {"role": "assistant", "content": "助手"}
        ]

        result = agent._find_last_unmatched_tool_call()
        assert result is None

    def test_find_last_unmatched_tool_call_found(self, agent):
        """测试查找未匹配的工具调用"""
        agent.chat_history = [
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1"}]}
            # 缺少对应的 tool response
        ]

        result = agent._find_last_unmatched_tool_call()
        assert result == 0


class TestAgentMemoryManagement:
    """测试 Agent 记忆管理"""

    @pytest.fixture
    def mock_llm(self):
        """模拟 LLM 实例"""
        llm = MagicMock()
        llm.chat = AsyncMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "总结内容"
        llm.chat.return_value = mock_response

        return llm

    @pytest.fixture
    def agent_small_memory(self, mock_llm):
        """创建小记忆容量的 Agent"""
        from app.core.agents.agent import Agent

        return Agent(
            task_id="test_task",
            model=mock_llm,
            max_memory=5  # 小记忆容量，便于测试
        )

    @pytest.mark.asyncio
    async def test_clear_memory_not_triggered(self, agent_small_memory):
        """测试记忆未超限时不触发清理"""
        agent_small_memory.chat_history = [
            {"role": "user", "content": "消息1"},
            {"role": "assistant", "content": "回复1"}
        ]

        original_length = len(agent_small_memory.chat_history)
        await agent_small_memory.clear_memory()

        assert len(agent_small_memory.chat_history) == original_length

    @pytest.mark.asyncio
    async def test_clear_memory_triggered(self, agent_small_memory):
        """测试记忆超限时触发清理"""
        # 添加超过 max_memory 的消息
        agent_small_memory.chat_history = [
            {"role": "system", "content": "系统"},
            {"role": "user", "content": "消息1"},
            {"role": "assistant", "content": "回复1"},
            {"role": "user", "content": "消息2"},
            {"role": "assistant", "content": "回复2"},
            {"role": "user", "content": "消息3"},
            {"role": "assistant", "content": "回复3"}
        ]

        with patch('app.core.agents.agent.simple_chat', new_callable=AsyncMock) as mock_simple_chat:
            mock_simple_chat.return_value = "历史总结"
            await agent_small_memory.clear_memory()

        # 记忆应该被压缩
        assert len(agent_small_memory.chat_history) <= agent_small_memory.max_memory
