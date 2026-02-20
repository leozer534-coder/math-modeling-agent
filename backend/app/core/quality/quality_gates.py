"""
Quality Gates - 质量闸门系统
============================

功能：
1. 代码质量检查
2. 论文质量检查
3. 模型验证检查
4. 可复现性检查

关键特性：
- 多维度质量评估
- 分级别通过标准
- 自动生成改进建议
"""

import ast
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.contracts import GateResult, QualityLevel


class GateCategory(Enum):
    """闸门类别"""

    CODE = "code"  # 代码质量
    PAPER = "paper"  # 论文质量
    MODEL = "model"  # 模型质量
    REPRODUCIBILITY = "reproducibility"  # 可复现性


@dataclass
class GateConfig:
    """闸门配置"""

    min_pass_score: float = 0.6  # 最低通过分数
    warning_threshold: float = 0.8  # 警告阈值
    strict_mode: bool = False  # 严格模式


# ================== 代码质量闸门 ==================


class CodeQualityGate:
    """代码质量闸门"""

    id = "code_quality"
    name = "代码质量检查"

    def __init__(self, config: Optional[GateConfig] = None):
        self.config = config or GateConfig()

    def check(self, bundle: Dict[str, Any]) -> GateResult:
        """
        检查代码质量

        Args:
            bundle: {
                "code": str,  # 代码内容
                "language": str,  # 语言 (python)
                "file_path": Optional[str]  # 文件路径
            }

        Returns:
            检查结果
        """
        code = bundle.get("code", "")
        language = bundle.get("language", "python")

        issues: List[str] = []
        suggestions: List[str] = []
        details: Dict[str, Any] = {}

        # 1. 基础检查
        basic_score, basic_issues = self._check_basic(code)
        issues.extend(basic_issues)
        details["basic_score"] = basic_score

        # 2. 语法检查
        syntax_score, syntax_issues = self._check_syntax(code, language)
        issues.extend(syntax_issues)
        details["syntax_score"] = syntax_score

        # 3. 代码风格检查
        style_score, style_issues = self._check_style(code)
        issues.extend(style_issues)
        details["style_score"] = style_score

        # 4. 复杂度检查
        complexity_score, complexity_issues = self._check_complexity(code)
        issues.extend(complexity_issues)
        details["complexity_score"] = complexity_score

        # 5. 文档检查
        doc_score, doc_issues = self._check_documentation(code)
        issues.extend(doc_issues)
        details["documentation_score"] = doc_score

        # 计算总分
        weights = {
            "basic": 0.2,
            "syntax": 0.3,
            "style": 0.2,
            "complexity": 0.15,
            "documentation": 0.15,
        }

        total_score = (
            basic_score * weights["basic"]
            + syntax_score * weights["syntax"]
            + style_score * weights["style"]
            + complexity_score * weights["complexity"]
            + doc_score * weights["documentation"]
        )

        # 确定等级
        level = self._score_to_level(total_score)
        passed = total_score >= self.config.min_pass_score

        # 生成建议
        if not passed:
            suggestions.append("代码质量未达标，请修复上述问题后重新提交")
        if doc_score < 0.5:
            suggestions.append("建议增加函数和类的文档字符串")
        if complexity_score < 0.5:
            suggestions.append("建议拆分过长的函数，降低代码复杂度")

        return GateResult(
            gate_id=self.id,
            passed=passed,
            score=total_score,
            level=level,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )

    def _check_basic(self, code: str) -> Tuple[float, List[str]]:
        """基础检查"""
        issues = []
        score = 1.0

        if not code.strip():
            return 0.0, ["代码为空"]

        # 检查是否有明显的调试代码
        if "print(" in code and code.count("print(") > 10:
            issues.append("包含过多print语句")
            score -= 0.1

        # 检查是否有硬编码路径
        if re.search(r'["\'][A-Za-z]:\\', code):
            issues.append("包含硬编码的Windows路径")
            score -= 0.1

        # 检查是否有TODO未处理
        todo_count = code.lower().count("todo")
        if todo_count > 3:
            issues.append(f"包含{todo_count}个未处理的TODO")
            score -= 0.05 * min(todo_count, 5)

        return max(0, score), issues

    def _check_syntax(self, code: str, language: str) -> Tuple[float, List[str]]:
        """语法检查"""
        if language != "python":
            return 1.0, []

        issues = []

        try:
            ast.parse(code)
            return 1.0, []
        except SyntaxError as e:
            issues.append(f"语法错误: {e.msg} (行 {e.lineno})")
            return 0.0, issues

    def _check_style(self, code: str) -> Tuple[float, List[str]]:
        """代码风格检查"""
        issues = []
        score = 1.0

        lines = code.split("\n")

        # 检查行长度
        long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > 120]
        if long_lines:
            issues.append(f"第 {long_lines[:5]} 行超过120字符")
            score -= 0.1

        # 检查缩进一致性
        indent_types = set()
        for line in lines:
            if line.startswith(" "):
                indent_types.add("space")
            elif line.startswith("\t"):
                indent_types.add("tab")

        if len(indent_types) > 1:
            issues.append("混用空格和Tab缩进")
            score -= 0.2

        # 检查命名规范
        if re.search(r"\bdef [A-Z]", code):
            issues.append("函数名应使用小写字母和下划线")
            score -= 0.1

        return max(0, score), issues

    def _check_complexity(self, code: str) -> Tuple[float, List[str]]:
        """复杂度检查"""
        issues = []
        score = 1.0

        # 检查函数长度
        functions = re.findall(r"def \w+\([^)]*\):[^\n]*\n((?:[ \t]+[^\n]*\n)*)", code)
        for func in functions:
            func_lines = len(func.strip().split("\n"))
            if func_lines > 50:
                issues.append("存在超过50行的函数")
                score -= 0.2
                break

        # 检查嵌套深度
        max_indent = 0
        for line in code.split("\n"):
            if line.strip():
                indent = len(line) - len(line.lstrip())
                spaces_per_indent = 4
                depth = indent // spaces_per_indent
                max_indent = max(max_indent, depth)

        if max_indent > 5:
            issues.append(f"代码嵌套过深（{max_indent}层）")
            score -= 0.2

        return max(0, score), issues

    def _check_documentation(self, code: str) -> Tuple[float, List[str]]:
        """文档检查"""
        issues = []

        # 统计函数和类
        func_count = len(re.findall(r"def \w+\(", code))
        class_count = len(re.findall(r"class \w+", code))

        # 统计文档字符串
        docstring_count = len(re.findall(r'"""[^"]*"""', code)) + len(
            re.findall(r"'''[^']*'''", code)
        )

        total = func_count + class_count
        if total == 0:
            return 1.0, []

        coverage = docstring_count / total if total > 0 else 0

        if coverage < 0.5:
            issues.append(f"文档覆盖率低（{coverage:.0%}）")

        return min(1.0, coverage), issues

    def _score_to_level(self, score: float) -> QualityLevel:
        """分数转等级"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "acceptable"
        elif score >= 0.3:
            return "needs_improvement"
        else:
            return "poor"

    def get_requirements(self) -> List[str]:
        """返回检查项列表"""
        return [
            "代码非空",
            "语法正确",
            "无过多调试代码",
            "无硬编码路径",
            "行长度<=120",
            "缩进一致",
            "函数长度<=50行",
            "嵌套深度<=5",
            "有文档字符串",
        ]


# ================== 论文质量闸门 ==================


class PaperQualityGate:
    """论文质量闸门"""

    id = "paper_quality"
    name = "论文质量检查"

    # 必需章节
    REQUIRED_SECTIONS = [
        "摘要",
        "问题重述",
        "问题分析",
        "模型假设",
        "符号说明",
        "模型建立",
        "模型求解",
        "结果分析",
        "模型检验",
        "模型评价",
        "参考文献",
    ]

    def __init__(self, config: Optional[GateConfig] = None):
        self.config = config or GateConfig()

    def check(self, bundle: Dict[str, Any]) -> GateResult:
        """
        检查论文质量

        Args:
            bundle: {
                "content": str,  # 论文内容
                "figures": List[str],  # 图片列表
                "tables": List[str]  # 表格列表
            }

        Returns:
            检查结果
        """
        content = bundle.get("content", "")
        figures = bundle.get("figures", [])
        tables = bundle.get("tables", [])

        issues: List[str] = []
        suggestions: List[str] = []
        details: Dict[str, Any] = {}

        # 1. 结构完整性检查
        structure_score, structure_issues = self._check_structure(content)
        issues.extend(structure_issues)
        details["structure_score"] = structure_score

        # 2. 摘要质量检查
        abstract_score, abstract_issues = self._check_abstract(content)
        issues.extend(abstract_issues)
        details["abstract_score"] = abstract_score

        # 3. 图表引用检查
        ref_score, ref_issues = self._check_figure_table_refs(content, figures, tables)
        issues.extend(ref_issues)
        details["reference_score"] = ref_score

        # 4. 公式规范性检查
        formula_score, formula_issues = self._check_formulas(content)
        issues.extend(formula_issues)
        details["formula_score"] = formula_score

        # 5. 字数检查
        word_score, word_issues = self._check_word_count(content)
        issues.extend(word_issues)
        details["word_count_score"] = word_score

        # 计算总分
        weights = {
            "structure": 0.3,
            "abstract": 0.2,
            "reference": 0.2,
            "formula": 0.15,
            "word_count": 0.15,
        }

        total_score = (
            structure_score * weights["structure"]
            + abstract_score * weights["abstract"]
            + ref_score * weights["reference"]
            + formula_score * weights["formula"]
            + word_score * weights["word_count"]
        )

        level = self._score_to_level(total_score)
        passed = total_score >= self.config.min_pass_score

        # 生成建议
        if structure_score < 0.7:
            suggestions.append("补充缺失的必需章节")
        if abstract_score < 0.7:
            suggestions.append("改进摘要，确保包含具体结果和数值")
        if ref_score < 0.8:
            suggestions.append("检查图表编号和引用的一致性")

        return GateResult(
            gate_id=self.id,
            passed=passed,
            score=total_score,
            level=level,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )

    def _check_structure(self, content: str) -> Tuple[float, List[str]]:
        """检查论文结构"""
        issues = []
        found_sections = []

        for section in self.REQUIRED_SECTIONS:
            patterns = [
                f"#{1, 3}\\s*{section}",
                f"\\\\section{{.*{section}.*}}",
                f"^{section}$",
            ]

            found = any(
                re.search(p, content, re.MULTILINE | re.IGNORECASE) for p in patterns
            )

            if found:
                found_sections.append(section)
            else:
                issues.append(f"缺少章节: {section}")

        coverage = len(found_sections) / len(self.REQUIRED_SECTIONS)

        return coverage, issues

    def _check_abstract(self, content: str) -> Tuple[float, List[str]]:
        """检查摘要质量"""
        issues = []
        score = 1.0

        # 提取摘要
        abstract_match = re.search(
            r"摘要[：:]\s*(.+?)(?=关键词|#|\\section)", content, re.DOTALL
        )

        if not abstract_match:
            abstract_match = re.search(
                r"^#\s*摘要\n(.+?)(?=^#)", content, re.MULTILINE | re.DOTALL
            )

        if not abstract_match:
            return 0.5, ["未找到摘要部分"]

        abstract = abstract_match.group(1).strip()

        # 检查字数
        if len(abstract) < 300:
            issues.append("摘要过短（少于300字）")
            score -= 0.2
        elif len(abstract) > 800:
            issues.append("摘要过长（超过800字）")
            score -= 0.1

        # 检查是否包含数值结果
        has_numbers = bool(re.search(r"\d+\.?\d*%|\d+\.?\d*[万亿]|\d+\.\d+", abstract))
        if not has_numbers:
            issues.append("摘要缺少具体数值结果")
            score -= 0.3

        # 检查是否结果导向
        result_keywords = ["结果", "表明", "发现", "达到", "提高", "降低"]
        if not any(k in abstract for k in result_keywords):
            issues.append("摘要偏向过程描述，缺少结果导向")
            score -= 0.2

        return max(0, score), issues

    def _check_figure_table_refs(
        self,
        content: str,
        figures: List[str],
        tables: List[str],
    ) -> Tuple[float, List[str]]:
        """检查图表引用"""
        issues = []

        # 统计文中引用
        fig_refs = set(re.findall(r"图\s*(\d+)", content))
        tab_refs = set(re.findall(r"表\s*(\d+)", content))

        # 检查图片引用
        if figures:
            for i in range(1, len(figures) + 1):
                if str(i) not in fig_refs:
                    issues.append(f"图{i}未在文中引用")

        # 检查表格引用
        if tables:
            for i in range(1, len(tables) + 1):
                if str(i) not in tab_refs:
                    issues.append(f"表{i}未在文中引用")

        total = len(figures) + len(tables)
        if total == 0:
            return 1.0, []

        missing = len(issues)
        score = 1 - (missing / total) if total > 0 else 1.0

        return max(0, score), issues

    def _check_formulas(self, content: str) -> Tuple[float, List[str]]:
        """检查公式规范性"""
        issues = []
        score = 1.0

        # 检查是否有公式
        inline_formulas = re.findall(r"\$[^$]+\$", content)
        block_formulas = re.findall(r"\$\$[^$]+\$\$", content)
        latex_formulas = re.findall(r"\\begin\{equation\}", content)

        total_formulas = (
            len(inline_formulas) + len(block_formulas) + len(latex_formulas)
        )

        if total_formulas < 5:
            issues.append("公式数量较少，建议增加数学表达")
            score -= 0.2

        # 检查公式是否有编号
        numbered = len(latex_formulas) + len(re.findall(r"\\\[", content))
        if total_formulas > 10 and numbered < total_formulas * 0.5:
            issues.append("部分重要公式缺少编号")
            score -= 0.1

        return max(0, score), issues

    def _check_word_count(self, content: str) -> Tuple[float, List[str]]:
        """检查字数"""
        issues = []

        # 移除代码块和公式
        cleaned = re.sub(r"```[^`]+```", "", content)
        cleaned = re.sub(r"\$[^$]+\$", "", cleaned)

        word_count = len(cleaned)

        if word_count < 8000:
            issues.append(f"论文字数不足（{word_count}字，建议8000+）")
            return 0.5, issues
        elif word_count < 15000:
            return 0.8, []
        elif word_count > 30000:
            issues.append(f"论文字数过多（{word_count}字）")
            return 0.9, issues

        return 1.0, []

    def _score_to_level(self, score: float) -> QualityLevel:
        """分数转等级"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "acceptable"
        elif score >= 0.3:
            return "needs_improvement"
        else:
            return "poor"

    def get_requirements(self) -> List[str]:
        """返回检查项列表"""
        return [
            "包含所有必需章节",
            "摘要300-800字",
            "摘要包含具体数值",
            "图表正确引用",
            "公式规范编号",
            "论文字数8000+",
        ]


# ================== 可复现性闸门 ==================


class ReproducibilityGate:
    """可复现性闸门"""

    id = "reproducibility"
    name = "可复现性检查"

    def __init__(self, config: Optional[GateConfig] = None):
        self.config = config or GateConfig()

    def check(self, bundle: Dict[str, Any]) -> GateResult:
        """
        检查可复现性

        Args:
            bundle: {
                "code_path": str,  # 代码目录
                "data_path": str,  # 数据目录
                "has_requirements": bool,  # 是否有依赖文件
                "has_readme": bool,  # 是否有说明文件
                "random_seeds": Dict[str, int]  # 随机种子
            }

        Returns:
            检查结果
        """
        issues: List[str] = []
        suggestions: List[str] = []
        details: Dict[str, Any] = {}

        # 1. 检查依赖文件
        has_requirements = bundle.get("has_requirements", False)
        if not has_requirements:
            issues.append("缺少依赖文件(requirements.txt)")
            suggestions.append("生成 requirements.txt 文件")
        details["has_requirements"] = has_requirements

        # 2. 检查说明文件
        has_readme = bundle.get("has_readme", False)
        if not has_readme:
            issues.append("缺少使用说明(README)")
            suggestions.append("创建 README 文件说明如何运行代码")
        details["has_readme"] = has_readme

        # 3. 检查随机种子
        random_seeds = bundle.get("random_seeds", {})
        if not random_seeds:
            issues.append("未设置随机种子")
            suggestions.append("在代码开头设置随机种子以确保可复现")
        details["random_seeds"] = random_seeds

        # 4. 检查数据可用性
        data_path = bundle.get("data_path", "")
        if data_path:
            data_exists = Path(data_path).exists() if data_path else False
            if not data_exists:
                issues.append("数据文件不存在或路径错误")
        details["data_available"] = bool(data_path)

        # 计算分数
        checks = [has_requirements, has_readme, bool(random_seeds), bool(data_path)]
        score = sum(checks) / len(checks)

        level = self._score_to_level(score)
        passed = score >= self.config.min_pass_score

        return GateResult(
            gate_id=self.id,
            passed=passed,
            score=score,
            level=level,
            issues=issues,
            suggestions=suggestions,
            details=details,
        )

    def _score_to_level(self, score: float) -> QualityLevel:
        """分数转等级"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "acceptable"
        else:
            return "needs_improvement"

    def get_requirements(self) -> List[str]:
        """返回检查项列表"""
        return [
            "requirements.txt 存在",
            "README 文件存在",
            "设置随机种子",
            "数据文件可访问",
        ]


# ================== 综合质量检查器 ==================


class QualityChecker:
    """综合质量检查器"""

    def __init__(self, config: Optional[GateConfig] = None):
        self.config = config or GateConfig()
        self.gates: Dict[str, Any] = {
            "code": CodeQualityGate(self.config),
            "paper": PaperQualityGate(self.config),
            "reproducibility": ReproducibilityGate(self.config),
        }

    def check_code(self, code: str, language: str = "python") -> GateResult:
        """检查代码质量"""
        return self.gates["code"].check({"code": code, "language": language})

    def check_paper(
        self,
        content: str,
        figures: Optional[List[str]] = None,
        tables: Optional[List[str]] = None,
    ) -> GateResult:
        """检查论文质量"""
        return self.gates["paper"].check(
            {
                "content": content,
                "figures": figures or [],
                "tables": tables or [],
            }
        )

    def check_reproducibility(
        self,
        code_path: str,
        data_path: str = "",
        has_requirements: bool = False,
        has_readme: bool = False,
        random_seeds: Optional[Dict[str, int]] = None,
    ) -> GateResult:
        """检查可复现性"""
        return self.gates["reproducibility"].check(
            {
                "code_path": code_path,
                "data_path": data_path,
                "has_requirements": has_requirements,
                "has_readme": has_readme,
                "random_seeds": random_seeds or {},
            }
        )

    def run_all_checks(
        self,
        code: str,
        paper_content: str,
        code_path: str = "",
    ) -> Dict[str, GateResult]:
        """运行所有检查"""
        results = {}

        results["code"] = self.check_code(code)
        results["paper"] = self.check_paper(paper_content)
        results["reproducibility"] = self.check_reproducibility(code_path)

        return results

    def get_overall_score(self, results: Dict[str, GateResult]) -> float:
        """计算综合分数"""
        weights = {"code": 0.3, "paper": 0.5, "reproducibility": 0.2}

        total = 0
        for gate_id, result in results.items():
            weight = weights.get(gate_id, 0)
            total += result.score * weight

        return total

    def format_report(self, results: Dict[str, GateResult]) -> str:
        """格式化报告"""
        lines = ["# 质量检查报告\n"]

        overall_score = self.get_overall_score(results)
        lines.append(f"**综合评分**: {overall_score:.1%}\n")

        for gate_id, result in results.items():
            gate_name = {
                "code": "代码质量",
                "paper": "论文质量",
                "reproducibility": "可复现性",
            }.get(gate_id, gate_id)

            status = "✅ 通过" if result.passed else "❌ 未通过"
            lines.append(f"\n## {gate_name} {status}")
            lines.append(f"- 评分: {result.score:.1%}")
            lines.append(f"- 等级: {result.level}")

            if result.issues:
                lines.append("\n**问题**:")
                for issue in result.issues:
                    lines.append(f"- {issue}")

            if result.suggestions:
                lines.append("\n**建议**:")
                for suggestion in result.suggestions:
                    lines.append(f"- {suggestion}")

        return "\n".join(lines)


# 便捷函数
def check_code_quality(code: str) -> GateResult:
    """便捷函数：检查代码质量"""
    checker = QualityChecker()
    return checker.check_code(code)


def check_paper_quality(content: str) -> GateResult:
    """便捷函数：检查论文质量"""
    checker = QualityChecker()
    return checker.check_paper(content)
