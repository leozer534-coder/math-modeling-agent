"""博弈论类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

GAME_THEORY_TEMPLATES = {
    "nash_equilibrium": CodeTemplate(
        name="纳什均衡博弈分析",
        category="博弈论",
        description="求解双人有限策略博弈的纳什均衡（纯策略和混合策略）",
        applicable_models=[
            "纳什均衡", "Nash", "博弈论", "Game Theory", "game_theory",
            "零和博弈", "混合策略", "纯策略均衡",
        ],
        dependencies=["numpy", "scipy", "matplotlib", "nashpy"],
        code='''import numpy as np
import matplotlib.pyplot as plt

# ========== 收益矩阵定义 ==========
# 行玩家（玩家1）的收益矩阵
A = np.array([
    [3, 0],
    [5, 1],
])  # TODO: 替换为实际收益矩阵

# 列玩家（玩家2）的收益矩阵
B = np.array([
    [3, 5],
    [0, 1],
])  # TODO: 替换为实际收益矩阵

strategy_names_p1 = ["策略1", "策略2"]  # TODO: 替换为实际策略名称
strategy_names_p2 = ["策略A", "策略B"]  # TODO: 替换为实际策略名称

n_strategies_p1, n_strategies_p2 = A.shape

print("=" * 60)
print("博弈论分析 - 纳什均衡求解")
print("=" * 60)
print(f"\\n玩家1策略数: {n_strategies_p1}, 玩家2策略数: {n_strategies_p2}")
print(f"\\n玩家1收益矩阵 A:\\n{A}")
print(f"\\n玩家2收益矩阵 B:\\n{B}")

# ========== 纯策略纳什均衡 ==========
print("\\n" + "-" * 40)
print("1. 纯策略纳什均衡")
print("-" * 40)

pure_nash = []
for i in range(n_strategies_p1):
    for j in range(n_strategies_p2):
        # 玩家1: 固定j列，检查i行是否为最大值
        is_best_p1 = A[i, j] == np.max(A[:, j])
        # 玩家2: 固定i行，检查j列是否为最大值
        is_best_p2 = B[i, j] == np.max(B[i, :])
        if is_best_p1 and is_best_p2:
            pure_nash.append((i, j))
            print(f"  纯策略均衡: ({strategy_names_p1[i]}, {strategy_names_p2[j]})")
            print(f"    收益: 玩家1={A[i, j]}, 玩家2={B[i, j]}")

if not pure_nash:
    print("  未找到纯策略纳什均衡")

# ========== 混合策略纳什均衡 ==========
print("\\n" + "-" * 40)
print("2. 混合策略纳什均衡")
print("-" * 40)

nash_equilibria = []

try:
    import nashpy as nash

    game = nash.Game(A, B)

    # Support Enumeration 方法
    print("\\n  [Support Enumeration]")
    for i, eq in enumerate(game.support_enumeration()):
        p1_strategy, p2_strategy = eq
        p1_payoff = p1_strategy @ A @ p2_strategy
        p2_payoff = p1_strategy @ B @ p2_strategy
        nash_equilibria.append({
            "method": "support_enumeration",
            "p1": p1_strategy,
            "p2": p2_strategy,
            "p1_payoff": p1_payoff,
            "p2_payoff": p2_payoff,
        })
        print(f"    均衡 {i+1}:")
        print(f"      玩家1混合策略: {np.round(p1_strategy, 4)}")
        print(f"      玩家2混合策略: {np.round(p2_strategy, 4)}")
        print(f"      期望收益: 玩家1={p1_payoff:.4f}, 玩家2={p2_payoff:.4f}")

    # Vertex Enumeration 方法
    print("\\n  [Vertex Enumeration]")
    for i, eq in enumerate(game.vertex_enumeration()):
        p1_strategy, p2_strategy = eq
        p1_payoff = p1_strategy @ A @ p2_strategy
        p2_payoff = p1_strategy @ B @ p2_strategy
        print(f"    均衡 {i+1}:")
        print(f"      玩家1混合策略: {np.round(p1_strategy, 4)}")
        print(f"      玩家2混合策略: {np.round(p2_strategy, 4)}")
        print(f"      期望收益: 玩家1={p1_payoff:.4f}, 玩家2={p2_payoff:.4f}")

except ImportError:
    print("  nashpy 未安装，使用 scipy 线性规划降级求解 (仅支持2x2博弈)")
    from scipy.optimize import linprog

    if n_strategies_p1 == 2 and n_strategies_p2 == 2:
        # 玩家2的混合策略: 使玩家1的两个纯策略期望收益相等
        # A[0,:] @ q = A[1,:] @ q => (A[0,:]-A[1,:]) @ q = 0
        diff_A = A[0, :] - A[1, :]
        if abs(diff_A[0] - diff_A[1]) > 1e-10:
            q2 = diff_A[0] / (diff_A[0] - diff_A[1])
            q2 = np.clip(q2, 0, 1)
            q = np.array([1 - q2, q2])
        else:
            q = np.array([0.5, 0.5])

        # 玩家1的混合策略: 使玩家2的两个纯策略期望收益相等
        diff_B = B[:, 0] - B[:, 1]
        if abs(diff_B[0] - diff_B[1]) > 1e-10:
            p2 = diff_B[0] / (diff_B[0] - diff_B[1])
            p2 = np.clip(p2, 0, 1)
            p = np.array([1 - p2, p2])
        else:
            p = np.array([0.5, 0.5])

        p1_payoff = p @ A @ q
        p2_payoff = p @ B @ q
        nash_equilibria.append({
            "method": "scipy_fallback",
            "p1": p,
            "p2": q,
            "p1_payoff": p1_payoff,
            "p2_payoff": p2_payoff,
        })
        print(f"    玩家1混合策略: {np.round(p, 4)}")
        print(f"    玩家2混合策略: {np.round(q, 4)}")
        print(f"    期望收益: 玩家1={p1_payoff:.4f}, 玩家2={p2_payoff:.4f}")
    else:
        print("    scipy 降级方案仅支持 2x2 博弈，请安装 nashpy")

# ========== 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 图1: 收益矩阵热力图
ax1 = axes[0]
combined = np.zeros_like(A, dtype=object)
for i in range(n_strategies_p1):
    for j in range(n_strategies_p2):
        combined[i, j] = f"({A[i,j]}, {B[i,j]})"

im = ax1.imshow(A, cmap="YlOrRd", alpha=0.7)
for i in range(n_strategies_p1):
    for j in range(n_strategies_p2):
        marker = " *" if (i, j) in pure_nash else ""
        ax1.text(j, i, f"({A[i,j]}, {B[i,j]}){marker}",
                 ha="center", va="center", fontsize=12, fontweight="bold")
ax1.set_xticks(range(n_strategies_p2))
ax1.set_xticklabels(strategy_names_p2)
ax1.set_yticks(range(n_strategies_p1))
ax1.set_yticklabels(strategy_names_p1)
ax1.set_xlabel("Player 2")
ax1.set_ylabel("Player 1")
ax1.set_title("Payoff Matrix (* = Pure NE)")
plt.colorbar(im, ax=ax1, shrink=0.8)

# 图2: 混合策略概率分布柱状图
ax2 = axes[1]
if nash_equilibria:
    eq = nash_equilibria[0]
    x_pos = np.arange(max(n_strategies_p1, n_strategies_p2))
    width = 0.35

    bars1 = ax2.bar(x_pos[:n_strategies_p1] - width/2, eq["p1"],
                    width, label="Player 1", color="steelblue", alpha=0.8)
    bars2 = ax2.bar(x_pos[:n_strategies_p2] + width/2, eq["p2"],
                    width, label="Player 2", color="coral", alpha=0.8)

    for bar in bars1:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                 f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=10)
    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                 f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=10)

    labels = [f"Strategy {i+1}" for i in range(max(n_strategies_p1, n_strategies_p2))]
    ax2.set_xticks(x_pos[:max(n_strategies_p1, n_strategies_p2)])
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Probability")
    ax2.set_title("Mixed Strategy Probability Distribution")
    ax2.legend()
    ax2.set_ylim(0, 1.15)
    ax2.grid(axis="y", alpha=0.3)
else:
    ax2.text(0.5, 0.5, "No Mixed NE Found", ha="center", va="center",
             transform=ax2.transAxes, fontsize=14)
    ax2.set_title("Mixed Strategy Probability Distribution")

plt.tight_layout()
plt.savefig("nash_equilibrium.png", dpi=150, bbox_inches="tight")
plt.show()
print("\\n[图片已保存: nash_equilibrium.png]")

# ========== 结构化输出 ==========
print("\\n" + "=" * 60)
print("<<< STRUCTURED_OUTPUT >>>")
print(f"纯策略纳什均衡数量: {len(pure_nash)}")
for idx, (i, j) in enumerate(pure_nash):
    print(f"  纯策略均衡 {idx+1}: ({strategy_names_p1[i]}, {strategy_names_p2[j]}), "
          f"收益=({A[i,j]}, {B[i,j]})")
print(f"混合策略纳什均衡数量: {len(nash_equilibria)}")
for idx, eq in enumerate(nash_equilibria):
    print(f"  混合均衡 {idx+1} [{eq['method']}]:")
    print(f"    P1策略概率: {np.round(eq['p1'], 4)}")
    print(f"    P2策略概率: {np.round(eq['p2'], 4)}")
    print(f"    期望收益: P1={eq['p1_payoff']:.4f}, P2={eq['p2_payoff']:.4f}")
print("<<< /STRUCTURED_OUTPUT >>>")
''',
    ),
    "evolutionary_game": CodeTemplate(
        name="演化博弈动态分析",
        category="博弈论",
        description="演化博弈论的复制者动态方程求解与相位图分析",
        applicable_models=[
            "演化博弈", "evolutionary game", "复制者动态",
            "演化稳定策略", "ESS", "replicator dynamics",
        ],
        dependencies=["numpy", "scipy", "matplotlib"],
        code='''import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ========== 博弈收益矩阵定义 ==========
# 对称博弈的收益矩阵 (策略1 vs 策略2)
# 行: 自己的策略, 列: 对手的策略
# payoff_matrix[i][j] = 采用策略i对抗策略j时的收益
payoff_matrix = np.array([
    [3, 0],
    [5, 1],
])  # TODO: 替换为实际收益矩阵

strategy_names = ["合作", "背叛"]  # TODO: 替换为实际策略名称
n_strategies = len(payoff_matrix)

print("=" * 60)
print("演化博弈动态分析 - 复制者动态")
print("=" * 60)
print(f"\\n收益矩阵:\\n{payoff_matrix}")
print(f"策略: {strategy_names}")

# ========== 复制者动态方程 ==========
def replicator_dynamics(t, x, A):
    """复制者动态微分方程。

    dx_i/dt = x_i * [(Ax)_i - x^T A x]

    Args:
        t: 时间（ODE 求解器需要）
        x: 各策略的种群比例向量
        A: 收益矩阵
    """
    # 确保比例非负且归一化
    x = np.maximum(x, 0)
    x_sum = np.sum(x)
    if x_sum > 0:
        x = x / x_sum

    # 各策略的适应度（期望收益）
    fitness = A @ x

    # 种群平均适应度
    avg_fitness = x @ fitness

    # 复制者动态方程
    dxdt = x * (fitness - avg_fitness)
    return dxdt


# ========== 数值求解 ==========
t_span = (0, 50)  # TODO: 调整时间范围
t_eval = np.linspace(t_span[0], t_span[1], 1000)

# 多个初始条件的演化轨迹
initial_conditions = [
    [0.1, 0.9],
    [0.3, 0.7],
    [0.5, 0.5],
    [0.7, 0.3],
    [0.9, 0.1],
]  # TODO: 按需调整初始条件

trajectories = []
for x0 in initial_conditions:
    x0 = np.array(x0, dtype=float)
    sol = solve_ivp(
        replicator_dynamics,
        t_span,
        x0,
        t_eval=t_eval,
        args=(payoff_matrix,),
        method="RK45",
        dense_output=True,
        rtol=1e-8,
        atol=1e-10,
    )
    trajectories.append(sol)

# ========== 稳定性分析 (雅可比矩阵) ==========
print("\\n" + "-" * 40)
print("稳定性分析")
print("-" * 40)

# 对于 2x2 博弈，只需分析 x1 的动态（x2 = 1 - x1）
# dx1/dt = x1 * (1-x1) * [(A[0,0]-A[1,0]) - (A[0,0]-A[1,0]+A[1,1]-A[0,1]) * x1]
if n_strategies == 2:
    a = payoff_matrix[0, 0] - payoff_matrix[1, 0]
    b = payoff_matrix[1, 1] - payoff_matrix[0, 1]

    equilibria_1d = [0.0, 1.0]  # x1 = 0 和 x1 = 1 始终是不动点
    if abs(a + b) > 1e-10:
        x_interior = a / (a + b)
        if 0 < x_interior < 1:
            equilibria_1d.append(x_interior)

    print("\\n不动点及稳定性:")
    for x_eq in equilibria_1d:
        # 雅可比矩阵 (1D): df/dx1 在不动点处的值
        # f(x1) = x1*(1-x1)*(a - (a+b)*x1)  其中 a, b 如上定义
        # f'(x1) = (1-2*x1)*(a-(a+b)*x1) + x1*(1-x1)*(-(a+b))
        jacobian_val = (1 - 2 * x_eq) * (a - (a + b) * x_eq) + \
                       x_eq * (1 - x_eq) * (-(a + b))

        if abs(jacobian_val) < 1e-10:
            stability = "中性稳定"
        elif jacobian_val < 0:
            stability = "渐近稳定 (ESS)"
        else:
            stability = "不稳定"

        x_full = [x_eq, 1 - x_eq]
        print(f"  x = [{x_eq:.4f}, {1-x_eq:.4f}] "
              f"({strategy_names[0]}={x_eq:.2%}, {strategy_names[1]}={1-x_eq:.2%})")
        print(f"    雅可比特征值: {jacobian_val:.6f} => {stability}")

# ========== 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 图1: 演化动态轨迹图
ax1 = axes[0]
colors = plt.cm.viridis(np.linspace(0, 1, len(trajectories)))
for idx, sol in enumerate(trajectories):
    x0_label = f"x0=({initial_conditions[idx][0]:.1f}, {initial_conditions[idx][1]:.1f})"
    ax1.plot(sol.t, sol.y[0], color=colors[idx], linewidth=1.5, label=x0_label)

ax1.set_xlabel("Time (t)", fontsize=12)
ax1.set_ylabel(f"Proportion of '{strategy_names[0]}'", fontsize=12)
ax1.set_title("Replicator Dynamics Trajectories", fontsize=13)
ax1.set_ylim(-0.05, 1.05)
ax1.legend(fontsize=9, loc="best")
ax1.grid(True, alpha=0.3)

# 标注不动点
if n_strategies == 2:
    for x_eq in equilibria_1d:
        ax1.axhline(y=x_eq, color="red", linestyle="--", alpha=0.4)

# 图2: 相位图 (2策略时为1D相位图, 展示 dx/dt vs x)
ax2 = axes[1]
if n_strategies == 2:
    x_range = np.linspace(0, 1, 500)
    dxdt_values = []
    for x1 in x_range:
        x_vec = np.array([x1, 1 - x1])
        dx = replicator_dynamics(0, x_vec, payoff_matrix)
        dxdt_values.append(dx[0])
    dxdt_values = np.array(dxdt_values)

    ax2.plot(x_range, dxdt_values, "b-", linewidth=2, label="dx1/dt")
    ax2.axhline(y=0, color="black", linewidth=0.8)
    ax2.fill_between(x_range, dxdt_values, 0,
                     where=(dxdt_values > 0), alpha=0.15, color="green", label="Increasing")
    ax2.fill_between(x_range, dxdt_values, 0,
                     where=(dxdt_values < 0), alpha=0.15, color="red", label="Decreasing")

    # 标注不动点
    for x_eq in equilibria_1d:
        ax2.plot(x_eq, 0, "ro", markersize=10, zorder=5)
        ax2.annotate(f"x={x_eq:.3f}", (x_eq, 0),
                     textcoords="offset points", xytext=(10, 15),
                     fontsize=10, arrowprops=dict(arrowstyle="->", color="red"))

    ax2.set_xlabel(f"Proportion of '{strategy_names[0]}' (x1)", fontsize=12)
    ax2.set_ylabel("dx1/dt", fontsize=12)
    ax2.set_title("Phase Portrait (1D)", fontsize=13)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("evolutionary_game.png", dpi=150, bbox_inches="tight")
plt.show()
print("\\n[图片已保存: evolutionary_game.png]")

# ========== 结构化输出 ==========
print("\\n" + "=" * 60)
print("<<< STRUCTURED_OUTPUT >>>")
print(f"博弈类型: {n_strategies}策略对称博弈")
print(f"策略: {strategy_names}")
print(f"收益矩阵:\\n{payoff_matrix}")
if n_strategies == 2:
    print(f"\\n不动点:")
    for x_eq in equilibria_1d:
        jacobian_val = (1 - 2 * x_eq) * (a - (a + b) * x_eq) + \
                       x_eq * (1 - x_eq) * (-(a + b))
        if abs(jacobian_val) < 1e-10:
            stability = "中性稳定"
        elif jacobian_val < 0:
            stability = "ESS (演化稳定策略)"
        else:
            stability = "不稳定"
        print(f"  x*=[{x_eq:.4f}, {1-x_eq:.4f}], "
              f"特征值={jacobian_val:.6f}, 稳定性={stability}")
print(f"\\n各初始条件的终态:")
for idx, sol in enumerate(trajectories):
    final_x = sol.y[:, -1]
    final_x = np.maximum(final_x, 0)
    final_x = final_x / final_x.sum()
    print(f"  x0={initial_conditions[idx]} => x_final={np.round(final_x, 4)}")
print("<<< /STRUCTURED_OUTPUT >>>")
''',
    ),
}
