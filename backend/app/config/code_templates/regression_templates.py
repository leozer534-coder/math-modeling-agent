"""回归类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

REGRESSION_TEMPLATES = {
    "multiple_linear_regression": CodeTemplate(
        name="多元线性回归",
        category="回归",
        description="使用 sklearn + statsmodels 进行多元线性回归分析，"
        "包含 OLS 回归摘要、系数显著性检验、多重共线性 VIF 检查和残差诊断。",
        applicable_models=[
            "多元线性回归", "multiple linear regression",
            "线性回归", "OLS", "最小二乘",
        ],
        dependencies=["numpy", "pandas", "sklearn", "statsmodels", "matplotlib"],
        code='''import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import statsmodels.api as sm
import matplotlib.pyplot as plt

# 数据准备
# data = pd.read_csv("data.csv")  # TODO: 替换
# feature_cols = ["x1", "x2", "x3"]  # TODO: 替换
# target_col = "y"  # TODO: 替换
# X = data[feature_cols].values
# y = data[target_col].values

# 划分数据集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ========== 1. sklearn 回归 ==========
model = LinearRegression()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

r2 = r2_score(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)

print("===METRICS_START===")
print(f"R2={r2:.6f}")
print(f"RMSE={rmse:.6f}")
print(f"MAE={mae:.6f}")
print("===METRICS_END===")

# ========== 2. statsmodels OLS 详细摘要 ==========
X_with_const = sm.add_constant(X)
ols_model = sm.OLS(y, X_with_const).fit()
print("\\nOLS 回归摘要:")
print(ols_model.summary())

# ========== 3. VIF 多重共线性检验 ==========
from statsmodels.stats.outliers_influence import variance_inflation_factor

vif_data = pd.DataFrame()
vif_data["特征"] = [f"x{i+1}" for i in range(X.shape[1])]
vif_data["VIF"] = [
    variance_inflation_factor(X_with_const, i + 1) for i in range(X.shape[1])
]
print("\\n多重共线性 (VIF):")
print(vif_data.to_string(index=False))

# ========== 4. 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 预测值 vs 实际值
axes[0].scatter(y_test, y_pred, alpha=0.6, edgecolors="k", linewidths=0.5)
lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
axes[0].plot(lims, lims, "r--", linewidth=2)
axes[0].set_xlabel("实际值"); axes[0].set_ylabel("预测值")
axes[0].set_title(f"预测值 vs 实际值 (R2={r2:.4f})")
axes[0].grid(True, alpha=0.3)

# 残差图
residuals = y_test - y_pred
axes[1].scatter(y_pred, residuals, alpha=0.6, edgecolors="k", linewidths=0.5)
axes[1].axhline(y=0, color="r", linestyle="--")
axes[1].set_xlabel("预测值"); axes[1].set_ylabel("残差")
axes[1].set_title("残差分布图")
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("linear_regression.png", dpi=150)
print("回归分析图已保存: linear_regression.png")
''',
    ),
    "regularized_regression": CodeTemplate(
        name="正则化回归 (Ridge/Lasso/ElasticNet)",
        category="回归",
        description="使用岭回归、Lasso 和弹性网络进行正则化回归，"
        "通过交叉验证自动选择最优正则化参数，对比三种模型性能。",
        applicable_models=[
            "岭回归", "ridge regression", "Lasso", "lasso回归",
            "弹性网络", "elastic net", "正则化回归", "regularized regression",
        ],
        dependencies=["numpy", "pandas", "sklearn", "matplotlib"],
        code='''import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV, LassoCV, ElasticNetCV
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt

# 数据准备
# data = pd.read_csv("data.csv")  # TODO: 替换
# feature_cols = ["x1", "x2", "x3"]  # TODO: 替换
# target_col = "y"  # TODO: 替换
# X = data[feature_cols].values
# y = data[target_col].values

# 划分与标准化
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# 正则化参数候选
alphas = np.logspace(-4, 2, 50)

# ========== 1. Ridge (L2) ==========
ridge = RidgeCV(alphas=alphas, cv=5)
ridge.fit(X_train_s, y_train)
y_pred_ridge = ridge.predict(X_test_s)

# ========== 2. Lasso (L1) ==========
lasso = LassoCV(alphas=alphas, cv=5, max_iter=10000, random_state=42)
lasso.fit(X_train_s, y_train)
y_pred_lasso = lasso.predict(X_test_s)

# ========== 3. ElasticNet (L1+L2) ==========
enet = ElasticNetCV(
    l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9],
    alphas=alphas, cv=5, max_iter=10000, random_state=42,
)
enet.fit(X_train_s, y_train)
y_pred_enet = enet.predict(X_test_s)

# ========== 评估对比 ==========
models = {
    "Ridge": (ridge, y_pred_ridge, ridge.alpha_),
    "Lasso": (lasso, y_pred_lasso, lasso.alpha_),
    "ElasticNet": (enet, y_pred_enet, enet.alpha_),
}

print("===METRICS_START===")
for name, (m, y_p, alpha) in models.items():
    r2 = r2_score(y_test, y_p)
    rmse = np.sqrt(mean_squared_error(y_test, y_p))
    mae = mean_absolute_error(y_test, y_p)
    print(f"{name}: alpha={alpha:.6f}, R2={r2:.6f}, RMSE={rmse:.6f}, MAE={mae:.6f}")
print("===METRICS_END===")

# Lasso 特征选择
n_features = X.shape[1]
feature_names = [f"x{i+1}" for i in range(n_features)]  # TODO: 替换
coef_df = pd.DataFrame({
    "特征": feature_names,
    "Ridge系数": ridge.coef_,
    "Lasso系数": lasso.coef_,
    "ElasticNet系数": enet.coef_,
})
print("\\n各模型系数对比:")
print(coef_df.to_string(index=False))
print(f"\\nLasso 保留特征数: {np.sum(lasso.coef_ != 0)}/{n_features}")

# ========== 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 系数对比柱状图
x_pos = np.arange(n_features)
w = 0.25
axes[0].bar(x_pos - w, ridge.coef_, w, label="Ridge", color="steelblue")
axes[0].bar(x_pos, lasso.coef_, w, label="Lasso", color="coral")
axes[0].bar(x_pos + w, enet.coef_, w, label="ElasticNet", color="seagreen")
axes[0].set_xticks(x_pos)
axes[0].set_xticklabels(feature_names, rotation=45, ha="right")
axes[0].set_ylabel("系数值"); axes[0].set_title("正则化回归系数对比")
axes[0].legend(); axes[0].grid(True, alpha=0.3, axis="y")

# 预测值对比散点图
best_name = max(models, key=lambda k: r2_score(y_test, models[k][1]))
best_pred = models[best_name][1]
axes[1].scatter(y_test, best_pred, alpha=0.6, edgecolors="k", linewidths=0.5)
lims = [min(y_test.min(), best_pred.min()), max(y_test.max(), best_pred.max())]
axes[1].plot(lims, lims, "r--", linewidth=2)
axes[1].set_xlabel("实际值"); axes[1].set_ylabel("预测值")
best_r2 = r2_score(y_test, best_pred)
axes[1].set_title(f"最优模型 {best_name} (R2={best_r2:.4f})")
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("regularized_regression.png", dpi=150)
print("正则化回归图已保存: regularized_regression.png")
''',
    ),
}
