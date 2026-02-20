"""
LaTeX 论文生成器

修复清单（基于审计报告）：
1. _escape_latex() 保护数学环境，不再破坏公式
2. _build_references() 使用 thebibliography 替代 enumerate
3. 添加 CUMCM 承诺书/编号页模板
4. 修复 _build_title_page / _build_abstract 中的 f-string 四重转义 bug
5. 修复 _convert_markdown_to_latex 列表关闭逻辑 bug
6. 增加 Markdown 表格、图片、代码块转换支持
7. CUMCM 页眉填充队伍编号
"""

import re
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class PaperTemplate(Enum):
    MCM_ICM = "mcm_icm"
    CUMCM = "cumcm"
    GENERAL = "general"


class PaperLanguage(Enum):
    CHINESE = "zh"
    ENGLISH = "en"


@dataclass
class PaperSection:
    title: str
    content: str
    level: int = 1
    label: Optional[str] = None


@dataclass
class Figure:
    path: str
    caption: str
    label: str
    width: str = "0.8\\textwidth"


@dataclass
class Table:
    caption: str
    label: str
    content: str
    headers: List[str] = field(default_factory=list)
    data: List[List[str]] = field(default_factory=list)


@dataclass
class Citation:
    key: str
    authors: str
    title: str
    year: str
    source: str
    url: Optional[str] = None


@dataclass
class PaperContent:
    title: str
    abstract: str
    keywords: List[str]
    sections: List[PaperSection]
    figures: List[Figure] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    appendix: Optional[str] = None


# mcmthesis 模板目录路径
MCMTHESIS_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "config" / "latex-template" / "mcmthesis"


MCMTHESIS_PREAMBLE = r"""
\documentclass{mcmthesis}
\mcmsetup{CTeX = false,
    tcn = {tcn}, problem = {problem},
    sheet = true, titleinsheet = true, keywordsinsheet = true,
    titlepage = false, abstract = true}
\usepackage{palatino}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{multirow}
\usepackage{float}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{listings}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{subfig}
\usepackage{natbib}
\usepackage{longtable}

\lstset{
    basicstyle=\ttfamily\small,
    breaklines=true,
    frame=single,
    numbers=left,
    numberstyle=\tiny,
    keywordstyle=\color{blue},
    commentstyle=\color{green!60!black},
    stringstyle=\color{red}
}

\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    citecolor=blue,
    urlcolor=blue
}
"""

CUMCM_PREAMBLE = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[UTF8]{ctex}
\usepackage{geometry}
\geometry{left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{multirow}
\usepackage{float}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{listings}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{indentfirst}
\usepackage{longtable}

\setlength{\parindent}{2em}

\pagestyle{fancy}
\fancyhf{}
\rhead{%TEAM_CONTROL_NUMBER%}
\lhead{第 \thepage 页 共 \pageref{LastPage} 页}
\renewcommand{\headrulewidth}{0.4pt}

\lstset{
    basicstyle=\ttfamily\small,
    breaklines=true,
    frame=single,
    numbers=left,
    numberstyle=\tiny,
    keywordstyle=\color{blue},
    commentstyle=\color{green!60!black},
    stringstyle=\color{red}
}

\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    citecolor=blue,
    urlcolor=blue
}

\renewcommand{\algorithmicrequire}{\textbf{输入：}}
\renewcommand{\algorithmicensure}{\textbf{输出：}}
"""

# CUMCM 承诺书模板
CUMCM_COMMITMENT_PAGE = r"""
\thispagestyle{empty}
\begin{center}
\vspace*{2cm}
{\heiti\zihao{2} 全国大学生数学建模竞赛}

\vspace{1cm}
{\heiti\zihao{2} 承\quad 诺\quad 书}

\vspace{2cm}
\end{center}

{\zihao{4}

我们仔细阅读了《全国大学生数学建模竞赛章程》和《全国大学生数学建模竞赛参赛规则》。

我们完全明白，在竞赛开始后参赛队员不能以任何方式（包括电话、电子邮件、网上咨询等）与队外的任何人（包括指导教师）研究、讨论与赛题有关的问题。

我们知道，抄袭别人的成果是违反竞赛规则的，如果引用别人的成果或其他公开的资料（包括网上查到的资料），必须按照规定的参考文献的表述方式在正文引用处和参考文献中明确列出。

我们郑重承诺，严格遵守竞赛规则，以保证竞赛的公正、公平性。如有违反竞赛规则的行为，我们将受到严肃处理。

}

\vspace{2cm}

\begin{center}
\zihao{4}
\begin{tabular}{p{4cm}p{8cm}}
参赛队号：& %TEAM_CONTROL_NUMBER% \\[1cm]
所属学校：& \underline{\hspace{7cm}} \\[1cm]
参赛队员1：& \underline{\hspace{7cm}} \\[1cm]
参赛队员2：& \underline{\hspace{7cm}} \\[1cm]
参赛队员3：& \underline{\hspace{7cm}} \\[1cm]
指导教师：& \underline{\hspace{7cm}} \\[1cm]
日\quad\quad 期：& \underline{\hspace{7cm}} \\
\end{tabular}
\end{center}

\newpage
"""

# CUMCM 编号页模板
CUMCM_NUMBER_PAGE = r"""
\thispagestyle{empty}
\begin{center}
\vspace*{3cm}
{\heiti\zihao{2} 全国大学生数学建模竞赛}

\vspace{2cm}
{\heiti\zihao{2} 编\quad 号\quad 专\quad 用\quad 页}

\vspace{3cm}
\zihao{4}
\begin{tabular}{|p{4cm}|p{8cm}|}
\hline
赛区评阅编号（由赛区组委会评阅前进行编号）：& \\[1cm]
\hline
全国统一编号（由赛区组委会送交全国前编号）：& \\[1cm]
\hline
全国评阅编号（由全国组委会评阅前进行编号）：& \\[1cm]
\hline
\end{tabular}
\end{center}

\newpage
"""


# ============================================================
# 数学环境保护工具函数
# ============================================================

# 匹配需要保护的数学环境（按优先级排列）
_MATH_PATTERNS = [
    # 显示数学: $$...$$ (贪心最短匹配)
    re.compile(r'\$\$(.+?)\$\$', re.DOTALL),
    # 行内数学: $...$（不跨行）
    re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)'),
    # \[...\] 显示数学
    re.compile(r'\\\[(.+?)\\\]', re.DOTALL),
    # \(...\) 行内数学
    re.compile(r'\\\((.+?)\\\)'),
    # LaTeX 数学环境: equation, align, gather, multline, cases, matrix 等
    re.compile(
        r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|'
        r'cases|split|aligned|gathered|bmatrix|pmatrix|vmatrix|'
        r'Bmatrix|Vmatrix|smallmatrix|array)\}'
        r'(.+?)'
        r'\\end\{\1\}',
        re.DOTALL,
    ),
]

# 独立 LaTeX 命令（\frac{}{}, \sqrt{}, \sum, \int 等），仅在非数学环境中出现时保护
_LATEX_CMD_PATTERN = re.compile(
    r'\\(?:frac|sqrt|sum|prod|int|lim|max|min|sup|inf|log|ln|exp|sin|cos|tan'
    r'|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|sigma|omega|phi|psi'
    r'|partial|nabla|infty|cdot|cdots|ldots|times|div|pm|mp|leq|geq|neq'
    r'|approx|equiv|subset|supset|cap|cup|in|notin|forall|exists'
    r'|mathbb|mathcal|mathbf|mathrm|hat|bar|vec|dot|tilde|overline'
    r'|left|right|big|Big|bigg|Bigg'
    r')(?:\{[^}]*\}|\b|[^a-zA-Z])'
)


def _protect_math_environments(text: str):
    """提取并保护数学环境，返回 (处理后文本, 占位符映射)。

    策略：将所有数学区域替换为唯一占位符，对剩余纯文本执行转义后再还原。
    """
    placeholders = {}
    counter = 0

    def _replace(match):
        nonlocal counter
        key = f"\x00MATH{counter}\x00"
        placeholders[key] = match.group(0)
        counter += 1
        return key

    # 按优先级依次替换
    for pattern in _MATH_PATTERNS:
        text = pattern.sub(_replace, text)

    # 保护独立 LaTeX 命令
    text = _LATEX_CMD_PATTERN.sub(_replace, text)

    return text, placeholders


def _restore_math_environments(text: str, placeholders: dict) -> str:
    """还原占位符为原始数学内容。"""
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text


class LaTeXGenerator:

    def __init__(
        self,
        template: PaperTemplate = PaperTemplate.CUMCM,
        language: PaperLanguage = PaperLanguage.CHINESE,
        team_control_number: str = "XXXXX",
        problem_choice: str = "A",
    ):
        self.template = template
        self.language = language
        self.team_control_number = team_control_number
        self.problem_choice = problem_choice

    def _uses_mcmthesis(self) -> bool:
        """判断是否使用 mcmthesis 文档类"""
        return self.template == PaperTemplate.MCM_ICM

    def generate(self, content: PaperContent) -> str:
        preamble = self._get_preamble()
        document = self._build_document(content)
        return preamble + document

    def _get_preamble(self) -> str:
        if self.template == PaperTemplate.MCM_ICM:
            return MCMTHESIS_PREAMBLE.replace(
                "{tcn}", self.team_control_number
            ).replace(
                "{problem}", self.problem_choice
            )
        elif self.template == PaperTemplate.CUMCM:
            # 填充队伍编号到页眉
            return CUMCM_PREAMBLE.replace(
                "%TEAM_CONTROL_NUMBER%", self.team_control_number
            )
        else:
            return CUMCM_PREAMBLE.replace(
                "%TEAM_CONTROL_NUMBER%", self.team_control_number
            )

    def _build_document(self, content: PaperContent) -> str:
        if self._uses_mcmthesis():
            return self._build_mcmthesis_document(content)
        return self._build_standard_document(content)

    def _build_mcmthesis_document(self, content: PaperContent) -> str:
        """使用 mcmthesis 文档类构建文档（MCM/ICM 美赛）"""
        parts = []

        parts.append(r"\title{" + self._escape_latex(content.title) + "}")
        parts.append("")
        parts.append(r"\begin{document}")
        parts.append("")

        # mcmthesis 的 Summary Sheet（abstract + keywords 环境）
        parts.append(r"\begin{abstract}")
        parts.append(self._escape_latex(content.abstract))
        parts.append(r"\end{abstract}")
        parts.append("")

        keywords_text = ", ".join(content.keywords)
        parts.append(r"\begin{keywords}")
        parts.append(self._escape_latex(keywords_text))
        parts.append(r"\end{keywords}")
        parts.append("")

        parts.append(r"\maketitle")
        parts.append("")

        parts.append(r"\tableofcontents")
        parts.append(r"\newpage")
        parts.append("")

        for section in content.sections:
            parts.append(self._build_section(section))
            parts.append("")

        if content.citations:
            parts.append(self._build_references(content.citations))
            parts.append("")

        if content.appendix:
            parts.append(self._build_appendix(content.appendix))
            parts.append("")

        parts.append(r"\end{document}")

        return "\n".join(parts)

    def _build_standard_document(self, content: PaperContent) -> str:
        """使用标准 article 文档类构建文档（CUMCM 国赛 / 通用）"""
        parts = []

        parts.append(r"\begin{document}")
        parts.append("")

        # 承诺书页
        commitment = CUMCM_COMMITMENT_PAGE.replace(
            "%TEAM_CONTROL_NUMBER%", self.team_control_number
        )
        parts.append(commitment)

        # 编号页
        parts.append(CUMCM_NUMBER_PAGE)

        # 标题页
        parts.append(self._build_title_page(content))
        parts.append("")

        # 摘要
        parts.append(self._build_abstract(content))
        parts.append("")

        parts.append(r"\newpage")
        parts.append(r"\tableofcontents")
        parts.append(r"\newpage")
        parts.append("")

        for section in content.sections:
            parts.append(self._build_section(section))
            parts.append("")

        if content.citations:
            parts.append(self._build_references(content.citations))
            parts.append("")

        if content.appendix:
            parts.append(self._build_appendix(content.appendix))
            parts.append("")

        parts.append(r"\end{document}")

        return "\n".join(parts)

    def _build_title_page(self, content: PaperContent) -> str:
        # 修复：不再使用 f-string 中的 \\\\，改用字符串拼接
        title_escaped = self._escape_latex(content.title)
        lines = [
            r"\begin{center}",
            r"\vspace*{1cm}",
            r"{\LARGE\textbf{" + title_escaped + r"}}",
            r"\end{center}",
        ]
        return "\n".join(lines)

    def _build_abstract(self, content: PaperContent) -> str:
        if self.language == PaperLanguage.CHINESE:
            sep = "、"
            section_title = "摘要"
            kw_label = r"\textbf{关键词：}"
        else:
            sep = ", "
            section_title = "Summary"
            kw_label = r"\textbf{Keywords:} "

        keywords_text = sep.join(content.keywords)
        abstract_escaped = self._escape_latex(content.abstract)
        keywords_escaped = self._escape_latex(keywords_text)

        lines = [
            r"\section*{" + section_title + "}",
            r"\addcontentsline{toc}{section}{" + section_title + "}",
            "",
            abstract_escaped,
            "",
            kw_label + keywords_escaped,
            "",
            r"\newpage",
        ]
        return "\n".join(lines)

    def _build_section(self, section: PaperSection) -> str:
        level_commands = {
            1: r"\section",
            2: r"\subsection",
            3: r"\subsubsection",
        }

        cmd = level_commands.get(section.level, r"\section")
        label = f"\\label{{{section.label}}}" if section.label else ""
        title_escaped = self._escape_latex(section.title)

        lines = [
            f"{cmd}{{{title_escaped}}}{label}",
            "",
            self._process_content(section.content),
        ]
        return "\n".join(lines)

    def _process_content(self, content: str) -> str:
        """处理正文内容：先保护数学环境，再转义普通文本，最后转换 Markdown 语法。"""
        # 1. 保护数学环境
        protected, placeholders = _protect_math_environments(content)

        # 2. 对非数学部分执行 LaTeX 转义
        escaped = self._escape_latex_text_only(protected)

        # 3. 转换 Markdown 语法
        converted = self._convert_markdown_to_latex(escaped)

        # 4. 还原数学环境
        result = _restore_math_environments(converted, placeholders)

        return result

    def _convert_markdown_to_latex(self, text: str) -> str:
        """将 Markdown 语法转换为 LaTeX 命令。

        支持：粗体、斜体、行内代码、无序列表、有序列表、
              代码块、Markdown 表格、图片引用。
        """
        # 代码块：```...``` → lstlisting 环境
        text = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: (
                "\\begin{lstlisting}"
                + (f"[language={m.group(1)}]" if m.group(1) else "")
                + "\n"
                + m.group(2)
                + "\\end{lstlisting}"
            ),
            text,
            flags=re.DOTALL,
        )

        # 图片：![caption](path) → \begin{figure}...\end{figure}
        def _replace_image(m):
            caption = m.group(1) or ""
            path = m.group(2)
            # 生成简单 label
            label = re.sub(r'[^a-zA-Z0-9]', '_', path)[:30]
            lines = [
                r"\begin{figure}[H]",
                r"    \centering",
                f"    \\includegraphics[width=0.8\\textwidth]{{{path}}}",
                f"    \\caption{{{self._escape_latex_text_only(caption)}}}",
                f"    \\label{{fig:{label}}}",
                r"\end{figure}",
            ]
            return "\n".join(lines)

        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _replace_image, text)

        # 粗体、斜体、行内代码（注意顺序：先粗体再斜体）
        text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
        text = re.sub(r'\*(.+?)\*', r'\\textit{\1}', text)
        text = re.sub(r'`(.+?)`', r'\\texttt{\1}', text)

        # 逐行处理：列表和表格
        lines = text.split('\n')
        result = []
        in_list_type = None  # 'itemize' 或 'enumerate'
        in_table = False
        table_lines = []

        for line in lines:
            stripped = line.strip()

            # Markdown 表格检测
            if '|' in stripped and stripped.startswith('|') and stripped.endswith('|'):
                if not in_table:
                    # 关闭之前的列表
                    if in_list_type:
                        result.append(f"\\end{{{in_list_type}}}")
                        in_list_type = None
                    in_table = True
                    table_lines = []
                table_lines.append(stripped)
                continue
            elif in_table:
                # 表格结束，转换并输出
                result.append(self._convert_markdown_table(table_lines))
                in_table = False
                table_lines = []

            # 无序列表
            if stripped.startswith('- ') or stripped.startswith('* '):
                if in_list_type != 'itemize':
                    if in_list_type:
                        result.append(f"\\end{{{in_list_type}}}")
                    result.append(r'\begin{itemize}')
                    in_list_type = 'itemize'
                item_content = stripped[2:]
                result.append(r'\item ' + item_content)
            # 有序列表
            elif re.match(r'^\d+\.\s', stripped):
                if in_list_type != 'enumerate':
                    if in_list_type:
                        result.append(f"\\end{{{in_list_type}}}")
                    result.append(r'\begin{enumerate}')
                    in_list_type = 'enumerate'
                item_content = re.sub(r'^\d+\.\s', '', stripped)
                result.append(r'\item ' + item_content)
            else:
                # 非列表行，关闭之前的列表
                if in_list_type:
                    result.append(f"\\end{{{in_list_type}}}")
                    in_list_type = None
                result.append(line)

        # 关闭未结束的列表
        if in_list_type:
            result.append(f"\\end{{{in_list_type}}}")

        # 关闭未结束的表格
        if in_table and table_lines:
            result.append(self._convert_markdown_table(table_lines))

        return '\n'.join(result)

    def _convert_markdown_table(self, table_lines: List[str]) -> str:
        """将 Markdown 表格转换为 LaTeX tabular 环境。"""
        if len(table_lines) < 2:
            return "\n".join(table_lines)

        # 解析表格行
        rows = []
        for i, line in enumerate(table_lines):
            cells = [c.strip() for c in line.strip('|').split('|')]
            # 检测分隔行（如 |---|---|---| ）
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            rows.append(cells)

        if not rows:
            return ""

        col_count = max(len(row) for row in rows)
        col_spec = "c" * col_count

        latex_rows = []
        for i, row in enumerate(rows):
            # 补齐列数
            while len(row) < col_count:
                row.append("")
            escaped = [self._escape_latex_text_only(c) for c in row]
            latex_rows.append(" & ".join(escaped) + r" \\")
            # 在表头后添加横线
            if i == 0:
                latex_rows.append(r"\hline")

        lines = [
            r"\begin{table}[H]",
            r"    \centering",
            f"    \\begin{{tabular}}{{{col_spec}}}",
            r"    \toprule",
        ]
        for row in latex_rows:
            lines.append(f"    {row}")
        lines.extend([
            r"    \bottomrule",
            "    \\end{tabular}",
            r"\end{table}",
        ])

        return "\n".join(lines)

    def _build_references(self, citations: List[Citation]) -> str:
        """使用 thebibliography 环境生成参考文献（支持 \\cite{} 引用）。"""
        if self.language == PaperLanguage.CHINESE:
            header = (
                r"\section*{参考文献}" + "\n"
                + r"\addcontentsline{toc}{section}{参考文献}"
            )
        else:
            header = (
                r"\section*{References}" + "\n"
                + r"\addcontentsline{toc}{section}{References}"
            )

        # 计算最大编号宽度
        max_label = str(len(citations))
        refs = [header, "", f"\\begin{{thebibliography}}{{{max_label}}}"]

        for citation in citations:
            ref_text = (
                f"{citation.authors}. {citation.title}. "
                f"{citation.source}, {citation.year}."
            )
            if citation.url:
                ref_text += f" \\url{{{citation.url}}}"
            # 对参考文献文本执行安全转义（保护 URL 中的特殊字符）
            escaped_text = self._escape_latex_text_only(ref_text)
            refs.append(f"\\bibitem{{{citation.key}}} {escaped_text}")

        refs.append(r"\end{thebibliography}")

        return "\n".join(refs)

    def _build_appendix(self, appendix_content: str) -> str:
        if self.language == PaperLanguage.CHINESE:
            header = r"\appendix" + "\n" + r"\section{附录}"
        else:
            header = r"\appendix" + "\n" + r"\section{Appendix}"

        lines = [
            header,
            "",
            self._process_content(appendix_content),
        ]
        return "\n".join(lines)

    def _escape_latex(self, text: str) -> str:
        """对文本执行 LaTeX 转义，自动保护数学环境。

        这是公共入口方法，用于标题、摘要、关键词等不需要 Markdown 转换的场景。
        """
        if not text:
            return ""

        # 保护数学环境
        protected, placeholders = _protect_math_environments(text)

        # 对非数学部分执行转义
        escaped = self._escape_latex_text_only(protected)

        # 还原数学环境
        return _restore_math_environments(escaped, placeholders)

    @staticmethod
    def _escape_latex_text_only(text: str) -> str:
        """仅对纯文本执行 LaTeX 特殊字符转义（不处理数学环境）。

        此方法假设输入中的数学环境已被占位符替代，因此可以安全地转义所有特殊字符。
        """
        if not text:
            return ""

        # 注意顺序：反斜杠不转义（LaTeX 命令需要保留）
        # $, {, }, ^, _ 不转义（这些由数学环境保护机制处理）
        # 仅转义在普通文本中需要转义的字符
        special_chars = {
            '&': r'\&',
            '%': r'\%',
            '#': r'\#',
            '~': r'\textasciitilde{}',
        }

        for char, replacement in special_chars.items():
            text = text.replace(char, replacement)

        return text

    def generate_figure(self, figure: Figure) -> str:
        """生成独立的图片 LaTeX 代码。"""
        caption_escaped = self._escape_latex(figure.caption)
        lines = [
            r"\begin{figure}[H]",
            r"    \centering",
            f"    \\includegraphics[width={figure.width}]{{{figure.path}}}",
            f"    \\caption{{{caption_escaped}}}",
            f"    \\label{{{figure.label}}}",
            r"\end{figure}",
        ]
        return "\n".join(lines)

    def generate_table(self, table: Table) -> str:
        """生成独立的表格 LaTeX 代码。"""
        if table.content:
            table_body = table.content
        else:
            col_count = len(table.headers)
            col_spec = "|" + "c|" * col_count

            header_row = " & ".join(table.headers) + r" \\"
            data_rows = []
            for row in table.data:
                data_rows.append(" & ".join(row) + r" \\")

            table_body = "\n".join([
                f"\\begin{{tabular}}{{{col_spec}}}",
                r"\hline",
                header_row,
                r"\hline",
                "\n".join(data_rows),
                r"\hline",
                r"\end{tabular}",
            ])

        caption_escaped = self._escape_latex(table.caption)
        lines = [
            r"\begin{table}[H]",
            r"    \centering",
            f"    \\caption{{{caption_escaped}}}",
            f"    \\label{{{table.label}}}",
            f"    {table_body}",
            r"\end{table}",
        ]
        return "\n".join(lines)

    def save_to_file(self, content: PaperContent, output_path: str) -> str:
        """保存 LaTeX 文件。如果使用 mcmthesis 模板，同时复制 cls 和资源文件。"""
        latex_content = self.generate(content)

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        # 使用 mcmthesis 模板时，复制 cls 和 logo 到输出目录
        if self._uses_mcmthesis():
            self._copy_mcmthesis_resources(path.parent)

        return str(path)

    def _copy_mcmthesis_resources(self, output_dir: Path) -> None:
        """将 mcmthesis.cls 和 figures/ 复制到输出目录，确保 .tex 可独立编译。"""
        cls_src = MCMTHESIS_TEMPLATE_DIR / "mcmthesis.cls"
        cls_dst = output_dir / "mcmthesis.cls"
        if cls_src.exists() and not cls_dst.exists():
            shutil.copy2(cls_src, cls_dst)

        figures_src = MCMTHESIS_TEMPLATE_DIR / "figures"
        figures_dst = output_dir / "figures"
        if figures_src.exists() and not figures_dst.exists():
            shutil.copytree(figures_src, figures_dst)


def markdown_to_paper_content(
    title: str,
    markdown_text: str,
    abstract: str,
    keywords: List[str],
    citations: Optional[List[Citation]] = None
) -> PaperContent:
    """将 Markdown 文本解析为 PaperContent 数据结构。

    支持 #/##/### 三级标题，#### 会被合并到上级章节内容中。
    """
    sections = []
    current_section = None
    current_content = []

    for line in markdown_text.split('\n'):
        if line.startswith('# '):
            if current_section:
                current_section.content = '\n'.join(current_content)
                sections.append(current_section)
            current_section = PaperSection(
                title=line[2:].strip(),
                content="",
                level=1
            )
            current_content = []
        elif line.startswith('## '):
            if current_section:
                current_section.content = '\n'.join(current_content)
                sections.append(current_section)
            current_section = PaperSection(
                title=line[3:].strip(),
                content="",
                level=2
            )
            current_content = []
        elif line.startswith('### '):
            if current_section:
                current_section.content = '\n'.join(current_content)
                sections.append(current_section)
            current_section = PaperSection(
                title=line[4:].strip(),
                content="",
                level=3
            )
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        current_section.content = '\n'.join(current_content)
        sections.append(current_section)

    return PaperContent(
        title=title,
        abstract=abstract,
        keywords=keywords,
        sections=sections,
        citations=citations or []
    )
