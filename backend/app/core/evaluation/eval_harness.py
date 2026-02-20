"""
Eval Harness - 评测框架
========================

功能：
1. 3-5套题目回归测试集
2. 自动化评测脚本
3. 质量指标追踪
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.schemas.contracts import QualityLevel
from app.utils.log_util import logger


@dataclass
class TestProblem:
    problem_id: str
    title: str
    description: str
    category: str
    difficulty: str
    expected_outputs: Dict[str, Any]
    data_files: List[str] = field(default_factory=list)
    time_limit_minutes: int = 60
    reference_solution: Optional[str] = None


@dataclass
class EvalMetric:
    name: str
    weight: float
    evaluator: Callable[[Any, Any], float]
    threshold: float = 0.6


@dataclass
class EvalResult:
    problem_id: str
    run_id: str
    scores: Dict[str, float]
    overall_score: float
    quality_level: QualityLevel
    duration_seconds: float
    issues: List[str] = field(default_factory=list)
    passed: bool = True
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RegressionReport:
    report_id: str
    run_id: str
    results: List[EvalResult]
    summary: Dict[str, Any]
    comparison_with_baseline: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class EvalHarness:
    def __init__(
        self,
        test_problems: Optional[List[TestProblem]] = None,
        metrics: Optional[List[EvalMetric]] = None,
    ):
        self.test_problems = test_problems or self._load_default_problems()
        self.metrics = metrics or self._get_default_metrics()
        self._results_history: List[RegressionReport] = []

    def _load_default_problems(self) -> List[TestProblem]:
        return [
            TestProblem(
                problem_id="test_optimization_01",
                title="资源分配优化",
                description="在有限资源下最大化产出的线性规划问题",
                category="optimization",
                difficulty="easy",
                expected_outputs={
                    "optimal_value_range": [1000, 1500],
                    "constraint_satisfied": True,
                },
            ),
            TestProblem(
                problem_id="test_prediction_01",
                title="销量预测",
                description="基于历史数据预测未来销量的时间序列问题",
                category="prediction",
                difficulty="medium",
                expected_outputs={"mape_threshold": 0.15, "r2_threshold": 0.8},
            ),
            TestProblem(
                problem_id="test_evaluation_01",
                title="方案综合评价",
                description="多指标综合评价与排序问题",
                category="evaluation",
                difficulty="easy",
                expected_outputs={"ranking_stability": True, "weight_sum": 1.0},
            ),
            TestProblem(
                problem_id="test_classification_01",
                title="风险分类",
                description="基于特征进行风险等级分类",
                category="classification",
                difficulty="medium",
                expected_outputs={"accuracy_threshold": 0.85, "f1_threshold": 0.8},
            ),
            TestProblem(
                problem_id="test_graph_01",
                title="路径规划",
                description="在网络中寻找最优路径",
                category="graph",
                difficulty="medium",
                expected_outputs={"path_valid": True, "is_shortest": True},
            ),
        ]

    def _get_default_metrics(self) -> List[EvalMetric]:
        return [
            EvalMetric(
                name="research_quality",
                weight=0.2,
                evaluator=self._eval_research_quality,
                threshold=0.6,
            ),
            EvalMetric(
                name="model_appropriateness",
                weight=0.25,
                evaluator=self._eval_model_appropriateness,
                threshold=0.7,
            ),
            EvalMetric(
                name="code_correctness",
                weight=0.25,
                evaluator=self._eval_code_correctness,
                threshold=0.8,
            ),
            EvalMetric(
                name="paper_quality",
                weight=0.2,
                evaluator=self._eval_paper_quality,
                threshold=0.6,
            ),
            EvalMetric(
                name="reproducibility",
                weight=0.1,
                evaluator=self._eval_reproducibility,
                threshold=0.9,
            ),
        ]

    async def run_regression(
        self,
        workflow_runner: Callable[[TestProblem], Any],
        run_id: Optional[str] = None,
        problems: Optional[List[str]] = None,
    ) -> RegressionReport:
        run_id = run_id or f"reg_{uuid.uuid4().hex[:8]}"
        results: List[EvalResult] = []

        test_set = self.test_problems
        if problems:
            test_set = [p for p in self.test_problems if p.problem_id in problems]

        for problem in test_set:
            try:
                result = await self._evaluate_single_problem(
                    problem, workflow_runner, run_id
                )
                results.append(result)
            except Exception as e:
                logger.error("Evaluation failed for %s: %s", problem.problem_id, e)
                results.append(
                    EvalResult(
                        problem_id=problem.problem_id,
                        run_id=run_id,
                        scores={},
                        overall_score=0.0,
                        quality_level=QualityLevel("poor"),
                        duration_seconds=0.0,
                        issues=[str(e)],
                        passed=False,
                    )
                )

        summary = self._generate_summary(results)
        comparison = self._compare_with_baseline(results)

        report = RegressionReport(
            report_id=f"rpt_{uuid.uuid4().hex[:8]}",
            run_id=run_id,
            results=results,
            summary=summary,
            comparison_with_baseline=comparison,
        )

        self._results_history.append(report)
        return report

    async def _evaluate_single_problem(
        self,
        problem: TestProblem,
        workflow_runner: Callable[[TestProblem], Any],
        run_id: str,
    ) -> EvalResult:
        start_time = datetime.now()

        try:
            workflow_output = await asyncio.wait_for(
                asyncio.coroutine(lambda: workflow_runner(problem))()
                if not asyncio.iscoroutinefunction(workflow_runner)
                else workflow_runner(problem),
                timeout=problem.time_limit_minutes * 60,
            )
        except asyncio.TimeoutError:
            return EvalResult(
                problem_id=problem.problem_id,
                run_id=run_id,
                scores={},
                overall_score=0.0,
                quality_level=QualityLevel("poor"),
                duration_seconds=problem.time_limit_minutes * 60,
                issues=["Timeout exceeded"],
                passed=False,
            )

        duration = (datetime.now() - start_time).total_seconds()

        scores: Dict[str, float] = {}
        issues: List[str] = []

        for metric in self.metrics:
            try:
                score = metric.evaluator(workflow_output, problem.expected_outputs)
                scores[metric.name] = score
                if score < metric.threshold:
                    issues.append(
                        f"{metric.name} below threshold ({score:.2f} < {metric.threshold})"
                    )
            except Exception as e:
                scores[metric.name] = 0.0
                issues.append(f"{metric.name} evaluation failed: {e}")

        overall_score = sum(scores.get(m.name, 0) * m.weight for m in self.metrics)

        quality_level = self._score_to_quality_level(overall_score)
        passed = overall_score >= 0.6 and len(issues) <= 2

        return EvalResult(
            problem_id=problem.problem_id,
            run_id=run_id,
            scores=scores,
            overall_score=overall_score,
            quality_level=quality_level,
            duration_seconds=duration,
            issues=issues,
            passed=passed,
        )

    def _generate_summary(self, results: List[EvalResult]) -> Dict[str, Any]:
        if not results:
            return {"total": 0, "passed": 0, "failed": 0}

        passed_count = sum(1 for r in results if r.passed)
        avg_score = sum(r.overall_score for r in results) / len(results)

        category_scores: Dict[str, List[float]] = {}
        for result in results:
            problem = next(
                (p for p in self.test_problems if p.problem_id == result.problem_id),
                None,
            )
            if problem:
                if problem.category not in category_scores:
                    category_scores[problem.category] = []
                category_scores[problem.category].append(result.overall_score)

        return {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "pass_rate": passed_count / len(results),
            "average_score": avg_score,
            "category_averages": {
                cat: sum(scores) / len(scores)
                for cat, scores in category_scores.items()
            },
        }

    def _compare_with_baseline(
        self, results: List[EvalResult]
    ) -> Optional[Dict[str, Any]]:
        if not self._results_history:
            return None

        baseline = self._results_history[-1]
        baseline_scores = {r.problem_id: r.overall_score for r in baseline.results}

        improvements: List[str] = []
        regressions: List[str] = []

        for result in results:
            if result.problem_id in baseline_scores:
                diff = result.overall_score - baseline_scores[result.problem_id]
                if diff > 0.05:
                    improvements.append(result.problem_id)
                elif diff < -0.05:
                    regressions.append(result.problem_id)

        return {
            "baseline_run_id": baseline.run_id,
            "improvements": improvements,
            "regressions": regressions,
            "net_change": len(improvements) - len(regressions),
        }

    def _score_to_quality_level(self, score: float) -> QualityLevel:
        if score >= 0.9:
            return QualityLevel("excellent")
        elif score >= 0.75:
            return QualityLevel("good")
        elif score >= 0.6:
            return QualityLevel("acceptable")
        elif score >= 0.4:
            return QualityLevel("needs_improvement")
        else:
            return QualityLevel("poor")

    def _eval_research_quality(self, output: Any, expected: Dict) -> float:
        if not output:
            return 0.0
        if hasattr(output, "research_package") and output.research_package:
            return 0.8
        return 0.5

    def _eval_model_appropriateness(self, output: Any, expected: Dict) -> float:
        if not output:
            return 0.0
        if hasattr(output, "model_plan") and output.model_plan:
            return 0.8
        return 0.5

    def _eval_code_correctness(self, output: Any, expected: Dict) -> float:
        if not output:
            return 0.0
        if hasattr(output, "code_output") and output.code_output:
            if expected.get("constraint_satisfied", True):
                return 0.9
        return 0.6

    def _eval_paper_quality(self, output: Any, expected: Dict) -> float:
        if not output:
            return 0.0
        if hasattr(output, "paper") and output.paper:
            return 0.7
        return 0.4

    def _eval_reproducibility(self, output: Any, expected: Dict) -> float:
        if not output:
            return 0.0
        if hasattr(output, "run_manifest") and output.run_manifest:
            return 1.0
        return 0.5

    def get_history(self) -> List[RegressionReport]:
        return self._results_history

    def format_report(self, report: RegressionReport) -> str:
        lines = [
            f"# 评测报告 {report.report_id}",
            f"运行ID: {report.run_id}",
            f"时间: {report.created_at}",
            "",
            "## 摘要",
            f"- 总测试数: {report.summary.get('total', 0)}",
            f"- 通过: {report.summary.get('passed', 0)}",
            f"- 失败: {report.summary.get('failed', 0)}",
            f"- 通过率: {report.summary.get('pass_rate', 0):.1%}",
            f"- 平均分: {report.summary.get('average_score', 0):.2f}",
            "",
            "## 详细结果",
        ]

        for result in report.results:
            status = "✓" if result.passed else "✗"
            lines.append(
                f"- [{status}] {result.problem_id}: {result.overall_score:.2f}"
            )
            if result.issues:
                for issue in result.issues:
                    lines.append(f"    - {issue}")

        return "\n".join(lines)


eval_harness = EvalHarness()


async def run_regression_tests(
    workflow_runner: Callable[[TestProblem], Any],
    run_id: Optional[str] = None,
) -> RegressionReport:
    return await eval_harness.run_regression(workflow_runner, run_id)
