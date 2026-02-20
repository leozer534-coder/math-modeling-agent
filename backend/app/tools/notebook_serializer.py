import os
import tempfile

import ansi2html
import nbformat
from nbformat import v4 as nbf

from app.utils.log_util import logger


class NotebookSerializer:
    """Notebook 序列化器，支持惰性写入以减少磁盘 I/O。

    cell 添加时仅在内存中修改并标记为脏，实际磁盘写入由以下机制触发:
    - flush(): 脏标记为 True 时写入
    - save_notebook(): 强制立即写入（用于最终保存）
    - 安全网: 每 _flush_interval 次修改自动 flush
    - section 切换 (add_markdown_segmentation_to_notebook): 自动 flush
    """

    def __init__(
        self,
        work_dir: str | None = None,
        notebook_name: str = "notebook.ipynb",
        flush_interval: int = 5,
    ):
        self.nb = nbf.new_notebook()
        self.notebook_path: str | None = None
        self.initialized: bool = True
        self.segmentation_output_content: dict[str, str] = {}
        # {
        #     "eda": {
        #     }
        # }
        self.current_segmentation: str = ""

        # 惰性写入状态
        self._dirty: bool = False
        self._flush_interval: int = flush_interval
        self._pending_writes: int = 0
        self._total_flushes: int = 0

        self.init_notebook(work_dir, notebook_name)

    def init_notebook(
        self,
        work_dir: str | None = None,
        notebook_name: str = "notebook.ipynb",
    ) -> None:
        """初始化notebook路径。

        Args:
            work_dir: jupyter工作目录路径
            notebook_name: notebook文件名,默认为notebook.ipynb
        """
        if work_dir:
            # 确保使用jupyter工作目录
            base, ext = os.path.splitext(notebook_name)
            if ext.lower() != ".ipynb":
                notebook_name += ".ipynb"

            # 在jupyter工作目录下创建notebook文件
            self.notebook_path = os.path.join(work_dir, notebook_name)

    def ansi_to_html(self, ansi_text: str) -> str:
        """将 ANSI 转义序列转换为 HTML。"""
        converter = ansi2html.Ansi2HTMLConverter()
        html_text = converter.convert(ansi_text)
        return html_text

    # ------------------------------------------------------------------ #
    #                        惰性写入核心方法                               #
    # ------------------------------------------------------------------ #

    def _mark_dirty(self) -> None:
        """标记 notebook 为脏，并在达到安全网间隔时自动 flush。"""
        self._dirty = True
        self._pending_writes += 1
        if self._pending_writes >= self._flush_interval:
            logger.debug(
                "NotebookSerializer 安全网触发: 累积 %d 次修改，自动 flush",
                self._pending_writes,
            )
            self.flush()

    def flush(self) -> None:
        """仅在脏标记为 True 时执行实际磁盘写入。

        写入采用原子性策略（先写临时文件再 rename），
        避免写入中断导致 notebook 文件损坏。
        """
        if not self._dirty:
            return
        self._write_atomic()
        self._dirty = False
        self._pending_writes = 0
        self._total_flushes += 1
        logger.debug(
            "NotebookSerializer flush 完成，累计写入次数: %d",
            self._total_flushes,
        )

    def _write_atomic(self) -> None:
        """原子性写入：先写临时文件再 os.replace，避免写入中断导致文件损坏。"""
        if not self.notebook_path:
            return
        notebook_content = nbformat.writes(self.nb)
        dir_name = os.path.dirname(self.notebook_path)
        # 当 notebook_path 仅为文件名（无目录部分）时，dir_name 为空字符串
        if not dir_name:
            dir_name = "."
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".ipynb.tmp", dir=dir_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(notebook_content)
                os.replace(tmp_path, self.notebook_path)
            except BaseException:
                # 写入或 rename 失败时清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        except OSError:
            # 原子写入整体失败时，回退到直接写入
            logger.warning(
                "原子写入失败，回退到直接写入: %s", self.notebook_path
            )
            with open(self.notebook_path, "w", encoding="utf-8") as f:
                f.write(notebook_content)

    def write_to_notebook(self) -> None:
        """写入 notebook（惰性模式：标记为脏，由 flush/安全网触发实际写入）。

        保持向后兼容：外部调用此方法时仅标记脏状态，
        不会立即产生磁盘 I/O。
        """
        self._mark_dirty()

    def save_notebook(self) -> None:
        """强制立即保存 notebook 到磁盘，用于最终保存。

        无论脏标记状态如何，都执行一次完整的原子性写入。
        """
        self._write_atomic()
        self._dirty = False
        self._pending_writes = 0
        self._total_flushes += 1
        logger.debug(
            "NotebookSerializer save_notebook 完成，累计写入次数: %d",
            self._total_flushes,
        )

    # ------------------------------------------------------------------ #
    #                        Cell 操作方法                                 #
    # ------------------------------------------------------------------ #

    def add_code_cell_to_notebook(self, code: str) -> None:
        """添加代码单元格到 notebook。"""
        code_cell = nbf.new_code_cell(source=code)
        self.nb["cells"].append(code_cell)
        self.write_to_notebook()

    def add_code_cell_output_to_notebook(self, output: str) -> None:
        """添加代码单元格输出。

        Args:
            output: 代码输出内容
        """
        if not self.nb["cells"]:
            logger.warning("Notebook 尚无 cell，无法添加输出")
            return
        html_content = self.ansi_to_html(output)
        if self.current_segmentation:
            # 确保键存在
            if self.current_segmentation not in self.segmentation_output_content:
                self.segmentation_output_content[self.current_segmentation] = ""
            self.segmentation_output_content[self.current_segmentation] += html_content

        cell_output = nbf.new_output(
            output_type="display_data", data={"text/html": html_content}
        )
        self.nb["cells"][-1]["outputs"].append(cell_output)
        self.write_to_notebook()

    def add_code_cell_error_to_notebook(self, error: str) -> None:
        """添加代码执行错误输出到最后一个 cell。"""
        if not self.nb["cells"]:
            logger.warning("Notebook 尚无 cell，无法添加错误输出")
            return
        nbf_error_output = nbf.new_output(
            output_type="error",
            ename="Error",
            evalue="Error message",
            traceback=[error],
        )
        self.nb["cells"][-1]["outputs"].append(nbf_error_output)
        self.write_to_notebook()

    def add_image_to_notebook(self, image: str, mime_type: str) -> None:
        """添加图片输出到最后一个 cell。"""
        if not self.nb["cells"]:
            logger.warning("Notebook 尚无 cell，无法添加图片")
            return
        image_output = nbf.new_output(
            output_type="display_data", data={mime_type: image}
        )
        self.nb["cells"][-1]["outputs"].append(image_output)
        self.write_to_notebook()

    def add_markdown_to_notebook(
        self, content: str, title: str | None = None
    ) -> None:
        """添加 Markdown 单元格到 notebook。"""
        if title:
            content = "##### " + title + ":\n" + content
        markdown_cell = nbf.new_markdown_cell(content)
        self.nb["cells"].append(markdown_cell)
        self.write_to_notebook()

    def add_markdown_segmentation_to_notebook(
        self, content: str, segmentation: str
    ) -> None:
        """添加markdown分段并初始化对应的output内容存储。

        切换 section 时自动 flush 之前的脏数据，确保前一段内容已持久化。

        Args:
            content: markdown内容
            segmentation: 分段名称
        """
        # section 切换时 flush 之前的脏数据
        self.flush()
        self.current_segmentation = segmentation
        # 初始化该分段的output内容
        self.segmentation_output_content[segmentation] = ""
        self.add_markdown_to_notebook(content, segmentation)

    def get_notebook_output_content(self, segmentation: str) -> str:
        """获取指定分段的输出内容。"""
        return self.segmentation_output_content.get(segmentation, "")
