"""验证类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

VALIDATION_TEMPLATES = {
    "cross_validation_tpl": CodeTemplate(
        name="K折交叉验证",
        category="验证",
        description="使用 sklearn 进行 K 折交叉验证",
        applicable_models=["交叉验证", "cross_validation", "模型验证"],
        dependencies=["sklearn", "numpy"],
        code='''import numpy as np
from sklearn.model_selection import cross_val_score, KFold

# model = ...  # TODO: 替换为模型
# X, y = ...   # TODO: 替换为数据

kf = KFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=kf, scoring="r2")

print(f"5-fold CV scores: {scores}")
print(f"Mean: {scores.mean():.4f} (+/- {scores.std():.4f})")
''',
    ),
    "sensitivity_analysis_tpl": CodeTemplate(
        name="参数敏感性分析",
        category="验证",
        description="单参数敏感性分析及可视化",
        applicable_models=["敏感性分析", "sensitivity_analysis", "参数分析"],
        dependencies=["numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt

# 目标函数
def model_func(param1=1.0, param2=2.0, param3=3.0):
    return ...  # TODO: 替换

# 基准参数
base_params = {"param1": 1.0, "param2": 2.0, "param3": 3.0}
base_result = model_func(**base_params)

# 对每个参数进行敏感性分析
fig, axes = plt.subplots(1, len(base_params), figsize=(5*len(base_params), 4))
for ax, (name, base_val) in zip(axes, base_params.items()):
    values = np.linspace(base_val * 0.5, base_val * 1.5, 30)
    results = []
    for v in values:
        params = base_params.copy()
        params[name] = v
        results.append(model_func(**params))
    ax.plot(values, results, "b-o", markersize=3)
    ax.axvline(base_val, color="r", linestyle="--", label="基准值")
    ax.set_xlabel(name); ax.set_ylabel("目标函数值")
    ax.set_title(f"{name} 敏感性分析"); ax.legend(); ax.grid(True)

plt.tight_layout()
plt.savefig("sensitivity_analysis.png", dpi=150)
plt.show()
''',
    ),
    "bootstrap_ci_tpl": CodeTemplate(
        name="Bootstrap 置信区间",
        category="验证",
        description="非参数 Bootstrap 方法估计置信区间",
        applicable_models=["bootstrap", "置信区间", "Bootstrap"],
        dependencies=["numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt

# 样本数据
data = np.array([...])  # TODO: 替换为实际数据

# ========== Bootstrap 参数 ==========
n_bootstrap = 2000     # 重抽样次数
confidence = 0.95      # 置信水平
np.random.seed(42)

# 统计量函数 (默认均值, 可替换为 np.median 等)
statistic_func = np.mean  # TODO: 可替换

n = len(data)
point_estimate = statistic_func(data)

# Bootstrap 重抽样
bootstrap_stats = np.array([
    statistic_func(np.random.choice(data, size=n, replace=True))
    for _ in range(n_bootstrap)
])

# 百分位法置信区间
alpha = 1 - confidence
ci_lower = np.percentile(bootstrap_stats, alpha / 2 * 100)
ci_upper = np.percentile(bootstrap_stats, (1 - alpha / 2) * 100)
se = np.std(bootstrap_stats)

print(f"点估计: {point_estimate:.4f}")
print(f"Bootstrap 标准误: {se:.4f}")
print(f"{confidence*100:.0f}% 置信区间: [{ci_lower:.4f}, {ci_upper:.4f}]")

# 可视化
plt.figure(figsize=(8, 5))
plt.hist(bootstrap_stats, bins=50, density=True, alpha=0.7, color="steelblue")
plt.axvline(point_estimate, color="red", linestyle="-", linewidth=2, label=f"点估计={point_estimate:.4f}")
plt.axvline(ci_lower, color="orange", linestyle="--", label=f"CI 下界={ci_lower:.4f}")
plt.axvline(ci_upper, color="orange", linestyle="--", label=f"CI 上界={ci_upper:.4f}")
plt.xlabel("统计量值"); plt.ylabel("密度")
plt.title(f"Bootstrap 分布 ({confidence*100:.0f}% CI)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("bootstrap_ci.png", dpi=150)
print("Bootstrap 置信区间图已保存: bootstrap_ci.png")
''',
    ),
}
