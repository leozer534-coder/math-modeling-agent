"""
Benchmark 评测框架 - Paper Benchmark System
==========================================

数学建模论文的综合质量评测系统

功能：
1. 多维度论文质量评测
2. 标准化评分体系
3. 评测报告生成
4. 改进建议输出
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.log_util import logger


try:
    from app.core.evaluation.metrics import (
        BenchmarkMetrics,  # noqa: F401
        CodeMetrics,
        InnovationMetrics,
        MetricCategory,  # noqa: F401
        MetricResult,
        ModelMetrics,
        PaperMetrics,
    )
except ImportError:
    # 防止循环导入
    pass


class QualityGrade(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"      # 90-100: 优秀，获奖水平
    GOOD = "good"               # 80-89: 良好，省奖水平
    ACCEPTABLE = "acceptable"   # 70-79: 合格，提交水平
    NEEDS_WORK = "needs_work"   # 60-69: 需要改进
    POOR = "poor"               # <60: 不合格


@dataclass
class BenchmarkResult:
    """评测结果"""
    benchmark_id: str
    task_id: str
    overall_score: float  # 0-100
    grade: QualityGrade
    dimension_scores: Dict[str, float]  # 各维度得分
    metric_results: List[MetricResult]  # 详细指标结果
    suggestions: List[str]  # 改进建议
    strengths: List[str]  # 优点
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "task_id": self.task_id,
            "overall_score": self.overall_score,
            "grade": self.grade.value,
            "dimension_scores": self.dimension_scores,
            "suggestions": self.suggestions,
            "strengths": self.strengths,
            "evaluated_at": self.evaluated_at,
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        grade_emoji = {
            QualityGrade.EXCELLENT: "🏆",
            QualityGrade.GOOD: "🥈", 
            QualityGrade.ACCEPTABLE: "✅",
            QualityGrade.NEEDS_WORK: "⚠️",
            QualityGrade.POOR: "❌",
        }
        
        lines = [
            "# 论文质量评测报告",
            "",
            f"**评测ID**: {self.benchmark_id}",
            f"**评测时间**: {self.evaluated_at}",
            "",
            "## 总体评分",
            "",
            f"**{grade_emoji.get(self.grade, '')} {self.overall_score:.1f}/100 分 ({self.grade.value})**",
            "",
            "## 各维度得分",
            "",
            "| 维度 | 得分 |",
            "|------|------|",
        ]
        
        for dim, score in self.dimension_scores.items():
            bar = "█" * int(score // 10) + "░" * (10 - int(score // 10))
            lines.append(f"| {dim} | {bar} {score:.0f} |")
        
        if self.strengths:
            lines.extend([
                "",
                "## ✨ 优点",
                "",
            ])
            for s in self.strengths:
                lines.append(f"- {s}")
        
        if self.suggestions:
            lines.extend([
                "",
                "## 💡 改进建议",
                "",
            ])
            for s in self.suggestions:
                lines.append(f"- {s}")
        
        return "\n".join(lines)


@dataclass
class PaperBundle:
    """论文数据包"""
    task_id: str
    problem_type: str = "optimization"
    problem_description: str = ""
    
    # 论文内容
    paper_content: str = ""
    abstract: str = ""
    
    # 模型信息
    selected_models: List[str] = field(default_factory=list)
    model_improvements: List[str] = field(default_factory=list)
    formulas: List[str] = field(default_factory=list)
    derivation_steps: int = 0
    
    # 代码信息
    code: str = ""
    execution_success: bool = False
    output_valid: bool = False
    
    # 图表信息
    figure_count: int = 0
    table_count: int = 0


class PaperBenchmark:
    """
    论文综合评测器
    
    评分维度（总计100分）：
    1. 模型选择合理性 (20分)
    2. 数学推导严谨性 (20分)
    3. 代码实现正确性 (20分)
    4. 论文写作质量 (25分)
    5. 创新性与亮点 (15分)
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else None
        self._history: List[BenchmarkResult] = []
    
    def evaluate(self, bundle: PaperBundle) -> BenchmarkResult:
        """
        对论文进行综合评测
        
        Args:
            bundle: 论文数据包
            
        Returns:
            评测结果
        """
        logger.info("开始评测任务 %s", bundle.task_id)
        
        metric_results: List[MetricResult] = []
        
        # 1. 模型选择评测
        model_selection = ModelMetrics.evaluate_model_selection(
            problem_type=bundle.problem_type,
            selected_models=bundle.selected_models,
            problem_description=bundle.problem_description
        )
        metric_results.append(model_selection)
        
        # 2. 数学推导评测
        math_rigor = ModelMetrics.evaluate_math_rigor(
            formulas=bundle.formulas,
            derivation_steps=bundle.derivation_steps
        )
        metric_results.append(math_rigor)
        
        # 3. 代码正确性评测
        code_correctness = CodeMetrics.evaluate_correctness(
            code=bundle.code,
            execution_success=bundle.execution_success,
            output_valid=bundle.output_valid
        )
        metric_results.append(code_correctness)
        
        # 4. 论文写作质量（结构 + 摘要 + 图表）
        structure = PaperMetrics.evaluate_structure(bundle.paper_content)
        abstract_quality = PaperMetrics.evaluate_abstract(bundle.abstract)
        figures = PaperMetrics.evaluate_figures_tables(
            bundle.figure_count,
            bundle.table_count,
            bundle.paper_content
        )
        
        # 合并论文写作分数
        paper_score = (
            structure.score * 0.4 +
            abstract_quality.score * 0.35 +
            figures.score * 0.25
        )
        paper_result = MetricResult(
            metric_name="论文写作质量",
            score=paper_score,
            weight=0.25,
            details=f"{structure.details}; {abstract_quality.details}; {figures.details}",
            suggestions=structure.suggestions + abstract_quality.suggestions + figures.suggestions
        )
        metric_results.append(paper_result)
        
        # 5. 创新性评测
        innovation = InnovationMetrics.evaluate_innovation(
            content=bundle.paper_content,
            model_improvements=bundle.model_improvements
        )
        metric_results.append(innovation)
        
        # 计算总分
        overall_score = sum(r.score * r.weight for r in metric_results)
        
        # 各维度得分
        dimension_scores = {
            "模型选择": model_selection.score,
            "数学推导": math_rigor.score,
            "代码实现": code_correctness.score,
            "论文写作": paper_score,
            "创新性": innovation.score,
        }
        
        # 确定等级
        grade = self._score_to_grade(overall_score)
        
        # 收集建议和优点
        suggestions = []
        strengths = []
        
        for result in metric_results:
            suggestions.extend(result.suggestions)
            if result.score >= 80:
                strengths.append(f"{result.metric_name}表现优秀")
        
        # 限制数量
        suggestions = suggestions[:5]
        strengths = strengths[:3]
        
        # 创建结果
        benchmark_result = BenchmarkResult(
            benchmark_id=f"bench_{uuid.uuid4().hex[:8]}",
            task_id=bundle.task_id,
            overall_score=overall_score,
            grade=grade,
            dimension_scores=dimension_scores,
            metric_results=metric_results,
            suggestions=suggestions,
            strengths=strengths,
        )
        
        # 保存结果
        self._history.append(benchmark_result)
        if self.output_dir:
            self._save_result(benchmark_result)
        
        logger.info("评测完成: %.1f分 (%s)", overall_score, grade.value)
        
        return benchmark_result
    
    def _score_to_grade(self, score: float) -> QualityGrade:
        """分数转等级"""
        if score >= 90:
            return QualityGrade.EXCELLENT
        elif score >= 80:
            return QualityGrade.GOOD
        elif score >= 70:
            return QualityGrade.ACCEPTABLE
        elif score >= 60:
            return QualityGrade.NEEDS_WORK
        else:
            return QualityGrade.POOR
    
    def _save_result(self, result: BenchmarkResult) -> None:
        """保存评测结果"""
        if not self.output_dir:
            return
            
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 JSON
        json_path = self.output_dir / f"{result.benchmark_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 保存 Markdown
        md_path = self.output_dir / f"{result.benchmark_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result.to_markdown())
    
    def get_history(self) -> List[BenchmarkResult]:
        """获取评测历史"""
        return self._history
    
    def compare_results(
        self, 
        result_a: BenchmarkResult, 
        result_b: BenchmarkResult
    ) -> Dict[str, Any]:
        """比较两次评测结果"""
        diff = {}
        
        for dim in result_a.dimension_scores:
            score_a = result_a.dimension_scores.get(dim, 0)
            score_b = result_b.dimension_scores.get(dim, 0)
            diff[dim] = {
                "before": score_a,
                "after": score_b,
                "change": score_b - score_a,
            }
        
        return {
            "overall_change": result_b.overall_score - result_a.overall_score,
            "grade_change": f"{result_a.grade.value} -> {result_b.grade.value}",
            "dimension_changes": diff,
        }


# 便捷函数
def create_benchmark(output_dir: Optional[str] = None) -> PaperBenchmark:
    """创建评测器实例"""
    return PaperBenchmark(output_dir)


def quick_evaluate(
    task_id: str,
    paper_content: str,
    code: str = "",
    **kwargs
) -> BenchmarkResult:
    """
    快速评测
    
    Args:
        task_id: 任务ID
        paper_content: 论文内容
        code: 代码内容
        **kwargs: 其他参数
        
    Returns:
        评测结果
    """
    benchmark = PaperBenchmark()
    
    bundle = PaperBundle(
        task_id=task_id,
        paper_content=paper_content,
        code=code,
        **kwargs
    )
    
    return benchmark.evaluate(bundle)
