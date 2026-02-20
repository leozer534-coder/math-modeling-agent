"""
图论工具模块 - TSP、最短路径
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class TSPResult:
    """TSP 求解结果"""
    route: List[int]
    total_distance: float
    method: str


def solve_tsp(
    distance_matrix: np.ndarray,
    method: str = "nearest_neighbor",
    n_restarts: int = 10,
    seed: Optional[int] = None,
) -> TSPResult:
    """求解旅行商问题 (TSP)

    Args:
        distance_matrix: n*n 距离矩阵
        method: 求解方法
            - "nearest_neighbor": 最近邻启发式
            - "2opt": 2-opt 改进
        n_restarts: 多起点重启次数
        seed: 随机种子

    Returns:
        TSPResult
    """
    D = np.asarray(distance_matrix, dtype=float)
    n = D.shape[0]
    rng = np.random.RandomState(seed)

    def nn_route(start: int) -> Tuple[List[int], float]:
        """最近邻启发式构造初始路径。"""
        visited = [start]
        current = start
        total = 0.0
        for _ in range(n - 1):
            unvisited = [j for j in range(n) if j not in visited]
            nearest = min(unvisited, key=lambda j: D[current, j])
            total += D[current, nearest]
            visited.append(nearest)
            current = nearest
        total += D[current, start]
        visited.append(start)
        return visited, total

    def two_opt(
        route: List[int], dist: float
    ) -> Tuple[List[int], float]:
        """2-opt 局部搜索改进路径。"""
        improved = True
        best_route = route[:]
        best_dist = dist
        while improved:
            improved = False
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    delta = (
                        D[best_route[i - 1], best_route[j]]
                        + D[best_route[i], best_route[j + 1]]
                        - D[best_route[i - 1], best_route[i]]
                        - D[best_route[j], best_route[j + 1]]
                    )
                    if delta < -1e-10:
                        best_route[i : j + 1] = reversed(
                            best_route[i : j + 1]
                        )
                        best_dist += delta
                        improved = True
        return best_route, best_dist

    best_route_overall: Optional[List[int]] = None
    best_dist_overall = float("inf")

    starts = rng.choice(n, size=min(n_restarts, n), replace=False)
    for start in starts:
        route, dist = nn_route(start)
        if method == "2opt":
            route, dist = two_opt(route, dist)
        if dist < best_dist_overall:
            best_dist_overall = dist
            best_route_overall = route

    return TSPResult(
        route=best_route_overall if best_route_overall is not None else [],
        total_distance=best_dist_overall,
        method=method,
    )


def shortest_path(
    graph: np.ndarray,
    source: int,
    target: Optional[int] = None,
    method: str = "dijkstra",
) -> Dict[str, Any]:
    """最短路径算法

    Args:
        graph: n*n 邻接/距离矩阵（0或inf表示无边）
        source: 起点索引
        target: 终点索引（None 则计算到所有节点）
        method: "dijkstra" 或 "floyd"

    Returns:
        dict: distances, predecessors, path (如果指定了 target)
    """
    from scipy.sparse.csgraph import (
        dijkstra,
        shortest_path as sp_shortest,
    )
    from scipy.sparse import csr_matrix

    G = np.asarray(graph, dtype=float)
    G[G == 0] = np.inf
    np.fill_diagonal(G, 0)

    sparse_G = csr_matrix(G)

    if method == "floyd":
        dist_matrix, predecessors = sp_shortest(
            sparse_G, method="FW", return_predecessors=True
        )
        distances = dist_matrix[source]
        preds = predecessors[source]
    else:
        distances, preds = dijkstra(
            sparse_G, indices=source, return_predecessors=True
        )

    result: Dict[str, Any] = {
        "distances": distances,
        "predecessors": preds,
    }

    if target is not None:
        path: List[int] = []
        current = target
        while current != source and current >= 0:
            path.append(current)
            current = preds[current]
        if current == source:
            path.append(source)
            path.reverse()
            result["path"] = path
            result["path_distance"] = distances[target]
        else:
            result["path"] = []
            result["path_distance"] = float("inf")

    return result
