"""微分方程模型代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

ODE_TEMPLATES = {
    "ode_solver": CodeTemplate(
        name="ODE数值求解",
        category="微分方程",
        description="使用 scipy.integrate.solve_ivp 求解常微分方程组，"
        "支持多变量动力系统和相图绘制。",
        applicable_models=["ODE", "常微分方程", "微分方程", "动力系统", "数值积分"],
        dependencies=["scipy", "numpy", "matplotlib"],
        placeholders={
            "{{T_START}}": "时间起点，默认 0",
            "{{T_END}}": "时间终点，默认 50",
            "{{Y0}}": "初始条件列表，如 [1.0, 0.0]",
        },
        code='''import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ===== 定义微分方程组 dy/dt = f(t, y) =====
def ode_system(t, y):
    """
    示例: 阻尼振荡器
      y[0]' = y[1]
      y[1]' = -0.5 * y[1] - 2.0 * y[0]
    TODO: 替换为实际方程
    """
    dydt = [
        y[1],
        -0.5 * y[1] - 2.0 * y[0],
    ]
    return dydt

# ===== 求解参数 =====
t_span = ({{T_START}}, {{T_END}})
y0 = {{Y0}}
t_eval = np.linspace(t_span[0], t_span[1], 1000)

# ===== 数值求解 =====
sol = solve_ivp(ode_system, t_span, y0, method="RK45", t_eval=t_eval, dense_output=True)
print(f"求解状态: {'成功' if sol.success else '失败'}")
print(f"时间步数: {len(sol.t)}")
print(f"终态: {sol.y[:, -1]}")

# ===== 时间序列图 =====
fig, axes = plt.subplots(len(y0), 1, figsize=(12, 4 * len(y0)), sharex=True)
if len(y0) == 1:
    axes = [axes]
var_names = [f"y{i}" for i in range(len(y0))]

for i, ax in enumerate(axes):
    ax.plot(sol.t, sol.y[i], linewidth=1.5)
    ax.set_ylabel(var_names[i], fontsize=12)
    ax.grid(True, alpha=0.3)
axes[-1].set_xlabel("时间 t")
axes[0].set_title("ODE 数值解")
plt.tight_layout()
plt.savefig("ode_time_series.png", dpi=150)
print("时间序列图已保存: ode_time_series.png")

# ===== 相图 (适用于 2 维系统) =====
if len(y0) >= 2:
    plt.figure(figsize=(8, 8))
    plt.plot(sol.y[0], sol.y[1], linewidth=1.0, alpha=0.8)
    plt.plot(sol.y[0, 0], sol.y[1, 0], "go", markersize=10, label="起点")
    plt.plot(sol.y[0, -1], sol.y[1, -1], "rs", markersize=10, label="终点")
    plt.xlabel(var_names[0])
    plt.ylabel(var_names[1])
    plt.title("相平面轨迹")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("ode_phase_portrait.png", dpi=150)
    print("相图已保存: ode_phase_portrait.png")
''',
    ),
    "sir_model": CodeTemplate(
        name="SIR传染病模型",
        category="微分方程",
        description="经典 SIR 三箱传染病模型，包含基本再生数 R0 计算、"
        "感染峰值预测和参数拟合。",
        applicable_models=["SIR", "传染病模型", "感染模型", "流行病"],
        dependencies=["scipy", "numpy", "matplotlib"],
        placeholders={
            "{{N}}": "总人口数",
            "{{I0}}": "初始感染人数",
            "{{BETA}}": "传播率，如 0.3",
            "{{GAMMA}}": "恢复率，如 0.1",
            "{{T_END}}": "模拟天数，默认 200",
        },
        code='''import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ===== SIR 模型参数 =====
N = {{N}}           # 总人口
I0 = {{I0}}         # 初始感染者
R0_init = 0         # 初始康复者
S0 = N - I0 - R0_init  # 初始易感者

beta = {{BETA}}     # 传播率 (每人每天有效接触率)
gamma = {{GAMMA}}   # 恢复率 (1/gamma = 平均感染期)

R0 = beta / gamma   # 基本再生数
print(f"基本再生数 R0 = {R0:.2f}")
print(f"{'疫情将爆发' if R0 > 1 else '疫情将自然消亡'}")

# ===== SIR 微分方程 =====
def sir_ode(t, y):
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return [dSdt, dIdt, dRdt]

# ===== 数值求解 =====
t_span = (0, {{T_END}})
t_eval = np.linspace(0, {{T_END}}, 1000)
sol = solve_ivp(sir_ode, t_span, [S0, I0, R0_init], t_eval=t_eval, method="RK45")

S, I, R = sol.y

# ===== 峰值分析 =====
peak_idx = np.argmax(I)
peak_day = sol.t[peak_idx]
peak_infected = I[peak_idx]
print(f"\\n感染峰值: 第 {peak_day:.0f} 天, 感染人数 {peak_infected:.0f}")
print(f"最终康复人数: {R[-1]:.0f} ({R[-1]/N*100:.1f}%)")
print(f"最终易感人数: {S[-1]:.0f} ({S[-1]/N*100:.1f}%)")

# ===== 可视化 =====
plt.figure(figsize=(12, 6))
plt.plot(sol.t, S, "b-", linewidth=2, label=f"易感者 S")
plt.plot(sol.t, I, "r-", linewidth=2, label=f"感染者 I")
plt.plot(sol.t, R, "g-", linewidth=2, label=f"康复者 R")
plt.axvline(x=peak_day, color="r", linestyle="--", alpha=0.5, label=f"峰值 (第{peak_day:.0f}天)")
plt.xlabel("时间 (天)")
plt.ylabel("人数")
plt.title(f"SIR 传染病模型 (R0={R0:.2f}, N={N})")
plt.legend(fontsize=11)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("sir_model.png", dpi=150)
print("SIR 模型图已保存: sir_model.png")
''',
    ),
    "seir_model": CodeTemplate(
        name="SEIR扩展传染病模型",
        category="微分方程",
        description="包含潜伏期 (Exposed) 的 SEIR 传染病模型，"
        "支持隔离策略模拟和不同干预措施对比。",
        applicable_models=["SEIR", "潜伏期", "隔离模型", "传染病扩展"],
        dependencies=["scipy", "numpy", "matplotlib"],
        placeholders={
            "{{N}}": "总人口数",
            "{{E0}}": "初始潜伏者人数",
            "{{I0}}": "初始感染人数",
            "{{BETA}}": "传播率，如 0.5",
            "{{SIGMA}}": "潜伏期转化率 (1/sigma = 平均潜伏期)，如 0.2",
            "{{GAMMA}}": "恢复率，如 0.1",
            "{{T_END}}": "模拟天数，默认 300",
        },
        code='''import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ===== SEIR 模型参数 =====
N = {{N}}
E0 = {{E0}}         # 初始潜伏者
I0 = {{I0}}         # 初始感染者
R0_init = 0
S0 = N - E0 - I0 - R0_init

beta = {{BETA}}     # 传播率
sigma = {{SIGMA}}   # 潜伏期转化率 (1/sigma = 平均潜伏期天数)
gamma = {{GAMMA}}   # 恢复率

R0 = beta / gamma
print(f"基本再生数 R0 = {R0:.2f}")
print(f"平均潜伏期: {1/sigma:.1f} 天, 平均感染期: {1/gamma:.1f} 天")

# ===== SEIR 微分方程 =====
def seir_ode(t, y, beta_val):
    S, E, I, R = y
    dSdt = -beta_val * S * I / N
    dEdt = beta_val * S * I / N - sigma * E
    dIdt = sigma * E - gamma * I
    dRdt = gamma * I
    return [dSdt, dEdt, dIdt, dRdt]

# ===== 场景对比: 无干预 vs 隔离措施 =====
t_span = (0, {{T_END}})
t_eval = np.linspace(0, {{T_END}}, 1000)
y0 = [S0, E0, I0, R0_init]

scenarios = {
    "无干预": beta,
    "弱隔离 (传播率降50%)": beta * 0.5,
    "强隔离 (传播率降80%)": beta * 0.2,
}

fig, axes = plt.subplots(1, len(scenarios), figsize=(6 * len(scenarios), 5))
colors = {"S": "blue", "E": "orange", "I": "red", "R": "green"}

for idx, (name, beta_val) in enumerate(scenarios.items()):
    sol = solve_ivp(
        lambda t, y: seir_ode(t, y, beta_val),
        t_span, y0, t_eval=t_eval, method="RK45",
    )
    S, E, I, R = sol.y
    peak_day = sol.t[np.argmax(I)]
    peak_I = np.max(I)

    ax = axes[idx] if len(scenarios) > 1 else axes
    ax.plot(sol.t, S, color=colors["S"], label="S")
    ax.plot(sol.t, E, color=colors["E"], label="E")
    ax.plot(sol.t, I, color=colors["I"], label="I")
    ax.plot(sol.t, R, color=colors["R"], label="R")
    ax.set_title(f"{name}\\n峰值: 第{peak_day:.0f}天, {peak_I:.0f}人")
    ax.set_xlabel("时间 (天)")
    ax.set_ylabel("人数")
    ax.legend()
    ax.grid(True, alpha=0.3)
    print(f"\\n{name}: 感染峰值 第{peak_day:.0f}天 / {peak_I:.0f}人, 最终康复 {R[-1]:.0f}")

plt.suptitle("SEIR 模型 - 隔离策略对比", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig("seir_model_comparison.png", dpi=150, bbox_inches="tight")
print("\\nSEIR 模型对比图已保存: seir_model_comparison.png")
''',
    ),
    "lotka_volterra": CodeTemplate(
        name="Lotka-Volterra捕食模型",
        category="微分方程",
        description="经典 Lotka-Volterra 捕食者-猎物动力学模型，"
        "包含相平面分析和种群周期性振荡可视化。",
        applicable_models=["Lotka-Volterra", "捕食模型", "种群动力学", "生态模型", "捕食者"],
        dependencies=["scipy", "numpy", "matplotlib"],
        placeholders={
            "{{ALPHA}}": "猎物增长率，如 1.0",
            "{{BETA}}": "捕食率，如 0.1",
            "{{DELTA}}": "捕食者增长率，如 0.075",
            "{{GAMMA_LV}}": "捕食者死亡率，如 1.5",
            "{{PREY0}}": "初始猎物数量，如 40",
            "{{PREDATOR0}}": "初始捕食者数量，如 9",
            "{{T_END}}": "模拟时间，默认 100",
        },
        code='''import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ===== Lotka-Volterra 参数 =====
alpha = {{ALPHA}}      # 猎物自然增长率
beta_lv = {{BETA}}     # 捕食率
delta = {{DELTA}}      # 捕食者因猎物增长率
gamma_lv = {{GAMMA_LV}}  # 捕食者自然死亡率

prey0 = {{PREY0}}
predator0 = {{PREDATOR0}}

# 平衡点
prey_eq = gamma_lv / delta
pred_eq = alpha / beta_lv
print(f"平衡点: 猎物 = {prey_eq:.2f}, 捕食者 = {pred_eq:.2f}")

# ===== Lotka-Volterra 方程 =====
def lotka_volterra(t, y):
    prey, predator = y
    dprey = alpha * prey - beta_lv * prey * predator
    dpredator = delta * prey * predator - gamma_lv * predator
    return [dprey, dpredator]

# ===== 数值求解 =====
t_span = (0, {{T_END}})
t_eval = np.linspace(0, {{T_END}}, 2000)
sol = solve_ivp(lotka_volterra, t_span, [prey0, predator0], t_eval=t_eval, method="RK45")
prey, predator = sol.y

# ===== 时间序列图 =====
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

axes[0].plot(sol.t, prey, "b-", linewidth=1.5, label="猎物")
axes[0].plot(sol.t, predator, "r-", linewidth=1.5, label="捕食者")
axes[0].set_xlabel("时间")
axes[0].set_ylabel("种群数量")
axes[0].set_title("Lotka-Volterra 种群动态")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# ===== 相平面图 =====
axes[1].plot(prey, predator, "g-", linewidth=0.8, alpha=0.7)
axes[1].plot(prey[0], predator[0], "ko", markersize=8, label="起点")
axes[1].plot(prey_eq, pred_eq, "r*", markersize=15, label=f"平衡点 ({prey_eq:.1f}, {pred_eq:.1f})")
axes[1].set_xlabel("猎物数量")
axes[1].set_ylabel("捕食者数量")
axes[1].set_title("相平面轨迹")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("lotka_volterra.png", dpi=150)
print("\\nLotka-Volterra 模型图已保存: lotka_volterra.png")

# 输出周期估计
from scipy.signal import find_peaks
peaks, _ = find_peaks(prey, distance=len(t_eval) // 20)
if len(peaks) >= 2:
    periods = np.diff(sol.t[peaks])
    print(f"猎物种群振荡周期: {np.mean(periods):.2f} (标准差: {np.std(periods):.2f})")
''',
    ),
}


def get_templates() -> list[CodeTemplate]:
    """返回所有微分方程模板列表。"""
    return list(ODE_TEMPLATES.values())
