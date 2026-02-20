"""
环境设置阶段 - 创建代码解释器、Agent 实例和用户输出

职责:
  1. 创建 CodeInterpreter (本地 Jupyter 或 E2B 云端)
  2. 创建 CoderAgent / WriterAgent / OpenAlexScholar
  3. 创建 UserOutput 实例
  4. 将所有服务对象写入 PipelineContext
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.setting import settings
from app.core.agents import CoderAgent, WriterAgent
from app.models.user_output import UserOutput
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class SetupStage:
    """环境设置阶段"""

    @property
    def name(self) -> str:
        return "setup"

    async def execute(self, ctx: PipelineContext) -> None:
        """初始化代码解释器和 Agent 实例（含错误处理层）"""
        try:
            await self._do_execute(ctx)
        except Exception:
            logger.error(
                "SetupStage 执行失败 [task_id=%s]",
                ctx.task_id,
                exc_info=True,
            )
            try:
                await ctx.send_progress("环境设置阶段执行失败", -1)
            except Exception:
                logger.warning("SetupStage: 发送错误进度通知失败")
            raise

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """SetupStage 核心业务逻辑"""
        await ctx.send_progress("正在准备执行环境...", 16)

        # 创建代码解释器
        notebook_serializer = NotebookSerializer(work_dir=ctx.work_dir)
        ctx.code_interpreter = await create_interpreter(
            kind="auto",
            task_id=ctx.task_id,
            work_dir=ctx.work_dir,
            notebook_serializer=notebook_serializer,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
        )

        # 创建文献搜索器
        scholar = OpenAlexScholar(
            task_id=ctx.task_id,
            email=settings.OPENALEX_EMAIL,
        )

        # 创建 CoderAgent
        coder_agent = CoderAgent(
            task_id=ctx.task_id,
            model=ctx.llms["coder"],
            work_dir=ctx.work_dir,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            code_interpreter=ctx.code_interpreter,
            enable_memory_system=settings.ENABLE_MEMORY_SYSTEM,
            comp_template=ctx.problem.comp_template,
        )
        ctx.agents["coder"] = coder_agent

        # 创建 WriterAgent
        writer_agent = WriterAgent(
            task_id=ctx.task_id,
            model=ctx.llms["writer"],
            comp_template=ctx.problem.comp_template,
            format_output=ctx.problem.format_output,
            scholar=scholar,
        )
        ctx.agents["writer"] = writer_agent

        # 创建用户输出
        ctx.user_output = UserOutput(
            work_dir=ctx.work_dir,
            ques_count=ctx.ques_count,
            comp_template=ctx.problem.comp_template,
        )

        await ctx.send_progress("执行环境准备完成", 20)
        logger.info("SetupStage 完成: 代码解释器和 Agent 已就绪")
