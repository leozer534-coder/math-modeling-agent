from enum import Enum


class CompTemplate(str, Enum):
    CHINA: str = "CHINA"
    AMERICAN: str = "AMERICAN"


class FormatOutPut(str, Enum):
    Markdown: str = "Markdown"
    LaTeX: str = "LaTeX"


class AgentType(str, Enum):
    COORDINATOR = "CoordinatorAgent"
    MODELER = "ModelerAgent"
    CODER = "CoderAgent"
    WRITER = "WriterAgent"
    SYSTEM = "SystemAgent"
    REVIEWER = "ReviewerAgent"
    ANALYZER = "AnalyzerAgent"
    VALIDATOR = "ValidatorAgent"
    OPTIMIZER = "OptimizerAgent"


class WorkflowMode(str, Enum):
    """工作流模式"""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    AWARD = "award"
    AUTO = "auto"


class AgentStatus(str, Enum):
    START = "start"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"
    SUCCESS = "success"
