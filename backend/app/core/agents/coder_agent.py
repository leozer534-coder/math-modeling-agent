import asyncio
import re

from app.core.agents.agent import Agent
from app.config.setting import settings
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage, InterpreterMessage
from app.tools.base_interpreter import BaseCodeInterpreter
from app.core.llm.llm import LLM
from app.schemas.A2A import CoderToWriter
from app.core.prompts import CODER_PROMPT
from app.utils.common_utils import get_current_files
import json
from app.core.prompts import get_reflection_prompt, get_completion_check_prompt
from app.core.functions import coder_tools

# TODO: 时间等待过久，stop 进程
# TODO: 支持 cuda
# TODO: 引入创新方案：


# 代码强
class CoderAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        work_dir: str,  # 工作目录
        max_chat_turns: int = settings.MAX_CHAT_TURNS,  # 最大聊天次数
        max_retries: int = settings.MAX_RETRIES,  # 最大反思次数
        code_interpreter: BaseCodeInterpreter = None,
        system_prompt: str | None = None,  # 允许外部注入增强 prompt（如代码模板）
    ) -> None:
        # CoderAgent 使用自定义 _trim_chat_history() 裁剪策略，
        # 禁用基类的 auto_summarize 避免每次 append 都触发 LLM 总结调用
        super().__init__(task_id, model, max_chat_turns, auto_summarize=False)
        self.work_dir = work_dir
        self.max_retries = max_retries
        self.is_first_run = True
        self.system_prompt = system_prompt or CODER_PROMPT
        self.code_interpreter = code_interpreter
        self.max_history_messages: int = 20  # 每次循环开始前保留的最大历史消息数

    async def run(self, prompt: str, subtask_title: str) -> CoderToWriter:
        logger.info("%s:开始:执行子任务: %s", self.__class__.__name__, subtask_title)
        self.current_chat_turns = 0  # 重置对话轮次计数器，防止跨子任务状态污染
        self._completion_checked = False
        self._code_executed = False  # 追踪本次子任务是否执行过代码
        self._successful_executions = 0  # 成功执行次数
        self._total_errors = 0  # 全局错误计数，不因成功重置
        MAX_TOTAL_ERRORS = 8  # 全局最大错误次数（跨成功重试）
        self.code_interpreter.add_section(subtask_title)

        # 如果是第一次运行，则添加系统提示
        if self.is_first_run:
            logger.info("首次运行，添加系统提示和数据集文件信息")
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )
            # 当前数据集文件
            await self.append_chat_history(
                {
                    "role": "user",
                    "content": f"当前文件夹下的数据集文件{get_current_files(self.work_dir, 'data')}",
                }
            )

        # 添加 sub_task
        logger.info("添加子任务提示: %s", prompt)
        await self.append_chat_history({"role": "user", "content": prompt})

        retry_count = 0
        last_error_message = ""

        while True:
            # 裁剪 chat_history，防止跨子任务历史无限膨胀
            self._trim_chat_history()

            # 全局错误次数检查（不因成功重置，防止交替成功/失败导致无限循环）
            if self._total_errors >= MAX_TOTAL_ERRORS:
                logger.error("全局错误次数超限: %s", MAX_TOTAL_ERRORS)
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"全局错误超限（{MAX_TOTAL_ERRORS}次）", type="error"),
                )
                return CoderToWriter(
                    code_response=f"任务失败，全局错误次数超限{MAX_TOTAL_ERRORS}",
                    created_images=await self.code_interpreter.get_created_images(
                        subtask_title
                    ) if self._code_executed else [],
                    failed=True,
                )

            if retry_count >= self.max_retries:
                logger.error("超过最大尝试次数: %s", self.max_retries)
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="超过最大尝试次数", type="error"),
                )
                logger.warning("任务失败，超过最大尝试次数%s, 最后错误信息: %s", self.max_retries, last_error_message)
                return CoderToWriter(
                    code_response=f"任务失败，超过最大尝试次数{self.max_retries}, 最后错误信息: {last_error_message}",
                    created_images=[],
                    failed=True,
                )
                

            if self.current_chat_turns >= self.max_chat_turns:
                logger.error("超过最大聊天次数: %s", self.max_chat_turns)
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="超过最大聊天次数", type="error"),
                )
                return CoderToWriter(
                    code_response=f"任务失败，超过最大聊天次数{self.max_chat_turns}",
                    created_images=await self.code_interpreter.get_created_images(
                        subtask_title
                    ) if self._code_executed else [],
                    failed=True,
                )

            self.current_chat_turns += 1
            logger.info("当前对话轮次: %s", self.current_chat_turns)
            
            try:
                response = await self.model.chat(
                    history=self.chat_history,
                    tools=coder_tools,
                    tool_choice="auto",
                    agent_name=self.__class__.__name__,
                )

                # 如果有工具调用
                if (
                    hasattr(response.choices[0].message, "tool_calls")
                    and response.choices[0].message.tool_calls
                ):
                    logger.info("检测到工具调用")
                    tool_call = response.choices[0].message.tool_calls[0]
                    tool_id = tool_call.id
                    
                    if tool_call.function.name == "execute_code":
                        logger.info("调用工具: %s", tool_call.function.name)
                        await redis_manager.publish_message(
                            self.task_id,
                            SystemMessage(
                                content=f"代码手调用{tool_call.function.name}工具"
                            ),
                        )

                        try:
                            args = json.loads(tool_call.function.arguments)
                            code = args["code"]
                        except (json.JSONDecodeError, KeyError) as parse_err:
                            logger.error("解析工具调用参数失败: %s", parse_err)
                            # 将解析错误作为工具结果返回给模型
                            await self.append_chat_history(
                                response.choices[0].message.model_dump()
                            )
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": f"参数解析失败: {parse_err}",
                                }
                            )
                            retry_count += 1
                            self._total_errors += 1
                            last_error_message = str(parse_err)
                            continue

                        await redis_manager.publish_message(
                            self.task_id,
                            InterpreterMessage(
                                input={"code": code},
                            ),
                        )

                        # 更新对话历史 - 添加助手的响应
                        await self.append_chat_history(
                            response.choices[0].message.model_dump()
                        )
                        logger.debug(
                            "助手响应: tool_calls=%d",
                            len(response.choices[0].message.tool_calls or []),
                        )

                        # 执行工具调用
                        logger.info("执行工具调用")
                        (
                            text_to_gpt,
                            error_occurred,
                            error_message,
                        ) = await self.code_interpreter.execute_code(code)

                        # === 输出截断保护：防止超长输出消耗上下文窗口 ===
                        MAX_OUTPUT_CHARS = 4000
                        if text_to_gpt and len(text_to_gpt) > MAX_OUTPUT_CHARS:
                            original_len = len(text_to_gpt)

                            # 截断前提取结构化标记块，防止截断破坏下游解析
                            _MARKER_PATTERNS = [
                                r"===METRICS_START===.*?===METRICS_END===",
                                r"===FIGURE:\s*[^=]+===",
                                r"===RESULT_SUMMARY===.*?===END_SUMMARY===",
                                r"===TABLE_START===.*?===TABLE_END===",
                            ]
                            preserved_markers: list[str] = []
                            for _pat in _MARKER_PATTERNS:
                                for _m in re.finditer(_pat, text_to_gpt, re.DOTALL):
                                    preserved_markers.append(_m.group(0))

                            head_size = MAX_OUTPUT_CHARS * 2 // 3  # 前2/3
                            tail_size = MAX_OUTPUT_CHARS // 3       # 后1/3
                            text_to_gpt = (
                                text_to_gpt[:head_size]
                                + f"\n\n... [输出已截断: 原始 {original_len} 字符，"
                                f"已保留前 {head_size} + 后 {tail_size} 字符] ...\n\n"
                                + text_to_gpt[-tail_size:]
                            )

                            # 将被保护的标记块附加到截断后的输出末尾
                            if preserved_markers:
                                markers_text = "\n".join(preserved_markers)
                                # 限制标记块总大小，避免反向膨胀
                                MAX_MARKERS_CHARS = 1500
                                if len(markers_text) > MAX_MARKERS_CHARS:
                                    markers_text = markers_text[:MAX_MARKERS_CHARS]
                                text_to_gpt += (
                                    "\n\n===PRESERVED_STRUCTURED_MARKERS===\n"
                                    + markers_text
                                )
                                logger.info(
                                    "截断时保护了 %d 个结构化标记块",
                                    len(preserved_markers),
                                )

                            logger.info(
                                "代码输出截断: %d -> %d 字符",
                                original_len, len(text_to_gpt),
                            )

                        if error_message and len(error_message) > MAX_OUTPUT_CHARS:
                            error_message = (
                                error_message[:MAX_OUTPUT_CHARS]
                                + f"\n... [错误信息截断: 原始 {len(error_message)} 字符]"
                            )

                        # 添加工具执行结果
                        if error_occurred:
                            # 即使发生错误也要添加tool响应
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": error_message,
                                }
                            )

                            logger.warning("代码执行错误: %s", error_message)
                            retry_count += 1
                            self._total_errors += 1
                            logger.info("当前尝试次:%s / %s", retry_count, self.max_retries)
                            last_error_message = error_message
                            reflection_prompt = get_reflection_prompt(error_message, code)

                            await redis_manager.publish_message(
                                self.task_id,
                                SystemMessage(content="代码手反思纠正错误", type="error"),
                            )

                            await self.append_chat_history(
                                {"role": "user", "content": reflection_prompt}
                            )
                            continue
                        else:
                            # 成功执行的tool响应
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": text_to_gpt,
                                }
                            )
                            # 将代码执行输出存储到 section_output，供 Writer 和指标提取使用
                            if text_to_gpt:
                                self.code_interpreter.add_content(subtask_title, text_to_gpt)
                            # 标记已成功执行代码
                            self._code_executed = True
                            self._successful_executions += 1
                            # 成功执行后重置重试计数
                            retry_count = 0
                            last_error_message = ""
                            # 重置完成度检查，允许新一轮工具调用后再次检查
                            self._completion_checked = False
                            # 成功执行后继续循环，等待下一步指令
                            continue
                else:
                    # 没有工具调用 - 检查任务是否真的完成
                    response_content = response.choices[0].message.content

                    # 将助手响应加入历史
                    await self.append_chat_history(
                        response.choices[0].message.model_dump()
                    )

                    # === 防护：未执行任何代码就尝试结束 ===
                    if (
                        not self._code_executed
                        and self.current_chat_turns < self.max_chat_turns - 2
                        and not self._completion_checked
                    ):
                        logger.warning(
                            "CoderAgent 尚未执行任何代码就尝试结束，强制要求编写代码"
                        )
                        self._completion_checked = True
                        nudge_prompt = (
                            "你尚未执行任何代码。本任务要求你编写并执行 Python 代码来完成求解。"
                            "请立即使用 execute_code 工具编写代码，完成任务要求的计算和可视化。"
                        )
                        await self.append_chat_history(
                            {"role": "user", "content": nudge_prompt}
                        )
                        continue

                    # 执行完成度检查（仅在非最后轮次时）
                    if self.current_chat_turns < self.max_chat_turns - 2:
                        if not self._completion_checked:
                            self._completion_checked = True

                            # 注入客观执行证据到 completion_check prompt
                            evidence_parts: list[str] = []
                            evidence_parts.append(
                                f"代码执行统计: 成功执行 {self._successful_executions} 次"
                            )
                            try:
                                created_imgs = await self.code_interpreter.get_created_images(
                                    subtask_title
                                )
                                if created_imgs:
                                    evidence_parts.append(
                                        f"已生成图表: {len(created_imgs)} 张"
                                    )
                                else:
                                    evidence_parts.append(
                                        "尚未生成任何图表（若任务要求可视化，请补充）"
                                    )
                            except Exception:
                                pass  # 图表获取失败不影响主流程

                            evidence_text = "\n".join(evidence_parts)
                            base_completion_prompt = get_completion_check_prompt(
                                prompt, response_content
                            )
                            enhanced_prompt = (
                                f"{base_completion_prompt}\n\n"
                                f"【客观执行证据】\n{evidence_text}\n"
                                f"请根据以上客观证据判断任务是否真正完成。"
                            )
                            await self.append_chat_history(
                                {"role": "user", "content": enhanced_prompt}
                            )
                            logger.info(
                                "执行增强完成度检查（注入执行证据: %d 次成功执行）",
                                self._successful_executions,
                            )
                            # 继续循环，让 LLM 决定是否需要继续执行
                            continue

                    # 任务确认完成
                    self._completion_checked = False
                    logger.info("任务完成确认")
                    return CoderToWriter(
                        code_response=response_content,
                        created_images=await self.code_interpreter.get_created_images(
                            subtask_title
                        ),
                    )
                    
            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                raise  # 不可重试的系统异常，直接上抛
            except Exception as e:
                logger.error("执行过程中发生异常: %s", e)
                retry_count += 1
                self._total_errors += 1
                last_error_message = str(e)
                continue

    def _trim_chat_history(self) -> None:
        """智能裁剪 chat_history，防止跨子任务历史无限膨胀。

        保留第一条 system prompt + 第二条数据集文件信息 + 最近 max_history_messages - 2 条消息，
        裁剪掉中间的旧对话，减少无关上下文对注意力的干扰和 Token 消耗。

        裁剪时保证 tool_call / tool_response 配对完整性：
        如果裁剪边界恰好落在 assistant(tool_calls) 与 tool response 之间，
        会自动向前扩展保留区域，避免拆散配对导致 LLM API 400 错误。
        """
        if len(self.chat_history) <= self.max_history_messages:
            return

        # 识别需要始终保留的前置消息
        pinned: list[dict] = []

        # 保留 system prompt（第一条 role=system）
        if self.chat_history and self.chat_history[0].get("role") == "system":
            pinned.append(self.chat_history[0])

        # 保留数据集文件信息（第二条 role=user，包含"当前文件夹下的数据集文件"）
        if (
            len(self.chat_history) > 1
            and self.chat_history[1].get("role") == "user"
            and "当前文件夹下的数据集文件" in self.chat_history[1].get("content", "")
        ):
            pinned.append(self.chat_history[1])

        # 计算尾部保留区域的起始索引
        keep_recent = self.max_history_messages - len(pinned)
        keep_start = len(self.chat_history) - keep_recent

        # === tool_call 配对完整性保护 ===
        # 如果保留区域的第一条消息是 role=tool，向前扩展直到找到对应的 assistant(tool_calls)
        while (
            keep_start > len(pinned)
            and self.chat_history[keep_start].get("role") == "tool"
        ):
            keep_start -= 1

        # 如果裁剪边界前一条是含 tool_calls 的 assistant 消息，也纳入保留区域
        if (
            keep_start > len(pinned)
            and self.chat_history[keep_start - 1].get("role") == "assistant"
            and self.chat_history[keep_start - 1].get("tool_calls")
        ):
            keep_start -= 1

        # 重建历史：固定前置消息 + 保留的尾部消息
        new_history: list[dict] = list(pinned)
        new_history.extend(self.chat_history[keep_start:])
        trimmed_count = keep_start - len(pinned)

        logger.info(
            "CoderAgent chat_history 裁剪完成: 原始 %d 条 -> 保留 %d 条（裁剪了 %d 条旧消息）",
            len(self.chat_history),
            len(new_history),
            trimmed_count,
        )
        self.chat_history = new_history