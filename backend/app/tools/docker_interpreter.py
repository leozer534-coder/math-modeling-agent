# docker_interpreter.py
"""
Docker 沙箱适配器

将 DockerSandbox 包装为 BaseCodeInterpreter 兼容接口，
使其可以与 LocalCodeInterpreter / E2BCodeInterpreter 无缝替换。
"""

from pathlib import Path

from app.schemas.response import (
    OutputItem,
    ResultModel,
    StdErrModel,
    SystemMessage,
)
from app.services.redis_manager import redis_manager
from app.tools.base_interpreter import BaseCodeInterpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.sandbox import DockerSandbox, ExecutionResult, SandboxConfig
from app.tools.sandbox.docker_sandbox import ExecutionStatus
from app.utils.log_util import logger


class DockerCodeInterpreter(BaseCodeInterpreter):
    """
    Docker 沙箱代码解释器

    通过 Docker 容器隔离执行 LLM 生成的代码，
    接口与 LocalCodeInterpreter / E2BCodeInterpreter 完全兼容。
    """

    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".gif", ".bmp")

    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
        timeout: int = 300,
        sandbox_config: SandboxConfig | None = None,
    ):
        super().__init__(task_id, work_dir, notebook_serializer, timeout=timeout)

        config = sandbox_config or SandboxConfig(
            timeout_seconds=timeout,
            memory_limit="4g",  # 数学建模需要更多内存
        )
        self._sandbox = DockerSandbox(config)

    async def initialize(self):
        """检查 Docker 可用性和镜像存在性"""
        if not await self._sandbox.check_docker_available():
            raise RuntimeError(
                "Docker 未安装或未运行，无法使用 Docker 沙箱。"
                "请安装并启动 Docker，或切换到其他执行模式。"
            )

        if not await self._sandbox.check_image_exists():
            raise RuntimeError(
                f"Docker 镜像 '{self._sandbox.config.image}' 不存在。"
                f"请先构建: docker build -t {self._sandbox.config.image} -f Dockerfile.sandbox ."
            )

        logger.info(
            f"✅ Docker 沙箱已就绪 [task={self.task_id}, "
            f"image={self._sandbox.config.image}]"
        )

    async def _pre_execute_code(self):
        """Docker 沙箱无需预执行初始化代码（容器每次都是全新环境）"""
        pass

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        """
        在 Docker 容器中执行代码

        Returns:
            (output_text, error_occurred, error_message)
        """
        logger.info("Docker 沙箱执行代码 [task=%s]", self.task_id)

        # 记录到 notebook
        self.notebook_serializer.add_code_cell_to_notebook(code)

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="开始在 Docker 沙箱中执行代码"),
        )

        # 准备输入文件：将工作目录中的数据文件传入容器
        input_files = self._collect_input_files()

        # 执行
        result: ExecutionResult = await self._sandbox.execute(
            code=code,
            timeout=self.timeout,
            input_files=input_files,
        )

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="Docker 沙箱代码执行完成"),
        )

        # 转换结果
        return self._convert_result(result)

    def _collect_input_files(self) -> dict[str, bytes] | None:
        """收集工作目录中需要传入容器的数据文件"""
        work_path = Path(self.work_dir)
        if not work_path.exists():
            return None

        input_files: dict[str, bytes] = {}
        # 只传入数据文件，跳过过大的文件（>50MB）
        max_file_size = 50 * 1024 * 1024
        allowed_extensions = (
            ".csv", ".xlsx", ".xls", ".json", ".txt", ".dat",
            ".tsv", ".parquet", ".h5", ".hdf5", ".mat", ".npy",
        )

        for item in work_path.iterdir():
            if (
                item.is_file()
                and item.suffix.lower() in allowed_extensions
                and item.stat().st_size <= max_file_size
            ):
                try:
                    input_files[item.name] = item.read_bytes()
                except OSError as e:
                    logger.warning("读取输入文件失败: %s: %s", item.name, e)

        return input_files if input_files else None

    def _convert_result(
        self, result: ExecutionResult
    ) -> tuple[str, bool, str]:
        """将 ExecutionResult 转换为 BaseCodeInterpreter 标准三元组"""
        text_to_gpt: list[str] = []
        content_to_display: list[OutputItem] = []
        error_occurred = False
        error_message = ""

        if result.is_success:
            if result.stdout:
                truncated = self._truncate_text(result.stdout)
                text_to_gpt.append(f"[stdout]\n{truncated}")
                content_to_display.append(
                    ResultModel(type="result", format="text", msg=result.stdout)
                )
                self.notebook_serializer.add_code_cell_output_to_notebook(
                    result.stdout
                )
        else:
            error_occurred = True
            if result.status == ExecutionStatus.TIMEOUT:
                error_message = f"代码执行超时（{self.timeout}秒），已被强制中断。"
            elif result.status == ExecutionStatus.RESOURCE_EXCEEDED:
                error_message = "代码执行超出资源限制（内存不足），已被终止。"
            else:
                error_message = self.delete_color_control_char(result.stderr or result.output)
                error_message = self._truncate_text(error_message)

            text_to_gpt.append(error_message)
            self.notebook_serializer.add_code_cell_error_to_notebook(error_message)
            content_to_display.append(StdErrModel(msg=error_message))

        # 即使成功也可能有 stderr 输出（警告等）
        if not error_occurred and result.stderr:
            text_to_gpt.append(f"[stderr]\n{self._truncate_text(result.stderr)}")

        # 复制容器生成的文件到工作目录
        self._copy_output_files(result)

        combined_text = "\n".join(text_to_gpt)
        combined_text = self._truncate_combined_output(combined_text)
        return combined_text, error_occurred, error_message

    def _copy_output_files(self, result: ExecutionResult) -> None:
        """将容器中生成的文件复制到工作目录（如果沙箱支持）"""
        # DockerSandbox 使用临时目录挂载，文件已在 temp_dir 中
        # 这里主要记录生成的文件信息
        for file_path in result.files_created:
            logger.debug("Docker 容器生成文件: %s", file_path)

    async def get_created_images(self, section: str) -> list[str]:
        """获取新创建的图片列表"""
        current_images = set()
        work_path = Path(self.work_dir)

        if work_path.exists():
            for file in work_path.iterdir():
                if file.is_file() and file.suffix.lower() in self.IMAGE_EXTENSIONS:
                    current_images.add(file.name)

        # 计算新增的图片
        new_images = current_images - self.last_created_images
        self.last_created_images = current_images

        logger.info("Docker 沙箱新创建的图片: %s", new_images)
        return list(new_images)

    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        logger.info("Docker 沙箱资源已清理 [task=%s]", self.task_id)
