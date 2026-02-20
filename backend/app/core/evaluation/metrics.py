"""
评测指标模块 - Evaluation Metrics
================================

提供数学建模论文的细粒度评测指标

指标类别：
1. 模型评测指标
2. 论文评测指标
3. 代码评测指标
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List


class MetricCategory(str, Enum):
    """指标类别"""
    MODEL = "model"
    PAPER = "paper"
    CODE = "code"
    INNOVATION = "innovation"


@dataclass
class MetricResult:
    """单个指标评测结果"""
    metric_name: str
    score: float  # 0-100
    weight: float  # 权重
    details: str = ""
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class MetricConfig:
    """指标配置"""
    name: str
    category: MetricCategory
    weight: float
    description: str
    evaluator: Callable[[Any], float]
    min_pass_score: float = 60.0


# ================== 模型评测指标 ==================

class ModelMetrics:
    """模型选择与实现评测"""
    
    @staticmethod
    def evaluate_model_selection(
        problem_type: str,
        selected_models: List[str],
        problem_description: str
    ) -> MetricResult:
        """
        评测模型选择合理性
        
        评分标准：
        - 模型与问题类型匹配度
        - 是否有多模型对比
        - 模型复杂度是否合适
        """
        score = 60.0
        suggestions = []
        
        # 检查是否选择了多个模型进行对比
        if len(selected_models) >= 2:
            score += 15
        elif len(selected_models) == 1:
            suggestions.append("建议增加对比模型以增强说服力")
        
        # 检查模型与问题类型的匹配
        type_model_mapping = {
            "optimization": ["线性规划", "整数规划", "动态规划", "遗传算法"],
            "prediction": ["回归", "时间序列", "ARIMA", "LSTM", "神经网络"],
            "classification": ["分类", "决策树", "随机森林", "SVM", "聚类"],
            "evaluation": ["层次分析", "TOPSIS", "熵权法", "模糊评价"],
            "graph": ["最短路径", "网络流", "Dijkstra", "图论"],
        }
        
        expected_keywords = type_model_mapping.get(problem_type, [])
        matched = 0
        for model in selected_models:
            for kw in expected_keywords:
                if kw.lower() in model.lower():
                    matched += 1
                    break
        
        if matched > 0:
            score += min(15, matched * 5)
        else:
            suggestions.append(f"建议考虑使用更适合{problem_type}类问题的模型")
        
        # 检查是否有创新模型
        innovative_keywords = ["改进", "优化", "混合", "融合", "增强"]
        for model in selected_models:
            if any(kw in model for kw in innovative_keywords):
                score += 10
                break
        
        return MetricResult(
            metric_name="模型选择合理性",
            score=min(100, score),
            weight=0.20,
            details=f"选用了 {len(selected_models)} 个模型",
            suggestions=suggestions
        )
    
    @staticmethod
    def evaluate_math_rigor(
        formulas: List[str],
        derivation_steps: int
    ) -> MetricResult:
        """
        评测数学推导严谨性
        
        评分标准：
        - 公式数量是否充足
        - 推导步骤完整性
        - 符号使用规范性
        """
        score = 50.0
        suggestions = []
        
        # 公式数量评分
        if len(formulas) >= 10:
            score += 20
        elif len(formulas) >= 5:
            score += 10
        else:
            suggestions.append("建议增加更多数学公式以增强论文专业性")
        
        # 推导步骤评分
        if derivation_steps >= 5:
            score += 20
        elif derivation_steps >= 3:
            score += 10
        else:
            suggestions.append("建议展示完整的推导过程")
        
        # 检查公式规范性（LaTeX 格式）
        latex_count = sum(1 for f in formulas if "$" in f or "\\" in f)
        if latex_count >= len(formulas) * 0.8:
            score += 10
        
        return MetricResult(
            metric_name="数学推导严谨性",
            score=min(100, score),
            weight=0.20,
            details=f"包含 {len(formulas)} 个公式，{derivation_steps} 步推导",
            suggestions=suggestions
        )


# ================== 论文评测指标 ==================

class PaperMetrics:
    """论文写作质量评测"""
    
    REQUIRED_SECTIONS = [
        "摘要", "问题重述", "问题分析", "模型假设", 
        "符号说明", "模型建立", "模型求解", 
        "结果分析", "模型评价", "参考文献"
    ]
    
    @staticmethod
    def evaluate_structure(content: str) -> MetricResult:
        """
        评测论文结构完整性
        """
        score = 0.0
        found_sections = []
        missing_sections = []
        
        for section in PaperMetrics.REQUIRED_SECTIONS:
            if section in content:
                found_sections.append(section)
                score += 10
            else:
                missing_sections.append(section)
        
        suggestions = []
        if missing_sections:
            suggestions.append(f"缺少以下章节：{', '.join(missing_sections[:3])}")
        
        return MetricResult(
            metric_name="论文结构完整性",
            score=min(100, score),
            weight=0.10,
            details=f"包含 {len(found_sections)}/{len(PaperMetrics.REQUIRED_SECTIONS)} 个必要章节",
            suggestions=suggestions
        )
    
    @staticmethod
    def evaluate_abstract(abstract: str) -> MetricResult:
        """
        评测摘要质量
        
        评分标准：
        - 长度适中 (300-500字)
        - 包含关键要素（问题、方法、结果、结论）
        """
        score = 50.0
        suggestions = []
        
        # 长度检查
        length = len(abstract)
        if 300 <= length <= 500:
            score += 20
        elif 200 <= length <= 600:
            score += 10
        else:
            suggestions.append("摘要长度建议控制在300-500字")
        
        # 关键要素检查
        key_elements = {
            "问题": ["问题", "研究", "针对", "本文"],
            "方法": ["模型", "方法", "算法", "采用", "建立"],
            "结果": ["结果", "得到", "求解", "计算"],
            "结论": ["结论", "表明", "证明", "有效"],
        }
        
        found_elements = 0
        for element, keywords in key_elements.items():
            if any(kw in abstract for kw in keywords):
                found_elements += 1
                score += 5
        
        if found_elements < 4:
            suggestions.append("摘要应包含问题、方法、结果、结论四要素")
        
        return MetricResult(
            metric_name="摘要质量",
            score=min(100, score),
            weight=0.08,
            details=f"摘要长度 {length} 字，包含 {found_elements}/4 个关键要素",
            suggestions=suggestions
        )
    
    @staticmethod
    def evaluate_figures_tables(
        figure_count: int,
        table_count: int,
        content: str
    ) -> MetricResult:
        """
        评测图表质量
        """
        score = 50.0
        suggestions = []
        
        # 数量评分
        total = figure_count + table_count
        if total >= 8:
            score += 25
        elif total >= 5:
            score += 15
        elif total >= 3:
            score += 10
        else:
            suggestions.append("建议增加图表以增强论文可读性")
        
        # 检查图表引用
        fig_refs = len(re.findall(r"图\s*\d+|Figure\s*\d+", content, re.I))
        table_refs = len(re.findall(r"表\s*\d+|Table\s*\d+", content, re.I))
        
        if fig_refs >= figure_count * 0.8:
            score += 15
        else:
            suggestions.append("确保所有图片都在正文中被引用")
            
        if table_refs >= table_count * 0.8:
            score += 10
        
        return MetricResult(
            metric_name="图表质量",
            score=min(100, score),
            weight=0.07,
            details=f"包含 {figure_count} 张图、{table_count} 个表",
            suggestions=suggestions
        )


# ================== 代码评测指标 ==================

class CodeMetrics:
    """代码质量评测"""
    
    @staticmethod
    def evaluate_correctness(
        code: str,
        execution_success: bool,
        output_valid: bool
    ) -> MetricResult:
        """
        评测代码正确性
        """
        score = 0.0
        suggestions = []
        
        # 语法正确性
        try:
            ast.parse(code)
            score += 30
        except SyntaxError:
            suggestions.append("代码存在语法错误")
            return MetricResult(
                metric_name="代码正确性",
                score=0,
                weight=0.20,
                details="代码语法错误",
                suggestions=suggestions
            )
        
        # 执行成功
        if execution_success:
            score += 40
        else:
            suggestions.append("代码执行失败，请检查依赖和逻辑")
        
        # 输出有效
        if output_valid:
            score += 30
        else:
            suggestions.append("代码输出结果不符合预期")
        
        return MetricResult(
            metric_name="代码正确性",
            score=score,
            weight=0.20,
            details=f"执行{'成功' if execution_success else '失败'}",
            suggestions=suggestions
        )
    
    @staticmethod
    def evaluate_code_quality(code: str) -> MetricResult:
        """
        评测代码质量（注释、规范性）
        """
        score = 50.0
        suggestions = []
        
        lines = code.split("\n")
        total_lines = len([line for line in lines if line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith("#")])
        docstring_count = code.count('"""') // 2 + code.count("'''") // 2
        
        # 注释比例
        comment_ratio = comment_lines / max(total_lines, 1)
        if comment_ratio >= 0.15:
            score += 20
        elif comment_ratio >= 0.08:
            score += 10
        else:
            suggestions.append("建议增加代码注释")
        
        # docstring
        if docstring_count >= 3:
            score += 15
        elif docstring_count >= 1:
            score += 8
        
        # 函数定义
        function_count = len(re.findall(r"def \w+\(", code))
        if function_count >= 3:
            score += 15
        elif function_count >= 1:
            score += 8
        else:
            suggestions.append("建议将重复逻辑封装为函数")
        
        return MetricResult(
            metric_name="代码质量",
            score=min(100, score),
            weight=0.05,
            details=f"{total_lines} 行代码，{comment_lines} 行注释，{function_count} 个函数",
            suggestions=suggestions
        )


# ================== 创新性评测 ==================

class InnovationMetrics:
    """创新性与亮点评测"""
    
    @staticmethod
    def evaluate_innovation(
        content: str,
        model_improvements: List[str]
    ) -> MetricResult:
        """
        评测创新性
        """
        score = 40.0
        suggestions = []
        
        # 检查创新关键词
        innovation_keywords = [
            "改进", "优化", "创新", "提出", "首次",
            "novel", "improved", "enhanced", "proposed"
        ]
        
        found_keywords = 0
        for kw in innovation_keywords:
            if kw.lower() in content.lower():
                found_keywords += 1
        
        score += min(20, found_keywords * 4)
        
        # 模型改进
        if model_improvements:
            score += min(25, len(model_improvements) * 8)
        else:
            suggestions.append("建议在基础模型上做适当改进和创新")
        
        # 敏感性分析
        if "敏感性" in content or "灵敏度" in content:
            score += 15
        else:
            suggestions.append("建议增加敏感性分析")
        
        return MetricResult(
            metric_name="创新性与亮点",
            score=min(100, score),
            weight=0.15,
            details=f"检测到 {found_keywords} 个创新相关关键词",
            suggestions=suggestions
        )


# ================== 综合评测 ==================

class BenchmarkMetrics:
    """综合评测指标管理器"""
    
    def __init__(self):
        self.model_metrics = ModelMetrics()
        self.paper_metrics = PaperMetrics()
        self.code_metrics = CodeMetrics()
        self.innovation_metrics = InnovationMetrics()
    
    def get_all_metrics(self) -> List[MetricConfig]:
        """获取所有指标配置"""
        return [
            MetricConfig(
                name="模型选择合理性",
                category=MetricCategory.MODEL,
                weight=0.20,
                description="评估模型与问题类型的匹配度",
                evaluator=ModelMetrics.evaluate_model_selection,
            ),
            MetricConfig(
                name="数学推导严谨性",
                category=MetricCategory.MODEL,
                weight=0.20,
                description="评估公式推导的完整性和规范性",
                evaluator=ModelMetrics.evaluate_math_rigor,
            ),
            MetricConfig(
                name="代码正确性",
                category=MetricCategory.CODE,
                weight=0.20,
                description="评估代码的语法正确性和执行结果",
                evaluator=CodeMetrics.evaluate_correctness,
            ),
            MetricConfig(
                name="论文写作质量",
                category=MetricCategory.PAPER,
                weight=0.25,
                description="评估论文结构、摘要、图表等",
                evaluator=lambda c: PaperMetrics.evaluate_structure(c),
            ),
            MetricConfig(
                name="创新性与亮点",
                category=MetricCategory.INNOVATION,
                weight=0.15,
                description="评估模型改进和创新点",
                evaluator=InnovationMetrics.evaluate_innovation,
            ),
        ]
