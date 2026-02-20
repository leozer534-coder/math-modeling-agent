from typing import Literal, Union
from app.schemas.enums import AgentType
from pydantic import BaseModel, Field
from uuid import uuid4


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    msg_type: Literal[
        "system", "agent", "user", "tool", "progress", "stream"
    ]  # system msg | agent message | user message | tool message | progress message | stream message
    content: str | None = None


class ToolMessage(Message):
    msg_type: str = "tool"
    tool_name: Literal["execute_code", "search_scholar"]
    input: dict | None = None
    output: list | None = None


class SystemMessage(Message):
    msg_type: str = "system"
    type: Literal["info", "warning", "success", "error"] = "info"


class UserMessage(Message):
    msg_type: str = "user"


class AgentMessage(Message):
    msg_type: str = "agent"
    agent_type: AgentType  # CoordinatorAgent | ModelerAgent | CoderAgent | WriterAgent


class ModelerMessage(AgentMessage):
    agent_type: AgentType = AgentType.MODELER


class CoordinatorMessage(AgentMessage):
    agent_type: AgentType = AgentType.COORDINATOR


class CodeExecution(BaseModel):
    res_type: Literal["stdout", "stderr", "result", "error"]
    msg: str | None = None


class StdOutModel(CodeExecution):
    res_type: str = "stdout"


class StdErrModel(CodeExecution):
    res_type: str = "stderr"


class ResultModel(CodeExecution):
    res_type: str = "result"
    format: Literal[
        "text",
        "html",
        "markdown",
        "png",
        "jpeg",
        "svg",
        "pdf",
        "latex",
        "json",
        "javascript",
    ]


class ErrorModel(CodeExecution):
    res_type: str = "error"
    name: str
    value: str
    traceback: str


# 代码执行结果类型
OutputItem = Union[StdOutModel, StdErrModel, ResultModel, ErrorModel]


class ProgressMessage(Message):
    """任务进度消息"""
    msg_type: str = "progress"
    type: Literal["info", "warning", "success", "error"] = "info"
    percent: float = 0.0
    phase: str = ""
    message: str = ""


class ScholarMessage(ToolMessage):
    tool_name: str = "search_scholar"
    input: dict | None = None  # query
    output: list[str] | None = None  # cites


class InterpreterMessage(ToolMessage):
    tool_name: str = "execute_code"
    input: dict | None = None  # code
    output: list[OutputItem] | None = None  # code_results


# 1. 只带 code
# 2. 只带 code result
class CoderMessage(AgentMessage):
    agent_type: AgentType = AgentType.CODER


class WriterMessage(AgentMessage):
    agent_type: AgentType = AgentType.WRITER
    sub_title: str | None = None


class StreamMessage(Message):
    """LLM 流式输出消息，前端按 message_id 拼接 delta"""
    msg_type: str = "stream"
    agent_type: str = ""       # 哪个 agent 在说话
    delta: str = ""            # 增量 token 内容
    message_id: str = ""       # 用于前端识别同一消息流
    done: bool = False         # 是否流式结束


# 所有可能的消息类型
MessageType = Union[
    SystemMessage,
    ProgressMessage,
    UserMessage,
    ModelerMessage,
    CoderMessage,
    WriterMessage,
    CoordinatorMessage,
    StreamMessage,
]
