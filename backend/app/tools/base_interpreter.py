# base_interpreter.py
import abc
import os
import re
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.code_sanitizer import CodeSanitizer
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger
from app.schemas.response import (
    OutputItem,
    InterpreterMessage,
)

# matplotlib 中文字体跨平台自动配置代码
# 在解释器初始化时自动预执行，无需 LLM 手动设置
MATPLOTLIB_SETUP_CODE = (
    "# 中文图表显示配置（跨平台自动检测）\n"
    "try:\n"
    "    import matplotlib\n"
    "    matplotlib.use('Agg')\n"
    "    import matplotlib.pyplot as plt\n"
    "    import platform\n"
    "    import warnings\n"
    "    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')\n"
    "\n"
    "    system = platform.system()\n"
    '    if system == "Windows":\n'
    '        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]\n'
    '    elif system == "Darwin":\n'
    '        plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "DejaVu Sans"]\n'
    "    else:\n"
    '        plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei", "DejaVu Sans"]\n'
    '    plt.rcParams["axes.unicode_minus"] = False\n'
    '    plt.rcParams["figure.dpi"] = 150\n'
    '    plt.rcParams["savefig.dpi"] = 150\n'
    '    plt.rcParams["savefig.bbox_inches"] = "tight"\n'
    "    print('matplotlib 中文字体配置完成')\n"
    "except Exception as _e:\n"
    "    print(f'matplotlib 配置跳过: {_e}')\n"
)


class BaseCodeInterpreter(abc.ABC):
    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
        timeout: int = 300,
    ):
        self.task_id = task_id
        self.work_dir = work_dir
        self.notebook_serializer = notebook_serializer
        self.timeout = timeout
        self.section_output: dict[str, dict[str, list[str]]] = {}
        self.last_created_images: set[str] = set()
        self.created_images: list[str] = []
        self.last_created_data_files: set[str] = set()

    @abc.abstractmethod
    async def initialize(self):
        """初始化解释器，必要时上传文件、启动内核等"""
        ...

    @abc.abstractmethod
    async def _pre_execute_code(self):
        """执行初始化代码"""
        ...

    def _sanitize_code(self, code: str) -> None:
        """在执行代码前进行安全审查，不安全则抛出 ValueError。

        所有子类的 execute_code 方法应在执行前调用此方法，
        作为防御纵深的一环，在沙箱隔离之前提供额外安全屏障。
        """
        CodeSanitizer.sanitize_or_raise(code)

    @abc.abstractmethod
    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        """执行一段代码，返回 (输出文本, 是否出错, 错误信息)"""
        ...

    @abc.abstractmethod
    async def cleanup(self):
        """清理资源，比如关闭沙箱或内核"""
        ...

    @abc.abstractmethod
    async def get_created_images(self, section: str) -> list[str]:
        """获取当前 section 创建的图片列表"""
        ...

    async def _push_to_websocket(self, content_to_display: list[OutputItem] | None):
        logger.info("执行结果已推送到WebSocket")

        agent_msg = InterpreterMessage(
            output=content_to_display,
        )
        logger.debug("发送消息: %s", agent_msg.model_dump_json())
        await redis_manager.publish_message(
            self.task_id,
            agent_msg,
        )

    def add_section(self, section_name: str) -> None:
        """确保添加的section结构正确"""

        if section_name not in self.section_output:
            self.section_output[section_name] = {"content": [], "images": []}

    def add_content(self, section: str, text: str) -> None:
        """向指定section添加文本内容"""
        self.add_section(section)
        self.section_output[section]["content"].append(text)

    def get_code_output(self, section: str) -> str:
        """获取指定section的代码输出，section 不存在时返回空字符串。"""
        section_data = self.section_output.get(section)
        if section_data is None:
            return ""
        return "\n".join(section_data["content"])

    def get_created_data_files(self, section: str) -> list[str]:
        """获取指定 section 新创建的数据文件列表（CSV/Excel/JSON 等）。

        采用与 get_created_images 相同的增量检测模式：
        对比 last_created_data_files 和当前工作目录中的数据文件，
        返回新增文件列表并更新快照。

        Args:
            section: 子任务标识。

        Returns:
            新创建的数据文件名列表。
        """
        data_extensions = (".csv", ".xlsx", ".xls", ".json", ".parquet", ".pkl")
        current_data_files = set()
        try:
            for f in os.listdir(self.work_dir):
                if f.lower().endswith(data_extensions) and os.path.isfile(
                    os.path.join(self.work_dir, f)
                ):
                    current_data_files.add(f)
        except OSError as e:
            logger.warning("扫描数据文件失败: %s", e)
            return []

        new_files = current_data_files - self.last_created_data_files
        self.last_created_data_files = current_data_files
        if new_files:
            logger.info("section=%s 新创建的数据文件: %s", section, new_files)
        return sorted(new_files)

    def delete_color_control_char(self, string: str) -> str:
        ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
        return ansi_escape.sub("", string)

    def _truncate_text(self, text: str, max_length: int = 1000) -> str:
        """截断文本，保留开头和结尾的重要信息"""
        if len(text) <= max_length:
            return text

        half_length = max_length // 2
        return text[:half_length] + "\n... (内容已截断) ...\n" + text[-half_length:]

    def _truncate_combined_output(self, combined_text: str, max_total: int = 8000) -> str:
        """对合并后的总输出做二次截断保护。

        单条输出由 _truncate_text() 控制（默认 1000 字符），但当多个输出块
        合并后总量可能远超预期。此方法作为防御性截断，防止超长合并输出
        浪费内存或在跳过 Agent 层时直接溢出 LLM 上下文窗口。

        Args:
            combined_text: 合并后的完整输出文本。
            max_total: 允许的最大字符数，默认 8000。

        Returns:
            截断后的文本，保留前 2/3 和后 1/3 的内容。
        """
        if not combined_text or len(combined_text) <= max_total:
            return combined_text
        head_size = max_total * 2 // 3
        tail_size = max_total // 3
        logger.info(
            "合并输出截断: %d -> %d 字符（前 %d + 后 %d）",
            len(combined_text), head_size + tail_size, head_size, tail_size,
        )
        return (
            combined_text[:head_size]
            + f"\n\n... [合并输出已截断: 原始 {len(combined_text)} 字符，"
            f"保留前 {head_size} + 后 {tail_size} 字符] ...\n\n"
            + combined_text[-tail_size:]
        )
