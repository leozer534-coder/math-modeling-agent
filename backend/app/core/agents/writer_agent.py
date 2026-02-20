from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import get_writer_prompt
from app.schemas.enums import CompTemplate, FormatOutPut
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage, WriterMessage
import json
from app.core.functions import writer_tools
from app.schemas.A2A import WriterResponse


# 长文本
# TODO: 并行 parallel
# TODO: 获取当前文件下的文件
# TODO: 引用cites tool
class WriterAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 10,  # 添加最大对话轮次限制
        comp_template: CompTemplate = CompTemplate,
        format_output: FormatOutPut = FormatOutPut.Markdown,
        scholar: OpenAlexScholar = None,
        max_memory: int = 25,  # 添加最大记忆轮次
    ) -> None:
        # WriterAgent 使用自定义 _trim_chat_history() 裁剪策略，
        # 禁用基类的 auto_summarize 避免每次 append 都触发 LLM 总结调用
        super().__init__(task_id, model, max_chat_turns, max_memory, auto_summarize=False)
        self.format_out_put = format_output
        self.comp_template = comp_template
        self.scholar = scholar
        self.is_first_run = True
        self.system_prompt = get_writer_prompt(format_output)
        self.available_images: list[str] = []
        self.max_history_messages: int = 12  # 每次 run() 开始前保留的最大历史消息数

    async def run(
        self,
        prompt: str,
        available_images: list[str] = None,
        sub_title: str = None,
    ) -> WriterResponse:
        """
        执行写作任务
        Args:
            prompt: 写作提示
            available_images: 可用的图片相对路径列表（如 20250420-173744-9f87792c/编号_分布.png）
            sub_title: 子任务标题
        """
        logger.info("subtitle是:%s", sub_title)

        if self.is_first_run:
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )

        if available_images:
            self.available_images = available_images
            # 构建编号化的图片清单，便于 Writer 准确引用
            image_lines = []
            for i, img in enumerate(available_images, 1):
                image_lines.append(f"  图{i}: {img}")
            image_list_str = "\n".join(image_lines)
            image_prompt = (
                f"\n\n【可用图片清单】\n{image_list_str}\n\n"
                f"【图片引用规范】\n"
                f"1. 引用格式必须为: ![图片描述](图片文件名)\n"
                f"2. 文件名必须从上述清单中精确复制，禁止自行编造文件名\n"
                f"3. 每张图片至少引用一次，并配有详细的图表分析说明\n"
                f"4. 图表分析应包含：数据趋势、关键发现、与模型结论的关联"
            )
            logger.info("image_prompt是:%s", image_prompt)
            prompt = prompt + image_prompt

        logger.info("%s:开始:执行对话", self.__class__.__name__)
        self.current_chat_turns = 0  # 重置对话轮次计数器，防止跨章节状态污染

        # 智能裁剪 chat_history，避免跨章节历史膨胀
        self._trim_chat_history()

        await self.append_chat_history({"role": "user", "content": prompt})

        # 获取历史消息用于本次对话
        response = await self.model.chat(
            history=self.chat_history,
            tools=writer_tools,
            tool_choice="auto",
            agent_name=self.__class__.__name__,
            sub_title=sub_title,
        )

        footnotes = []

        # 多轮工具调用循环，支持连续多次工具调用
        tool_call_rounds = 0
        MAX_TOOL_ROUNDS = 5  # 工具调用最大轮次，防止无限循环
        while (
            hasattr(response.choices[0].message, "tool_calls")
            and response.choices[0].message.tool_calls
            and tool_call_rounds < MAX_TOOL_ROUNDS
        ):
            tool_call_rounds += 1
            logger.info("检测到工具调用")
            tool_call = response.choices[0].message.tool_calls[0]
            tool_id = tool_call.id
            if tool_call.function.name == "search_papers":
                logger.info("调用工具: search_papers")
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"写作手调用{tool_call.function.name}工具"),
                )

                try:
                    args = json.loads(tool_call.function.arguments)
                    query = args["query"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error("解析工具调用参数失败: %s", e)
                    # 将错误反馈给模型，让它改为直接输出
                    await self.append_chat_history(
                        response.choices[0].message.model_dump()
                    )
                    await self.append_chat_history(
                        {
                            "role": "tool",
                            "content": f"工具参数解析失败: {e}，请不要再调用工具，直接撰写内容即可。",
                            "tool_call_id": tool_id,
                            "name": "search_papers",
                        }
                    )
                    # 重新调用 LLM，不再提供工具选项，强制直接输出
                    response = await self.model.chat(
                        history=self.chat_history,
                        agent_name=self.__class__.__name__,
                        sub_title=sub_title,
                    )
                    break

                await redis_manager.publish_message(
                    self.task_id,
                    WriterMessage(
                        input={"query": query},
                    ),
                )

                # 更新对话历史 - 添加助手的响应
                await self.append_chat_history(response.choices[0].message.model_dump())
                logger.debug("助手响应: %s", response.choices[0].message.model_dump())

                try:
                    papers = await self.scholar.search_papers(query)
                except Exception as e:
                    error_msg = f"搜索文献失败: {str(e)}"
                    logger.error(error_msg)
                    # 将错误作为工具结果返回，让模型决定下一步
                    await self.append_chat_history(
                        {
                            "role": "tool",
                            "content": error_msg,
                            "tool_call_id": tool_id,
                            "name": "search_papers",
                        }
                    )
                    break

                # TODO: pass to frontend
                papers_str = self.scholar.papers_to_str(papers)
                logger.info("搜索文献结果\n%s", papers_str)
                await self.append_chat_history(
                    {
                        "role": "tool",
                        "content": papers_str,
                        "tool_call_id": tool_id,
                        "name": "search_papers",
                    }
                )
                # 继续下一轮对话，让模型决定是否需要再次调用工具
                response = await self.model.chat(
                    history=self.chat_history,
                    tools=writer_tools,
                    tool_choice="auto",
                    agent_name=self.__class__.__name__,
                    sub_title=sub_title,
                )
            else:
                # 未知工具调用，跳出循环
                logger.warning("未知的工具调用: %s", tool_call.function.name)
                break

        # 如果因工具调用轮次超限退出，最后的 response 可能仍含 tool_calls 而无内容
        if (
            tool_call_rounds >= MAX_TOOL_ROUNDS
            and hasattr(response.choices[0].message, "tool_calls")
            and response.choices[0].message.tool_calls
        ):
            logger.warning(
                "WriterAgent 工具调用轮次超限（%d/%d），强制不带工具调用输出内容",
                tool_call_rounds,
                MAX_TOOL_ROUNDS,
            )
            await self.append_chat_history(response.choices[0].message.model_dump())
            # 添加提示让模型直接输出内容
            await self.append_chat_history(
                {
                    "role": "user",
                    "content": "工具调用次数已达上限，请不要再调用工具，直接根据已有信息撰写内容。",
                }
            )
            response = await self.model.chat(
                history=self.chat_history,
                agent_name=self.__class__.__name__,
                sub_title=sub_title,
            )

        response_content = response.choices[0].message.content or ""
        self.chat_history.append({"role": "assistant", "content": response_content})

        # === 输出质量验证 ===
        MIN_CONTENT_LENGTH = 200  # 有效论文章节最低字符数

        if not response_content.strip() or len(response_content.strip()) < MIN_CONTENT_LENGTH:
            logger.warning(
                "WriterAgent 输出过短或为空（%d 字符），触发补写重试",
                len(response_content.strip()),
            )
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="写作手输出过短，正在补写...", type="warning"),
            )
            retry_prompt = (
                "你上一次的输出为空或过短，请重新完整撰写该章节。"
                "要求：内容详实、结构完整、不少于200字。"
            )
            await self.append_chat_history({"role": "user", "content": retry_prompt})
            retry_response = await self.model.chat(
                history=self.chat_history,
                agent_name=self.__class__.__name__,
                sub_title=sub_title,
            )
            retry_content = retry_response.choices[0].message.content or ""
            if len(retry_content.strip()) > len(response_content.strip()):
                response_content = retry_content
                logger.info("补写成功，新内容长度: %d 字符", len(response_content))
                # 替换已追加的短内容，而不是再追加一条
                self.chat_history[-1] = {"role": "assistant", "content": response_content}
            else:
                logger.warning("补写未改善，使用原始输出")

        logger.info("%s:完成:执行对话", self.__class__.__name__)
        return WriterResponse(response_content=response_content, footnotes=footnotes)

    def _trim_chat_history(self) -> None:
        """智能裁剪 chat_history，防止跨章节历史膨胀。

        保留第一条 system prompt + 最近 max_history_messages - 1 条消息，
        裁剪掉中间的旧章节对话，减少无关上下文对注意力的干扰和 Token 消耗。

        裁剪时保证 tool_call / tool_response 配对完整性：
        如果裁剪边界恰好落在 assistant(tool_calls) 与 tool response 之间，
        会自动向前扩展保留区域，避免拆散配对导致 LLM API 400 错误。
        """
        if len(self.chat_history) <= self.max_history_messages:
            return

        # 识别 system prompt（第一条 role=system 的消息）
        pinned_count = 0
        system_msg = None
        if self.chat_history and self.chat_history[0].get("role") == "system":
            system_msg = self.chat_history[0]
            pinned_count = 1

        # 计算尾部保留区域的起始索引
        keep_recent = self.max_history_messages - pinned_count
        keep_start = len(self.chat_history) - keep_recent

        # === tool_call 配对完整性保护 ===
        # 如果保留区域的第一条消息是 role=tool，向前扩展直到找到对应的 assistant(tool_calls)
        while (
            keep_start > pinned_count
            and self.chat_history[keep_start].get("role") == "tool"
        ):
            keep_start -= 1

        # 如果裁剪边界前一条是含 tool_calls 的 assistant 消息，也纳入保留区域
        if (
            keep_start > pinned_count
            and self.chat_history[keep_start - 1].get("role") == "assistant"
            and self.chat_history[keep_start - 1].get("tool_calls")
        ):
            keep_start -= 1

        # 从被裁剪的消息中提取 assistant 回复摘要
        trimmed_messages = self.chat_history[pinned_count:keep_start]
        summary_parts: list[str] = []
        for msg in trimmed_messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                # 截取每个 assistant 回复的前150字符作为摘要
                content = msg["content"][:150]
                if len(msg["content"]) > 150:
                    content += "..."
                summary_parts.append(content)

        # 重建历史：system prompt + 裁剪摘要 + 保留的尾部消息
        new_history: list[dict] = []
        if system_msg:
            new_history.append(system_msg)

        # 注入被裁剪章节的简要摘要，保持跨章节连贯性
        if summary_parts:
            trimmed_summary = "\n---\n".join(summary_parts)
            # 总摘要长度限制，避免过度膨胀
            if len(trimmed_summary) > 800:
                trimmed_summary = trimmed_summary[:800] + "..."
            new_history.append({
                "role": "user",
                "content": (
                    "【前序章节写作摘要，请保持风格和术语一致】\n"
                    f"{trimmed_summary}"
                ),
            })

        new_history.extend(self.chat_history[keep_start:])
        trimmed_count = keep_start - pinned_count

        logger.info(
            "WriterAgent chat_history 裁剪完成: 原始 %d 条 -> 保留 %d 条（裁剪了 %d 条旧章节消息）",
            len(self.chat_history),
            len(new_history),
            trimmed_count,
        )
        self.chat_history = new_history

    async def summarize(self) -> str:
        """
        总结对话内容
        """
        try:
            await self.append_chat_history(
                {"role": "user", "content": "请简单总结以上完成什么任务取得什么结果:"}
            )
            # 获取历史消息用于本次对话
            response = await self.model.chat(
                history=self.chat_history, agent_name=self.__class__.__name__
            )
            await self.append_chat_history(
                {"role": "assistant", "content": response.choices[0].message.content}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("总结生成失败: %s", e)
            # 返回一个基础总结，避免完全失败
            return "由于网络原因无法生成详细总结，但已完成主要任务处理。"
