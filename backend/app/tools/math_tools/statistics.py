"""
统计工具模块 - 假设检验、灰色关联分析
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class HypothesisTestResult:
    """假设检验结果"""
    test_name: str
    statistic: float
    p_value: float
    reject_null: bool
    significance_level: float
    conclusion: str


def hypothesis_test(
    data1: np.ndarray,
    data2: Optional[np.ndarray] = None,
    test_type: str = "t_test",
    alternative: str = "two-sided",
    alpha: float = 0.05,
) -> HypothesisTestResult:
    """统一假设检验接口

    Args:
        data1: 第一组数据
        data2: 第二组数据（单样本检验时为 None）
        test_type: 检验类型
            - "t_test": 独立样本 t 检验
            - "paired_t_test": 配对 t 检验
            - "one_sample_t": 单样本 t 检验（data2 为期望均值标量）
            - "mann_whitney": Mann-Whitney U 检验
            - "wilcoxon": Wilcoxon 符号秩检验
            - "chi_square": 卡方检验
            - "anova": 单因素方差分析（data1=list of arrays）
            - "normality": 正态性检验（Shapiro-Wilk）
        alternative: "two-sided" / "less" / "greater"
        alpha: 显著性水平

    Returns:
        HypothesisTestResult
    """
    from scipy import stats

    d1 = np.asarray(data1, dtype=float).flatten()

    if test_type == "t_test":
        d2 = np.asarray(data2, dtype=float).flatten()
        stat, p = stats.ttest_ind(d1, d2, alternative=alternative)
        name = "独立样本 t 检验"
    elif test_type == "paired_t_test":
        d2 = np.asarray(data2, dtype=float).flatten()
        stat, p = stats.ttest_rel(d1, d2, alternative=alternative)
        name = "配对 t 检验"
    elif test_type == "one_sample_t":
        mu = float(data2) if data2 is not None else 0
        stat, p = stats.ttest_1samp(d1, mu, alternative=alternative)
        name = "单样本 t 检验"
    elif test_type == "mann_whitney":
        d2 = np.asarray(data2, dtype=float).flatten()
        stat, p = stats.mannwhitneyu(d1, d2, alternative=alternative)
        name = "Mann-Whitney U 检验"
    elif test_type == "wilcoxon":
        d2 = (
            np.asarray(data2, dtype=float).flatten()
            if data2 is not None
            else None
        )
        if d2 is not None:
            stat, p = stats.wilcoxon(d1, d2, alternative=alternative)
        else:
            stat, p = stats.wilcoxon(d1, alternative=alternative)
        name = "Wilcoxon 符号秩检验"
    elif test_type == "chi_square":
        if data2 is not None:
            stat, p = stats.chisquare(
                d1, f_exp=np.asarray(data2, dtype=float).flatten()
            )
        else:
            stat, p = stats.chisquare(d1)
        name = "卡方检验"
    elif test_type == "anova":
        groups = [np.asarray(g, dtype=float).flatten() for g in data1]
        stat, p = stats.f_oneway(*groups)
        name = "单因素方差分析 (ANOVA)"
    elif test_type == "normality":
        stat, p = stats.shapiro(d1)
        name = "Shapiro-Wilk 正态性检验"
    else:
        raise ValueError(f"不支持的检验类型: {test_type}")

    reject = p < alpha
    if reject:
        conclusion = (
            f"在 alpha={alpha} 的显著性水平下，拒绝原假设 (p={p:.6f})"
        )
    else:
        conclusion = (
            f"在 alpha={alpha} 的显著性水平下，不能拒绝原假设 (p={p:.6f})"
        )

    return HypothesisTestResult(
        test_name=name,
        statistic=float(stat),
        p_value=float(p),
        reject_null=reject,
        significance_level=alpha,
        conclusion=conclusion,
    )


def grey_relational_analysis(
    data: np.ndarray,
    reference: Optional[np.ndarray] = None,
    rho: float = 0.5,
) -> Dict[str, Any]:
    """灰色关联分析

    Args:
        data: m*n 数据矩阵（m个比较序列，n个数据点）
        reference: 参考序列（默认取各列最优值）
        rho: 分辨系数（0-1，通常取0.5）

    Returns:
        dict: grey_coefficients, grey_degrees, rankings
    """
    X = np.asarray(data, dtype=float)
    m, n = X.shape

    # 归一化（极差法）
    X_min = X.min(axis=0)
    X_max = X.max(axis=0)
    ranges = X_max - X_min
    ranges[ranges == 0] = 1
    X_norm = (X - X_min) / ranges

    # 参考序列
    if reference is None:
        ref = X_norm.max(axis=0)
    else:
        ref = (np.asarray(reference, dtype=float) - X_min) / ranges

    # 差值矩阵
    delta = np.abs(X_norm - ref)
    delta_min = delta.min()
    delta_max = delta.max()

    # 关联系数
    coefficients = (delta_min + rho * delta_max) / (
        delta + rho * delta_max + 1e-10
    )

    # 关联度
    degrees = coefficients.mean(axis=1)
    rankings = np.argsort(-degrees) + 1

    return {
        "grey_coefficients": coefficients,
        "grey_degrees": degrees,
        "rankings": rankings,
    }
