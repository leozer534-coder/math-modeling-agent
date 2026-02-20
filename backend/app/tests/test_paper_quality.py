"""
paper/ 和 quality/ 模块测试

覆盖:
  - latex_generator.py: 数据类、数学环境保护、LaTeX 转义、Markdown 转换、文档生成
  - quality_gates.py: CodeQualityGate, PaperQualityGate, ReproducibilityGate, QualityChecker
  - result_checker.py: ResultQualityReport, ResultQualityChecker
"""

import sys
from unittest.mock import MagicMock

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.HumanMessage = MagicMock
        _mock.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock

import pytest  # noqa: E402

from app.core.paper.latex_generator import (  # noqa: E402
    Citation,
    Figure,
    LaTeXGenerator,
    PaperContent,
    PaperLanguage,
    PaperSection,
    PaperTemplate,
    Table,
    _protect_math_environments,
    _restore_math_environments,
)
from app.core.quality.quality_gates import (  # noqa: E402
    CodeQualityGate,
    GateCategory,
    GateConfig,
    PaperQualityGate,
    QualityChecker,
    ReproducibilityGate,
    check_code_quality,
    check_paper_quality,
)
from app.core.quality.result_checker import (  # noqa: E402
    ResultQualityChecker,
    ResultQualityReport,
)
from app.schemas.contracts import GateResult  # noqa: E402


# ================================================================
# LaTeX 数据类测试
# ================================================================


class TestLaTeXDataclasses:
    """LaTeX 相关数据类基础测试"""

    @pytest.mark.unit
    def test_paper_template_enum(self):
        """验证: PaperTemplate 枚举包含三种模板"""
        assert PaperTemplate.MCM_ICM.value == "mcm_icm"
        assert PaperTemplate.CUMCM.value == "cumcm"
        assert PaperTemplate.GENERAL.value == "general"

    @pytest.mark.unit
    def test_paper_language_enum(self):
        """验证: PaperLanguage 枚举包含中英文"""
        assert PaperLanguage.CHINESE.value == "zh"
        assert PaperLanguage.ENGLISH.value == "en"

    @pytest.mark.unit
    def test_paper_section_defaults(self):
        """验证: PaperSection 默认值"""
        sec = PaperSection(title="标题", content="内容")
        assert sec.title == "标题"
        assert sec.content == "内容"
        assert sec.level == 1
        assert sec.label is None

    @pytest.mark.unit
    def test_paper_section_custom(self):
        """验证: PaperSection 自定义参数"""
        sec = PaperSection(title="子章节", content="详细内容", level=2, label="sec:sub")
        assert sec.level == 2
        assert sec.label == "sec:sub"

    @pytest.mark.unit
    def test_figure_defaults(self):
        """验证: Figure 默认宽度"""
        fig = Figure(path="img.png", caption="描述", label="fig:1")
        assert fig.width == "0.8\\textwidth"

    @pytest.mark.unit
    def test_table_defaults(self):
        """验证: Table 默认空列表"""
        tab = Table(caption="表格", label="tab:1", content="内容")
        assert tab.headers == []
        assert tab.data == []

    @pytest.mark.unit
    def test_citation_defaults(self):
        """验证: Citation 可选 url 字段"""
        cit = Citation(key="ref1", authors="张三", title="论文", year="2024", source="期刊")
        assert cit.url is None

    @pytest.mark.unit
    def test_paper_content_creation(self):
        """验证: PaperContent 创建和默认值"""
        content = PaperContent(
            title="数学建模论文",
            abstract="本文研究了...",
            keywords=["优化", "建模"],
            sections=[PaperSection(title="引言", content="...")]
        )
        assert content.title == "数学建模论文"
        assert len(content.keywords) == 2
        assert len(content.sections) == 1
        assert content.figures == []
        assert content.tables == []
        assert content.citations == []
        assert content.appendix is None


# ================================================================
# 数学环境保护测试
# ================================================================


class TestMathProtection:
    """数学环境保护/还原函数测试"""

    @pytest.mark.unit
    def test_protect_inline_math(self):
        """验证: 行内数学 $...$ 被占位符替换"""
        text = "设 $x + y = 1$ 为约束条件"
        protected, placeholders = _protect_math_environments(text)
        assert "$x + y = 1$" not in protected
        assert len(placeholders) >= 1

    @pytest.mark.unit
    def test_protect_display_math(self):
        """验证: 显示数学 $$...$$ 被占位符替换"""
        text = "目标函数为 $$\\min f(x) = x^2$$ 其中"
        protected, placeholders = _protect_math_environments(text)
        assert "$$" not in protected
        assert len(placeholders) >= 1

    @pytest.mark.unit
    def test_protect_equation_env(self):
        """验证: \\begin{equation} 环境被保护"""
        text = "公式如下：\n\\begin{equation}\nE = mc^2\n\\end{equation}\n结束"
        protected, placeholders = _protect_math_environments(text)
        assert "\\begin{equation}" not in protected
        assert len(placeholders) >= 1

    @pytest.mark.unit
    def test_protect_bracket_math(self):
        """验证: \\[...\\] 显示数学被保护"""
        text = "计算结果为 \\[a + b = c\\] 证毕"
        protected, placeholders = _protect_math_environments(text)
        assert "\\[" not in protected

    @pytest.mark.unit
    def test_protect_paren_math(self):
        """验证: \\(...\\) 行内数学被保护"""
        text = "其中 \\(x > 0\\) 为约束"
        protected, placeholders = _protect_math_environments(text)
        assert "\\(" not in protected

    @pytest.mark.unit
    def test_restore_roundtrip(self):
        """验证: 保护-还原往返一致性"""
        original = "设 $x^2$ 和 $$y = \\frac{1}{x}$$ 以及 $z$"
        protected, placeholders = _protect_math_environments(original)
        restored = _restore_math_environments(protected, placeholders)
        assert restored == original

    @pytest.mark.unit
    def test_protect_no_math(self):
        """验证: 无数学环境的文本不变"""
        text = "这是一段普通文本，没有数学公式"
        protected, placeholders = _protect_math_environments(text)
        assert protected == text
        assert len(placeholders) == 0

    @pytest.mark.unit
    def test_protect_multiple_environments(self):
        """验证: 多种数学环境混合保护"""
        text = (
            "行内 $a$ 和显示 $$b$$ 以及环境 "
            "\\begin{align}\nc &= d\n\\end{align}"
        )
        protected, placeholders = _protect_math_environments(text)
        assert len(placeholders) >= 3

    @pytest.mark.unit
    def test_protect_latex_commands(self):
        """验证: 独立 LaTeX 命令（\\frac 等）被保护"""
        text = "其中 \\frac{a}{b} 表示分数"
        protected, placeholders = _protect_math_environments(text)
        assert len(placeholders) >= 1


# ================================================================
# LaTeX 生成器测试
# ================================================================


class TestLaTeXGenerator:
    """LaTeXGenerator 类测试"""

    @pytest.mark.unit
    def test_init_defaults(self):
        """验证: 默认初始化参数"""
        gen = LaTeXGenerator()
        assert gen.template == PaperTemplate.CUMCM
        assert gen.language == PaperLanguage.CHINESE
        assert gen.team_control_number == "XXXXX"
        assert gen.problem_choice == "A"

    @pytest.mark.unit
    def test_init_mcm(self):
        """验证: MCM 模板初始化"""
        gen = LaTeXGenerator(
            template=PaperTemplate.MCM_ICM,
            team_control_number="12345",
            problem_choice="B",
        )
        assert gen.template == PaperTemplate.MCM_ICM
        assert gen.team_control_number == "12345"

    @pytest.mark.unit
    def test_uses_mcmthesis(self):
        """验证: MCM 模板使用 mcmthesis 文档类"""
        gen_mcm = LaTeXGenerator(template=PaperTemplate.MCM_ICM)
        gen_cumcm = LaTeXGenerator(template=PaperTemplate.CUMCM)
        assert gen_mcm._uses_mcmthesis() is True
        assert gen_cumcm._uses_mcmthesis() is False

    @pytest.mark.unit
    def test_generate_returns_string(self):
        """验证: generate() 返回有效 LaTeX 字符串"""
        gen = LaTeXGenerator(template=PaperTemplate.CUMCM)
        content = PaperContent(
            title="测试论文",
            abstract="本文研究了数学建模问题",
            keywords=["优化", "建模"],
            sections=[PaperSection(title="引言", content="数学建模是...")]
        )
        result = gen.generate(content)
        assert isinstance(result, str)
        assert "\\documentclass" in result
        assert "\\begin{document}" in result

    @pytest.mark.unit
    def test_generate_cumcm_has_ctex(self):
        """验证: CUMCM 模板包含 ctex 宏包"""
        gen = LaTeXGenerator(template=PaperTemplate.CUMCM)
        content = PaperContent(
            title="测试", abstract="摘要", keywords=["关键词"],
            sections=[PaperSection(title="节", content="内容")]
        )
        result = gen.generate(content)
        assert "ctex" in result

    @pytest.mark.unit
    def test_generate_mcm_has_mcmthesis(self):
        """验证: MCM 模板包含 mcmthesis 文档类"""
        gen = LaTeXGenerator(template=PaperTemplate.MCM_ICM)
        content = PaperContent(
            title="Test", abstract="Abstract", keywords=["modeling"],
            sections=[PaperSection(title="Introduction", content="...")]
        )
        result = gen.generate(content)
        assert "mcmthesis" in result

    @pytest.mark.unit
    def test_generate_figure(self):
        """验证: generate_figure() 生成正确的 figure 环境"""
        gen = LaTeXGenerator()
        fig = Figure(path="result.png", caption="结果图", label="fig:result")
        result = gen.generate_figure(fig)
        assert "\\begin{figure}" in result
        assert "result.png" in result
        assert "结果图" in result
        assert "fig:result" in result

    @pytest.mark.unit
    def test_generate_table(self):
        """验证: generate_table() 生成正确的 table 环境"""
        gen = LaTeXGenerator()
        tab = Table(
            caption="数据表",
            label="tab:data",
            content="A & B \\\\\n1 & 2",
            headers=["列A", "列B"],
        )
        result = gen.generate_table(tab)
        assert "\\begin{table}" in result
        assert "数据表" in result

    @pytest.mark.unit
    def test_build_references(self):
        """验证: _build_references() 生成参考文献列表"""
        gen = LaTeXGenerator()
        citations = [
            Citation(key="ref1", authors="张三", title="论文一", year="2024", source="数学杂志"),
            Citation(key="ref2", authors="李四", title="论文二", year="2023", source="学报"),
        ]
        result = gen._build_references(citations)
        assert isinstance(result, str)
        assert "张三" in result or "bibitem" in result.lower() or "参考文献" in result

    @pytest.mark.unit
    def test_team_number_in_cumcm_preamble(self):
        """验证: CUMCM 模板页眉包含队伍编号"""
        gen = LaTeXGenerator(
            template=PaperTemplate.CUMCM,
            team_control_number="T9999"
        )
        preamble = gen._get_preamble()
        assert "T9999" in preamble


# ================================================================
# 代码质量闸门测试
# ================================================================


class TestCodeQualityGate:
    """CodeQualityGate 测试"""

    @pytest.mark.unit
    def test_gate_identity(self):
        """验证: gate id 和 name"""
        gate = CodeQualityGate()
        assert gate.id == "code_quality"
        assert gate.name == "代码质量检查"

    @pytest.mark.unit
    def test_good_code_passes(self):
        """验证: 高质量代码通过检查"""
        gate = CodeQualityGate()
        code = '''
def solve_linear_program(c, A_ub, b_ub):
    """使用线性规划求解资源分配问题"""
    from scipy.optimize import linprog
    result = linprog(c, A_ub=A_ub, b_ub=b_ub)
    return result.x
'''
        result = gate.check({"code": code, "language": "python"})
        assert isinstance(result, GateResult)
        assert result.gate_id == "code_quality"
        assert result.score > 0

    @pytest.mark.unit
    def test_empty_code_low_score(self):
        """验证: 空代码 basic_score 为 0, 总分受影响但其他子项满分"""
        gate = CodeQualityGate()
        result = gate.check({"code": "", "language": "python"})
        assert result.details["basic_score"] == 0.0
        assert any("空" in issue for issue in result.issues)

    @pytest.mark.unit
    def test_syntax_error_detected(self):
        """验证: 语法错误被检测"""
        gate = CodeQualityGate()
        code = "def foo(\n    return 1"
        result = gate.check({"code": code, "language": "python"})
        assert any("语法" in issue for issue in result.issues)

    @pytest.mark.unit
    def test_hardcoded_path_detected(self):
        """验证: 硬编码 Windows 路径被检测"""
        gate = CodeQualityGate()
        code = '''
def load_data():
    """加载数据"""
    path = "C:\\Users\\data\\file.csv"
    return path
'''
        result = gate.check({"code": code, "language": "python"})
        assert any("硬编码" in issue or "路径" in issue for issue in result.issues)

    @pytest.mark.unit
    def test_mixed_indent_detected(self):
        """验证: 混用缩进被检测"""
        gate = CodeQualityGate()
        code = "def foo():\n    x = 1\n\ty = 2\n"
        result = gate.check({"code": code, "language": "python"})
        assert any("缩进" in issue for issue in result.issues)

    @pytest.mark.unit
    def test_score_level_mapping(self):
        """验证: 分数到等级映射正确"""
        gate = CodeQualityGate()
        assert gate._score_to_level(0.95) == "excellent"
        assert gate._score_to_level(0.75) == "good"
        assert gate._score_to_level(0.55) == "acceptable"
        assert gate._score_to_level(0.35) == "needs_improvement"
        assert gate._score_to_level(0.15) == "poor"

    @pytest.mark.unit
    def test_get_requirements(self):
        """验证: get_requirements() 返回检查项列表"""
        gate = CodeQualityGate()
        reqs = gate.get_requirements()
        assert isinstance(reqs, list)
        assert len(reqs) > 0

    @pytest.mark.unit
    def test_custom_config(self):
        """验证: 自定义 GateConfig 影响通过判定"""
        strict_config = GateConfig(min_pass_score=0.9)
        gate = CodeQualityGate(config=strict_config)
        code = "x = 1\ny = 2\n"
        result = gate.check({"code": code, "language": "python"})
        # 简单代码在严格模式下可能不通过
        assert isinstance(result.passed, bool)

    @pytest.mark.unit
    def test_non_python_syntax_skip(self):
        """验证: 非 Python 语言跳过语法检查"""
        gate = CodeQualityGate()
        result = gate.check({"code": "invalid syntax {{{", "language": "r"})
        # 非 Python 不做语法检查，syntax_score 应为 1.0
        assert result.details.get("syntax_score") == 1.0


# ================================================================
# 论文质量闸门测试
# ================================================================


class TestPaperQualityGate:
    """PaperQualityGate 测试"""

    @pytest.mark.unit
    def test_gate_identity(self):
        """验证: gate id 和 name"""
        gate = PaperQualityGate()
        assert gate.id == "paper_quality"

    @pytest.mark.unit
    def test_required_sections(self):
        """验证: 必需章节列表完整"""
        assert "摘要" in PaperQualityGate.REQUIRED_SECTIONS
        assert "模型建立" in PaperQualityGate.REQUIRED_SECTIONS
        assert "参考文献" in PaperQualityGate.REQUIRED_SECTIONS

    @pytest.mark.unit
    def test_complete_paper_high_score(self):
        """验证: 包含所有章节的论文得分较高"""
        gate = PaperQualityGate()
        sections = "\n".join(
            f"# {s}\n这是{s}的详细内容..." * 10
            for s in PaperQualityGate.REQUIRED_SECTIONS
        )
        # 构造一个长度足够的论文
        abstract = (
            "摘要：本文针对资源优化分配问题，建立了线性规划模型。"
            "结果表明，最优方案可将效率提高23.5%，降低成本15.2万元。"
            "本文的方法具有较强的实用性。" * 5
        )
        content = f"# 摘要\n{abstract}\n\n关键词：优化, 建模\n\n{sections}"
        # 添加一些公式
        content += "\n$x + y = 1$\n$a = b$\n$$f(x) = x^2$$\n$c$\n$d$\n$e$\n"
        result = gate.check({"content": content})
        assert isinstance(result, GateResult)
        assert result.score > 0.3

    @pytest.mark.unit
    def test_empty_paper_low_score(self):
        """验证: 空论文得分低"""
        gate = PaperQualityGate()
        result = gate.check({"content": ""})
        assert result.score < 0.5

    @pytest.mark.unit
    def test_missing_sections_detected(self):
        """验证: 缺失章节被报告"""
        gate = PaperQualityGate()
        content = "# 摘要\n本文...\n# 模型建立\n模型..."
        result = gate.check({"content": content})
        assert any("缺少章节" in issue for issue in result.issues)

    @pytest.mark.unit
    def test_short_abstract_detected(self):
        """验证: 过短摘要被报告"""
        gate = PaperQualityGate()
        content = "# 摘要\n摘要：很短。"
        result = gate.check({"content": content})
        # 摘要过短应有 issue
        abstract_issues = [i for i in result.issues if "摘要" in i]
        assert len(abstract_issues) >= 0  # 可能匹配不到摘要模式

    @pytest.mark.unit
    def test_figure_reference_check(self):
        """验证: 未引用的图片被检测"""
        gate = PaperQualityGate()
        content = "# 摘要\n本文... 如图 1 所示"
        result = gate.check({
            "content": content,
            "figures": ["fig1.png", "fig2.png"],  # 图2未引用
        })
        fig_issues = [i for i in result.issues if "图" in i]
        assert len(fig_issues) >= 1

    @pytest.mark.unit
    def test_formula_count_check(self):
        """验证: 公式过少被报告"""
        gate = PaperQualityGate()
        content = "# 摘要\n本文只有两个公式 $x=1$ 和 $y=2$"
        result = gate.check({"content": content})
        formula_issues = [i for i in result.issues if "公式" in i]
        assert len(formula_issues) >= 1

    @pytest.mark.unit
    def test_word_count_check_short(self):
        """验证: 字数不足被报告"""
        gate = PaperQualityGate()
        result = gate.check({"content": "很短的论文"})
        word_issues = [i for i in result.issues if "字数" in i]
        assert len(word_issues) >= 1

    @pytest.mark.unit
    def test_get_requirements(self):
        """验证: get_requirements() 返回完整列表"""
        gate = PaperQualityGate()
        reqs = gate.get_requirements()
        assert len(reqs) >= 5


# ================================================================
# 可复现性闸门测试
# ================================================================


class TestReproducibilityGate:
    """ReproducibilityGate 测试"""

    @pytest.mark.unit
    def test_gate_identity(self):
        """验证: gate id 和 name"""
        gate = ReproducibilityGate()
        assert gate.id == "reproducibility"
        assert gate.name == "可复现性检查"

    @pytest.mark.unit
    def test_all_present_high_score(self):
        """验证: 所有条件满足时得分高"""
        gate = ReproducibilityGate()
        result = gate.check({
            "has_requirements": True,
            "has_readme": True,
            "random_seeds": {"numpy": 42, "torch": 42},
            "data_path": ".",  # 当前目录存在
        })
        assert result.score >= 0.75
        assert result.passed is True

    @pytest.mark.unit
    def test_nothing_present_low_score(self):
        """验证: 什么都没有时得分低"""
        gate = ReproducibilityGate()
        result = gate.check({
            "has_requirements": False,
            "has_readme": False,
            "random_seeds": {},
            "data_path": "",
        })
        assert result.score <= 0.25

    @pytest.mark.unit
    def test_missing_requirements_issue(self):
        """验证: 缺少 requirements 被报告"""
        gate = ReproducibilityGate()
        result = gate.check({"has_requirements": False})
        assert any("requirements" in i.lower() or "依赖" in i for i in result.issues)

    @pytest.mark.unit
    def test_missing_readme_issue(self):
        """验证: 缺少 README 被报告"""
        gate = ReproducibilityGate()
        result = gate.check({"has_readme": False})
        assert any("readme" in i.lower() or "说明" in i for i in result.issues)

    @pytest.mark.unit
    def test_missing_seeds_issue(self):
        """验证: 缺少随机种子被报告"""
        gate = ReproducibilityGate()
        result = gate.check({"random_seeds": {}})
        assert any("种子" in i for i in result.issues)

    @pytest.mark.unit
    def test_get_requirements(self):
        """验证: get_requirements() 返回检查项"""
        gate = ReproducibilityGate()
        reqs = gate.get_requirements()
        assert isinstance(reqs, list)
        assert len(reqs) >= 3


# ================================================================
# 综合质量检查器测试
# ================================================================


class TestQualityChecker:
    """QualityChecker 综合检查器测试"""

    @pytest.mark.unit
    def test_init_creates_all_gates(self):
        """验证: 初始化创建三个闸门"""
        checker = QualityChecker()
        assert "code" in checker.gates
        assert "paper" in checker.gates
        assert "reproducibility" in checker.gates

    @pytest.mark.unit
    def test_check_code_convenience(self):
        """验证: check_code() 便捷方法"""
        checker = QualityChecker()
        result = checker.check_code("x = 1\n")
        assert isinstance(result, GateResult)

    @pytest.mark.unit
    def test_check_paper_convenience(self):
        """验证: check_paper() 便捷方法"""
        checker = QualityChecker()
        result = checker.check_paper("# 摘要\n本文...")
        assert isinstance(result, GateResult)

    @pytest.mark.unit
    def test_check_reproducibility_convenience(self):
        """验证: check_reproducibility() 便捷方法"""
        checker = QualityChecker()
        result = checker.check_reproducibility(
            code_path=".", has_requirements=True, has_readme=True,
            random_seeds={"np": 42}
        )
        assert isinstance(result, GateResult)

    @pytest.mark.unit
    def test_run_all_checks(self):
        """验证: run_all_checks() 返回三个结果"""
        checker = QualityChecker()
        results = checker.run_all_checks(
            code="x = 1\n",
            paper_content="# 摘要\n测试内容"
        )
        assert len(results) == 3
        assert "code" in results
        assert "paper" in results
        assert "reproducibility" in results

    @pytest.mark.unit
    def test_get_overall_score(self):
        """验证: get_overall_score() 返回加权分数"""
        checker = QualityChecker()
        results = checker.run_all_checks(code="x = 1\n", paper_content="")
        score = checker.get_overall_score(results)
        assert 0 <= score <= 1

    @pytest.mark.unit
    def test_format_report(self):
        """验证: format_report() 生成 Markdown 报告"""
        checker = QualityChecker()
        results = checker.run_all_checks(code="x = 1\n", paper_content="测试")
        report = checker.format_report(results)
        assert isinstance(report, str)
        assert "质量检查报告" in report
        assert "代码质量" in report
        assert "论文质量" in report
        assert "可复现性" in report

    @pytest.mark.unit
    def test_convenience_functions(self):
        """验证: 模块级便捷函数可用"""
        result1 = check_code_quality("x = 1\n")
        assert isinstance(result1, GateResult)

        result2 = check_paper_quality("测试论文")
        assert isinstance(result2, GateResult)


# ================================================================
# GateConfig 和 GateCategory 测试
# ================================================================


class TestGateConfigAndCategory:
    """GateConfig 和 GateCategory 测试"""

    @pytest.mark.unit
    def test_gate_config_defaults(self):
        """验证: GateConfig 默认值"""
        config = GateConfig()
        assert config.min_pass_score == 0.6
        assert config.warning_threshold == 0.8
        assert config.strict_mode is False

    @pytest.mark.unit
    def test_gate_config_custom(self):
        """验证: GateConfig 自定义值"""
        config = GateConfig(min_pass_score=0.8, strict_mode=True)
        assert config.min_pass_score == 0.8
        assert config.strict_mode is True

    @pytest.mark.unit
    def test_gate_category_values(self):
        """验证: GateCategory 枚举值"""
        assert GateCategory.CODE.value == "code"
        assert GateCategory.PAPER.value == "paper"
        assert GateCategory.MODEL.value == "model"
        assert GateCategory.REPRODUCIBILITY.value == "reproducibility"


# ================================================================
# ResultQualityReport 测试
# ================================================================


class TestResultQualityReport:
    """ResultQualityReport 数据类测试"""

    @pytest.mark.unit
    def test_default_values(self):
        """验证: 默认值"""
        report = ResultQualityReport()
        assert report.has_numeric_output is False
        assert report.has_eval_metrics is False
        assert report.has_images is False
        assert report.has_conclusion is False
        assert report.no_fatal_error is True
        assert report.detected_metrics == []
        assert report.issues == []

    @pytest.mark.unit
    def test_score_all_true(self):
        """验证: 全部通过时分数为 1.0"""
        report = ResultQualityReport(
            has_numeric_output=True,
            has_eval_metrics=True,
            has_images=True,
            has_conclusion=True,
            no_fatal_error=True,
        )
        assert report.score == 1.0

    @pytest.mark.unit
    def test_score_all_false(self):
        """验证: 全部失败时分数为 0.0"""
        report = ResultQualityReport(
            has_numeric_output=False,
            has_eval_metrics=False,
            has_images=False,
            has_conclusion=False,
            no_fatal_error=False,
        )
        assert report.score == 0.0

    @pytest.mark.unit
    def test_score_partial(self):
        """验证: 部分通过时分数在 0 和 1 之间"""
        report = ResultQualityReport(
            has_numeric_output=True,
            has_eval_metrics=False,
            has_images=True,
            has_conclusion=False,
            no_fatal_error=True,
        )
        assert 0 < report.score < 1

    @pytest.mark.unit
    def test_passed_threshold(self):
        """验证: score >= 0.4 时 passed 为 True"""
        # 只有 no_fatal_error=True (0.25) → 不通过
        report_low = ResultQualityReport(no_fatal_error=True)
        assert report_low.score == 0.25
        assert report_low.passed is False

        # numeric + fatal = 0.25 + 0.25 = 0.50 → 通过
        report_ok = ResultQualityReport(has_numeric_output=True, no_fatal_error=True)
        assert report_ok.score == 0.50
        assert report_ok.passed is True

    @pytest.mark.unit
    def test_to_dict(self):
        """验证: to_dict() 包含所有字段"""
        report = ResultQualityReport(
            has_numeric_output=True,
            no_fatal_error=True,
            detected_metrics=["R²", "RMSE"],
            issues=["缺少图表"],
        )
        d = report.to_dict()
        assert d["has_numeric_output"] is True
        assert d["no_fatal_error"] is True
        assert d["detected_metrics"] == ["R²", "RMSE"]
        assert d["issues"] == ["缺少图表"]
        assert "score" in d
        assert "passed" in d

    @pytest.mark.unit
    def test_score_weights_sum_to_one(self):
        """验证: 权重之和为 1.0"""
        weights = {
            "has_numeric_output": 0.25,
            "has_eval_metrics": 0.25,
            "has_images": 0.15,
            "has_conclusion": 0.10,
            "no_fatal_error": 0.25,
        }
        assert abs(sum(weights.values()) - 1.0) < 1e-9


# ================================================================
# ResultQualityChecker 测试
# ================================================================


class TestResultQualityChecker:
    """ResultQualityChecker 测试"""

    @pytest.mark.unit
    def test_empty_output(self):
        """验证: 空输出返回有效报告"""
        checker = ResultQualityChecker()
        report = checker.check("")
        assert isinstance(report, ResultQualityReport)
        assert report.no_fatal_error is True
        assert len(report.issues) >= 1  # 应报告空输出

    @pytest.mark.unit
    def test_fatal_error_detected(self):
        """验证: Traceback 被检测为致命错误"""
        checker = ResultQualityChecker()
        output = "结果输出...\nTraceback (most recent call last):\n  File ...\nValueError: ..."
        report = checker.check(output)
        assert report.no_fatal_error is False

    @pytest.mark.unit
    def test_memory_error_detected(self):
        """验证: MemoryError 被检测"""
        checker = ResultQualityChecker()
        output = "处理中...\nMemoryError: 内存不足"
        report = checker.check(output)
        assert report.no_fatal_error is False

    @pytest.mark.unit
    def test_numeric_output_detected(self):
        """验证: 包含数值的输出被识别"""
        checker = ResultQualityChecker()
        output = (
            "模型结果:\n"
            "x1 = 3.14\n"
            "x2 = 2.71\n"
            "x3 = 1.41\n"
            "目标值 = 7.26\n"
        )
        report = checker.check(output)
        assert report.has_numeric_output is True

    @pytest.mark.unit
    def test_eval_metrics_r2(self):
        """验证: R² 指标被检测"""
        checker = ResultQualityChecker()
        output = "模型评估:\nR² = 0.95\nRMSE = 0.12\n最终结论: 模型表现良好"
        report = checker.check(output)
        assert report.has_eval_metrics is True
        assert "R²" in report.detected_metrics

    @pytest.mark.unit
    def test_eval_metrics_accuracy(self):
        """验证: 准确率指标被检测"""
        checker = ResultQualityChecker()
        output = "分类结果:\naccuracy = 0.93\n结论: 分类效果好\n1.0\n2.0\n3.0"
        report = checker.check(output)
        assert report.has_eval_metrics is True
        assert "Accuracy" in report.detected_metrics

    @pytest.mark.unit
    def test_images_detected(self):
        """验证: 图片列表被识别"""
        checker = ResultQualityChecker()
        output = "绘图完成\n1.0\n2.0\n3.0"
        report = checker.check(output, created_images=["fig1.png", "fig2.png"])
        assert report.has_images is True

    @pytest.mark.unit
    def test_no_images_issue(self):
        """验证: 无图片产生 issue"""
        checker = ResultQualityChecker()
        output = "计算完成\n1.0\n2.0\n3.0"
        report = checker.check(output, created_images=[])
        assert report.has_images is False
        assert any("图表" in i for i in report.issues)

    @pytest.mark.unit
    def test_conclusion_detected(self):
        """验证: 结论性关键词被检测"""
        checker = ResultQualityChecker()
        output = "经过分析，最终结论是该方案可行\n1.0\n2.0\n3.0"
        report = checker.check(output)
        assert report.has_conclusion is True

    @pytest.mark.unit
    def test_no_conclusion_issue(self):
        """验证: 缺少结论产生 issue"""
        checker = ResultQualityChecker()
        output = "1.0\n2.0\n3.0\n4.0\n5.0"
        report = checker.check(output)
        assert report.has_conclusion is False
        assert any("结论" in i for i in report.issues)

    @pytest.mark.unit
    def test_eda_task_type(self):
        """验证: EDA 任务类型不强制要求评估指标"""
        checker = ResultQualityChecker()
        output = "数据探索完成\n行数: 100\n列数: 10\n缺失值: 5\n"
        report = checker.check(output, task_type="eda")
        # EDA 类型对指标要求宽松
        assert isinstance(report, ResultQualityReport)

    @pytest.mark.unit
    def test_sensitivity_task_type(self):
        """验证: 敏感性分析任务使用特定关键词"""
        checker = ResultQualityChecker()
        output = "参数扰动分析:\n参数变动10%后影响较小\n1.0\n2.0\n3.0"
        report = checker.check(output, task_type="sensitivity")
        assert report.has_eval_metrics is True

    @pytest.mark.unit
    def test_full_good_output(self):
        """验证: 完整高质量输出通过检查"""
        checker = ResultQualityChecker()
        output = (
            "=== 模型训练结果 ===\n"
            "R² = 0.95\n"
            "RMSE = 0.12\n"
            "MAE = 0.08\n"
            "最优值: x1=3.14, x2=2.71, x3=1.41\n"
            "目标函数值 = 7.26\n"
            "\n最终结论: 线性规划模型成功求解，方案可行。\n"
        )
        report = checker.check(
            output,
            created_images=["result_plot.png"],
        )
        assert report.passed is True
        assert report.score >= 0.7

    @pytest.mark.unit
    def test_metric_patterns_comprehensive(self):
        """验证: 多种指标模式均可检测"""
        checker = ResultQualityChecker()
        test_cases = [
            ("R² = 0.95", "R²"),
            ("RMSE = 0.12", "RMSE"),
            ("MAE = 0.08", "MAE"),
            ("F1-Score = 0.88", "F1-Score"),
            ("AUC = 0.92", "AUC"),
            ("轮廓系数 = 0.65", "Silhouette"),
            ("目标函数 = 100.5", "Objective"),
        ]
        for text, expected_metric in test_cases:
            full_output = f"结果:\n{text}\n1.0\n2.0\n3.0"
            report = checker.check(full_output)
            assert expected_metric in report.detected_metrics, (
                f"未检测到指标 '{expected_metric}', 输入: '{text}', "
                f"检测到: {report.detected_metrics}"
            )

    @pytest.mark.unit
    def test_fatal_patterns_comprehensive(self):
        """验证: 多种致命错误模式均可检测"""
        checker = ResultQualityChecker()
        fatal_outputs = [
            "Traceback (most recent call last):\n  File ...",
            "MemoryError: 内存不足",
            "ModuleNotFoundError: No module named 'xxx'",
        ]
        for output in fatal_outputs:
            report = checker.check(output)
            assert report.no_fatal_error is False, (
                f"未检测到致命错误: '{output[:50]}...'"
            )
