"""
验证工具模块 - 交叉验证、敏感性分析、Bootstrap 置信区间
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    scores: np.ndarray
    mean_score: float
    std_score: float
    fold_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SensitivityResult:
    """敏感性分析结果"""
    parameter_name: str
    values: np.ndarray
    results: np.ndarray
    sensitivity_index: float
    conclusion: str


def cross_validate(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
    scoring: str = "accuracy",
) -> CrossValidationResult:
    """K 折交叉验证（sklearn 兼容模型）

    Args:
        model: sklearn 兼容的模型对象（有 fit/predict 方法）
        X: 特征矩阵
        y: 标签向量
        cv: 折数
        scoring: 评分指标 ("accuracy", "r2", "neg_mean_squared_error", etc.)

    Returns:
        CrossValidationResult
    """
    from sklearn.model_selection import cross_val_score

    scores = cross_val_score(model, X, y, cv=cv, scoring=scoring)

    return CrossValidationResult(
        scores=scores,
        mean_score=float(scores.mean()),
        std_score=float(scores.std()),
    )


def sensitivity_analysis(
    func: Callable[..., float],
    base_params: Dict[str, float],
    param_name: str,
    variation_range: Tuple[float, float] = (0.8, 1.2),
    n_points: int = 20,
) -> SensitivityResult:
    """单参数敏感性分析

    Args:
        func: 模型函数 func(**params) -> float
        base_params: 基准参数字典
        param_name: 要分析的参数名
        variation_range: 变化范围（相对于基准值的比例）
        n_points: 采样点数

    Returns:
        SensitivityResult
    """
    base_value = base_params[param_name]
    low = base_value * variation_range[0]
    high = base_value * variation_range[1]
    values = np.linspace(low, high, n_points)

    results = []
    for v in values:
        params = base_params.copy()
        params[param_name] = v
        results.append(func(**params))

    results_arr = np.array(results)
    base_result = func(**base_params)

    # 敏感性指数 = 结果变化率 / 参数变化率
    if base_value != 0 and base_result != 0:
        param_change = (values[-1] - values[0]) / base_value
        result_change = (results_arr[-1] - results_arr[0]) / base_result
        sensitivity_index = (
            abs(result_change / param_change) if param_change != 0 else 0
        )
    else:
        sensitivity_index = float(np.std(results_arr))

    if sensitivity_index > 1.0:
        conclusion = (
            f"参数 {param_name} 对结果高度敏感"
            f"（敏感性指数={sensitivity_index:.3f}）"
        )
    elif sensitivity_index > 0.5:
        conclusion = (
            f"参数 {param_name} 对结果中等敏感"
            f"（敏感性指数={sensitivity_index:.3f}）"
        )
    else:
        conclusion = (
            f"参数 {param_name} 对结果不敏感"
            f"（敏感性指数={sensitivity_index:.3f}）"
        )

    return SensitivityResult(
        parameter_name=param_name,
        values=values,
        results=results_arr,
        sensitivity_index=sensitivity_index,
        conclusion=conclusion,
    )


def bootstrap_confidence_interval(
    data: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.mean,
    confidence: float = 0.95,
    n_bootstrap: int = 1000,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Bootstrap 置信区间估计

    Args:
        data: 样本数据
        statistic: 统计量函数（默认为均值）
        confidence: 置信水平
        n_bootstrap: 重抽样次数
        seed: 随机种子

    Returns:
        dict: point_estimate, ci_lower, ci_upper, confidence,
              bootstrap_distribution, standard_error
    """
    rng = np.random.RandomState(seed)
    data = np.asarray(data).flatten()
    n = len(data)

    point_estimate = statistic(data)
    bootstrap_stats = np.array([
        statistic(rng.choice(data, size=n, replace=True))
        for _ in range(n_bootstrap)
    ])

    alpha = 1 - confidence
    ci_lower = float(np.percentile(bootstrap_stats, alpha / 2 * 100))
    ci_upper = float(
        np.percentile(bootstrap_stats, (1 - alpha / 2) * 100)
    )

    return {
        "point_estimate": float(point_estimate),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "confidence": confidence,
        "bootstrap_distribution": bootstrap_stats,
        "standard_error": float(np.std(bootstrap_stats)),
    }
