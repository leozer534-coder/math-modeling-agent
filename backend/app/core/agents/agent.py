from app.core.llm.llm import LLM, simple_chat
from app.utils.log_util import logger

# TODO: Memory 的管理
# TODO: 评估任务完成情况，rethinking


class Agent:
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,  # 单个agent最大对话轮次
        max_memory: int = 12,  # 最大记忆轮次
        auto_summarize: bool = True,  # 是否在 append_chat_history 时自动触发 LLM 总结压缩
    ) -> None:
        self.task_id = task_id
        self.model = model
        self.chat_history: list[dict] = []  # 存储对话历史
        self.max_chat_turns = max_chat_turns  # 最大对话轮次
        self.current_chat_turns = 0  # 当前对话轮次计数器
        self.max_memory = max_memory  # 最大记忆轮次
        self.auto_summarize = auto_summarize  # 子类有自定义裁剪策略时应设为 False

    async def run(self, *args, **kwargs):
        """执行 Agent 的核心任务。子类必须覆写此方法。"""
        raise NotImplementedError("子类必须实现 run() 方法")

    async def append_chat_history(self, msg: dict) -> None:
        """向对话历史中追加消息，并在必要时触发内存清理。"""
        logger.debug(
            "添加消息: role=%s, 当前历史长度=%d",
            msg.get("role"), len(self.chat_history),
        )
        self.chat_history.append(msg)
        logger.debug("添加后历史长度=%d", len(self.chat_history))

        # 只有在启用自动总结且添加非tool消息时才进行内存清理，
        # 避免在工具调用期间破坏消息结构。
        # 子类（如 CoderAgent、WriterAgent）有自定义 _trim_chat_history() 策略时，
        # 应将 auto_summarize 设为 False，避免重复的 LLM 总结调用。
        if not self.auto_summarize:
            logger.debug("跳过内存清理(auto_summarize=False)")
        elif msg.get("role") != "tool":
            logger.debug("触发内存清理")
            await self.clear_memory()
        else:
            logger.debug("跳过内存清理(tool消息)")

    async def clear_memory(self):
        """当聊天历史超过最大记忆轮次时，使用 simple_chat 进行总结压缩"""
        logger.debug(
            "检查内存清理: 当前=%d, 最大=%d",
            len(self.chat_history), self.max_memory,
        )

        if len(self.chat_history) <= self.max_memory:
            logger.debug("无需清理内存")
            return

        logger.debug("开始内存清理")
        logger.info(
            "%s:开始清除记忆，当前记录数：%s",
            self.__class__.__name__,
            len(self.chat_history),
        )

        try:
            # 保留第一条系统消息
            system_msg = (
                self.chat_history[0]
                if self.chat_history and self.chat_history[0]["role"] == "system"
                else None
            )

            # 查找需要保留的消息范围 - 保留最后几条完整的对话和工具调用
            preserve_start_idx = self._find_safe_preserve_point()
            logger.debug("保留起始索引: %d", preserve_start_idx)

            # 确定需要总结的消息范围
            start_idx = 1 if system_msg else 0
            end_idx = preserve_start_idx
            logger.debug("总结范围: %d -> %d", start_idx, end_idx)

            if end_idx > start_idx:
                # 构造总结提示
                summarize_history = []
                if system_msg:
                    summarize_history.append(system_msg)

                summarize_history.append(
                    {
                        "role": "user",
                        "content": f"请简洁总结以下对话的关键内容和重要结论，保留重要的上下文信息：\n\n{self._format_history_for_summary(self.chat_history[start_idx:end_idx])}",
                    }
                )

                # 调用 simple_chat 进行总结
                summary = await simple_chat(self.model, summarize_history)

                # 重构聊天历史：系统消息 + 总结 + 保留的消息
                new_history = []
                if system_msg:
                    new_history.append(system_msg)

                new_history.append(
                    {"role": "assistant", "content": f"[历史对话总结] {summary}"}
                )

                # 添加需要保留的消息（最后几条完整对话）
                new_history.extend(self.chat_history[preserve_start_idx:])

                self.chat_history = new_history
                logger.debug("内存清理完成，新历史长度: %d", len(self.chat_history))
                logger.info(
                    "%s:记忆清除完成，压缩至：%s条记录",
                    self.__class__.__name__,
                    len(self.chat_history),
                )
            else:
                # 如果找不到安全的裁剪点且历史过长，强制截断
                if len(self.chat_history) > self.max_memory * 2:
                    logger.warning(
                        "无法找到安全裁剪点，强制截断: 保留最近 %d 条消息",
                        self.max_memory,
                    )
                    system_msgs = [
                        m
                        for m in self.chat_history[:2]
                        if m.get("role") == "system"
                    ]
                    self.chat_history = (
                        system_msgs
                        + self.chat_history[-(self.max_memory - len(system_msgs)):]
                    )
                else:
                    logger.info(
                        "%s:无需清除记忆，记录数量合理",
                        self.__class__.__name__,
                    )

        except Exception as e:
            logger.error("记忆清除失败，使用简单切片策略: %s", e)
            # 如果总结失败，回退到安全的策略：保留系统消息和最后几条消息，确保工具调用完整性
            safe_history = self._get_safe_fallback_history()
            self.chat_history = safe_history

    def _find_safe_preserve_point(self) -> int:
        """找到安全的保留起始点，确保不会破坏工具调用序列"""
        # 最少保留最后3条消息，确保基本对话完整性
        min_preserve = min(3, len(self.chat_history))
        preserve_start = len(self.chat_history) - min_preserve
        logger.debug(
            "寻找安全保留点: 历史长度=%d, 最少保留=%d, 开始位置=%d",
            len(self.chat_history), min_preserve, preserve_start,
        )

        # 从后往前查找，确保不会在工具调用序列中间切断
        for i in range(preserve_start, -1, -1):
            if i >= len(self.chat_history):
                continue

            # 检查从这个位置开始是否是安全的（没有孤立的tool消息）
            is_safe = self._is_safe_cut_point(i)
            logger.debug("检查位置 %d: 安全=%s", i, is_safe)
            if is_safe:
                logger.debug("找到安全保留点: %d", i)
                return i

        # 如果找不到安全点，至少保留最后1条消息
        fallback = len(self.chat_history) - 1
        logger.debug("未找到安全点，使用备用位置: %d", fallback)
        return fallback

    def _is_safe_cut_point(self, start_idx: int) -> bool:
        """检查从指定位置开始切割是否安全（不会产生孤立的tool消息）"""
        if start_idx >= len(self.chat_history):
            logger.debug("切割点 %d >= 历史长度，安全", start_idx)
            return True

        # 检查切割后的消息序列是否有孤立的tool消息
        tool_messages = []
        for i in range(start_idx, len(self.chat_history)):
            msg = self.chat_history[i]
            if isinstance(msg, dict) and msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id")
                tool_messages.append((i, tool_call_id))
                logger.debug(
                    "发现tool消息在位置 %d, tool_call_id=%s", i, tool_call_id,
                )

                # 向前查找对应的tool_calls消息
                if tool_call_id:
                    found_tool_call = False
                    for j in range(start_idx, i):
                        prev_msg = self.chat_history[j]
                        if (
                            isinstance(prev_msg, dict)
                            and "tool_calls" in prev_msg
                            and prev_msg["tool_calls"]
                        ):
                            for tool_call in prev_msg["tool_calls"]:
                                if tool_call.get("id") == tool_call_id:
                                    found_tool_call = True
                                    logger.debug(
                                        "找到对应的tool_call在位置 %d", j,
                                    )
                                    break
                            if found_tool_call:
                                break

                    if not found_tool_call:
                        logger.debug(
                            "tool消息 %s 没有找到对应的tool_call，切割点不安全",
                            tool_call_id,
                        )
                        return False

        logger.debug(
            "切割点 %d 安全，检查了 %d 个tool消息",
            start_idx, len(tool_messages),
        )
        return True

    def _get_safe_fallback_history(self) -> list:
        """获取安全的后备历史记录，确保不会有孤立的tool消息"""
        if not self.chat_history:
            return []

        # 保留系统消息
        safe_history = []
        if self.chat_history and self.chat_history[0]["role"] == "system":
            safe_history.append(self.chat_history[0])

        # 从后往前查找安全的消息序列
        for preserve_count in range(1, min(4, len(self.chat_history)) + 1):
            start_idx = len(self.chat_history) - preserve_count
            if self._is_safe_cut_point(start_idx):
                safe_history.extend(self.chat_history[start_idx:])
                return safe_history

        # 如果都不安全，只保留最后一条非tool消息
        for i in range(len(self.chat_history) - 1, -1, -1):
            msg = self.chat_history[i]
            if isinstance(msg, dict) and msg.get("role") != "tool":
                safe_history.append(msg)
                break

        return safe_history

    def _find_last_unmatched_tool_call(self) -> int | None:
        """查找最后一个未匹配的tool call的索引"""
        logger.debug("开始查找未匹配的tool_call")

        # 从后往前查找，寻找没有对应tool response的tool call
        for i in range(len(self.chat_history) - 1, -1, -1):
            msg = self.chat_history[i]

            # 检查是否是包含tool_calls的消息
            if isinstance(msg, dict) and "tool_calls" in msg and msg["tool_calls"]:
                logger.debug("在位置 %d 发现tool_calls消息", i)

                # 检查每个tool call是否都有对应的response
                for tool_call in msg["tool_calls"]:
                    tool_call_id = tool_call.get("id")
                    logger.debug("检查tool_call_id: %s", tool_call_id)

                    if tool_call_id:
                        # 在后续消息中查找对应的tool response
                        response_found = False
                        for j in range(i + 1, len(self.chat_history)):
                            response_msg = self.chat_history[j]
                            if (
                                isinstance(response_msg, dict)
                                and response_msg.get("role") == "tool"
                                and response_msg.get("tool_call_id") == tool_call_id
                            ):
                                logger.debug("找到匹配的tool响应在位置 %d", j)
                                response_found = True
                                break

                        if not response_found:
                            # 找到未匹配的tool call
                            logger.debug(
                                "发现未匹配的tool_call在位置 %d, id=%s",
                                i, tool_call_id,
                            )
                            return i

        logger.debug("没有发现未匹配的tool_call")
        return None

    def _format_history_for_summary(self, history: list[dict]) -> str:
        """格式化历史记录用于总结"""
        formatted = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "") or ""
            # 限制长度
            if len(content) > 500:
                content = content[:500] + "..."
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
