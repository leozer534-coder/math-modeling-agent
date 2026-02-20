"""
LLM Token 计量集成测试 - Test LLM Metering Integration

测试 LLM 类的基础功能。
注意: 计量(metering)、错误分类(_classify_error)、重试延迟(_calculate_retry_delay)
等功能尚未在 LLM 类中实现，相关测试已移除。
"""

from app.core.llm.llm import LLM


class TestLLMBasic:
    """LLM 基础功能测试"""

    def test_llm_import(self):
        """测试 LLM 导入"""
        assert LLM is not None

    def test_llm_init(self):
        """测试 LLM 基础初始化"""
        llm = LLM(
            api_key="test-key",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            task_id="test-task-123",
        )

        assert llm.task_id == "test-task-123"
        assert llm.model == "gpt-4"
        assert llm.api_key == "test-key"
        assert llm.base_url == "https://api.openai.com/v1"
        assert llm.chat_count == 0

    def test_llm_init_empty_base_url(self):
        """测试空 base_url 的 LLM 初始化"""
        llm = LLM(
            api_key="test-key",
            model="gpt-4",
            base_url="",
            task_id="test-task",
        )

        assert llm.base_url == ""

    def test_llm_validate_and_fix_tool_calls_empty(self):
        """测试空历史记录的工具调用验证"""
        llm = LLM("key", "model", "", "task")

        result = llm._validate_and_fix_tool_calls([])
        assert result == []

    def test_llm_validate_and_fix_tool_calls_none(self):
        """测试 None 历史记录的工具调用验证"""
        llm = LLM("key", "model", "", "task")

        result = llm._validate_and_fix_tool_calls(None)
        assert result is None

    def test_llm_validate_and_fix_tool_calls_normal_messages(self):
        """测试普通消息不被修改"""
        llm = LLM("key", "model", "", "task")

        history = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = llm._validate_and_fix_tool_calls(history)
        assert len(result) == 3

    def test_llm_validate_and_fix_tool_calls_orphan_tool_response(self):
        """测试孤立的工具响应被移除"""
        llm = LLM("key", "model", "", "task")

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "tool", "tool_call_id": "call_123", "content": "result"},
        ]

        result = llm._validate_and_fix_tool_calls(history)
        # 孤立的 tool 响应应被移除
        assert len(result) == 1
        assert result[0]["role"] == "user"
