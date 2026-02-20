"""预测类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

PREDICTION_TEMPLATES = {
    "arima_forecast": CodeTemplate(
        name="ARIMA 时间序列预测",
        category="预测",
        description="使用 ARIMA/SARIMA 进行时间序列预测",
        applicable_models=["ARIMA", "时间序列", "SARIMA", "time_series"],
        dependencies=["statsmodels", "numpy", "matplotlib", "pandas"],
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

# 加载数据
# data = pd.read_csv("data.csv")  # TODO: 替换
# y = data["column_name"].values

# ADF 平稳性检验
adf_result = adfuller(y)
print(f"ADF 统计量: {adf_result[0]:.4f}, p值: {adf_result[1]:.4f}")

# 差分阶数
d = 0 if adf_result[1] < 0.05 else 1

# ARIMA 建模
model = SARIMAX(y, order=(1, d, 1), enforce_stationarity=False, enforce_invertibility=False)
fitted = model.fit(disp=False)
print(fitted.summary())

# 预测
n_forecast = 10  # TODO: 替换
forecast = fitted.get_forecast(steps=n_forecast, alpha=0.05)
pred = forecast.predicted_mean
ci = forecast.conf_int()

# 可视化
plt.figure(figsize=(12, 6))
plt.plot(y, label="历史数据")
plt.plot(range(len(y), len(y) + n_forecast), pred, "r--", label="预测")
plt.fill_between(range(len(y), len(y) + n_forecast), ci.iloc[:, 0], ci.iloc[:, 1], alpha=0.2, color="red")
plt.legend(); plt.title("ARIMA 时间序列预测")
plt.tight_layout(); plt.savefig("arima_forecast.png", dpi=150)
plt.show()
''',
    ),
    "xgboost_prediction": CodeTemplate(
        name="XGBoost/LightGBM 预测",
        category="预测",
        description="使用 XGBoost 或 LightGBM 进行回归/分类预测",
        applicable_models=["XGBoost", "LightGBM", "GBDT", "梯度提升"],
        dependencies=["xgboost", "sklearn", "numpy", "matplotlib"],
        code='''import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt

# 加载数据
# X, y = ...  # TODO: 替换

# 划分数据集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# XGBoost 回归
model = xgb.XGBRegressor(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    subsample=0.8, colsample_bytree=0.8, random_state=42,
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# 预测与评估
y_pred = model.predict(X_test)
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")
print(f"MAE:  {mean_absolute_error(y_test, y_pred):.4f}")
print(f"R2:   {r2_score(y_test, y_pred):.4f}")

# 交叉验证
cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
print(f"5-fold CV R2: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# 特征重要性
feat_imp = model.feature_importances_
plt.figure(figsize=(10, 6))
plt.barh(range(len(feat_imp)), sorted(feat_imp, reverse=True))
plt.title("特征重要性"); plt.tight_layout()
plt.savefig("feature_importance.png", dpi=150)
plt.show()
''',
    ),
    "exponential_smoothing_tpl": CodeTemplate(
        name="Holt-Winters 指数平滑",
        category="预测",
        description="Holt-Winters 指数平滑法进行时间序列预测，支持趋势和季节性",
        applicable_models=["指数平滑", "Holt-Winters", "exponential_smoothing", "ETS"],
        dependencies=["statsmodels", "numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# 时间序列数据
# y = np.array([...])  # TODO: 替换为实际数据

# ========== 指数平滑参数 ==========
trend = "add"          # 趋势类型: "add" / "mul" / None
seasonal = None        # 季节类型: "add" / "mul" / None
seasonal_periods = None  # 季节周期，如 12(月度)、4(季度)  # TODO: 按需设置
n_forecast = 10        # TODO: 预测步数

# 建模与拟合
model = ExponentialSmoothing(
    y, trend=trend, seasonal=seasonal,
    seasonal_periods=seasonal_periods,
)
fitted = model.fit(optimized=True)

# 预测
forecast = fitted.forecast(steps=n_forecast)
fitted_values = fitted.fittedvalues

# 评估
residuals = y - fitted_values
rmse = np.sqrt(np.mean(residuals**2))
mae = np.mean(np.abs(residuals))
print(f"拟合 RMSE: {rmse:.4f}, MAE: {mae:.4f}")
print(f"AIC: {fitted.aic:.2f}, BIC: {fitted.bic:.2f}")
print(f"预测值: {forecast}")

# 可视化
plt.figure(figsize=(12, 6))
plt.plot(range(len(y)), y, "b-o", markersize=3, label="历史数据")
plt.plot(range(len(y)), fitted_values, "g--", label="拟合值")
plt.plot(range(len(y), len(y)+n_forecast), forecast, "r-s", markersize=4, label="预测值")
plt.axvline(x=len(y)-0.5, color="gray", linestyle=":", alpha=0.5)
plt.xlabel("时间"); plt.ylabel("数值")
plt.title("Holt-Winters 指数平滑预测")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("exponential_smoothing.png", dpi=150)
print("指数平滑预测图已保存: exponential_smoothing.png")
''',
    ),
    "neural_network_tpl": CodeTemplate(
        name="BP 神经网络",
        category="预测",
        description="sklearn MLPRegressor/MLPClassifier 实现神经网络",
        applicable_models=["神经网络", "BP神经网络", "neural_network", "MLP"],
        dependencies=["sklearn", "numpy", "matplotlib"],
        code='''import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# X, y = ...  # TODO: 替换为实际数据

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler_X, scaler_y = StandardScaler(), StandardScaler()
X_train_s = scaler_X.fit_transform(X_train)
X_test_s = scaler_X.transform(X_test)
y_train_s = scaler_y.fit_transform(y_train.reshape(-1, 1)).ravel()

model = MLPRegressor(
    hidden_layer_sizes=(64, 32), activation="relu",
    max_iter=500, random_state=42, early_stopping=True
)
model.fit(X_train_s, y_train_s)

y_pred_s = model.predict(X_test_s)
y_pred = scaler_y.inverse_transform(y_pred_s.reshape(-1, 1)).ravel()

print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")
print(f"R2: {r2_score(y_test, y_pred):.4f}")

plt.figure(figsize=(8, 5))
plt.scatter(y_test, y_pred, alpha=0.6)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--")
plt.xlabel("实际值"); plt.ylabel("预测值")
plt.title("BP 神经网络预测结果"); plt.grid(True)
plt.tight_layout(); plt.savefig("nn_prediction.png", dpi=150)
plt.show()
''',
    ),
    "prophet_forecast_tpl": CodeTemplate(
        name="Prophet 时序预测",
        category="预测",
        description="Facebook Prophet 时间序列预测（自动趋势+季节性）",
        applicable_models=["Prophet", "prophet", "Facebook Prophet"],
        dependencies=["prophet", "pandas", "matplotlib"],
        code='''import pandas as pd
import matplotlib.pyplot as plt

# 准备数据 (必须有 ds 和 y 列)
# df = pd.read_csv("data.csv")  # TODO: 替换
# df = df.rename(columns={"日期列": "ds", "值列": "y"})

try:
    from prophet import Prophet

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=30)  # TODO: 调整预测天数
    forecast = model.predict(future)

    fig = model.plot(forecast)
    plt.title("Prophet 时序预测")
    plt.tight_layout()
    plt.savefig("prophet_forecast.png", dpi=150)
    plt.show()

    print("预测结果（最后5行）:")
    print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail())
except ImportError:
    print("Prophet 未安装，请使用 ARIMA 等替代方法")
''',
    ),
    "lstm_time_series": CodeTemplate(
        name="LSTM 时间序列预测",
        category="预测",
        description="使用 LSTM 神经网络进行时间序列预测，支持多步预测和置信区间",
        applicable_models=[
            "LSTM", "长短期记忆", "lstm", "GRU", "循环神经网络", "RNN",
            "深度学习预测", "神经网络预测", "deep_learning_forecast",
        ],
        dependencies=["torch", "numpy", "pandas", "matplotlib", "sklearn"],
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ========== 1. 数据加载与预处理 ==========
# data = pd.read_csv("data.csv")  # TODO: 替换为实际数据路径
# series = data["column_name"].values.astype(float)  # TODO: 替换为目标列名

# 归一化
scaler = MinMaxScaler(feature_range=(0, 1))
series_scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()

# 滑动窗口构造训练样本
lookback = 30  # TODO: 根据数据特性调整回看窗口
n_forecast = 10  # TODO: 预测步数

def create_sequences(data, lookback):
    """构造滑动窗口序列。"""
    X, y = [], []
    for i in range(len(data) - lookback):
        X.append(data[i : i + lookback])
        y.append(data[i + lookback])
    return np.array(X), np.array(y)

X, y = create_sequences(series_scaled, lookback)

# 划分训练/验证集 (8:2)
split = int(len(X) * 0.8)
X_train, X_val = X[:split], X[split:]
y_train, y_val = y[:split], y[split:]

# 转为 PyTorch 张量 (batch, seq_len, features)
X_train_t = torch.FloatTensor(X_train).unsqueeze(-1)
y_train_t = torch.FloatTensor(y_train)
X_val_t = torch.FloatTensor(X_val).unsqueeze(-1)
y_val_t = torch.FloatTensor(y_val)

train_loader = DataLoader(
    TensorDataset(X_train_t, y_train_t), batch_size=32, shuffle=True
)

# ========== 2. LSTM 模型定义 ==========
class LSTMPredictor(nn.Module):
    """LSTM 时间序列预测模型。"""

    def __init__(self, input_size=1, hidden_size=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])
        return out.squeeze(-1)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = LSTMPredictor(input_size=1, hidden_size=64, num_layers=2, dropout=0.2).to(device)

# ========== 3. 模型训练 ==========
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = nn.MSELoss()
n_epochs = 100  # TODO: 根据数据规模调整
train_losses, val_losses = [], []

for epoch in range(n_epochs):
    model.train()
    epoch_loss = 0.0
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        pred = model(xb)
        loss = criterion(pred, yb)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item() * xb.size(0)
    train_losses.append(epoch_loss / len(X_train))

    model.eval()
    with torch.no_grad():
        val_pred = model(X_val_t.to(device))
        v_loss = criterion(val_pred, y_val_t.to(device)).item()
    val_losses.append(v_loss)

    if (epoch + 1) % 20 == 0:
        print(f"Epoch {epoch+1}/{n_epochs}  train_loss={train_losses[-1]:.6f}  val_loss={v_loss:.6f}")

# ========== 4. 预测与反归一化 ==========
model.eval()
with torch.no_grad():
    y_val_pred_scaled = model(X_val_t.to(device)).cpu().numpy()

# 反归一化
y_val_actual = scaler.inverse_transform(y_val.reshape(-1, 1)).flatten()
y_val_pred = scaler.inverse_transform(y_val_pred_scaled.reshape(-1, 1)).flatten()

# 多步预测（递归方式）
last_window = series_scaled[-lookback:]
future_preds_scaled = []
for _ in range(n_forecast):
    inp = torch.FloatTensor(last_window).unsqueeze(0).unsqueeze(-1).to(device)
    with torch.no_grad():
        next_val = model(inp).cpu().item()
    future_preds_scaled.append(next_val)
    last_window = np.append(last_window[1:], next_val)

future_preds = scaler.inverse_transform(
    np.array(future_preds_scaled).reshape(-1, 1)
).flatten()

# ========== 5. 评估指标 ==========
mae = mean_absolute_error(y_val_actual, y_val_pred)
rmse = np.sqrt(mean_squared_error(y_val_actual, y_val_pred))
r2 = r2_score(y_val_actual, y_val_pred)
mape = np.mean(np.abs((y_val_actual - y_val_pred) / (y_val_actual + 1e-8))) * 100

print("\\n===METRICS_START===")
print(f"MAE:  {mae:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"R2:   {r2:.4f}")
print(f"MAPE: {mape:.2f}%")
print("===METRICS_END===")
print(f"未来 {n_forecast} 步预测值: {future_preds.tolist()}")

# ========== 6. 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 图1: 预测值 vs 实际值
axes[0].plot(y_val_actual, "b-o", markersize=3, label="实际值")
axes[0].plot(y_val_pred, "r--s", markersize=3, label="预测值")
axes[0].set_xlabel("样本索引")
axes[0].set_ylabel("数值")
axes[0].set_title("LSTM 预测值 vs 实际值")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# 图2: 训练损失曲线
axes[1].plot(train_losses, label="训练损失")
axes[1].plot(val_losses, label="验证损失")
axes[1].set_xlabel("Epoch")
axes[1].set_ylabel("Loss (MSE)")
axes[1].set_title("训练与验证损失曲线")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("lstm_prediction.png", dpi=150)
print("===FIGURE: lstm_prediction.png | LSTM 预测结果与训练损失曲线===")
plt.show()
''',
    ),
    "stacking_ensemble": CodeTemplate(
        name="Stacking 集成学习",
        category="预测",
        description="使用 Stacking 方法融合多个基学习器进行预测，支持回归和分类",
        applicable_models=[
            "Stacking", "集成学习", "模型融合", "ensemble",
            "Blending", "stacking_ensemble", "模型集成",
        ],
        dependencies=["scikit-learn", "xgboost", "lightgbm", "numpy", "pandas", "matplotlib"],
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score

# ========== 1. 数据加载与预处理 ==========
# data = pd.read_csv("data.csv")  # TODO: 替换为实际数据路径
# feature_columns = ["feat1", "feat2", "feat3"]  # TODO: 替换为特征列名
# target_column = "target"  # TODO: 替换为目标列名
# X = data[feature_columns].values
# y = data[target_column].values

# 任务类型: "regression" 或 "classification"
task_type = "regression"  # TODO: 根据实际任务类型修改

# 划分训练/测试集 (8:2)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"训练集: {X_train.shape[0]} 样本, 测试集: {X_test.shape[0]} 样本")
print(f"特征数: {X_train.shape[1]}, 任务类型: {task_type}")

# ========== 2. 定义基学习器与元学习器 ==========
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import Ridge, LogisticRegression, LinearRegression
from sklearn.ensemble import StackingRegressor, StackingClassifier

try:
    import xgboost as xgb
    xgb_available = True
except ImportError:
    xgb_available = False
    print("Warning: xgboost 未安装，将跳过 XGBoost 基学习器")

try:
    import lightgbm as lgb
    lgb_available = True
except ImportError:
    lgb_available = False
    print("Warning: lightgbm 未安装，将跳过 LightGBM 基学习器")

if task_type == "regression":
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    # 基学习器列表
    base_estimators = [
        ("rf", RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        )),
        ("ridge", Ridge(alpha=1.0)),
    ]
    if xgb_available:
        base_estimators.append(("xgb", xgb.XGBRegressor(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
            verbosity=0,
        )))
    if lgb_available:
        base_estimators.append(("lgb", lgb.LGBMRegressor(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
            verbose=-1,
        )))

    # 元学习器
    meta_learner = LinearRegression()

    # Stacking 模型
    stacking_model = StackingRegressor(
        estimators=base_estimators,
        final_estimator=meta_learner,
        cv=5,
        n_jobs=-1,
    )
    scoring = "r2"

else:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        classification_report,
    )

    # 基学习器列表
    base_estimators = [
        ("rf", RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
        )),
        ("ridge_clf", LogisticRegression(
            max_iter=1000, random_state=42, C=1.0
        )),
    ]
    if xgb_available:
        base_estimators.append(("xgb", xgb.XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
            verbosity=0, use_label_encoder=False, eval_metric="logloss",
        )))
    if lgb_available:
        base_estimators.append(("lgb", lgb.LGBMClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
            verbose=-1,
        )))

    # 元学习器
    meta_learner = LogisticRegression(max_iter=1000, random_state=42)

    # Stacking 模型
    stacking_model = StackingClassifier(
        estimators=base_estimators,
        final_estimator=meta_learner,
        cv=5,
        n_jobs=-1,
    )
    scoring = "accuracy"

print(f"\\n基学习器: {[name for name, _ in base_estimators]}")
print(f"元学习器: {meta_learner.__class__.__name__}")

# ========== 3. 训练 Stacking 模型 ==========
print("\\n训练 Stacking 模型 (5-fold CV)...")
stacking_model.fit(X_train, y_train)
y_pred_stacking = stacking_model.predict(X_test)

# ========== 4. 各基学习器单独训练与对比 ==========
print("\\n训练各基学习器进行对比...")
model_results = {}

for name, estimator in base_estimators:
    estimator.fit(X_train, y_train)
    y_pred_base = estimator.predict(X_test)
    cv_scores_base = cross_val_score(estimator, X, y, cv=5, scoring=scoring, n_jobs=-1)

    if task_type == "regression":
        model_results[name] = {
            "R2": r2_score(y_test, y_pred_base),
            "MAE": mean_absolute_error(y_test, y_pred_base),
            "RMSE": np.sqrt(mean_squared_error(y_test, y_pred_base)),
            "CV_mean": cv_scores_base.mean(),
            "CV_std": cv_scores_base.std(),
        }
    else:
        model_results[name] = {
            "Accuracy": accuracy_score(y_test, y_pred_base),
            "F1": f1_score(y_test, y_pred_base, average="weighted", zero_division=0),
            "CV_mean": cv_scores_base.mean(),
            "CV_std": cv_scores_base.std(),
        }

# Stacking 模型评估
cv_scores_stacking = cross_val_score(stacking_model, X, y, cv=5, scoring=scoring, n_jobs=-1)
if task_type == "regression":
    model_results["Stacking"] = {
        "R2": r2_score(y_test, y_pred_stacking),
        "MAE": mean_absolute_error(y_test, y_pred_stacking),
        "RMSE": np.sqrt(mean_squared_error(y_test, y_pred_stacking)),
        "CV_mean": cv_scores_stacking.mean(),
        "CV_std": cv_scores_stacking.std(),
    }
else:
    model_results["Stacking"] = {
        "Accuracy": accuracy_score(y_test, y_pred_stacking),
        "F1": f1_score(y_test, y_pred_stacking, average="weighted", zero_division=0),
        "CV_mean": cv_scores_stacking.mean(),
        "CV_std": cv_scores_stacking.std(),
    }

# ========== 5. 输出评估结果 ==========
print("\\n===METRICS_START===")
results_df = pd.DataFrame(model_results).T
print(results_df.to_string())
print("===METRICS_END===")

if task_type == "classification":
    print("\\nStacking 分类报告:")
    print(classification_report(y_test, y_pred_stacking, zero_division=0))

# ========== 6. 可视化: 各模型性能对比柱状图 ==========
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

model_names = list(model_results.keys())
colors = ["steelblue"] * (len(model_names) - 1) + ["coral"]

if task_type == "regression":
    # 图1: R2 对比
    r2_values = [model_results[m]["R2"] for m in model_names]
    bars1 = axes[0].bar(model_names, r2_values, color=colors, edgecolor="white", alpha=0.85)
    for bar, val in zip(bars1, r2_values):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    axes[0].set_ylabel("R2 Score")
    axes[0].set_title("Model Comparison - R2")
    axes[0].grid(axis="y", alpha=0.3)

    # 图2: RMSE 对比
    rmse_values = [model_results[m]["RMSE"] for m in model_names]
    bars2 = axes[1].bar(model_names, rmse_values, color=colors, edgecolor="white", alpha=0.85)
    for bar, val in zip(bars2, rmse_values):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    axes[1].set_ylabel("RMSE")
    axes[1].set_title("Model Comparison - RMSE")
    axes[1].grid(axis="y", alpha=0.3)
else:
    # 图1: Accuracy 对比
    acc_values = [model_results[m]["Accuracy"] for m in model_names]
    bars1 = axes[0].bar(model_names, acc_values, color=colors, edgecolor="white", alpha=0.85)
    for bar, val in zip(bars1, acc_values):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    axes[0].set_ylabel("Accuracy")
    axes[0].set_title("Model Comparison - Accuracy")
    axes[0].grid(axis="y", alpha=0.3)

    # 图2: F1 对比
    f1_values = [model_results[m]["F1"] for m in model_names]
    bars2 = axes[1].bar(model_names, f1_values, color=colors, edgecolor="white", alpha=0.85)
    for bar, val in zip(bars2, f1_values):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f"{val:.4f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    axes[1].set_ylabel("F1 Score")
    axes[1].set_title("Model Comparison - F1")
    axes[1].grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("stacking_ensemble_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("\\n[图片已保存: stacking_ensemble_comparison.png]")

# ========== 结构化输出 ==========
print("\\n" + "=" * 60)
print("<<< STRUCTURED_OUTPUT >>>")
print(f"任务类型: {task_type}")
print(f"基学习器: {[name for name, _ in base_estimators]}")
print(f"元学习器: {meta_learner.__class__.__name__}")
print(f"交叉验证折数: 5")
print(f"\\n各模型性能对比:")
for name, metrics in model_results.items():
    metrics_str = ", ".join(f"{k}={v:.4f}" for k, v in metrics.items())
    print(f"  {name}: {metrics_str}")
best_model = max(model_results.items(), key=lambda x: x[1].get("R2", x[1].get("Accuracy", 0)))
print(f"\\n最优模型: {best_model[0]}")
print("<<< /STRUCTURED_OUTPUT >>>")
''',
    ),
    "random_forest": CodeTemplate(
        name="随机森林回归与分类",
        category="预测",
        description="使用随机森林进行回归或分类预测，含特征重要性分析和交叉验证",
        applicable_models=[
            "随机森林", "Random Forest", "random_forest", "RF",
            "集成学习", "Bagging", "ensemble",
        ],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report,
)

# ========== 1. 数据加载与预处理 ==========
# data = pd.read_csv("data.csv")  # TODO: 替换为实际数据路径
# feature_columns = ["feat1", "feat2", "feat3"]  # TODO: 替换为特征列名
# target_column = "target"  # TODO: 替换为目标列名
# X = data[feature_columns].values
# y = data[target_column].values

# 任务类型: "regression" 或 "classification"
task_type = "regression"  # TODO: 根据实际任务类型修改

# 划分训练/测试集 (8:2)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"训练集: {X_train.shape[0]} 样本, 测试集: {X_test.shape[0]} 样本")
print(f"特征数: {X_train.shape[1]}, 任务类型: {task_type}")

# ========== 2. 模型训练 ==========
if task_type == "regression":
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    scoring = "r2"
else:
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    scoring = "accuracy"

model.fit(X_train, y_train)
y_pred = model.predict(X_test)

# ========== 3. 交叉验证 ==========
cv_scores = cross_val_score(model, X, y, cv=5, scoring=scoring, n_jobs=-1)
print(f"\\n5-fold CV ({scoring}): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# ========== 4. 模型评估 ==========
print("\\n===METRICS_START===")
if task_type == "regression":
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"R2:   {r2:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"5-fold CV R2: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
else:
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"5-fold CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    print("\\n分类报告:")
    print(classification_report(y_test, y_pred, zero_division=0))
print("===METRICS_END===")

# ========== 5. 特征重要性分析 ==========
importances = model.feature_importances_
# feature_names = feature_columns  # TODO: 确保 feature_columns 已定义
feature_names = [f"特征{i+1}" for i in range(X.shape[1])]  # TODO: 替换为实际特征名

sorted_idx = np.argsort(importances)[::-1]
sorted_importances = importances[sorted_idx]
sorted_names = [feature_names[i] for i in sorted_idx]

print("\\n特征重要性排序:")
for i, (name, imp) in enumerate(zip(sorted_names, sorted_importances)):
    print(f"  {i+1}. {name}: {imp:.4f}")

# ========== 6. 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 图1: 特征重要性柱状图（取前 20 个）
n_display = min(20, len(sorted_names))
axes[0].barh(
    range(n_display),
    sorted_importances[:n_display][::-1],
    color="steelblue", edgecolor="white",
)
axes[0].set_yticks(range(n_display))
axes[0].set_yticklabels(sorted_names[:n_display][::-1])
axes[0].set_xlabel("重要性")
axes[0].set_title("随机森林特征重要性 (Top {})".format(n_display))
axes[0].grid(True, axis="x", alpha=0.3)

# 图2: 预测值 vs 实际值
if task_type == "regression":
    axes[1].scatter(y_test, y_pred, alpha=0.6, edgecolors="k", linewidths=0.5)
    min_val = min(y_test.min(), y_pred.min())
    max_val = max(y_test.max(), y_pred.max())
    axes[1].plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2, label="理想线")
    axes[1].set_xlabel("实际值")
    axes[1].set_ylabel("预测值")
    axes[1].set_title(f"预测值 vs 实际值 (R²={r2:.4f})")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
else:
    from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(ax=axes[1], cmap="Blues")
    axes[1].set_title(f"混淆矩阵 (Accuracy={acc:.4f})")

plt.tight_layout()
plt.savefig("random_forest_result.png", dpi=150)
print("===FIGURE: random_forest_result.png | 随机森林预测结果===")
plt.show()
''',
    ),
}
