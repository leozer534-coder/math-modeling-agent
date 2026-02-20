import asyncio
import queue
import time

import jupyter_client

import os

from app.tools.base_interpreter import BaseCodeInterpreter, MATPLOTLIB_SETUP_CODE
from app.tools.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.response import (
    OutputItem,
    ResultModel,
    StdErrModel,
    SystemMessage,
)


class LocalCodeInterpreter(BaseCodeInterpreter):
    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
    ):
        super().__init__(task_id, work_dir, notebook_serializer)
        self.km, self.kc = None, None
        self.interrupt_signal = False

    async def initialize(self):
        # 本地内核一般不需异步上传文件，直接切换目录即可
        # 初始化 Jupyter 内核管理器和客户端（卸载到线程池，避免阻塞事件循环 2-5 秒）
        logger.info("初始化本地内核")
        loop = asyncio.get_running_loop()
        self.km, self.kc = await loop.run_in_executor(
            None,
            lambda: jupyter_client.manager.start_new_kernel(kernel_name="python3"),
        )
        # _pre_execute_code 内部调用同步的 execute_code_，同样卸载到线程池
        await loop.run_in_executor(None, self._pre_execute_code)

    def _pre_execute_code(self):
        """执行内核初始化代码：设置工作目录、注入 math_tools 路径、配置中文字体和随机种子。"""
        # 计算 tools 目录的绝对路径（即 backend/app/tools/）
        # 注入后 Jupyter 内核中可直接 from math_tools import ...
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        init_code = (
            f"import os, sys\n"
            f"work_dir = r'{self.work_dir}'\n"
            f"os.makedirs(work_dir, exist_ok=True)\n"
            f"os.chdir(work_dir)\n"
            f"print('当前工作目录:', os.getcwd())\n"
            f"# 注入 math_tools 路径，使代码可以 from math_tools import ...\n"
            f"_tools_dir = r'{tools_dir}'\n"
            f"if _tools_dir not in sys.path:\n"
            f"    sys.path.insert(0, _tools_dir)\n"
            f"    print('已注入 math_tools 路径:', _tools_dir)\n"
        )
        self.execute_code_(init_code)

        # 使用共享的跨平台 matplotlib 中文字体配置
        self.execute_code_(MATPLOTLIB_SETUP_CODE)

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
        self.execute_code_(seed_code)

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        # 代码安全审查：在执行前检测危险模式
        self._sanitize_code(code)

        logger.info("执行代码: %s", code)
        #  添加代码到notebook
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[OutputItem] | None = []
        error_occurred: bool = False
        error_message: str = ""

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="开始执行代码"),
        )
        # 执行 Python 代码（卸载到线程池，避免阻塞事件循环）
        logger.info("开始在本地执行代码...")
        loop = asyncio.get_running_loop()
        execution = await loop.run_in_executor(None, self.execute_code_, code)
        logger.info("代码执行完成，开始处理结果...")

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="代码执行完成"),
        )

        for mark, out_str in execution:
            if mark in ("stdout", "execute_result_text", "display_text"):
                text_to_gpt.append(self._truncate_text(f"[{mark}]\n{out_str}"))
                #  添加text到notebook
                content_to_display.append(
                    ResultModel(type="result", format="text", msg=out_str)
                )
                self.notebook_serializer.add_code_cell_output_to_notebook(out_str)

            elif mark in (
                "execute_result_png",
                "execute_result_jpeg",
                "display_png",
                "display_jpeg",
            ):
                # TODO: 视觉模型解释图像
                text_to_gpt.append(f"[{mark} 图片已生成，内容为 base64，未展示]")

                #  添加image到notebook
                if "png" in mark:
                    self.notebook_serializer.add_image_to_notebook(out_str, "image/png")
                    content_to_display.append(
                        ResultModel(type="result", format="png", msg=out_str)
                    )
                else:
                    self.notebook_serializer.add_image_to_notebook(
                        out_str, "image/jpeg"
                    )
                    content_to_display.append(
                        ResultModel(type="result", format="jpeg", msg=out_str)
                    )

            elif mark == "error":
                error_occurred = True
                error_message = self.delete_color_control_char(out_str)
                error_message = self._truncate_text(error_message)
                logger.error("执行错误: %s", error_message)
                text_to_gpt.append(error_message)
                #  添加error到notebook
                self.notebook_serializer.add_code_cell_error_to_notebook(out_str)
                content_to_display.append(StdErrModel(msg=out_str))

        logger.info("text_to_gpt: %s", text_to_gpt)
        combined_text = "\n".join(text_to_gpt)
        combined_text = self._truncate_combined_output(combined_text)

        await self._push_to_websocket(content_to_display)

        return (
            combined_text,
            error_occurred,
            error_message,
        )

    def execute_code_(self, code: str) -> list[tuple[str, str]]:
        """执行代码并收集内核输出，带总超时保护。"""
        self.kc.execute(code)
        logger.info("执行代码: %s", code)
        # 收集内核输出消息
        msg_list: list[dict] = []
        start_time = time.time()
        while True:
            # 总超时保护：防止内核挂起导致循环永不终止
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                logger.error(
                    "代码执行超时（%d秒），强制中断内核", self.timeout
                )
                self.km.interrupt_kernel()
                raise TimeoutError(
                    f"代码执行超时，已超过 {self.timeout} 秒"
                )
            try:
                iopub_msg = self.kc.get_iopub_msg(timeout=1)
                msg_list.append(iopub_msg)
                if (
                    iopub_msg["msg_type"] == "status"
                    and iopub_msg["content"].get("execution_state") == "idle"
                ):
                    break
            except queue.Empty:
                # get_iopub_msg 超时（1秒内无消息），检查中断信号后继续等待
                if self.interrupt_signal:
                    self.km.interrupt_kernel()
                    self.interrupt_signal = False
                continue
            except Exception as e:
                logger.warning(
                    "获取内核消息时发生异常: %s", e, exc_info=True
                )
                if self.interrupt_signal:
                    self.km.interrupt_kernel()
                    self.interrupt_signal = False
                continue

        all_output: list[tuple[str, str]] = []
        for iopub_msg in msg_list:
            if iopub_msg["msg_type"] == "stream":
                if iopub_msg["content"].get("name") == "stdout":
                    output = iopub_msg["content"]["text"]
                    all_output.append(("stdout", output))
            elif iopub_msg["msg_type"] == "execute_result":
                if "data" in iopub_msg["content"]:
                    if "text/plain" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/plain"]
                        all_output.append(("execute_result_text", output))
                    if "text/html" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/html"]
                        all_output.append(("execute_result_html", output))
                    if "image/png" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/png"]
                        all_output.append(("execute_result_png", output))
                    if "image/jpeg" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/jpeg"]
                        all_output.append(("execute_result_jpeg", output))
            elif iopub_msg["msg_type"] == "display_data":
                if "data" in iopub_msg["content"]:
                    if "text/plain" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/plain"]
                        all_output.append(("display_text", output))
                    if "text/html" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["text/html"]
                        all_output.append(("display_html", output))
                    if "image/png" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/png"]
                        all_output.append(("display_png", output))
                    if "image/jpeg" in iopub_msg["content"]["data"]:
                        output = iopub_msg["content"]["data"]["image/jpeg"]
                        all_output.append(("display_jpeg", output))
            elif iopub_msg["msg_type"] == "error":
                # TODO: 正确返回格式
                if "traceback" in iopub_msg["content"]:
                    output = "\n".join(iopub_msg["content"]["traceback"])
                    cleaned_output = self.delete_color_control_char(output)
                    all_output.append(("error", cleaned_output))
        return all_output

    async def get_created_images(self, section: str) -> list[str]:
        """获取新创建的图片列表"""
        current_images = set()
        files = os.listdir(self.work_dir)
        for file in files:
            if file.endswith((".png", ".jpg", ".jpeg")):
                current_images.add(file)

        # 计算新增的图片
        new_images = current_images - self.last_created_images

        # 更新last_created_images为当前的图片集合
        self.last_created_images = current_images

        logger.info("新创建的图片列表: %s", new_images)
        return list(new_images)  # 最后转换为list返回

    async def cleanup(self):
        """清理内核资源，确保不因清理失败掩盖原始异常。"""
        if self.kc is not None:
            try:
                self.kc.stop_channels()
            except Exception as e:
                logger.warning("关闭 KernelClient 通道失败: %s", e)
        if self.km is not None:
            try:
                self.km.shutdown_kernel(now=True)
            except Exception as e:
                logger.warning("关闭 KernelManager 失败: %s", e)
        logger.info("内核资源清理完成")

    def send_interrupt_signal(self):
        self.interrupt_signal = True

    def restart_jupyter_kernel(self):
        """重启 Jupyter 内核并重新初始化工作目录和 math_tools 路径。"""
        self.kc.shutdown()
        self.km, self.kc = jupyter_client.manager.start_new_kernel(
            kernel_name="python3"
        )
        self.interrupt_signal = False
        # 重启后需要重新执行初始化代码（工作目录 + math_tools 路径注入）
        self._pre_execute_code()

    def _create_work_dir(self):
        """Ensure the working directory exists after a restart."""
        os.makedirs(self.work_dir, exist_ok=True)
