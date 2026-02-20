"""
LaTeX Renderer - LaTeX 模板集成
================================

功能：
1. Markdown 转 LaTeX
2. 数学公式规范化
3. 图表引用管理
4. 符号表自动生成
5. 参考文献格式化

关键特性：
- 支持数学建模竞赛格式
- 自动处理图表交叉引用
- 内置常用模板
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from app.utils.log_util import logger


class TemplateType(Enum):
    """模板类型"""

    CUMCM = "cumcm"  # 全国大学生数学建模竞赛
    MCM_ICM = "mcm_icm"  # 美国数学建模竞赛
    ACADEMIC = "academic"  # 学术论文
    CUSTOM = "custom"  # 自定义


@dataclass
class FigureReference:
    """图片引用"""

    id: str
    label: str
    caption: str
    path: str
    position: str = "htbp"


@dataclass
class TableReference:
    """表格引用"""

    id: str
    label: str
    caption: str
    content: str


@dataclass
class SymbolEntry:
    """符号条目"""

    symbol: str  # LaTeX 符号
    description: str  # 描述
    unit: str = ""  # 单位


@dataclass
class LaTeXDocument:
    """LaTeX 文档"""

    title: str
    abstract: str
    keywords: List[str]
    sections: List[Dict[str, str]]  # {title, content}
    figures: List[FigureReference] = field(default_factory=list)
    tables: List[TableReference] = field(default_factory=list)
    symbols: List[SymbolEntry] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    appendices: List[Dict[str, str]] = field(default_factory=list)


class LaTeXRenderer:
    """LaTeX 渲染器"""

    # CUMCM 模板
    CUMCM_TEMPLATE = r"""\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{graphicx}
\usepackage{subfigure}
\usepackage{float}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{appendix}

\geometry{left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm}

\title{%(title)s}
\date{}

\begin{document}

\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\textbf{关键词：} %(keywords)s

%(symbols_table)s

%(content)s

%(references)s

%(appendices)s

\end{document}
"""

    # Markdown 转 LaTeX 规则
    MD_TO_LATEX_RULES = [
        # 标题
        (r"^# (.+)$", r"\\section{\\1}"),
        (r"^## (.+)$", r"\\subsection{\\1}"),
        (r"^### (.+)$", r"\\subsubsection{\\1}"),
        # 粗体和斜体
        (r"\*\*(.+?)\*\*", r"\\textbf{\\1}"),
        (r"\*(.+?)\*", r"\\textit{\\1}"),
        # 代码块
        (r"`([^`]+)`", r"\\texttt{\\1}"),
        # 列表
        (r"^- (.+)$", r"\\item \\1"),
        (r"^\d+\. (.+)$", r"\\item \\1"),
        # 图片
        (
            r"!\[(.+?)\]\((.+?)\)",
            r"\\begin{figure}[H]\n\\centering\n\\includegraphics[width=0.8\\textwidth]{\\2}\n\\caption{\\1}\n\\end{figure}",
        ),
    ]

    def __init__(self, template_type: TemplateType = TemplateType.CUMCM):
        self.template_type = template_type

    def markdown_to_latex(self, markdown: str) -> str:
        """
        将 Markdown 转换为 LaTeX

        Args:
            markdown: Markdown 文本

        Returns:
            LaTeX 文本
        """
        latex = markdown

        # 应用转换规则
        for pattern, replacement in self.MD_TO_LATEX_RULES:
            latex = re.sub(pattern, replacement, latex, flags=re.MULTILINE)

        # 处理数学公式（保持不变）
        # 行内公式已经是 $...$ 格式
        # 行间公式需要转换
        latex = re.sub(
            r"\$\$(.+?)\$\$",
            r"\\begin{equation}\n\\1\n\\end{equation}",
            latex,
            flags=re.DOTALL,
        )

        # 处理列表环境
        latex = self._process_lists(latex)

        # 处理特殊字符
        latex = self._escape_special_chars(latex)

        return latex

    def _process_lists(self, latex: str) -> str:
        """处理列表环境"""
        lines = latex.split("\n")
        result = []
        in_itemize = False
        in_enumerate = False

        for line in lines:
            if line.strip().startswith("\\item"):
                if not in_itemize and not in_enumerate:
                    # 判断是有序还是无序列表
                    if re.match(r"^\d+\.", line.strip()):
                        result.append("\\begin{enumerate}")
                        in_enumerate = True
                    else:
                        result.append("\\begin{itemize}")
                        in_itemize = True
                result.append(line)
            else:
                if in_itemize:
                    result.append("\\end{itemize}")
                    in_itemize = False
                if in_enumerate:
                    result.append("\\end{enumerate}")
                    in_enumerate = False
                result.append(line)

        if in_itemize:
            result.append("\\end{itemize}")
        if in_enumerate:
            result.append("\\end{enumerate}")

        return "\n".join(result)

    def _escape_special_chars(self, text: str) -> str:
        """转义特殊字符（排除已有的 LaTeX 命令）"""
        # 不转义已经是 LaTeX 命令的部分
        # 只转义独立的特殊字符
        escapes = [
            ("%", "\\%"),
            ("&", "\\&"),
            ("#", "\\#"),
            ("_", "\\_"),
        ]

        for char, escaped in escapes:
            # 只转义不在命令中的字符
            text = re.sub(r"(?<!\\)" + re.escape(char), escaped, text)

        return text

    def format_equation(
        self,
        equation: str,
        label: Optional[str] = None,
        numbered: bool = True,
    ) -> str:
        """
        格式化数学公式

        Args:
            equation: 公式内容
            label: 标签（用于引用）
            numbered: 是否编号

        Returns:
            格式化的 LaTeX 公式
        """
        env = "equation" if numbered else "equation*"

        result = f"\\begin{{{env}}}\n"
        result += f"    {equation}\n"

        if label and numbered:
            result += f"    \\label{{eq:{label}}}\n"

        result += f"\\end{{{env}}}"

        return result

    def format_figure(
        self,
        path: str,
        caption: str,
        label: str,
        width: str = "0.8\\textwidth",
        position: str = "H",
    ) -> str:
        """
        格式化图片

        Args:
            path: 图片路径
            caption: 标题
            label: 标签
            width: 宽度
            position: 位置

        Returns:
            格式化的 LaTeX 图片
        """
        return f"""\\begin{{figure}}[{position}]
    \\centering
    \\includegraphics[width={width}]{{{path}}}
    \\caption{{{caption}}}
    \\label{{fig:{label}}}
\\end{{figure}}"""

    def format_table(
        self,
        data: List[List[str]],
        headers: List[str],
        caption: str,
        label: str,
        position: str = "H",
    ) -> str:
        """
        格式化表格

        Args:
            data: 表格数据
            headers: 表头
            caption: 标题
            label: 标签
            position: 位置

        Returns:
            格式化的 LaTeX 表格
        """
        num_cols = len(headers)
        col_spec = "|" + "c|" * num_cols

        result = f"""\\begin{{table}}[{position}]
    \\centering
    \\caption{{{caption}}}
    \\label{{tab:{label}}}
    \\begin{{tabular}}{{{col_spec}}}
    \\hline
    {" & ".join(headers)} \\\\
    \\hline
"""

        for row in data:
            result += f"    {' & '.join(str(cell) for cell in row)} \\\\\n"

        result += """    \\hline
    \\end{tabular}
\\end{table}"""

        return result

    def generate_symbols_table(self, symbols: List[SymbolEntry]) -> str:
        """
        生成符号说明表

        Args:
            symbols: 符号列表

        Returns:
            LaTeX 符号表
        """
        if not symbols:
            return ""

        result = """\\section*{符号说明}
\\begin{table}[H]
    \\centering
    \\begin{tabular}{|c|l|l|}
    \\hline
    \\textbf{符号} & \\textbf{说明} & \\textbf{单位} \\\\
    \\hline
"""

        for sym in symbols:
            unit = sym.unit if sym.unit else "-"
            result += f"    ${sym.symbol}$ & {sym.description} & {unit} \\\\\n"

        result += """    \\hline
    \\end{tabular}
\\end{table}
"""

        return result

    def format_references(self, references: List[str]) -> str:
        """
        格式化参考文献

        Args:
            references: 参考文献列表

        Returns:
            LaTeX 参考文献
        """
        if not references:
            return ""

        result = """\\begin{thebibliography}{99}
"""

        for i, ref in enumerate(references, 1):
            result += f"    \\bibitem{{{i}}} {ref}\n"

        result += "\\end{thebibliography}"

        return result

    def format_appendix(
        self,
        title: str,
        content: str,
        is_code: bool = False,
    ) -> str:
        """
        格式化附录

        Args:
            title: 附录标题
            content: 附录内容
            is_code: 是否为代码

        Returns:
            LaTeX 附录
        """
        result = f"\\section{{{title}}}\n"

        if is_code:
            result += """\\begin{lstlisting}[language=Python, basicstyle=\\small\\ttfamily, breaklines=true]
"""
            result += content
            result += "\n\\end{lstlisting}"
        else:
            result += content

        return result

    def render_document(self, doc: LaTeXDocument) -> str:
        """
        渲染完整文档

        Args:
            doc: LaTeX 文档对象

        Returns:
            完整的 LaTeX 文档
        """
        # 转换各部分
        content_parts = []
        for section in doc.sections:
            section_content = self.markdown_to_latex(section["content"])
            content_parts.append(f"\\section{{{section['title']}}}\n{section_content}")

        content = "\n\n".join(content_parts)

        # 生成符号表
        symbols_table = self.generate_symbols_table(doc.symbols)

        # 生成参考文献
        references = self.format_references(doc.references)

        # 生成附录
        appendices_parts = []
        if doc.appendices:
            appendices_parts.append("\\begin{appendices}")
            for app in doc.appendices:
                is_code = "code" in app.get("title", "").lower() or "代码" in app.get(
                    "title", ""
                )
                appendices_parts.append(
                    self.format_appendix(app["title"], app["content"], is_code)
                )
            appendices_parts.append("\\end{appendices}")
        appendices = "\n".join(appendices_parts)

        # 填充模板
        latex = self.CUMCM_TEMPLATE % {
            "title": doc.title,
            "abstract": doc.abstract,
            "keywords": "；".join(doc.keywords),
            "symbols_table": symbols_table,
            "content": content,
            "references": references,
            "appendices": appendices,
        }

        return latex

    def save_document(
        self,
        latex: str,
        output_path: str,
        encoding: str = "utf-8",
    ) -> str:
        """
        保存 LaTeX 文档

        Args:
            latex: LaTeX 内容
            output_path: 输出路径
            encoding: 编码

        Returns:
            保存的文件路径
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(latex, encoding=encoding)

        logger.info("LaTeX document saved to %s", path)

        return str(path)


# 便捷函数
def markdown_to_latex(markdown: str) -> str:
    """
    便捷函数：将 Markdown 转换为 LaTeX

    Args:
        markdown: Markdown 文本

    Returns:
        LaTeX 文本
    """
    renderer = LaTeXRenderer()
    return renderer.markdown_to_latex(markdown)


def create_cumcm_document(
    title: str,
    abstract: str,
    keywords: List[str],
    content_sections: List[Dict[str, str]],
    symbols: Optional[List[Dict[str, str]]] = None,
    references: Optional[List[str]] = None,
) -> str:
    """
    便捷函数：创建全国大学生数学建模竞赛格式的文档

    Args:
        title: 标题
        abstract: 摘要
        keywords: 关键词
        content_sections: 内容章节列表
        symbols: 符号列表
        references: 参考文献列表

    Returns:
        LaTeX 文档内容
    """
    renderer = LaTeXRenderer(TemplateType.CUMCM)

    symbol_entries = []
    if symbols:
        for s in symbols:
            symbol_entries.append(
                SymbolEntry(
                    symbol=s.get("symbol", ""),
                    description=s.get("description", ""),
                    unit=s.get("unit", ""),
                )
            )

    doc = LaTeXDocument(
        title=title,
        abstract=abstract,
        keywords=keywords,
        sections=content_sections,
        symbols=symbol_entries,
        references=references or [],
    )

    return renderer.render_document(doc)
