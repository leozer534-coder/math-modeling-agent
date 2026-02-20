import os
from e2b_code_interpreter import AsyncSandbox
from app.schemas.response import (
    ErrorModel,
    OutputItem,
    ResultModel,
    StdErrModel,
    StdOutModel,
    SystemMessage,
)
from app.services.redis_manager import redis_manager
from app.tools.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger
from app.config.setting import settings
import json
from app.tools.base_interpreter import BaseCodeInterpreter, MATPLOTLIB_SETUP_CODE


class E2BCodeInterpreter(BaseCodeInterpreter):
    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
    ):
        super().__init__(task_id, work_dir, notebook_serializer)
        self.sbx = None
        self._seen_images: set[str] = set()

    @classmethod
    async def create(
        cls,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
    ) -> "E2BCodeInterpreter":
        """创建并初始化 E2BCodeInterpreter 实例"""
        instance = cls(task_id, work_dir, notebook_serializer)
        return instance

    async def initialize(self, timeout: int = 3000):
        """异步初始化沙箱环境"""
        try:
            self.sbx = await AsyncSandbox.create(
                api_key=settings.E2B_API_KEY, timeout=timeout
            )
            logger.info("沙箱环境初始化成功")
            await self._pre_execute_code()
            await self._upload_all_files()
        except Exception as e:
            logger.error("初始化沙箱环境失败: %s", e)
            raise

    async def _upload_all_files(self):
        """上传工作目录中的所有文件到沙箱"""
        try:
            logger.info("开始上传文件，工作目录: %s", self.work_dir)
            if not os.path.exists(self.work_dir):
                logger.error("工作目录不存在: %s", self.work_dir)
                raise FileNotFoundError(f"工作目录不存在: {self.work_dir}")

            files = [
                f for f in os.listdir(self.work_dir) if f.endswith((".csv", ".xlsx"))
            ]
            logger.info("工作目录中的文件列表: %s", files)

            for file in files:
                file_path = os.path.join(self.work_dir, file)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read()
                            # 使用官方推荐的 files.write 方法
                            await self.sbx.files.write(f"/home/user/{file}", content)
                            logger.info("成功上传文件到沙箱: %s", file)
                    except Exception as e:
                        logger.error("上传文件 %s 失败: %s", file, e)
                        raise

        except Exception as e:
            logger.error("文件上传过程失败: %s", e)
            raise

    async def _pre_execute_code(self):
        """执行沙箱初始化代码：配置 matplotlib 中文字体和随机种子。"""
        # 使用共享的跨平台 matplotlib 中文字体配置
        await self.execute_code(MATPLOTLIB_SETUP_CODE)

        # 随机种子配置（默认值，可被后续代码覆盖）
        seed_code = (
            "try:\n"
            "    import numpy as np\n"
            "    np.random.seed(42)\n"
            "    import random\n"
            "    random.seed(42)\n"
            "    print('随机种子已设置: 42')\n"
            "except Exception as _e:\n"
            "    print(f'随机种子设置跳过: {_e}')\n"
        )
        await self.execute_code(seed_code)

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        """执行代码并返回结果"""

        if not self.sbx:
            raise RuntimeError("沙箱环境未初始化")

        # 代码安全审查：在执行前检测危险模式
        self._sanitize_code(code)

        logger.info("执行代码 (%d 字符)", len(code))
        logger.debug("执行代码内容: %s", code)
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[OutputItem] | None = []
        error_occurred: bool = False
        error_message: str = ""

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="开始执行代码"),
        )
        # 执行 Python 代码
        logger.info("开始在沙箱中执行代码...")
        execution = await self.sbx.run_code(code)  # 返回 Execution 对象
        logger.info("代码执行完成，开始处理结果...")

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="代码执行完成"),
        )

        # 处理执行错误
        if execution.error:
            error_occurred = True
            error_message = f"Error: {execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
            error_message = self._truncate_text(error_message)
            logger.error("执行错误: %s", error_message)
            text_to_gpt.append(self.delete_color_control_char(error_message))
            content_to_display.append(
                ErrorModel(
                    name=execution.error.name,
                    value=execution.error.value,
                    traceback=execution.error.traceback,
                )
            )
        # 处理标准输出和标准错误

        if execution.logs:
            if execution.logs.stdout:
                stdout_str = "\n".join(execution.logs.stdout)
                stdout_str = self._truncate_text(stdout_str)
                logger.info("标准输出: %s", stdout_str)
                text_to_gpt.append(stdout_str)
                content_to_display.append(
                    StdOutModel(msg="\n".join(execution.logs.stdout))
                )
                self.notebook_serializer.add_code_cell_output_to_notebook(stdout_str)

            if execution.logs.stderr:
                stderr_str = "\n".join(execution.logs.stderr)
                stderr_str = self._truncate_text(stderr_str)
                logger.warning("标准错误: %s", stderr_str)
                text_to_gpt.append(stderr_str)
                content_to_display.append(
                    StdErrModel(msg="\n".join(execution.logs.stderr))
                )

            # 处理执行结果
        if execution.results:
            for result in execution.results:
                # 1. 文本格式
                if str(result):
                    content_to_display.append(
                        ResultModel(type="result", format="text", msg=str(result))
                    )
                # 2. HTML格式
                if result._repr_html_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="html", msg=result._repr_html_()
                        )
                    )
                # 3. Markdown格式
                if result._repr_markdown_():
                    content_to_display.append(
                        ResultModel(
                            type="result",
                            format="markdown",
                            msg=result._repr_markdown_(),
                        )
                    )
                # 4. PNG图片（base64字符串，前端可直接渲染）
                if result._repr_png_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="png", msg=result._repr_png_()
                        )
                    )
                # 5. JPEG图片
                if result._repr_jpeg_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="jpeg", msg=result._repr_jpeg_()
                        )
                    )
                # 6. SVG
                if result._repr_svg_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="svg", msg=result._repr_svg_()
                        )
                    )
                # 7. PDF
                if result._repr_pdf_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="pdf", msg=result._repr_pdf_()
                        )
                    )
                # 8. LaTeX
                if result._repr_latex_():
                    content_to_display.append(
                        ResultModel(
                            type="result", format="latex", msg=result._repr_latex_()
                        )
                    )
                # 9. JSON
                if result._repr_json_():
                    content_to_display.append(
                        ResultModel(
                            type="result",
                            format="json",
                            msg=json.dumps(result._repr_json_()),
                        )
                    )
                # 10. JavaScript
                if result._repr_javascript_():
                    content_to_display.append(
                        ResultModel(
                            type="result",
                            format="javascript",
                            msg=result._repr_javascript_(),
                        )
                    )

                    # 处理主要结果
                # if result.is_main_result and result.text:
                #     result_text = self._truncate_text(result.text)
                #     logger.info(f"主要结果: {result_text}")
                #     text_to_gpt.append(result_text)
                #     self.notebook_serializer.add_code_cell_output_to_notebook(
                #         result_text
                #     )

        # 限制返回的文本总长度

        for item in content_to_display:
            if isinstance(item, ResultModel):
                if item.format in ["text", "html", "markdown", "json"]:
                    text_to_gpt.append(
                        self._truncate_text(f"[{item.format}]\n{item.msg}")
                    )
                elif item.format in ["png", "jpeg", "svg", "pdf"]:
                    text_to_gpt.append(
                        f"[{item.format} 图片已生成，内容为 base64，未展示]"
                    )

        logger.debug("text_to_gpt: %s", text_to_gpt)

        combined_text = "\n".join(text_to_gpt)
        combined_text = self._truncate_combined_output(combined_text)

        # 在代码执行完成后，立即同步文件
        try:
            await self.download_all_files_from_sandbox()
            logger.info("文件同步完成")
        except Exception as e:
            logger.error("文件同步失败: %s", e)

        # 保存到分段内容
        ## TODO: Base64 等图像需要优化
        await self._push_to_websocket(content_to_display)

        return (
            combined_text,
            error_occurred,
            error_message,
        )

    async def get_created_images(self, section: str) -> list[str]:
        """获取当前 section 创建的图片列表（仅返回本次新增，不重复）"""
        if not self.sbx:
            logger.warning("沙箱环境未初始化")
            return []

        try:
            files = await self.sbx.files.list("./")
            for file in files:
                if file.path.endswith(".png") or file.path.endswith(".jpg"):
                    self.add_section(section)
                    self.section_output[section]["images"].append(file.name)

            all_images = set(self.section_output[section].get("images", []))
            new_images = list(all_images - self._seen_images)
            self._seen_images.update(new_images)
            self.created_images = new_images
            logger.info("%s-获取创建的图片列表: %s", section, new_images)
            return new_images
        except Exception as e:
            logger.error("获取创建的图片列表失败: %s", e)
            return []

    async def cleanup(self):
        """清理资源并关闭沙箱"""
        if not self.sbx:
            return
        try:
            try:
                running = await self.sbx.is_running()
            except Exception as e:
                logger.warning("检查沙箱状态失败: %s，仍将尝试清理", e)
                running = True  # 假设还在运行，确保尝试 kill

            if running:
                try:
                    await self.download_all_files_from_sandbox()
                except Exception as e:
                    logger.error("下载沙箱文件失败: %s", e)
        finally:
            try:
                await self.sbx.kill()
                logger.info("E2B 沙箱已关闭")
            except Exception as e:
                logger.error("关闭 E2B 沙箱失败: %s", e)
            # 这里可以选择不抛出异常，因为这是清理步骤

    async def download_all_files_from_sandbox(self) -> None:
        """从沙箱中下载所有文件并与本地同步"""
        try:
            # 获取沙箱中的文件列表
            sandbox_files = await self.sbx.files.list("/home/user")
            _sandbox_files_dict = {f.name: f for f in sandbox_files}

            # 获取本地文件列表
            local_files = set()
            if os.path.exists(self.work_dir):
                local_files = set(os.listdir(self.work_dir))

            # 下载新文件或更新已修改的文件
            for file in sandbox_files:
                try:
                    # 排除 .bash_logout、.bashrc 和 .profile 文件
                    if file.name in [".bash_logout", ".bashrc", ".profile"]:
                        continue

                    local_path = os.path.join(self.work_dir, file.name)
                    should_download = True

                    # 检查文件是否需要更新
                    if file.name in local_files:
                        # 这里可以添加文件修改时间或内容哈希的比较
                        # 暂时简单处理，有同名文件就更新
                        pass

                    if should_download:
                        # 使用 bytes 格式读取文件内容，确保正确处理二进制数据
                        content = await self.sbx.files.read(file.path, format="bytes")

                        # 确保目标目录存在
                        os.makedirs(self.work_dir, exist_ok=True)

                        # 写入文件
                        with open(local_path, "wb") as f:
                            f.write(content)
                        logger.info("同步文件: %s", file.name)

                except Exception as e:
                    logger.error("同步文件 %s 失败: %s", file.name, e)
                    continue

            logger.info("文件同步完成")

        except Exception as e:
            logger.error("文件同步失败: %s", e)
