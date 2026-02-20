"""
优化工具模块 - 线性规划、整数规划、多目标优化、元启发式算法
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class OptimizationResult:
    """优化结果"""
    optimal_value: float
    optimal_solution: np.ndarray
    status: str  # "optimal" / "infeasible" / "unbounded" / "suboptimal"
    iterations: int = 0
    message: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


def solve_linear_program(
    c: np.ndarray,
    A_ub: Optional[np.ndarray] = None,
    b_ub: Optional[np.ndarray] = None,
    A_eq: Optional[np.ndarray] = None,
    b_eq: Optional[np.ndarray] = None,
    bounds: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
    maximize: bool = False,
) -> OptimizationResult:
    """求解线性规划问题

    min c^T x  s.t. A_ub @ x <= b_ub, A_eq @ x == b_eq

    Args:
        c: 目标函数系数向量
        A_ub: 不等式约束矩阵
        b_ub: 不等式约束右端项
        A_eq: 等式约束矩阵
        b_eq: 等式约束右端项
        bounds: 变量上下界列表
        maximize: True 时求最大值（内部取反）

    Returns:
        OptimizationResult
    """
    from scipy.optimize import linprog

    c = np.asarray(c, dtype=float)
    obj_c = -c if maximize else c

    result = linprog(
        c=obj_c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    status_map = {
        0: "optimal",
        1: "suboptimal",
        2: "infeasible",
        3: "unbounded",
        4: "suboptimal",
    }
    opt_val = -result.fun if maximize else result.fun

    return OptimizationResult(
        optimal_value=opt_val if result.success else float("nan"),
        optimal_solution=result.x if result.x is not None else np.array([]),
        status=status_map.get(result.status, "unknown"),
        iterations=result.nit,
        message=result.message,
    )


def solve_integer_program(
    c: np.ndarray,
    A_ub: Optional[np.ndarray] = None,
    b_ub: Optional[np.ndarray] = None,
    A_eq: Optional[np.ndarray] = None,
    b_eq: Optional[np.ndarray] = None,
    bounds: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
    integer_vars: Optional[List[int]] = None,
    maximize: bool = False,
) -> OptimizationResult:
    """求解整数规划（混合整数线性规划）

    Args:
        c: 目标函数系数
        A_ub, b_ub: 不等式约束
        A_eq, b_eq: 等式约束
        bounds: 变量界
        integer_vars: 整数变量索引列表（None 表示全部整数）
        maximize: 是否最大化

    Returns:
        OptimizationResult
    """
    from scipy.optimize import milp, LinearConstraint, Bounds as ScipyBounds

    c = np.asarray(c, dtype=float)
    n = len(c)
    obj_c = -c if maximize else c

    constraints = []
    if A_ub is not None and b_ub is not None:
        constraints.append(LinearConstraint(A_ub, ub=b_ub))
    if A_eq is not None and b_eq is not None:
        constraints.append(LinearConstraint(A_eq, lb=b_eq, ub=b_eq))

    if bounds is not None:
        lb = np.array([b[0] if b[0] is not None else -np.inf for b in bounds])
        ub = np.array([b[1] if b[1] is not None else np.inf for b in bounds])
        variable_bounds = ScipyBounds(lb=lb, ub=ub)
    else:
        variable_bounds = ScipyBounds(lb=0, ub=np.inf)

    # 整数约束
    integrality = np.zeros(n)
    if integer_vars is None:
        integrality[:] = 1
    else:
        for idx in integer_vars:
            integrality[idx] = 1

    result = milp(
        c=obj_c,
        constraints=constraints,
        integrality=integrality,
        bounds=variable_bounds,
    )

    opt_val = -result.fun if maximize and result.success else result.fun

    return OptimizationResult(
        optimal_value=opt_val if result.success else float("nan"),
        optimal_solution=result.x if result.x is not None else np.array([]),
        status="optimal" if result.success else "infeasible",
        message=result.message,
    )


def multi_objective_optimize(
    objectives: List[Callable[[np.ndarray], float]],
    bounds: List[Tuple[float, float]],
    pop_size: int = 100,
    n_gen: int = 200,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """NSGA-II 多目标优化

    Args:
        objectives: 目标函数列表（均为最小化）
        bounds: 变量界 [(lb, ub), ...]
        pop_size: 种群大小
        n_gen: 迭代代数
        seed: 随机种子

    Returns:
        dict: pareto_front (ndarray), pareto_set (ndarray), n_solutions (int)
    """
    from scipy.optimize import differential_evolution

    # 简化实现: 使用加权和法生成多组 Pareto 近似解
    n_obj = len(objectives)
    rng = np.random.RandomState(seed)

    pareto_solutions = []
    pareto_objectives = []

    # 生成均匀分布的权重向量
    n_weights = min(pop_size, 50)
    if n_obj == 2:
        weights_list = [
            (w / n_weights, 1 - w / n_weights)
            for w in range(n_weights + 1)
        ]
    else:
        weights_list = [
            tuple(rng.dirichlet(np.ones(n_obj))) for _ in range(n_weights)
        ]

    for weights in weights_list:

        def weighted_obj(x: np.ndarray, w: tuple = weights) -> float:
            return sum(w_i * f(x) for w_i, f in zip(w, objectives))

        result = differential_evolution(
            weighted_obj,
            bounds=bounds,
            seed=rng.randint(0, 2**31),
            maxiter=n_gen // 2,
            popsize=15,
            tol=1e-6,
        )
        if result.success:
            obj_vals = [f(result.x) for f in objectives]
            pareto_solutions.append(result.x.copy())
            pareto_objectives.append(obj_vals)

    if not pareto_solutions:
        return {
            "pareto_front": np.array([]),
            "pareto_set": np.array([]),
            "n_solutions": 0,
        }

    pareto_front = np.array(pareto_objectives)
    pareto_set = np.array(pareto_solutions)

    # 简单非支配排序过滤
    is_dominated = np.zeros(len(pareto_front), dtype=bool)
    for i in range(len(pareto_front)):
        for j in range(len(pareto_front)):
            if i != j and np.all(pareto_front[j] <= pareto_front[i]) and np.any(
                pareto_front[j] < pareto_front[i]
            ):
                is_dominated[i] = True
                break

    pareto_front = pareto_front[~is_dominated]
    pareto_set = pareto_set[~is_dominated]

    return {
        "pareto_front": pareto_front,
        "pareto_set": pareto_set,
        "n_solutions": len(pareto_front),
    }


def simulated_annealing(
    objective: Callable[[np.ndarray], float],
    x0: np.ndarray,
    bounds: Optional[List[Tuple[float, float]]] = None,
    T0: float = 1000.0,
    T_min: float = 1e-8,
    alpha: float = 0.95,
    max_iter: int = 10000,
    seed: Optional[int] = None,
) -> OptimizationResult:
    """模拟退火算法

    Args:
        objective: 目标函数（最小化）
        x0: 初始解
        bounds: 变量界
        T0: 初始温度
        T_min: 终止温度
        alpha: 降温系数
        max_iter: 最大迭代次数
        seed: 随机种子

    Returns:
        OptimizationResult
    """
    from scipy.optimize import dual_annealing

    if bounds is None:
        delta = np.abs(x0) + 10
        bounds = [(-d, d) for d in delta]

    result = dual_annealing(
        objective,
        bounds=bounds,
        x0=x0,
        maxiter=max_iter,
        seed=seed,
        initial_temp=T0,
    )

    return OptimizationResult(
        optimal_value=result.fun,
        optimal_solution=result.x,
        status="optimal" if result.success else "suboptimal",
        iterations=result.nit if hasattr(result, "nit") else 0,
        message=result.message if hasattr(result, "message") else "",
    )


def particle_swarm_optimize(
    objective: Callable[[np.ndarray], float],
    bounds: List[Tuple[float, float]],
    n_particles: int = 50,
    max_iter: int = 200,
    w: float = 0.7,
    c1: float = 1.5,
    c2: float = 1.5,
    seed: Optional[int] = None,
) -> OptimizationResult:
    """粒子群优化 (PSO)

    Args:
        objective: 目标函数（最小化）
        bounds: 变量界
        n_particles: 粒子数
        max_iter: 最大迭代
        w: 惯性权重
        c1: 个体学习因子
        c2: 社会学习因子
        seed: 随机种子

    Returns:
        OptimizationResult
    """
    rng = np.random.RandomState(seed)
    n_dims = len(bounds)
    lb = np.array([b[0] for b in bounds])
    ub = np.array([b[1] for b in bounds])

    # 初始化
    positions = rng.uniform(lb, ub, (n_particles, n_dims))
    velocities = rng.uniform(
        -(ub - lb) * 0.1, (ub - lb) * 0.1, (n_particles, n_dims)
    )
    personal_best_pos = positions.copy()
    personal_best_val = np.array([objective(p) for p in positions])
    global_best_idx = np.argmin(personal_best_val)
    global_best_pos = personal_best_pos[global_best_idx].copy()
    global_best_val = personal_best_val[global_best_idx]

    for iteration in range(max_iter):
        r1 = rng.random((n_particles, n_dims))
        r2 = rng.random((n_particles, n_dims))

        velocities = (
            w * velocities
            + c1 * r1 * (personal_best_pos - positions)
            + c2 * r2 * (global_best_pos - positions)
        )
        positions = np.clip(positions + velocities, lb, ub)

        for i in range(n_particles):
            val = objective(positions[i])
            if val < personal_best_val[i]:
                personal_best_val[i] = val
                personal_best_pos[i] = positions[i].copy()
                if val < global_best_val:
                    global_best_val = val
                    global_best_pos = positions[i].copy()

    return OptimizationResult(
        optimal_value=global_best_val,
        optimal_solution=global_best_pos,
        status="suboptimal",
        iterations=max_iter,
        message=f"PSO completed with {n_particles} particles over {max_iter} iterations",
    )
