from app.utils.common_utils import transform_link, split_footnotes
from app.utils.log_util import logger
import asyncio
import random
from app.schemas.response import (
    CoderMessage,
    WriterMessage,
    ModelerMessage,
    SystemMessage,
    CoordinatorMessage,
)
from app.services.redis_manager import redis_manager
from litellm import acompletion, ModelResponse
import litellm
from app.schemas.enums import AgentType
from app.utils.track import agent_metrics

litellm.callbacks = [agent_metrics]
litellm.enable_json_schema_validation = True

class LLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        task_id: str,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.chat_count = 0
        self.max_tokens: int | None = None  # 添加最大token数限制
        self.task_id = task_id

    async def chat(
        self,
        history: list | None = None,
        tools: list | None = None,
        tool_choice: str | None = None,
        max_retries: int = 8,  # 添加最大重试次数
        retry_delay: float = 1.0,  # 添加重试延迟
        top_p: float | None = None,  # 添加top_p参数,
        agent_name: AgentType = AgentType.SYSTEM,  # CoderAgent or WriterAgent
        sub_title: str | None = None,
    ) -> ModelResponse:
        logger.info("subtitle是:%s", sub_title)

        # 临时诊断：确认 API Key 是否传入
        masked = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else ("***" if self.api_key else "(EMPTY)")
        logger.info("LLM.chat 诊断: model=%s, api_key=%s, base_url=%s", self.model, masked, self.base_url)

        # 验证和修复工具调用完整性
        if history:
            history = self._validate_and_fix_tool_calls(history)

        kwargs = {
            "api_key": self.api_key,
            "model": self.model,
            "messages": history,
            "stream": False,
            "top_p": top_p,
            "metadata": {"agent_name": agent_name},
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        if self.base_url:
            kwargs["base_url"] = self.base_url

        # TODO: stream 输出
        # 可重试的瞬时异常类型（网络/超时/API 响应异常）
        _RETRYABLE_EXCEPTIONS = (
            OSError,
            ConnectionError,
            TimeoutError,
            ValueError,
        )
        for attempt in range(max_retries):
            try:
                # completion = self.client.chat.completions.create(**kwargs)
                response = await acompletion(**kwargs)
                logger.info(
                    "API返回: model=%s, usage=%s, choices=%d",
                    getattr(response, "model", "unknown"),
                    getattr(response, "usage", None),
                    len(response.choices) if response.choices else 0,
                )
                logger.debug("API完整返回: %s", response)
                if not response or not hasattr(response, "choices"):
                    raise ValueError("无效的API响应")
                if not response.choices:
                    raise ValueError(
                        "LLM 返回了空的 choices 列表，"
                        "可能因内容审核或 API 限制导致"
                    )
                self.chat_count += 1
                await self.send_message(response, agent_name, sub_title)
                return response
            except _RETRYABLE_EXCEPTIONS as e:
                logger.error("第%s次重试（可重试异常）: %s", attempt + 1, e)
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    # 指数退避 + 随机抖动，避免惊群效应
                    jitter = random.uniform(0, 1.0)
                    backoff_time = min(
                        retry_delay * (2 ** attempt) + jitter, 30.0
                    )
                    logger.info(
                        "第%s次重试将在 %.2f 秒后执行（指数退避）",
                        attempt + 1,
                        backoff_time,
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                # 脱敏处理：隐藏可能包含密钥的字段值
                safe_kwargs = {
                    k: ("***" if "key" in k.lower() or "secret" in k.lower() else v)
                    for k, v in kwargs.items()
                }
                logger.debug("请求参数: %s", safe_kwargs)
                raise  # 如果所有重试都失败，则抛出异常
            except Exception as e:
                # 不可重试的编程错误（TypeError、AttributeError 等），立即抛出
                logger.error("LLM 调用发生不可重试错误: %s", e)
                raise

    async def chat_stream(
        self,
        history: list | None = None,
        agent_name: AgentType = AgentType.SYSTEM,
        sub_title: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        top_p: float | None = None,
    ) -> str:
        """流式 LLM 调用：逐 token 推送 StreamMessage 到前端。

        返回完整拼接的响应文本。非流式功能（tools 等）仍使用 chat()。
        """
        from app.schemas.response import StreamMessage
        from uuid import uuid4

        # 验证和修复工具调用完整性
        if history:
            history = self._validate_and_fix_tool_calls(history)

        kwargs = {
            "api_key": self.api_key,
            "model": self.model,
            "messages": history,
            "stream": True,
            "top_p": top_p,
            "metadata": {"agent_name": agent_name},
        }

        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens
        if self.base_url:
            kwargs["base_url"] = self.base_url

        message_id = str(uuid4())
        full_content = ""

        _RETRYABLE_EXCEPTIONS = (
            OSError,
            ConnectionError,
            TimeoutError,
        )

        for attempt in range(max_retries):
            try:
                response = await acompletion(**kwargs)

                async for chunk in response:
                    delta_content = ""
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            delta_content = delta.content

                    if delta_content:
                        full_content += delta_content
                        # 推送增量 token 到前端
                        await redis_manager.publish_message(
                            self.task_id,
                            StreamMessage(
                                content=delta_content,
                                agent_type=agent_name.value if hasattr(agent_name, 'value') else str(agent_name),
                                delta=delta_content,
                                message_id=message_id,
                                done=False,
                            ),
                        )

                # 流式结束标记
                await redis_manager.publish_message(
                    self.task_id,
                    StreamMessage(
                        content="",
                        agent_type=agent_name.value if hasattr(agent_name, 'value') else str(agent_name),
                        delta="",
                        message_id=message_id,
                        done=True,
                    ),
                )

                self.chat_count += 1
                logger.info(
                    "流式输出完成: model=%s, 内容长度=%d",
                    self.model,
                    len(full_content),
                )
                return full_content

            except _RETRYABLE_EXCEPTIONS as e:
                logger.error("流式调用第%s次重试: %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    jitter = random.uniform(0, 1.0)
                    backoff_time = min(
                        retry_delay * (2 ** attempt) + jitter, 30.0
                    )
                    await asyncio.sleep(backoff_time)
                    full_content = ""  # 重置
                    message_id = str(uuid4())  # 新 ID
                    continue
                raise
            except Exception as e:
                logger.error("流式 LLM 调用不可重试错误: %s", e)
                raise

        raise RuntimeError("chat_stream: 所有重试均失败")

    def _validate_and_fix_tool_calls(self, history: list) -> list:
        """验证并修复工具调用完整性。"""
        if not history:
            return history

        logger.debug("开始验证工具调用，历史消息数量: %d", len(history))

        # 查找所有未匹配的tool_calls
        fixed_history = []
        i = 0

        while i < len(history):
            msg = history[i]

            # 如果是包含tool_calls的消息
            if isinstance(msg, dict) and "tool_calls" in msg and msg["tool_calls"]:
                logger.debug("发现tool_calls消息在位置 %d", i)

                # 检查每个tool_call是否都有对应的response，分别处理
                valid_tool_calls = []
                invalid_tool_calls = []

                for tool_call in msg["tool_calls"]:
                    tool_call_id = tool_call.get("id")
                    logger.debug("  检查tool_call_id: %s", tool_call_id)

                    if tool_call_id:
                        # 查找对应的tool响应
                        found_response = False
                        for j in range(i + 1, len(history)):
                            if (
                                history[j].get("role") == "tool"
                                and history[j].get("tool_call_id") == tool_call_id
                            ):
                                logger.debug("  找到匹配响应在位置 %d", j)
                                found_response = True
                                break

                        if found_response:
                            valid_tool_calls.append(tool_call)
                        else:
                            logger.debug("  未找到匹配响应: %s", tool_call_id)
                            invalid_tool_calls.append(tool_call)

                # 根据检查结果处理消息
                if valid_tool_calls:
                    # 有有效的tool_calls，保留它们
                    fixed_msg = msg.copy()
                    fixed_msg["tool_calls"] = valid_tool_calls
                    fixed_history.append(fixed_msg)
                    logger.debug(
                        "  保留 %d 个有效tool_calls，移除 %d 个无效的",
                        len(valid_tool_calls),
                        len(invalid_tool_calls),
                    )
                else:
                    # 没有有效的tool_calls，移除tool_calls但可能保留其他内容
                    cleaned_msg = {k: v for k, v in msg.items() if k != "tool_calls"}
                    if cleaned_msg.get("content"):
                        fixed_history.append(cleaned_msg)
                        logger.debug("  移除所有tool_calls，保留消息内容")
                    else:
                        logger.debug("  完全移除空的tool_calls消息")

            # 如果是tool响应消息，检查是否是孤立的
            elif isinstance(msg, dict) and msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id")
                logger.debug("检查tool响应消息: %s", tool_call_id)

                # 查找对应的tool_calls
                found_call = False
                for j in range(len(fixed_history)):
                    if fixed_history[j].get("tool_calls") and any(
                        tc.get("id") == tool_call_id
                        for tc in fixed_history[j]["tool_calls"]
                    ):
                        found_call = True
                        break

                if found_call:
                    fixed_history.append(msg)
                    logger.debug("  保留有效的tool响应")
                else:
                    logger.debug("  移除孤立的tool响应: %s", tool_call_id)

            else:
                # 普通消息，直接保留
                fixed_history.append(msg)

            i += 1

        if len(fixed_history) != len(history):
            logger.debug(
                "修复完成: %d -> %d 条消息", len(history), len(fixed_history)
            )
        else:
            logger.debug("验证通过，无需修复")

        return fixed_history

    async def send_message(self, response, agent_name, sub_title=None):
        logger.info("subtitle是:%s", sub_title)
        content = response.choices[0].message.content

        if content is None:
            # tool_calls 响应不包含文本内容，无需发送消息给前端
            return

        match agent_name:
            case AgentType.CODER:
                agent_msg: CoderMessage = CoderMessage(content=content)
            case AgentType.WRITER:
                # 处理 Markdown 格式的图片语法
                content, _ = split_footnotes(content)
                content = transform_link(self.task_id, content)
                agent_msg: WriterMessage = WriterMessage(
                    content=content,
                    sub_title=sub_title,
                )
            case AgentType.MODELER:
                agent_msg: ModelerMessage = ModelerMessage(content=content)
            case AgentType.SYSTEM:
                agent_msg: SystemMessage = SystemMessage(content=content)
            case AgentType.COORDINATOR:
                agent_msg: CoordinatorMessage = CoordinatorMessage(content=content)
            case _:
                raise ValueError(f"不支持的agent类型: {agent_name}")

        await redis_manager.publish_message(
            self.task_id,
            agent_msg,
        )


# class DeepSeekModel(LLM):
#     def __init__(
#         self,
#         api_key: str,
#         model: str,
#         base_url: str,
#         task_id: str,
#     ):
#         super().__init__(api_key, model, base_url, task_id)
# self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)


async def simple_chat(model: LLM, history: list) -> str:
    """简单的 LLM 对话调用，带基础错误处理和 1 次重试。

    Args:
        model (LLM): LLM 实例，包含 api_key、model、base_url 等配置。
        history (list): 构造好的历史记录（包含 system_prompt, user_prompt）。

    Returns:
        str: LLM 返回的文本内容。

    Raises:
        ValueError: 当 LLM 返回无效响应（choices 为空）时抛出。
        Exception: 当重试耗尽后仍然失败时，抛出最后一次异常。
    """
    kwargs = {
        "api_key": model.api_key,
        "model": model.model,
        "messages": history,
        "stream": False,
    }

    if model.base_url:
        kwargs["base_url"] = model.base_url

    max_attempts = 2  # 首次调用 + 1 次重试
    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            response = await acompletion(**kwargs)

            if not response or not response.choices:
                raise ValueError("simple_chat 收到无效的 API 响应: choices 为空")

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("simple_chat 收到空的响应内容")

            return content
        except Exception as e:
            last_exception = e
            logger.warning(
                "simple_chat 第 %s 次调用失败: %s",
                attempt + 1,
                e,
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(1.0)
                continue

    # 所有重试均失败，抛出最后一次异常
    raise last_exception  # type: ignore[misc]
