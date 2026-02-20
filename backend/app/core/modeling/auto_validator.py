"""
Auto Validator - 自动模型验证模块
=================================

功能：
1. 基线对比验证
2. 残差诊断
3. 交叉验证/回测
4. 模型评分与排序
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from app.core.knowledge_base import MathModelingKnowledgeBase
from app.schemas.contracts import QualityLevel, ValidationReport
from app.utils.log_util import logger


@dataclass
class BaselineComparison:
    """基线对比结果"""

    baseline_model: str
    target_model: str
    metrics_comparison: Dict[str, Dict[str, float]]
    statistical_tests: Dict[str, Any]
    winner: str
    confidence: float


@dataclass
class ResidualDiagnostics:
    """残差诊断结果"""

    normality_test: Dict[str, Any]
    homoscedasticity_test: Dict[str, Any]
    autocorrelation_test: Dict[str, Any]
    outlier_indices: List[int]
    diagnostics_passed: bool
    issues: List[str]


@dataclass
class CrossValidationResult:
    """交叉验证结果"""

    method: str
    n_splits: int
    scores: List[float]
    mean_score: float
    std_score: float
    fold_details: List[Dict]


class AutoValidator:
    """自动模型验证器"""

    DEFAULT_REGRESSION_METRICS = ["rmse", "mae", "r2", "mape"]
    DEFAULT_CLASSIFICATION_METRICS = ["accuracy", "precision", "recall", "f1"]

    NORMALITY_P_THRESHOLD = 0.05
    HOMOSCEDASTICITY_P_THRESHOLD = 0.05
    DURBIN_WATSON_LOWER = 1.5
    DURBIN_WATSON_UPPER = 2.5
    OUTLIER_ZSCORE_THRESHOLD = 3.0

    def __init__(self, knowledge_base: MathModelingKnowledgeBase):
        """初始化自动验证器"""
        self.knowledge_base = knowledge_base

    async def validate_model(
        self,
        model_id: str,
        X: Any,
        y: Any,
        baseline_model: Optional[str] = None,
    ) -> ValidationReport:
        """
        自动验证模型，生成标准验证报告

        Args:
            model_id: 目标模型ID
            X: 特征数据
            y: 真实标签
            baseline_model: 基线模型ID

        Returns:
            ValidationReport
        """
        issues: List[str] = []
        model = self._resolve_model(model_id)
        model_name = self._resolve_model_name(model_id)

        if model is None:
            issues.append("未找到模型实例，无法执行验证")
            return ValidationReport(
                model_id=model_id,
                model_name=model_name,
                metrics={},
                baseline_comparison={},
                sensitivity_results=[],
                residual_analysis={},
                cross_validation={},
                overall_rating="poor",
                recommendation="模型未就绪，需先加载模型",
                issues_found=issues,
            )

        X_arr = self._to_numpy(X)
        y_arr = self._to_numpy(y)
        y_pred = self._predict(model, X_arr)

        if y_pred is None:
            issues.append("模型无法生成预测结果")
            return ValidationReport(
                model_id=model_id,
                model_name=model_name,
                metrics={},
                baseline_comparison={},
                sensitivity_results=[],
                residual_analysis={},
                cross_validation={},
                overall_rating="poor",
                recommendation="预测失败，请检查模型接口",
                issues_found=issues,
            )

        problem_type = self._infer_problem_type(y_arr, y_pred)
        metrics = self._compute_metrics(
            y_arr, y_pred, self._default_metrics(problem_type)
        )

        residual_diag = self.diagnose_residuals(y_arr, y_pred)

        baseline_comparison: Dict[str, Any] = {}
        if baseline_model:
            baseline_instance = self._resolve_model(baseline_model)
            if baseline_instance is None:
                issues.append("未找到基线模型实例")
            else:
                baseline_pred = self._predict(baseline_instance, X_arr)
                if baseline_pred is None:
                    issues.append("基线模型预测失败")
                else:
                    comparison = self.compare_to_baseline(
                        target_predictions=y_pred,
                        baseline_predictions=baseline_pred,
                        y_true=y_arr,
                        metrics=list(metrics.keys()),
                    )
                    baseline_comparison = asdict(comparison)

        cross_validation: Dict[str, Any] = {}
        try:
            cv_result = self.cross_validate(model, X_arr, y_arr)
            cross_validation = asdict(cv_result)
        except Exception as exc:
            logger.warning("Cross validation failed: %s", exc)
            issues.append("交叉验证执行失败")

        overall_score = self._evaluate_report_score(metrics, residual_diag, cross_validation)
        overall_rating = self._score_to_quality(overall_score)
        recommendation = self._generate_recommendation(
            overall_rating, residual_diag, baseline_comparison
        )

        return ValidationReport(
            model_id=model_id,
            model_name=model_name,
            metrics=metrics,
            baseline_comparison=baseline_comparison,
            sensitivity_results=[],
            residual_analysis=asdict(residual_diag),
            cross_validation=cross_validation,
            overall_rating=overall_rating,
            recommendation=recommendation,
            issues_found=issues + residual_diag.issues,
        )

    def compare_to_baseline(
        self,
        target_predictions: Any,
        baseline_predictions: Any,
        y_true: Any,
        metrics: List[str],
    ) -> BaselineComparison:
        """与基线模型进行对比"""
        y_true_arr = self._to_numpy(y_true)
        target_pred = self._to_numpy(target_predictions)
        baseline_pred = self._to_numpy(baseline_predictions)

        metric_results = self._compute_metrics(y_true_arr, target_pred, metrics)
        baseline_results = self._compute_metrics(y_true_arr, baseline_pred, metrics)

        metrics_comparison: Dict[str, Dict[str, float]] = {}
        improvements: List[float] = []

        for metric in metrics:
            name = self._normalize_metric_name(metric)
            if name not in metric_results or name not in baseline_results:
                continue
            target_val = metric_results[name]
            baseline_val = baseline_results[name]
            improvement = self._compute_improvement(name, baseline_val, target_val)
            metrics_comparison[name] = {
                "baseline": float(baseline_val),
                "target": float(target_val),
                "improvement": float(improvement),
            }
            improvements.append(improvement)

        statistical_tests = self._perform_statistical_tests(
            target_pred, baseline_pred, y_true_arr
        )

        avg_improvement = float(np.mean(improvements)) if improvements else 0.0
        winner = "target" if avg_improvement > 0 else "baseline"
        if abs(avg_improvement) < 1e-6:
            winner = "tie"

        confidence = min(0.95, 0.5 + abs(avg_improvement) / 100)

        return BaselineComparison(
            baseline_model="baseline",
            target_model="target",
            metrics_comparison=metrics_comparison,
            statistical_tests=statistical_tests,
            winner=winner,
            confidence=confidence,
        )

    def diagnose_residuals(self, y_true: Any, y_pred: Any) -> ResidualDiagnostics:
        """执行残差诊断"""
        y_true_arr = self._to_numpy(y_true)
        y_pred_arr = self._to_numpy(y_pred)
        residuals = y_true_arr - y_pred_arr

        normality_test = self._test_normality(residuals)
        homoscedasticity_test = self._test_homoscedasticity(y_pred_arr, residuals)
        autocorrelation_test = self._test_autocorrelation(residuals)
        outlier_indices = self._detect_outliers(residuals)

        issues: List[str] = []
        if not normality_test.get("passed", True):
            issues.append("残差不满足正态性假设")
        if not homoscedasticity_test.get("passed", True):
            issues.append("存在异方差性")
        if not autocorrelation_test.get("passed", True):
            issues.append("残差存在自相关")
        if outlier_indices:
            issues.append(f"检测到{len(outlier_indices)}个异常值")

        diagnostics_passed = len(issues) == 0

        return ResidualDiagnostics(
            normality_test=normality_test,
            homoscedasticity_test=homoscedasticity_test,
            autocorrelation_test=autocorrelation_test,
            outlier_indices=outlier_indices,
            diagnostics_passed=diagnostics_passed,
            issues=issues,
        )

    def cross_validate(
        self,
        model: Any,
        X: Any,
        y: Any,
        method: str = "k-fold",
        n_splits: int = 5,
    ) -> CrossValidationResult:
        """执行交叉验证/回测"""
        X_arr = self._to_numpy(X)
        y_arr = self._to_numpy(y)
        splits = self._build_splits(y_arr, method, n_splits)

        scores: List[float] = []
        fold_details: List[Dict] = []

        for i, (train_idx, test_idx) in enumerate(splits, start=1):
            fold_model = self._clone_model(model)
            X_train, X_test = X_arr[train_idx], X_arr[test_idx]
            y_train, y_test = y_arr[train_idx], y_arr[test_idx]

            try:
                if hasattr(fold_model, "fit"):
                    fold_model.fit(X_train, y_train)
                y_pred = self._predict(fold_model, X_test)

                if y_pred is None:
                    raise ValueError("预测失败")

                problem_type = self._infer_problem_type(y_test, y_pred)
                metrics = self._compute_metrics(
                    y_test, y_pred, self._default_metrics(problem_type)
                )
                primary_metric = self._select_primary_metric(metrics, problem_type)
                score = self._normalize_metric_score(primary_metric, metrics[primary_metric])

                scores.append(score)
                fold_details.append(
                    {
                        "fold": i,
                        "train_size": int(len(train_idx)),
                        "test_size": int(len(test_idx)),
                        "primary_metric": primary_metric,
                        "metrics": metrics,
                        "score": float(score),
                    }
                )
            except Exception as exc:
                logger.warning("Cross validation fold %s failed: %s", i, exc)
                fold_details.append({"fold": i, "error": str(exc)})

        mean_score = float(np.mean(scores)) if scores else 0.0
        std_score = float(np.std(scores)) if scores else 0.0

        return CrossValidationResult(
            method=method,
            n_splits=n_splits,
            scores=scores,
            mean_score=mean_score,
            std_score=std_score,
            fold_details=fold_details,
        )

    def rank_models(
        self,
        validation_reports: List[ValidationReport],
    ) -> List[Tuple[str, float, str]]:
        """根据验证报告对模型进行排序"""
        ranking: List[Tuple[str, float, str]] = []

        for report in validation_reports:
            residual = report.residual_analysis or {}
            residual_diag = ResidualDiagnostics(
                normality_test=residual.get("normality_test", {}),
                homoscedasticity_test=residual.get("homoscedasticity_test", {}),
                autocorrelation_test=residual.get("autocorrelation_test", {}),
                outlier_indices=residual.get("outlier_indices", []),
                diagnostics_passed=residual.get("diagnostics_passed", False),
                issues=residual.get("issues", []),
            )
            score = self._evaluate_report_score(
                report.metrics, residual_diag, report.cross_validation
            )
            recommendation = self._score_to_recommendation(score)
            ranking.append((report.model_id, score, recommendation))

        ranking.sort(key=lambda item: item[1], reverse=True)
        return ranking

    def _resolve_model(self, model_id: str) -> Any:
        """解析模型实例"""
        for attr in ("model_registry", "models_registry", "model_store", "model_instances"):
            registry = getattr(self.knowledge_base, attr, None)
            if isinstance(registry, dict) and model_id in registry:
                return registry.get(model_id)
        for method in ("get_model", "get_model_instance", "resolve_model"):
            getter = getattr(self.knowledge_base, method, None)
            if callable(getter):
                try:
                    return getter(model_id)
                except Exception as e:
                    logger.debug("通过 %s 解析模型 %s 失败: %s", method, model_id, e)
                    continue
        return None

    def _resolve_model_name(self, model_id: str) -> str:
        """解析模型名称"""
        models = getattr(self.knowledge_base, "models", {})
        model = models.get(model_id) if isinstance(models, dict) else None
        if model and hasattr(model, "name"):
            return str(model.name)
        return model_id

    def _predict(self, model: Any, X: np.ndarray) -> Optional[np.ndarray]:
        """统一预测接口"""
        try:
            if hasattr(model, "predict"):
                return self._to_numpy(model.predict(X))
            if callable(model):
                return self._to_numpy(model(X))
        except Exception as exc:
            logger.warning("Predict failed: %s", exc)
        return None

    def _clone_model(self, model: Any) -> Any:
        """克隆模型实例，避免交叉验证污染"""
        try:
            return copy.deepcopy(model)
        except Exception as e:
            logger.warning("深拷贝模型失败，返回原始模型: %s", e)
            return model

    def _default_metrics(self, problem_type: str) -> List[str]:
        if problem_type == "classification":
            return self.DEFAULT_CLASSIFICATION_METRICS
        return self.DEFAULT_REGRESSION_METRICS

    def _infer_problem_type(self, y_true: np.ndarray, y_pred: np.ndarray) -> str:
        """基于标签类型简单推断问题类型"""
        y_true = np.asarray(y_true)
        if np.issubdtype(y_true.dtype, np.integer):
            unique_count = len(np.unique(y_true))
            if unique_count <= 20:
                return "classification"
        if np.all((y_pred >= 0) & (y_pred <= 1)) and len(np.unique(y_true)) <= 2:
            return "classification"
        return "regression"

    def _compute_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray, metrics: List[str]
    ) -> Dict[str, float]:
        results: Dict[str, float] = {}
        for metric in metrics:
            name = self._normalize_metric_name(metric)
            value = self._compute_metric(name, y_true, y_pred)
            if value is not None:
                results[name] = float(value)
        return results

    def _compute_metric(
        self, name: str, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Optional[float]:
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        if name == "rmse":
            return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        if name == "mse":
            return float(np.mean((y_true - y_pred) ** 2))
        if name == "mae":
            return float(np.mean(np.abs(y_true - y_pred)))
        if name == "mape":
            mask = y_true != 0
            if np.any(mask):
                return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
            return None
        if name == "r2":
            ss_res = float(np.sum((y_true - y_pred) ** 2))
            ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
            return float(1 - ss_res / ss_tot) if ss_tot != 0 else 0.0
        if name in {"accuracy", "precision", "recall", "f1"}:
            y_true_cls, y_pred_cls = self._to_classification_labels(y_true, y_pred)
            if name == "accuracy":
                return float(np.mean(y_true_cls == y_pred_cls))
            tp = np.sum((y_true_cls == 1) & (y_pred_cls == 1))
            fp = np.sum((y_true_cls == 0) & (y_pred_cls == 1))
            fn = np.sum((y_true_cls == 1) & (y_pred_cls == 0))
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            if name == "precision":
                return float(precision)
            if name == "recall":
                return float(recall)
            if name == "f1":
                return float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        return None

    def _to_classification_labels(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        if y_pred.dtype.kind in {"f", "c"}:
            y_pred = (y_pred >= 0.5).astype(int)
        if y_true.dtype.kind in {"f", "c"}:
            y_true = (y_true >= 0.5).astype(int)
        return y_true.astype(int), y_pred.astype(int)

    def _normalize_metric_name(self, metric: str) -> str:
        name = metric.strip().lower()
        mapping = {
            "r²": "r2",
            "r^2": "r2",
            "r2": "r2",
            "rmse": "rmse",
            "mse": "mse",
            "mae": "mae",
            "mape": "mape",
            "accuracy": "accuracy",
            "准确率": "accuracy",
            "precision": "precision",
            "精确率": "precision",
            "recall": "recall",
            "召回率": "recall",
            "f1": "f1",
            "f1分数": "f1",
            "f1-score": "f1",
        }
        return mapping.get(name, name)

    def _compute_improvement(self, name: str, baseline: float, target: float) -> float:
        higher_better = name in {"r2", "accuracy", "precision", "recall", "f1"}
        if baseline == 0:
            return target - baseline
        if higher_better:
            return (target - baseline) / abs(baseline) * 100
        return (baseline - target) / abs(baseline) * 100

    def _perform_statistical_tests(
        self, target_pred: np.ndarray, baseline_pred: np.ndarray, y_true: np.ndarray
    ) -> Dict[str, Any]:
        target_errors = np.abs(y_true - target_pred)
        baseline_errors = np.abs(y_true - baseline_pred)

        tests: Dict[str, Any] = {}
        if len(target_errors) < 2:
            return {
                "paired_ttest": {"error": "样本不足"},
                "wilcoxon": {"error": "样本不足"},
            }

        try:
            t_stat, t_p = stats.ttest_rel(baseline_errors, target_errors)
            tests["paired_ttest"] = {
                "statistic": float(t_stat),
                "p_value": float(t_p),
                "significant": t_p < 0.05,
            }
        except Exception as exc:
            tests["paired_ttest"] = {"error": str(exc)}

        try:
            w_stat, w_p = stats.wilcoxon(baseline_errors, target_errors)
            tests["wilcoxon"] = {
                "statistic": float(w_stat),
                "p_value": float(w_p),
                "significant": w_p < 0.05,
            }
        except Exception as exc:
            tests["wilcoxon"] = {"error": str(exc)}

        return tests

    def _test_normality(self, residuals: np.ndarray) -> Dict[str, Any]:
        residuals = np.asarray(residuals, dtype=float)
        if len(residuals) < 3:
            return {"test": "Shapiro-Wilk", "passed": True, "note": "样本不足"}

        sample = residuals
        if len(sample) > 5000:
            rng = np.random.default_rng(42)
            sample = rng.choice(sample, size=5000, replace=False)

        stat, p_value = stats.shapiro(sample)
        return {
            "test": "Shapiro-Wilk",
            "statistic": float(stat),
            "p_value": float(p_value),
            "passed": p_value > self.NORMALITY_P_THRESHOLD,
        }

    def _test_homoscedasticity(
        self, y_pred: np.ndarray, residuals: np.ndarray
    ) -> Dict[str, Any]:
        residuals = np.asarray(residuals, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        n = len(residuals)
        if n < 3:
            return {"test": "Breusch-Pagan", "passed": True, "note": "样本不足"}

        y_pred_centered = y_pred - np.mean(y_pred)
        X = np.column_stack([np.ones(n), y_pred_centered])
        y = residuals ** 2
        try:
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            y_hat = X @ beta
            ss_res = np.sum((y - y_hat) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
            lm = n * r2
            p_value = 1 - stats.chi2.cdf(lm, df=1)
            return {
                "test": "Breusch-Pagan",
                "lm_stat": float(lm),
                "p_value": float(p_value),
                "passed": p_value > self.HOMOSCEDASTICITY_P_THRESHOLD,
            }
        except Exception as exc:
            return {"test": "Breusch-Pagan", "error": str(exc), "passed": True}

    def _test_autocorrelation(self, residuals: np.ndarray) -> Dict[str, Any]:
        residuals = np.asarray(residuals, dtype=float)
        if len(residuals) < 2:
            return {"test": "Durbin-Watson", "statistic": 2.0, "passed": True}

        diff = np.diff(residuals)
        denominator = np.sum(residuals**2)
        statistic = float(np.sum(diff**2) / denominator) if denominator != 0 else 2.0
        passed = self.DURBIN_WATSON_LOWER < statistic < self.DURBIN_WATSON_UPPER
        return {
            "test": "Durbin-Watson",
            "statistic": statistic,
            "passed": passed,
        }

    def _detect_outliers(self, residuals: np.ndarray) -> List[int]:
        residuals = np.asarray(residuals, dtype=float)
        if residuals.size == 0:
            return []
        z_scores = np.abs(stats.zscore(residuals, nan_policy="omit"))
        return np.where(z_scores > self.OUTLIER_ZSCORE_THRESHOLD)[0].tolist()

    def _build_splits(
        self, y: np.ndarray, method: str, n_splits: int
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        n_samples = len(y)
        indices = np.arange(n_samples)
        rng = np.random.default_rng(42)

        if method == "time-series":
            fold_size = max(1, n_samples // (n_splits + 1))
            splits = []
            for i in range(n_splits):
                train_end = fold_size * (i + 1)
                test_end = min(n_samples, train_end + fold_size)
                if test_end <= train_end:
                    break
                train_idx = indices[:train_end]
                test_idx = indices[train_end:test_end]
                splits.append((train_idx, test_idx))
            return splits

        if method == "stratified":
            return self._build_stratified_splits(y, n_splits, rng)

        rng.shuffle(indices)
        folds = np.array_split(indices, n_splits)
        return [
            (
                np.concatenate([folds[j] for j in range(n_splits) if j != i]),
                folds[i],
            )
            for i in range(n_splits)
        ]

    def _build_stratified_splits(
        self, y: np.ndarray, n_splits: int, rng: np.random.Generator
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        y = np.asarray(y)
        classes, y_indices = np.unique(y, return_inverse=True)
        fold_indices = [[] for _ in range(n_splits)]

        for cls in range(len(classes)):
            cls_indices = np.where(y_indices == cls)[0]
            rng.shuffle(cls_indices)
            cls_folds = np.array_split(cls_indices, n_splits)
            for i in range(n_splits):
                fold_indices[i].extend(cls_folds[i].tolist())

        splits: List[Tuple[np.ndarray, np.ndarray]] = []
        for i in range(n_splits):
            test_idx = np.array(fold_indices[i])
            train_idx = np.array(
                [idx for j in range(n_splits) if j != i for idx in fold_indices[j]]
            )
            splits.append((train_idx, test_idx))
        return splits

    def _select_primary_metric(self, metrics: Dict[str, float], problem_type: str) -> str:
        if problem_type == "classification":
            for name in ("accuracy", "f1", "precision", "recall"):
                if name in metrics:
                    return name
        for name in ("r2", "rmse", "mae", "mape"):
            if name in metrics:
                return name
        return next(iter(metrics.keys()))

    def _normalize_metric_score(self, name: str, value: float) -> float:
        higher_better = name in {"r2", "accuracy", "precision", "recall", "f1"}
        if higher_better:
            return float(max(0.0, min(1.0, value)))
        return float(1 / (1 + value))

    def _evaluate_report_score(
        self,
        metrics: Dict[str, float],
        residual_diag: ResidualDiagnostics,
        cross_validation: Dict[str, Any],
    ) -> float:
        if not metrics:
            return 0.0
        problem_type = "classification" if "accuracy" in metrics else "regression"
        primary = self._select_primary_metric(metrics, problem_type)
        metric_score = self._normalize_metric_score(primary, metrics[primary])

        residual_score = 1.0 if residual_diag.diagnostics_passed else 0.5

        cv_score = 0.0
        if cross_validation:
            cv_score = float(cross_validation.get("mean_score", 0.0))

        return float(0.6 * metric_score + 0.25 * cv_score + 0.15 * residual_score)

    def _score_to_quality(self, score: float) -> QualityLevel:
        if score >= 0.85:
            return "excellent"
        if score >= 0.7:
            return "good"
        if score >= 0.55:
            return "acceptable"
        if score >= 0.4:
            return "needs_improvement"
        return "poor"

    def _score_to_recommendation(self, score: float) -> str:
        if score >= 0.85:
            return "优先采用"
        if score >= 0.7:
            return "推荐采用"
        if score >= 0.55:
            return "可用但需优化"
        return "暂不推荐"

    def _generate_recommendation(
        self,
        overall_rating: QualityLevel,
        residual_diag: ResidualDiagnostics,
        baseline_comparison: Dict[str, Any],
    ) -> str:
        recommendations: List[str] = []
        if overall_rating in {"poor", "needs_improvement"}:
            recommendations.append("建议优化特征工程或调整模型结构")
        if not residual_diag.diagnostics_passed:
            recommendations.extend(residual_diag.issues)
        if baseline_comparison.get("winner") == "baseline":
            recommendations.append("基线模型表现更优，建议回退或重新训练")
        if not recommendations:
            return "模型表现稳定，可进入下一阶段"
        return "；".join(recommendations)

    @staticmethod
    def _to_numpy(value: Any) -> np.ndarray:
        return np.asarray(value)


__all__ = [
    "BaselineComparison",
    "ResidualDiagnostics",
    "CrossValidationResult",
    "AutoValidator",
]
