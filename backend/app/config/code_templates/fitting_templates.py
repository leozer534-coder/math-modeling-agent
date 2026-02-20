"""拟合类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

FITTING_TEMPLATES = {
    "polynomial_fitting": CodeTemplate(
        name="多项式拟合",
        category="拟合",
        description="使用多项式拟合数据，自动搜索最佳阶数 (1-5)，"
        "输出 R2、RMSE 等评估指标，并绘制拟合曲线。",
        applicable_models=[
            "多项式拟合", "polynomial fitting", "polynomial regression",
            "多项式回归", "多项式",
        ],
        dependencies=["numpy", "sklearn", "matplotlib"],
        code='''import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt

# 数据准备
# X = np.array([...])  # TODO: 替换为自变量数据
# y = np.array([...])  # TODO: 替换为因变量数据

# 确保 X 为二维
if X.ndim == 1:
    X = X.reshape(-1, 1)

# 多项式拟合（尝试不同阶数）
best_degree = 1
best_r2 = -np.inf
results = {}

for degree in range(1, 6):
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    y_pred = model.predict(X_poly)
    r2 = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    results[degree] = {"r2": r2, "rmse": rmse, "model": model, "poly": poly}
    print(f"  阶数 {degree}: R2={r2:.6f}, RMSE={rmse:.6f}")
    if r2 > best_r2:
        best_r2 = r2
        best_degree = degree

print(f"\\n===METRICS_START===")
print(f"best_degree={best_degree}")
print(f"R2={results[best_degree]['r2']:.6f}")
print(f"RMSE={results[best_degree]['rmse']:.6f}")
print(f"===METRICS_END===")

# 可视化（仅支持一维自变量）
if X.shape[1] == 1:
    plt.figure(figsize=(10, 6))
    plt.scatter(X.ravel(), y, c="steelblue", alpha=0.7, label="原始数据")
    X_plot = np.linspace(X.min(), X.max(), 300).reshape(-1, 1)
    best = results[best_degree]
    X_plot_poly = best["poly"].transform(X_plot)
    y_plot = best["model"].predict(X_plot_poly)
    plt.plot(X_plot.ravel(), y_plot, "r-", linewidth=2,
             label=f"{best_degree}阶多项式 (R2={best['r2']:.4f})")
    plt.xlabel("X"); plt.ylabel("y")
    plt.title("多项式拟合结果")
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
    plt.savefig("polynomial_fitting.png", dpi=150)
    print("拟合图已保存: polynomial_fitting.png")
''',
    ),
    "curve_fitting": CodeTemplate(
        name="曲线拟合",
        category="拟合",
        description="使用 scipy.optimize.curve_fit 进行非线性曲线拟合，"
        "内置指数、对数、幂函数等常见模型，自动选择最佳拟合函数。",
        applicable_models=[
            "曲线拟合", "curve fitting", "非线性拟合", "nonlinear fitting",
        ],
        dependencies=["numpy", "scipy", "matplotlib"],
        code='''import numpy as np
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt

# 数据准备
# x = np.array([...])  # TODO: 替换为自变量数据
# y = np.array([...])  # TODO: 替换为因变量数据

# 候选拟合函数
def func_exp(x, a, b, c):
    """指数函数: y = a * exp(b * x) + c"""
    return a * np.exp(b * x) + c

def func_log(x, a, b):
    """对数函数: y = a * ln(x) + b"""
    return a * np.log(x + 1e-10) + b

def func_power(x, a, b, c):
    """幂函数: y = a * x^b + c"""
    return a * np.power(np.abs(x) + 1e-10, b) + c

def func_logistic(x, L, k, x0, b):
    """Logistic 函数: y = L / (1 + exp(-k*(x-x0))) + b"""
    return L / (1 + np.exp(-k * (x - x0))) + b

candidates = {
    "指数函数": (func_exp, [1, 0.01, 0]),
    "对数函数": (func_log, [1, 1]),
    "幂函数": (func_power, [1, 1, 0]),
    "Logistic": (func_logistic, [max(y), 1, np.median(x), min(y)]),
}

# 逐一拟合，选出最佳
best_name, best_r2, best_params, best_func = None, -np.inf, None, None
results = {}

for name, (func, p0) in candidates.items():
    try:
        popt, _ = curve_fit(func, x, y, p0=p0, maxfev=10000)
        y_pred = func(x, *popt)
        r2 = r2_score(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        results[name] = {"r2": r2, "rmse": rmse, "params": popt}
        print(f"  {name}: R2={r2:.6f}, RMSE={rmse:.6f}")
        if r2 > best_r2:
            best_r2 = r2
            best_name = name
            best_params = popt
            best_func = func
    except RuntimeError:
        print(f"  {name}: 拟合失败 (未收敛)")

print(f"\\n===METRICS_START===")
print(f"best_model={best_name}")
print(f"R2={best_r2:.6f}")
print(f"RMSE={results[best_name]['rmse']:.6f}")
print(f"params={best_params.tolist()}")
print(f"===METRICS_END===")

# 可视化
plt.figure(figsize=(10, 6))
plt.scatter(x, y, c="steelblue", alpha=0.7, label="原始数据")
x_plot = np.linspace(x.min(), x.max(), 300)
y_plot = best_func(x_plot, *best_params)
plt.plot(x_plot, y_plot, "r-", linewidth=2,
         label=f"{best_name} (R2={best_r2:.4f})")
plt.xlabel("X"); plt.ylabel("y")
plt.title("非线性曲线拟合"); plt.legend()
plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("curve_fitting.png", dpi=150)
print("拟合图已保存: curve_fitting.png")
''',
    ),
    "spline_interpolation": CodeTemplate(
        name="样条插值",
        category="拟合",
        description="使用三次样条插值和 B 样条平滑拟合数据，"
        "支持平滑因子调整，适用于数据点较少或需要光滑曲线的场景。",
        applicable_models=[
            "样条插值", "spline interpolation", "B样条", "插值",
            "三次样条", "cubic spline",
        ],
        dependencies=["numpy", "scipy", "matplotlib"],
        code='''import numpy as np
from scipy.interpolate import CubicSpline, UnivariateSpline
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt

# 数据准备 (x 必须严格递增)
# x = np.array([...])  # TODO: 替换
# y = np.array([...])  # TODO: 替换

# 按 x 排序
sort_idx = np.argsort(x)
x, y = x[sort_idx], y[sort_idx]

# ========== 1. 三次样条插值 (精确过点) ==========
cs = CubicSpline(x, y)

# ========== 2. B 样条平滑 (允许偏差, 抗噪声) ==========
# s: 平滑因子, 越大越光滑; 设为 None 时自动选择
us = UnivariateSpline(x, y, s=None, k=3)

# 密集采样用于绘图
x_dense = np.linspace(x.min(), x.max(), 500)
y_cs = cs(x_dense)
y_us = us(x_dense)

# 评估 (在原始点上)
y_cs_fit = cs(x)
y_us_fit = us(x)

r2_cs = r2_score(y, y_cs_fit)
r2_us = r2_score(y, y_us_fit)
rmse_cs = np.sqrt(mean_squared_error(y, y_cs_fit))
rmse_us = np.sqrt(mean_squared_error(y, y_us_fit))

print("===METRICS_START===")
print(f"CubicSpline_R2={r2_cs:.6f}")
print(f"CubicSpline_RMSE={rmse_cs:.6f}")
print(f"UnivariateSpline_R2={r2_us:.6f}")
print(f"UnivariateSpline_RMSE={rmse_us:.6f}")
print("===METRICS_END===")

# 可视化
plt.figure(figsize=(10, 6))
plt.scatter(x, y, c="steelblue", zorder=5, label="原始数据")
plt.plot(x_dense, y_cs, "r-", linewidth=2,
         label=f"三次样条插值 (R2={r2_cs:.4f})")
plt.plot(x_dense, y_us, "g--", linewidth=2,
         label=f"B样条平滑 (R2={r2_us:.4f})")
plt.xlabel("X"); plt.ylabel("y")
plt.title("样条插值与平滑拟合")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("spline_interpolation.png", dpi=150)
print("插值图已保存: spline_interpolation.png")
''',
    ),
}
