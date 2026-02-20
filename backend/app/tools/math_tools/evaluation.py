"""
评价工具模块 - AHP、TOPSIS、熵权法、模糊评价、PCA
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class AHPResult:
    """AHP 分析结果"""
    weights: np.ndarray
    consistency_ratio: float
    is_consistent: bool
    eigenvalue: float
    consistency_index: float
    message: str = ""


@dataclass
class TOPSISResult:
    """TOPSIS 评价结果"""
    scores: np.ndarray
    rankings: np.ndarray
    positive_distances: np.ndarray
    negative_distances: np.ndarray


@dataclass
class EntropyWeightResult:
    """熵权法结果"""
    weights: np.ndarray
    entropies: np.ndarray
    divergences: np.ndarray


def ahp_analysis(comparison_matrix: np.ndarray) -> AHPResult:
    """层次分析法（AHP）- 计算权重并检验一致性

    Args:
        comparison_matrix: n*n 比较矩阵（正互反矩阵）

    Returns:
        AHPResult: 权重、一致性比率等
    """
    A = np.asarray(comparison_matrix, dtype=float)
    n = A.shape[0]

    # 特征值法求权重
    eigenvalues, eigenvectors = np.linalg.eig(A)
    max_idx = np.argmax(eigenvalues.real)
    max_eigenvalue = eigenvalues[max_idx].real
    weights = eigenvectors[:, max_idx].real
    weights = weights / weights.sum()

    # 一致性检验
    ci = (max_eigenvalue - n) / (n - 1) if n > 1 else 0
    # 随机一致性指标 RI 表（1-15阶）
    ri_table = {
        1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
        7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49, 11: 1.51,
        12: 1.54, 13: 1.56, 14: 1.58, 15: 1.59,
    }
    ri = ri_table.get(n, 1.59)
    cr = ci / ri if ri > 0 else 0

    return AHPResult(
        weights=weights,
        consistency_ratio=cr,
        is_consistent=cr < 0.1,
        eigenvalue=max_eigenvalue,
        consistency_index=ci,
        message=(
            "一致性通过"
            if cr < 0.1
            else f"一致性未通过 (CR={cr:.4f} >= 0.1)，请调整比较矩阵"
        ),
    )


def topsis_evaluate(
    decision_matrix: np.ndarray,
    weights: np.ndarray,
    benefit_criteria: Optional[List[bool]] = None,
) -> TOPSISResult:
    """TOPSIS 逼近理想解排序法

    Args:
        decision_matrix: m*n 决策矩阵（m个方案，n个指标）
        weights: n 维权重向量
        benefit_criteria: 各指标是否为效益型（True=越大越好），默认全为 True

    Returns:
        TOPSISResult
    """
    X = np.asarray(decision_matrix, dtype=float)
    w = np.asarray(weights, dtype=float)
    m, n = X.shape

    if benefit_criteria is None:
        benefit_criteria = [True] * n

    # 1. 向量归一化
    norms = np.sqrt((X**2).sum(axis=0))
    norms[norms == 0] = 1
    R = X / norms

    # 2. 加权归一化
    V = R * w

    # 3. 确定理想解和负理想解
    positive_ideal = np.zeros(n)
    negative_ideal = np.zeros(n)
    for j in range(n):
        if benefit_criteria[j]:
            positive_ideal[j] = V[:, j].max()
            negative_ideal[j] = V[:, j].min()
        else:
            positive_ideal[j] = V[:, j].min()
            negative_ideal[j] = V[:, j].max()

    # 4. 计算距离
    d_pos = np.sqrt(((V - positive_ideal) ** 2).sum(axis=1))
    d_neg = np.sqrt(((V - negative_ideal) ** 2).sum(axis=1))

    # 5. 计算贴近度
    scores = d_neg / (d_pos + d_neg + 1e-10)
    rankings = np.argsort(-scores) + 1

    return TOPSISResult(
        scores=scores,
        rankings=rankings,
        positive_distances=d_pos,
        negative_distances=d_neg,
    )


def entropy_weight(decision_matrix: np.ndarray) -> EntropyWeightResult:
    """熵权法 - 客观赋权

    Args:
        decision_matrix: m*n 决策矩阵

    Returns:
        EntropyWeightResult
    """
    X = np.asarray(decision_matrix, dtype=float)
    m, n = X.shape

    # 归一化（极差法）
    X_min = X.min(axis=0)
    X_max = X.max(axis=0)
    ranges = X_max - X_min
    ranges[ranges == 0] = 1
    P = (X - X_min) / ranges

    # 计算比重
    P_sum = P.sum(axis=0)
    P_sum[P_sum == 0] = 1
    P_ratio = P / P_sum

    # 计算信息熵
    P_ratio_safe = np.where(P_ratio > 0, P_ratio, 1)  # 避免 log(0)
    entropies = (
        -1 / np.log(m + 1e-10) * (P_ratio * np.log(P_ratio_safe)).sum(axis=0)
    )
    entropies = np.clip(entropies, 0, 1)

    # 信息效用值 (差异系数)
    divergences = 1 - entropies

    # 权重
    div_sum = divergences.sum()
    weights = divergences / div_sum if div_sum > 0 else np.ones(n) / n

    return EntropyWeightResult(
        weights=weights, entropies=entropies, divergences=divergences
    )


def fuzzy_evaluation(
    factor_matrix: np.ndarray,
    weights: np.ndarray,
    levels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """模糊综合评价

    Args:
        factor_matrix: n*m 模糊评价矩阵（n个因素对m个等级的隶属度）
        weights: n 维因素权重
        levels: 等级标签列表

    Returns:
        dict: result_vector, best_level, best_index, level_scores
    """
    R = np.asarray(factor_matrix, dtype=float)
    w = np.asarray(weights, dtype=float).reshape(1, -1)
    n, m_levels = R.shape

    if levels is None:
        levels = [f"等级{i+1}" for i in range(m_levels)]

    # 模糊合成（加权平均型）
    B = w @ R
    B = B.flatten()

    # 归一化
    b_sum = B.sum()
    if b_sum > 0:
        B = B / b_sum

    best_idx = int(np.argmax(B))

    return {
        "result_vector": B,
        "best_level": levels[best_idx],
        "best_index": best_idx,
        "level_scores": dict(zip(levels, B.tolist())),
    }


def pca_analysis(
    data: np.ndarray,
    n_components: Optional[int] = None,
    variance_threshold: float = 0.85,
) -> Dict[str, Any]:
    """主成分分析（PCA）

    Args:
        data: m*n 数据矩阵（m个样本，n个特征）
        n_components: 指定主成分个数，None 则按累计方差阈值自动确定
        variance_threshold: 累计方差贡献率阈值

    Returns:
        dict: components, explained_variance_ratio, cumulative_variance,
              n_components, transformed_data, loadings
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA

    X = np.asarray(data, dtype=float)
    X_scaled = StandardScaler().fit_transform(X)

    # 先做全量 PCA 分析方差
    pca_full = PCA()
    pca_full.fit(X_scaled)
    cumvar = np.cumsum(pca_full.explained_variance_ratio_)

    if n_components is None:
        n_components = int(np.searchsorted(cumvar, variance_threshold) + 1)
        n_components = min(n_components, X.shape[1])

    pca = PCA(n_components=n_components)
    X_transformed = pca.fit_transform(X_scaled)

    return {
        "components": pca.components_,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "cumulative_variance": np.cumsum(pca.explained_variance_ratio_),
        "n_components": n_components,
        "transformed_data": X_transformed,
        "loadings": pca.components_.T * np.sqrt(pca.explained_variance_),
    }
