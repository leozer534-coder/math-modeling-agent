"""优化类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

OPTIMIZATION_TEMPLATES = {
    "linear_program": CodeTemplate(
        name="线性规划求解",
        category="优化",
        description="使用 scipy.optimize.linprog 或 PuLP 求解线性规划问题",
        applicable_models=["线性规划", "LP", "linear_programming"],
        dependencies=["scipy", "numpy"],
        code='''import numpy as np
from scipy.optimize import linprog

# 定义目标函数系数 (最小化 c^T x)
c = np.array([...])  # TODO: 替换为实际系数

# 不等式约束 A_ub @ x <= b_ub
A_ub = np.array([[...]])  # TODO: 替换
b_ub = np.array([...])

# 等式约束 A_eq @ x == b_eq (可选)
A_eq = None
b_eq = None

# 变量界
bounds = [(0, None) for _ in range(len(c))]

# 求解
result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

print(f"最优值: {result.fun:.4f}")
print(f"最优解: {result.x}")
print(f"求解状态: {result.message}")
''',
    ),
    "integer_program": CodeTemplate(
        name="整数规划求解",
        category="优化",
        description="使用 PuLP 求解整数/混合整数规划",
        applicable_models=["整数规划", "MILP", "0-1规划", "integer_programming"],
        dependencies=["pulp", "numpy"],
        code='''import pulp
import numpy as np

# 创建问题
prob = pulp.LpProblem("IntegerProgramming", pulp.LpMinimize)

# 定义变量 (整数)
n = 5  # TODO: 替换为实际变量数
x = [pulp.LpVariable(f"x{i}", lowBound=0, cat="Integer") for i in range(n)]

# 目标函数
c = [...]  # TODO: 替换为实际系数
prob += pulp.lpSum(c[i] * x[i] for i in range(n))

# 约束条件
# prob += pulp.lpSum(a[i] * x[i] for i in range(n)) <= b  # TODO: 添加约束

# 求解
prob.solve(pulp.PULP_CBC_CMD(msg=0))

print(f"状态: {pulp.LpStatus[prob.status]}")
print(f"最优值: {pulp.value(prob.objective):.4f}")
for v in prob.variables():
    print(f"  {v.name} = {v.varValue}")
''',
    ),
    "nsga2_multi_objective": CodeTemplate(
        name="NSGA-II 多目标优化",
        category="优化",
        description="使用 pymoo 框架的 NSGA-II 算法进行真正的多目标进化优化求解，支持 Pareto 前沿提取、TOPSIS 折中解选取和 Hypervolume 指标评估",
        applicable_models=["NSGA-II", "多目标优化", "Pareto", "nsga2", "MOEA/D", "多目标进化"],
        dependencies=["pymoo", "numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json

# ============================================================
# pymoo NSGA-II 真正多目标优化实现
# 降级策略: 若 pymoo 不可用则回退到 scipy 加权和法
# ============================================================

USE_PYMOO = True
try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.indicators.hv import HV
    from pymoo.termination import get_termination
except ImportError:
    USE_PYMOO = False
    print("[警告] pymoo 未安装，将降级使用 scipy 加权和法近似求解")


def topsis_select(pareto_F: np.ndarray) -> int:
    """使用 TOPSIS 方法从 Pareto 前沿中选出最优折中解。

    Args:
        pareto_F: Pareto 前沿目标值矩阵，形状 (n_solutions, n_objectives)

    Returns:
        最优折中解在 pareto_F 中的索引
    """
    F = pareto_F.copy()
    n, m = F.shape

    # 1. 向量归一化
    norm = np.sqrt((F ** 2).sum(axis=0))
    norm[norm == 0] = 1e-12
    R = F / norm

    # 2. 等权重（所有目标同等重要）  # TODO: 根据实际需求调整权重
    weights = np.ones(m) / m
    V = R * weights

    # 3. 正理想解和负理想解（所有目标均为最小化）
    ideal = V.min(axis=0)
    nadir = V.max(axis=0)

    # 4. 计算到理想解和负理想解的欧氏距离
    dist_ideal = np.sqrt(((V - ideal) ** 2).sum(axis=1))
    dist_nadir = np.sqrt(((V - nadir) ** 2).sum(axis=1))

    # 5. 相对贴近度
    denom = dist_ideal + dist_nadir
    denom[denom == 0] = 1e-12
    closeness = dist_nadir / denom

    return int(np.argmax(closeness))


if USE_PYMOO:
    # ==============================================================
    # 1. 定义多目标优化问题 (继承 pymoo Problem)
    # ==============================================================
    class MultiObjectiveProblem(Problem):
        """自定义多目标优化问题。

        TODO: 根据实际问题修改以下内容：
          - n_var: 决策变量个数
          - n_obj: 目标函数个数
          - n_ieq_constr: 不等式约束个数 (g(x) <= 0)
          - xl / xu: 决策变量下界/上界
          - _evaluate: 目标函数和约束的计算逻辑
        """

        def __init__(self):
            super().__init__(
                n_var=2,            # TODO: 决策变量维数
                n_obj=2,            # TODO: 目标函数个数
                n_ieq_constr=2,     # TODO: 不等式约束个数 (g <= 0)
                xl=np.array([-5.0, -5.0]),   # TODO: 变量下界
                xu=np.array([5.0, 5.0]),      # TODO: 变量上界
            )

        def _evaluate(self, X, out, *args, **kwargs):
            """批量评估目标函数和约束。

            Args:
                X: 决策变量矩阵，形状 (pop_size, n_var)
                out: 输出字典，需填充 "F" (目标值) 和 "G" (约束值)
            """
            x1 = X[:, 0]
            x2 = X[:, 1]

            # --- 目标函数 (均为最小化) ---
            # TODO: 替换为实际目标函数
            f1 = x1 ** 2 + x2 ** 2
            f2 = (x1 - 1) ** 2 + (x2 - 1) ** 2

            out["F"] = np.column_stack([f1, f2])

            # --- 不等式约束 g(x) <= 0 ---
            # TODO: 替换为实际约束条件
            g1 = -(x1 + x2 - 1)     # x1 + x2 >= 1
            g2 = x1 + x2 - 8        # x1 + x2 <= 8

            out["G"] = np.column_stack([g1, g2])

    # ==============================================================
    # 2. 配置 NSGA-II 算法
    # ==============================================================
    problem = MultiObjectiveProblem()

    algorithm = NSGA2(
        pop_size=100,
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True,
    )

    termination = get_termination("n_gen", 200)

    # ==============================================================
    # 3. 执行优化（保存每代历史用于收敛曲线）
    # ==============================================================
    res = minimize(
        problem,
        algorithm,
        termination,
        seed=42,
        save_history=True,
        verbose=False,
    )

    # ==============================================================
    # 4. 提取 Pareto 前沿解集
    # ==============================================================
    pareto_F = res.F   # 目标值矩阵 (n_solutions, n_obj)
    pareto_X = res.X   # 决策变量矩阵 (n_solutions, n_var)

    # ==============================================================
    # 5. TOPSIS 选取最优折中解
    # ==============================================================
    compromise_idx = topsis_select(pareto_F)
    compromise_F = pareto_F[compromise_idx]
    compromise_X = pareto_X[compromise_idx]

    # ==============================================================
    # 6. 计算 Hypervolume 指标
    # ==============================================================
    # 参考点应 "支配" 所有 Pareto 解（取各目标最大值 * 1.1）
    ref_point = pareto_F.max(axis=0) * 1.1 + 1e-6
    hv_indicator = HV(ref_point=ref_point)
    hypervolume = float(hv_indicator(pareto_F))

    # 计算每代 Hypervolume 用于收敛曲线
    hv_history = []
    for entry in res.history:
        gen_F = entry.opt.get("F")
        if gen_F is not None and len(gen_F) > 0:
            hv_val = float(hv_indicator(gen_F))
            hv_history.append(hv_val)
        else:
            hv_history.append(0.0)

    generations = list(range(1, len(hv_history) + 1))

    # ==============================================================
    # 7. 可视化
    # ==============================================================

    # --- 图 1: Pareto 前沿散点图（标注折中解） ---
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    ax1.scatter(
        pareto_F[:, 0], pareto_F[:, 1],
        c="steelblue", alpha=0.7, edgecolors="white", s=40, label="Pareto 解"
    )
    ax1.scatter(
        compromise_F[0], compromise_F[1],
        c="red", marker="*", s=250, zorder=5,
        edgecolors="black", linewidths=0.8,
        label=f"TOPSIS 折中解 ({compromise_F[0]:.4f}, {compromise_F[1]:.4f})"
    )
    ax1.set_xlabel("目标 1", fontsize=12)
    ax1.set_ylabel("目标 2", fontsize=12)
    ax1.set_title("NSGA-II Pareto 前沿", fontsize=14)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    fig1.savefig("pareto_front.png", dpi=150, bbox_inches="tight")
    plt.close(fig1)
    print("===FIGURE: pareto_front.png | NSGA-II Pareto 前沿===")

    # --- 图 2: Hypervolume 收敛曲线 ---
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.plot(generations, hv_history, "b-", linewidth=1.5, alpha=0.8)
    ax2.fill_between(generations, hv_history, alpha=0.1, color="blue")
    ax2.set_xlabel("迭代代数", fontsize=12)
    ax2.set_ylabel("Hypervolume", fontsize=12)
    ax2.set_title("NSGA-II 收敛曲线 (Hypervolume)", fontsize=14)
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig("convergence_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print("===FIGURE: convergence_curve.png | NSGA-II 收敛曲线 (Hypervolume)===")

    # ==============================================================
    # 8. 结构化指标输出
    # ==============================================================
    metrics = {
        "hypervolume": round(hypervolume, 6),
        "pareto_size": len(pareto_F),
        "compromise_objectives": [round(float(v), 6) for v in compromise_F],
        "compromise_variables": [round(float(v), 6) for v in compromise_X],
        "ref_point": [round(float(v), 6) for v in ref_point],
        "final_gen_hv": round(hv_history[-1], 6) if hv_history else None,
    }
    print("===METRICS_START===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print("===METRICS_END===")

    print(f"\\n[结果] Pareto 解集大小: {len(pareto_F)}")
    print(f"[结果] Hypervolume: {hypervolume:.6f}")
    print(f"[结果] TOPSIS 折中解目标值: {compromise_F}")
    print(f"[结果] TOPSIS 折中解决策变量: {compromise_X}")

else:
    # ==============================================================
    # 降级方案: scipy 加权和法近似 Pareto 前沿
    # ==============================================================
    from scipy.optimize import differential_evolution

    # TODO: 替换为实际目标函数
    def f1(x):
        return x[0] ** 2 + x[1] ** 2

    def f2(x):
        return (x[0] - 1) ** 2 + (x[1] - 1) ** 2

    bounds_fallback = [(-5, 5), (-5, 5)]  # TODO: 替换

    n_weights = 50
    pareto_f_list = []
    pareto_x_list = []
    for w in np.linspace(0, 1, n_weights):
        def weighted(x, w=w):
            return w * f1(x) + (1 - w) * f2(x)
        result = differential_evolution(weighted, bounds_fallback, seed=42, tol=1e-8)
        if result.success:
            pareto_f_list.append([f1(result.x), f2(result.x)])
            pareto_x_list.append(result.x.tolist())

    pareto_f_arr = np.array(pareto_f_list)

    # TOPSIS 折中解
    compromise_idx = topsis_select(pareto_f_arr)
    compromise_F = pareto_f_arr[compromise_idx]
    compromise_X = pareto_x_list[compromise_idx]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(pareto_f_arr[:, 0], pareto_f_arr[:, 1], c="steelblue", alpha=0.6, label="Pareto 近似解")
    ax.scatter(
        compromise_F[0], compromise_F[1],
        c="red", marker="*", s=250, zorder=5,
        label=f"TOPSIS 折中解 ({compromise_F[0]:.4f}, {compromise_F[1]:.4f})"
    )
    ax.set_xlabel("目标 1")
    ax.set_ylabel("目标 2")
    ax.set_title("Pareto 前沿 (加权和法降级)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("pareto_front.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("===FIGURE: pareto_front.png | Pareto 前沿 (加权和法降级)===")

    metrics = {
        "method": "weighted_sum_fallback",
        "pareto_size": len(pareto_f_arr),
        "compromise_objectives": [round(float(v), 6) for v in compromise_F],
        "compromise_variables": [round(float(v), 6) for v in compromise_X],
    }
    print("===METRICS_START===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print("===METRICS_END===")

    print(f"\\n[降级] 找到 {len(pareto_f_arr)} 个 Pareto 近似解 (加权和法)")
    print(f"[降级] TOPSIS 折中解目标值: {compromise_F}")
''',
    ),
    "simulated_annealing_tpl": CodeTemplate(
        name="模拟退火算法",
        category="优化",
        description="模拟退火求解组合优化或连续优化问题",
        applicable_models=["模拟退火", "SA", "simulated_annealing"],
        dependencies=["numpy", "scipy"],
        code='''import numpy as np
from scipy.optimize import dual_annealing

# 目标函数
def objective(x):
    return ...  # TODO: 替换

# 变量界
bounds = [(-10, 10), (-10, 10)]  # TODO: 替换

result = dual_annealing(objective, bounds=bounds, maxiter=1000, seed=42)

print(f"最优值: {result.fun:.6f}")
print(f"最优解: {result.x}")
print(f"成功: {result.success}")
''',
    ),
    "pso_optimization": CodeTemplate(
        name="粒子群优化算法",
        category="优化",
        description="PSO 粒子群算法求解连续优化问题",
        applicable_models=["粒子群", "PSO", "particle_swarm"],
        dependencies=["numpy"],
        code='''import numpy as np

# 目标函数 (最小化)
def objective(x):
    return ...  # TODO: 替换

# ========== PSO 参数 ==========
bounds = [(-10, 10), (-10, 10)]  # TODO: 替换为各维变量界
n_particles = 50   # 粒子数
max_iter = 200      # 最大迭代
w = 0.7             # 惯性权重
c1 = 1.5            # 个体学习因子
c2 = 1.5            # 社会学习因子

np.random.seed(42)
n_dims = len(bounds)
lb = np.array([b[0] for b in bounds])
ub = np.array([b[1] for b in bounds])

# 初始化粒子位置和速度
positions = np.random.uniform(lb, ub, (n_particles, n_dims))
velocities = np.random.uniform(-(ub-lb)*0.1, (ub-lb)*0.1, (n_particles, n_dims))
personal_best_pos = positions.copy()
personal_best_val = np.array([objective(p) for p in positions])
global_best_idx = np.argmin(personal_best_val)
global_best_pos = personal_best_pos[global_best_idx].copy()
global_best_val = personal_best_val[global_best_idx]

# 迭代优化
for it in range(max_iter):
    r1 = np.random.random((n_particles, n_dims))
    r2 = np.random.random((n_particles, n_dims))
    velocities = (w * velocities
                  + c1 * r1 * (personal_best_pos - positions)
                  + c2 * r2 * (global_best_pos - positions))
    positions = np.clip(positions + velocities, lb, ub)
    for i in range(n_particles):
        val = objective(positions[i])
        if val < personal_best_val[i]:
            personal_best_val[i] = val
            personal_best_pos[i] = positions[i].copy()
            if val < global_best_val:
                global_best_val = val
                global_best_pos = positions[i].copy()

print(f"PSO 最优值: {global_best_val:.6f}")
print(f"PSO 最优解: {global_best_pos}")
print(f"粒子数={n_particles}, 迭代={max_iter}")
''',
    ),
    "nonlinear_program": CodeTemplate(
        name="非线性规划求解",
        category="优化",
        description="使用 scipy.optimize.minimize 求解非线性规划问题",
        applicable_models=["非线性规划", "NLP", "nonlinear_programming"],
        dependencies=["scipy", "numpy"],
        code='''import numpy as np
from scipy.optimize import minimize

# 目标函数
def objective(x):
    return x[0]**2 + x[1]**2  # TODO: 替换为实际目标函数

# 约束条件
constraints = [
    {"type": "ineq", "fun": lambda x: x[0] + x[1] - 1},  # g(x) >= 0
    {"type": "eq", "fun": lambda x: x[0] - x[1]},        # h(x) = 0
]  # TODO: 替换为实际约束

# 变量界
bounds = [(-10, 10), (-10, 10)]  # TODO: 替换
x0 = np.array([0.5, 0.5])  # 初始点

result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints)

print(f"最优值: {result.fun:.6f}")
print(f"最优解: {result.x}")
print(f"成功: {result.success}")
print(f"消息: {result.message}")
''',
    ),
    "genetic_algorithm": CodeTemplate(
        name="遗传算法",
        category="优化",
        description="遗传算法求解组合/连续优化问题",
        applicable_models=["遗传算法", "GA", "genetic_algorithm"],
        dependencies=["numpy"],
        code='''import numpy as np

def objective(x):
    return -(x[0]**2 + x[1]**2)  # TODO: 替换（负号表示最大化转最小化）

# 参数设置
bounds = np.array([[-5, 5], [-5, 5]])  # TODO: 替换
pop_size, n_gen = 100, 200
n_vars = len(bounds)
pc, pm = 0.8, 0.1  # 交叉/变异概率

# 初始化种群
pop = bounds[:, 0] + (bounds[:, 1] - bounds[:, 0]) * np.random.rand(pop_size, n_vars)
fitness = np.array([objective(ind) for ind in pop])

for gen in range(n_gen):
    # 轮盘赌选择
    f_shifted = fitness - fitness.min() + 1e-6
    prob = f_shifted / f_shifted.sum()
    parents_idx = np.random.choice(pop_size, pop_size, p=prob)
    parents = pop[parents_idx]

    # 交叉（单点）
    offspring = parents.copy()
    for i in range(0, pop_size - 1, 2):
        if np.random.rand() < pc:
            pt = np.random.randint(1, n_vars)
            offspring[i, pt:], offspring[i+1, pt:] = parents[i+1, pt:].copy(), parents[i, pt:].copy()

    # 变异
    for i in range(pop_size):
        if np.random.rand() < pm:
            j = np.random.randint(n_vars)
            offspring[i, j] = bounds[j, 0] + (bounds[j, 1] - bounds[j, 0]) * np.random.rand()

    # 边界裁剪
    offspring = np.clip(offspring, bounds[:, 0], bounds[:, 1])

    # 精英保留
    new_fitness = np.array([objective(ind) for ind in offspring])
    best_idx = np.argmin(fitness)
    worst_idx = np.argmax(new_fitness)
    offspring[worst_idx] = pop[best_idx]
    new_fitness[worst_idx] = fitness[best_idx]

    pop, fitness = offspring, new_fitness

best_idx = np.argmin(fitness)
print(f"最优值: {fitness[best_idx]:.6f}")
print(f"最优解: {pop[best_idx]}")
''',
    ),
    "monte_carlo_simulation": CodeTemplate(
        name="蒙特卡洛模拟",
        category="优化",
        description="蒙特卡洛方法进行随机模拟和积分估计",
        applicable_models=["蒙特卡洛", "Monte Carlo", "monte_carlo", "随机模拟"],
        dependencies=["numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)
n_simulations = 10000

# 示例：模拟估计圆周率
# TODO: 替换为实际模拟逻辑
x = np.random.uniform(-1, 1, n_simulations)
y = np.random.uniform(-1, 1, n_simulations)
inside = (x**2 + y**2) <= 1
pi_estimate = 4 * inside.sum() / n_simulations

print(f"模拟次数: {n_simulations}")
print(f"估计值: {pi_estimate:.6f}")

# 收敛性分析
estimates = []
for n in range(100, n_simulations + 1, 100):
    est = 4 * inside[:n].sum() / n
    estimates.append(est)

plt.figure(figsize=(10, 5))
plt.plot(range(100, n_simulations + 1, 100), estimates, "b-", alpha=0.7)
plt.axhline(y=np.pi, color="r", linestyle="--", label="真值")
plt.xlabel("模拟次数"); plt.ylabel("估计值")
plt.title("蒙特卡洛模拟收敛性"); plt.legend(); plt.grid(True)
plt.tight_layout(); plt.savefig("monte_carlo.png", dpi=150)
plt.show()
''',
    ),
}
