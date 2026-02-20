"""概率统计模型代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

STATISTICS_TEMPLATES = {
    "hypothesis_test": CodeTemplate(
        name="假设检验",
        category="统计",
        description="使用 scipy.stats 进行多种假设检验，包含正态性检验 (Shapiro-Wilk)、"
        "t 检验、卡方检验、单因素 ANOVA 和显著性可视化。",
        applicable_models=["假设检验", "t检验", "卡方检验", "ANOVA", "显著性检验", "统计检验"],
        dependencies=["scipy", "numpy", "pandas", "matplotlib", "seaborn"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{GROUP_COLUMN}}": "分组变量列名",
            "{{VALUE_COLUMN}}": "数值变量列名",
            "{{ALPHA}}": "显著性水平，默认 0.05",
        },
        code='''import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
group_col = "{{GROUP_COLUMN}}"
value_col = "{{VALUE_COLUMN}}"
alpha = {{ALPHA}}

groups = df[group_col].unique()
group_data = [df[df[group_col] == g][value_col].dropna().values for g in groups]

print("=" * 50)
print("假设检验分析报告")
print("=" * 50)

# ===== 1. 正态性检验 (Shapiro-Wilk) =====
print("\\n[1] 正态性检验 (Shapiro-Wilk)")
all_normal = True
for g, data in zip(groups, group_data):
    if len(data) >= 3:
        stat, p = stats.shapiro(data)
        normal = "正态" if p > alpha else "非正态"
        if p <= alpha:
            all_normal = False
        print(f"  {g}: W={stat:.4f}, p={p:.4f} -> {normal}")

# ===== 2. 双样本检验 =====
if len(groups) == 2:
    print(f"\\n[2] 双样本检验 (alpha={alpha})")
    if all_normal:
        # Levene 方差齐性检验
        lev_stat, lev_p = stats.levene(*group_data)
        equal_var = lev_p > alpha
        print(f"  Levene 方差齐性: F={lev_stat:.4f}, p={lev_p:.4f} -> {'齐性' if equal_var else '不齐'}")
        # 独立样本 t 检验
        t_stat, t_p = stats.ttest_ind(*group_data, equal_var=equal_var)
        print(f"  t 检验: t={t_stat:.4f}, p={t_p:.4f} -> {'显著差异' if t_p < alpha else '无显著差异'}")
    else:
        # Mann-Whitney U 检验 (非参数)
        u_stat, u_p = stats.mannwhitneyu(*group_data, alternative="two-sided")
        print(f"  Mann-Whitney U: U={u_stat:.4f}, p={u_p:.4f} -> {'显著差异' if u_p < alpha else '无显著差异'}")

# ===== 3. 多组检验 (ANOVA / Kruskal-Wallis) =====
if len(groups) >= 3:
    print(f"\\n[3] 多组检验 (alpha={alpha})")
    if all_normal:
        f_stat, f_p = stats.f_oneway(*group_data)
        print(f"  单因素 ANOVA: F={f_stat:.4f}, p={f_p:.4f} -> {'显著差异' if f_p < alpha else '无显著差异'}")
    else:
        h_stat, h_p = stats.kruskal(*group_data)
        print(f"  Kruskal-Wallis: H={h_stat:.4f}, p={h_p:.4f} -> {'显著差异' if h_p < alpha else '无显著差异'}")

# ===== 可视化 =====
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 箱线图
sns.boxplot(data=df, x=group_col, y=value_col, ax=axes[0], palette="Set2")
axes[0].set_title("各组箱线图")
axes[0].grid(True, alpha=0.3)

# 分布直方图
for g, data in zip(groups, group_data):
    axes[1].hist(data, bins=15, alpha=0.5, label=str(g), density=True)
axes[1].set_xlabel(value_col)
axes[1].set_ylabel("密度")
axes[1].set_title("各组分布")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("hypothesis_test_results.png", dpi=150)
print("\\n检验结果可视化已保存: hypothesis_test_results.png")
''',
    ),
    "bayesian_inference": CodeTemplate(
        name="贝叶斯推断",
        category="统计",
        description="基于贝叶斯定理进行参数推断，包含先验分布设定、"
        "后验分布更新、可信区间计算和可视化。",
        applicable_models=["贝叶斯", "Bayesian", "后验推断", "先验", "贝叶斯估计"],
        dependencies=["scipy", "numpy", "matplotlib"],
        placeholders={
            "{{PRIOR_MEAN}}": "先验均值，如 0.5",
            "{{PRIOR_STD}}": "先验标准差，如 0.1",
            "{{OBSERVED_DATA}}": "观测数据列表，如 [0.52, 0.48, 0.55, ...]",
            "{{CREDIBLE_LEVEL}}": "可信水平，默认 0.95",
        },
        code='''import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

# ===== 参数设置 =====
prior_mean = {{PRIOR_MEAN}}
prior_std = {{PRIOR_STD}}
observed = np.array({{OBSERVED_DATA}})
credible_level = {{CREDIBLE_LEVEL}}

print("=" * 50)
print("贝叶斯推断分析报告")
print("=" * 50)

# ===== 先验分布 (正态) =====
prior_var = prior_std ** 2
print(f"\\n先验分布: N({prior_mean}, {prior_std}^2)")
print(f"观测数据: n={len(observed)}, 均值={observed.mean():.4f}, 标准差={observed.std():.4f}")

# ===== 似然函数参数 (假设已知方差用观测标准差) =====
obs_mean = observed.mean()
obs_var = observed.var()
n = len(observed)

# ===== 后验分布 (共轭正态-正态) =====
# 后验精度 = 先验精度 + 似然精度
posterior_var = 1.0 / (1.0 / prior_var + n / obs_var)
posterior_mean = posterior_var * (prior_mean / prior_var + n * obs_mean / obs_var)
posterior_std = np.sqrt(posterior_var)

print(f"\\n后验分布: N({posterior_mean:.4f}, {posterior_std:.4f}^2)")

# ===== 可信区间 =====
tail = (1 - credible_level) / 2
ci_low = stats.norm.ppf(tail, loc=posterior_mean, scale=posterior_std)
ci_high = stats.norm.ppf(1 - tail, loc=posterior_mean, scale=posterior_std)
print(f"{credible_level*100:.0f}% 可信区间: [{ci_low:.4f}, {ci_high:.4f}]")

# MAP 估计 (对于正态后验等于均值)
map_estimate = posterior_mean
print(f"MAP 估计: {map_estimate:.4f}")

# ===== 可视化 =====
x = np.linspace(
    min(prior_mean - 4 * prior_std, posterior_mean - 4 * posterior_std),
    max(prior_mean + 4 * prior_std, posterior_mean + 4 * posterior_std),
    500,
)

prior_pdf = stats.norm.pdf(x, loc=prior_mean, scale=prior_std)
posterior_pdf = stats.norm.pdf(x, loc=posterior_mean, scale=posterior_std)
likelihood_pdf = stats.norm.pdf(x, loc=obs_mean, scale=np.sqrt(obs_var / n))

plt.figure(figsize=(12, 6))
plt.plot(x, prior_pdf, "b--", linewidth=2, label=f"先验 N({prior_mean}, {prior_std:.2f})")
plt.plot(x, likelihood_pdf, "g:", linewidth=2, label=f"似然 (x̄={obs_mean:.4f})")
plt.plot(x, posterior_pdf, "r-", linewidth=2, label=f"后验 N({posterior_mean:.4f}, {posterior_std:.4f})")
plt.axvspan(ci_low, ci_high, alpha=0.15, color="red",
            label=f"{credible_level*100:.0f}% 可信区间 [{ci_low:.4f}, {ci_high:.4f}]")
plt.axvline(x=map_estimate, color="darkred", linestyle="-.", alpha=0.7, label=f"MAP={map_estimate:.4f}")
plt.xlabel("参数值")
plt.ylabel("概率密度")
plt.title("贝叶斯推断: 先验 → 后验更新")
plt.legend(fontsize=9)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("bayesian_inference.png", dpi=150)
print("\\n贝叶斯推断图已保存: bayesian_inference.png")
''',
    ),
    "grey_relational": CodeTemplate(
        name="灰色关联分析",
        category="统计",
        description="灰色关联分析 (GRA)，计算各因素序列与参考序列的关联度，"
        "支持关联系数矩阵和关联度排序输出。",
        applicable_models=["灰色关联", "GRA", "Grey Relational", "灰色系统"],
        dependencies=["numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{REFERENCE_COLUMN}}": "参考序列列名 (目标变量)",
            "{{RHO}}": "分辨系数，默认 0.5",
        },
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
ref_col = "{{REFERENCE_COLUMN}}"
rho = {{RHO}}

# 分离参考序列与比较序列
ref = df[ref_col].values
compare_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != ref_col]
compare = df[compare_cols].values

print("=" * 50)
print("灰色关联分析报告")
print(f"参考序列: {ref_col}")
print(f"比较序列: {compare_cols}")
print(f"分辨系数 rho = {rho}")
print("=" * 50)

# ===== 均值化无量纲处理 =====
ref_norm = ref / ref.mean()
compare_norm = compare / compare.mean(axis=0)

# ===== 计算差序列 =====
diff = np.abs(compare_norm - ref_norm.reshape(-1, 1))
delta_min = diff.min()
delta_max = diff.max()

# ===== 计算关联系数 =====
xi = (delta_min + rho * delta_max) / (diff + rho * delta_max)

# ===== 关联度 =====
grey_relational_grade = xi.mean(axis=0)
result_df = pd.DataFrame({
    "因素": compare_cols,
    "关联度": grey_relational_grade,
}).sort_values("关联度", ascending=False)

print("\\n灰色关联度排序:")
for idx, row in result_df.iterrows():
    print(f"  {row['因素']}: {row['关联度']:.4f}")

# ===== 可视化 =====
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 关联度柱状图
axes[0].barh(result_df["因素"], result_df["关联度"], color="steelblue")
axes[0].set_xlabel("关联度")
axes[0].set_title(f"灰色关联度排序 (rho={rho})")
axes[0].invert_yaxis()
axes[0].grid(True, alpha=0.3)

# 关联系数热力图
import seaborn as sns
xi_df = pd.DataFrame(xi, columns=compare_cols)
sns.heatmap(xi_df.T, cmap="YlOrRd", annot=False, ax=axes[1])
axes[1].set_xlabel("样本序号")
axes[1].set_ylabel("因素")
axes[1].set_title("关联系数矩阵热力图")

plt.tight_layout()
plt.savefig("grey_relational_analysis.png", dpi=150)
print("\\n灰色关联分析图已保存: grey_relational_analysis.png")
''',
    ),
    "grey_prediction": CodeTemplate(
        name="灰色预测GM(1,1)",
        category="统计",
        description="灰色预测 GM(1,1) 模型，含累加生成 (AGO)、参数估计、"
        "预测输出和残差检验 (后验差比检验)。",
        applicable_models=["GM(1,1)", "灰色预测", "Grey Prediction", "灰色模型"],
        dependencies=["numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{VALUE_COLUMN}}": "时间序列数据列名",
            "{{PREDICT_STEPS}}": "向前预测步数，默认 5",
        },
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
x0 = df["{{VALUE_COLUMN}}"].values.astype(float)
n = len(x0)
predict_steps = {{PREDICT_STEPS}}

print("=" * 50)
print("GM(1,1) 灰色预测模型")
print(f"原始数据长度: {n}, 预测步数: {predict_steps}")
print("=" * 50)

# ===== 1-AGO 累加生成 =====
x1 = np.cumsum(x0)

# ===== 构造紧邻均值生成序列 =====
z1 = 0.5 * (x1[:-1] + x1[1:])

# ===== 最小二乘参数估计 =====
B = np.column_stack([-z1, np.ones(n - 1)])
Y = x0[1:].reshape(-1, 1)
params = np.linalg.lstsq(B, Y, rcond=None)[0]
a, b = params.flatten()
print(f"\\n参数估计: a = {a:.6f}, b = {b:.6f}")

# ===== 预测 (累加序列) =====
total_len = n + predict_steps
x1_hat = np.zeros(total_len)
x1_hat[0] = x0[0]
for k in range(1, total_len):
    x1_hat[k] = (x0[0] - b / a) * np.exp(-a * k) + b / a

# ===== IAGO 累减还原 =====
x0_hat = np.zeros(total_len)
x0_hat[0] = x0[0]
x0_hat[1:] = np.diff(x1_hat)

# ===== 拟合精度评估 =====
residuals = x0 - x0_hat[:n]
relative_error = np.abs(residuals[1:]) / np.abs(x0[1:])  # 跳过第一个
avg_relative_error = relative_error.mean()

# 后验差比检验
s1 = np.std(x0, ddof=1)
s2 = np.std(residuals, ddof=1)
C = s2 / s1  # 后验差比
P = np.mean(np.abs(residuals - residuals.mean()) < 0.6745 * s1)  # 小误差概率

print(f"\\n模型评估:")
print(f"  平均相对误差: {avg_relative_error*100:.2f}%")
print(f"  后验差比 C = {C:.4f} ({'合格' if C < 0.65 else '不合格'})")
print(f"  小误差概率 P = {P:.4f} ({'合格' if P > 0.7 else '不合格'})")

grade_C = "优" if C < 0.35 else ("良" if C < 0.5 else ("合格" if C < 0.65 else "不合格"))
grade_P = "优" if P > 0.95 else ("良" if P > 0.8 else ("合格" if P > 0.7 else "不合格"))
print(f"  精度等级: C -> {grade_C}, P -> {grade_P}")

# ===== 预测结果 =====
print(f"\\n预测结果 (未来 {predict_steps} 步):")
for i in range(n, total_len):
    print(f"  第 {i + 1} 期: {x0_hat[i]:.4f}")

# ===== 可视化 =====
plt.figure(figsize=(12, 6))
t_all = np.arange(1, total_len + 1)
plt.plot(t_all[:n], x0, "bo-", markersize=6, label="原始数据")
plt.plot(t_all[:n], x0_hat[:n], "rs--", markersize=5, label="拟合值")
plt.plot(t_all[n:], x0_hat[n:], "g^--", markersize=6, label="预测值")
plt.axvline(x=n + 0.5, color="gray", linestyle=":", alpha=0.5, label="预测起点")
plt.xlabel("期数")
plt.ylabel("数值")
plt.title(f"GM(1,1) 灰色预测 (平均相对误差={avg_relative_error*100:.2f}%, C={C:.4f})")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grey_prediction_gm11.png", dpi=150)
print("\\nGM(1,1) 预测图已保存: grey_prediction_gm11.png")
''',
    ),
    "queuing_theory_tpl": CodeTemplate(
        name="排队论模型",
        category="统计",
        description="排队论经典模型，包含 M/M/1 单服务台和 M/M/c 多服务台模型，"
        "计算系统利用率、平均等待时间、平均队长等指标，并可视化到达率与等待时间的关系。",
        applicable_models=["排队论", "M/M/1", "M/M/c", "queuing", "等待时间", "服务系统"],
        dependencies=["numpy", "scipy", "matplotlib"],
        code='''import numpy as np
from scipy.special import factorial
import matplotlib.pyplot as plt

# ========== 排队论模型 ==========

# ===== 参数设置 =====
lam = 5.0    # 到达率 lambda (单位时间平均到达顾客数)  # TODO: 替换
mu = 8.0     # 服务率 mu (单位时间平均服务顾客数)      # TODO: 替换
c = 3        # 服务台数量 (M/M/c 模型使用)             # TODO: 替换

print("=" * 60)
print("排队论模型分析报告")
print("=" * 60)
print(f"到达率 lambda = {lam}")
print(f"服务率 mu = {mu}")
print(f"服务台数量 c = {c}")

# ========== 1. M/M/1 模型 ==========
print(f"\\n{'='*60}")
print("M/M/1 单服务台模型")
print("=" * 60)

rho_1 = lam / mu  # 系统利用率 (交通强度)

if rho_1 >= 1:
    print(f"系统利用率 rho = {rho_1:.4f} >= 1, 系统不稳定 (队列将无限增长)!")
else:
    # M/M/1 稳态指标
    Lq_1 = rho_1 ** 2 / (1 - rho_1)         # 平均排队队长 (不含正在服务的)
    Ls_1 = rho_1 / (1 - rho_1)               # 平均系统队长 (含正在服务的)
    Wq_1 = rho_1 / (mu * (1 - rho_1))        # 平均排队等待时间
    Ws_1 = 1 / (mu * (1 - rho_1))            # 平均逗留时间 (等待+服务)
    P0_1 = 1 - rho_1                          # 系统空闲概率

    print(f"  系统利用率 rho = {rho_1:.4f}")
    print(f"  系统空闲概率 P0 = {P0_1:.4f}")
    print(f"  平均排队队长 Lq = {Lq_1:.4f}")
    print(f"  平均系统队长 Ls = {Ls_1:.4f}")
    print(f"  平均排队等待时间 Wq = {Wq_1:.4f}")
    print(f"  平均逗留时间 Ws = {Ws_1:.4f}")

# ========== 2. M/M/c 模型 ==========
print(f"\\n{'='*60}")
print(f"M/M/c 多服务台模型 (c={c})")
print("=" * 60)

rho_c = lam / (c * mu)  # 系统利用率

if rho_c >= 1:
    print(f"系统利用率 rho = {rho_c:.4f} >= 1, 系统不稳定!")
else:
    a = lam / mu  # 交通强度

    # Erlang-C 公式: 计算所有服务台忙的概率 P(排队)
    # P0 = [sum_{k=0}^{c-1} (a^k/k!) + (a^c/c!) * 1/(1-rho)]^{-1}
    sum_part = sum((a ** k) / factorial(k, exact=True) for k in range(c))
    last_term = (a ** c) / factorial(c, exact=True) * (1.0 / (1.0 - rho_c))
    P0_c = 1.0 / (sum_part + last_term)

    # Erlang-C 公式: C(c, a) = P(排队)
    erlang_c = ((a ** c) / factorial(c, exact=True)) * (1.0 / (1.0 - rho_c)) * P0_c

    # M/M/c 稳态指标
    Lq_c = erlang_c * rho_c / (1 - rho_c)     # 平均排队队长
    Ls_c = Lq_c + a                             # 平均系统队长
    Wq_c = Lq_c / lam                           # 平均排队等待时间
    Ws_c = Wq_c + 1.0 / mu                      # 平均逗留时间

    print(f"  系统利用率 rho = {rho_c:.4f}")
    print(f"  系统空闲概率 P0 = {P0_c:.4f}")
    print(f"  Erlang-C (排队概率) = {erlang_c:.4f}")
    print(f"  平均排队队长 Lq = {Lq_c:.4f}")
    print(f"  平均系统队长 Ls = {Ls_c:.4f}")
    print(f"  平均排队等待时间 Wq = {Wq_c:.4f}")
    print(f"  平均逗留时间 Ws = {Ws_c:.4f}")

# ========== 3. 可视化: 到达率 vs 等待时间 ==========
print(f"\\n{'='*60}")
print("可视化分析")
print("=" * 60)

lambda_range = np.linspace(0.1, mu * 0.95, 200)  # 到达率范围 (保持 rho < 1)
Wq_mm1_list = []
Wq_mmc_list = []

for l in lambda_range:
    # M/M/1
    r1 = l / mu
    if r1 < 1:
        Wq_mm1_list.append(r1 / (mu * (1 - r1)))
    else:
        Wq_mm1_list.append(np.nan)

    # M/M/c
    rc = l / (c * mu)
    if rc < 1:
        a_tmp = l / mu
        sum_tmp = sum((a_tmp ** k) / factorial(k, exact=True) for k in range(c))
        last_tmp = (a_tmp ** c) / factorial(c, exact=True) * (1.0 / (1.0 - rc))
        p0_tmp = 1.0 / (sum_tmp + last_tmp)
        ec_tmp = ((a_tmp ** c) / factorial(c, exact=True)) * (1.0 / (1.0 - rc)) * p0_tmp
        lq_tmp = ec_tmp * rc / (1 - rc)
        Wq_mmc_list.append(lq_tmp / l)
    else:
        Wq_mmc_list.append(np.nan)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 子图1: 等待时间 vs 到达率
axes[0].plot(lambda_range, Wq_mm1_list, "b-", linewidth=2, label="M/M/1")
axes[0].plot(lambda_range, Wq_mmc_list, "r--", linewidth=2, label=f"M/M/{c}")
axes[0].axvline(x=lam, color="gray", linestyle=":", alpha=0.7, label=f"当前 lambda={lam}")
axes[0].set_xlabel("到达率 lambda")
axes[0].set_ylabel("平均排队等待时间 Wq")
axes[0].set_title("到达率 vs 平均排队等待时间")
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].set_ylim(bottom=0, top=max(filter(lambda x: not np.isnan(x), Wq_mm1_list)) * 1.2)

# 子图2: 系统利用率 vs 到达率
rho_mm1 = lambda_range / mu
rho_mmc = lambda_range / (c * mu)
axes[1].plot(lambda_range, rho_mm1, "b-", linewidth=2, label="M/M/1 rho")
axes[1].plot(lambda_range, rho_mmc, "r--", linewidth=2, label=f"M/M/{c} rho")
axes[1].axhline(y=1.0, color="black", linestyle="-", alpha=0.3, label="rho=1 (不稳定)")
axes[1].axvline(x=lam, color="gray", linestyle=":", alpha=0.7, label=f"当前 lambda={lam}")
axes[1].set_xlabel("到达率 lambda")
axes[1].set_ylabel("系统利用率 rho")
axes[1].set_title("到达率 vs 系统利用率")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("queuing_theory_analysis.png", dpi=150)
print("排队论分析图已保存: queuing_theory_analysis.png")
''',
    ),
}


def get_templates() -> list[CodeTemplate]:
    """返回所有统计模板列表。"""
    return list(STATISTICS_TEMPLATES.values())
