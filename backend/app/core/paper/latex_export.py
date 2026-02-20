"""
LaTeX 导出公共模块

提供从 Markdown 内容生成 LaTeX 文件的公共方法，供所有工作流复用。
"""

from app.core.paper.latex_generator import (
    LaTeXGenerator,
    PaperLanguage,
    PaperTemplate,
    markdown_to_paper_content,
)
from app.schemas.enums import CompTemplate
from app.utils.log_util import logger


def generate_latex_from_markdown(
    markdown_content: str,
    output_path: str,
    comp_template: CompTemplate,
    title: str = "",
    abstract: str = "",
    keywords: list[str] | None = None,
    team_control_number: str = "XXXXX",
    problem_choice: str = "A",
) -> str:
    """从 Markdown 内容生成 LaTeX 文件（公共方法）

    根据竞赛模板类型自动选择对应的 LaTeX 模板：
    - CHINA  → CUMCM 国赛模板（中文）
    - AMERICAN → MCM/ICM 美赛模板（mcmthesis，英文）

    Args:
        markdown_content: Markdown 格式的论文内容
        output_path: LaTeX 文件输出路径（如 /path/to/paper.tex）
        comp_template: 竞赛模板类型
        title: 论文标题
        abstract: 摘要文本
        keywords: 关键词列表
        team_control_number: 队伍编号（仅 MCM/ICM 使用）
        problem_choice: 选题编号（仅 MCM/ICM 使用）

    Returns:
        生成的 LaTeX 文件路径
    """
    is_mcm = comp_template == CompTemplate.AMERICAN
    template = PaperTemplate.MCM_ICM if is_mcm else PaperTemplate.CUMCM
    language = PaperLanguage.ENGLISH if is_mcm else PaperLanguage.CHINESE

    # 设置默认值
    if not title:
        title = "Mathematical Modeling Paper" if is_mcm else "数学建模论文"
    if keywords is None:
        keywords = (
            ["Mathematical Modeling", "Optimization", "Prediction"]
            if is_mcm
            else ["数学建模", "优化", "预测"]
        )

    latex_generator = LaTeXGenerator(
        template=template,
        language=language,
        team_control_number=team_control_number,
        problem_choice=problem_choice,
    )

    paper_content = markdown_to_paper_content(
        title=title,
        markdown_text=markdown_content,
        abstract=abstract,
        keywords=keywords,
        citations=[],
    )

    # save_to_file 会自动复制 mcmthesis.cls 和 figures/ 到输出目录
    latex_path = latex_generator.save_to_file(paper_content, output_path)

    logger.info("LaTeX 文件已生成: %s", latex_path)
    return latex_path
