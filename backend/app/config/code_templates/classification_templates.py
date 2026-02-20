"""分类模型代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

CLASSIFICATION_TEMPLATES = {
    "logistic_regression": CodeTemplate(
        name="逻辑回归分类",
        category="分类",
        description="使用 sklearn LogisticRegression 进行二分类或多分类任务，"
        "包含特征标准化、训练测试集划分、混淆矩阵可视化和分类报告输出。",
        applicable_models=["逻辑回归", "Logistic Regression", "logistic", "二分类"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib", "seaborn"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{TARGET_COLUMN}}": "目标变量列名",
            "{{TEST_SIZE}}": "测试集比例，默认 0.2",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

# ===== 数据加载与预处理 =====
df = pd.read_csv("{{DATA_PATH}}")
target_col = "{{TARGET_COLUMN}}"
X = df.drop(columns=[target_col])
y = df[target_col]

# 仅保留数值列
X = X.select_dtypes(include=[np.number])
X = X.fillna(X.median())

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size={{TEST_SIZE}}, random_state=42, stratify=y
)

# 特征标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ===== 模型训练 =====
model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train_scaled, y_train)

# ===== 模型评估 =====
y_pred = model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
print(f"准确率: {accuracy:.4f}")
print("\\n分类报告:")
print(classification_report(y_test, y_pred))

# ===== 混淆矩阵可视化 =====
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False)
plt.xlabel("预测标签")
plt.ylabel("真实标签")
plt.title(f"逻辑回归混淆矩阵 (准确率={accuracy:.4f})")
plt.tight_layout()
plt.savefig("logistic_regression_confusion_matrix.png", dpi=150)
print("混淆矩阵已保存: logistic_regression_confusion_matrix.png")

# 特征系数
coef_df = pd.DataFrame({
    "特征": X.columns,
    "系数": model.coef_.flatten() if model.coef_.shape[0] == 1 else np.mean(np.abs(model.coef_), axis=0),
}).sort_values("系数", key=abs, ascending=False)
print("\\n特征重要性 (按系数绝对值排序):")
print(coef_df.to_string(index=False))
''',
    ),
    "decision_tree": CodeTemplate(
        name="决策树分类",
        category="分类",
        description="使用 sklearn DecisionTreeClassifier 进行分类，"
        "支持树结构可视化、特征重要性分析和剪枝参数调优。",
        applicable_models=["决策树", "Decision Tree", "CART", "ID3", "C4.5"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{TARGET_COLUMN}}": "目标变量列名",
            "{{MAX_DEPTH}}": "树的最大深度，默认 5",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
target_col = "{{TARGET_COLUMN}}"
X = df.drop(columns=[target_col])
y = df[target_col]
X = X.select_dtypes(include=[np.number]).fillna(X.select_dtypes(include=[np.number]).median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ===== 模型训练 (含预剪枝) =====
model = DecisionTreeClassifier(
    max_depth={{MAX_DEPTH}},
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
)
model.fit(X_train, y_train)

# ===== 模型评估 =====
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"准确率: {accuracy:.4f}")
print("\\n分类报告:")
print(classification_report(y_test, y_pred))

# ===== 决策树可视化 =====
plt.figure(figsize=(20, 10))
plot_tree(
    model,
    feature_names=list(X.columns),
    filled=True,
    rounded=True,
    fontsize=8,
    max_depth=3,  # 可视化时限制深度，避免过密
)
plt.title("决策树结构")
plt.tight_layout()
plt.savefig("decision_tree_structure.png", dpi=150, bbox_inches="tight")
print("决策树结构已保存: decision_tree_structure.png")

# ===== 特征重要性 =====
importance_df = pd.DataFrame({
    "特征": X.columns,
    "重要性": model.feature_importances_,
}).sort_values("重要性", ascending=False)

plt.figure(figsize=(10, 6))
plt.barh(importance_df["特征"][:15], importance_df["重要性"][:15])
plt.xlabel("特征重要性")
plt.title("决策树 - 特征重要性排名 (Top 15)")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig("decision_tree_feature_importance.png", dpi=150)
print("特征重要性已保存: decision_tree_feature_importance.png")
print(importance_df.to_string(index=False))
''',
    ),
    "random_forest": CodeTemplate(
        name="随机森林分类",
        category="分类",
        description="使用 sklearn RandomForestClassifier 进行集成分类，"
        "包含特征重要性排序、OOB 误差估计和 K 折交叉验证。",
        applicable_models=["随机森林", "Random Forest", "RF", "集成学习"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{TARGET_COLUMN}}": "目标变量列名",
            "{{N_ESTIMATORS}}": "树的数量，默认 100",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
target_col = "{{TARGET_COLUMN}}"
X = df.drop(columns=[target_col])
y = df[target_col]
X = X.select_dtypes(include=[np.number]).fillna(X.select_dtypes(include=[np.number]).median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ===== 模型训练 =====
model = RandomForestClassifier(
    n_estimators={{N_ESTIMATORS}},
    max_depth=None,
    oob_score=True,
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)

# ===== 模型评估 =====
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"测试集准确率: {accuracy:.4f}")
print(f"OOB 准确率: {model.oob_score_:.4f}")
print("\\n分类报告:")
print(classification_report(y_test, y_pred))

# K 折交叉验证
cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
print(f"\\n5 折交叉验证准确率: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# ===== 特征重要性可视化 =====
importance_df = pd.DataFrame({
    "特征": X.columns,
    "重要性": model.feature_importances_,
}).sort_values("重要性", ascending=False)

plt.figure(figsize=(10, 6))
top_n = min(20, len(importance_df))
plt.barh(importance_df["特征"][:top_n], importance_df["重要性"][:top_n], color="steelblue")
plt.xlabel("特征重要性 (Gini)")
plt.title(f"随机森林 - 特征重要性排名 (Top {top_n})")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig("random_forest_feature_importance.png", dpi=150)
print(f"特征重要性已保存: random_forest_feature_importance.png")
print(importance_df.head(top_n).to_string(index=False))
''',
    ),
    "svm": CodeTemplate(
        name="SVM分类",
        category="分类",
        description="使用 sklearn SVC 进行支持向量机分类，"
        "包含核函数选择、参数网格搜索和决策边界可视化（二维特征时）。",
        applicable_models=["SVM", "支持向量机", "SVC", "Support Vector"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{TARGET_COLUMN}}": "目标变量列名",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt

# ===== 数据加载与预处理 =====
df = pd.read_csv("{{DATA_PATH}}")
target_col = "{{TARGET_COLUMN}}"
X = df.drop(columns=[target_col])
y = df[target_col]
X = X.select_dtypes(include=[np.number]).fillna(X.select_dtypes(include=[np.number]).median())

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ===== 网格搜索最优参数 =====
param_grid = {
    "C": [0.1, 1, 10],
    "kernel": ["rbf", "linear"],
    "gamma": ["scale", "auto"],
}
grid_search = GridSearchCV(
    SVC(random_state=42), param_grid, cv=3, scoring="accuracy", n_jobs=-1
)
grid_search.fit(X_train_scaled, y_train)
print(f"最优参数: {grid_search.best_params_}")
print(f"交叉验证最优准确率: {grid_search.best_score_:.4f}")

# ===== 使用最优模型评估 =====
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
print(f"\\n测试集准确率: {accuracy:.4f}")
print("\\n分类报告:")
print(classification_report(y_test, y_pred))

# ===== 决策边界可视化 (取前两个主成分) =====
from sklearn.decomposition import PCA

pca = PCA(n_components=2)
X_train_2d = pca.fit_transform(X_train_scaled)
X_test_2d = pca.transform(X_test_scaled)

svm_2d = SVC(**grid_search.best_params_, random_state=42)
svm_2d.fit(X_train_2d, y_train)

h = 0.05
x_min, x_max = X_train_2d[:, 0].min() - 1, X_train_2d[:, 0].max() + 1
y_min, y_max = X_train_2d[:, 1].min() - 1, X_train_2d[:, 1].max() + 1
xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))
Z = svm_2d.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)

plt.figure(figsize=(10, 7))
plt.contourf(xx, yy, Z, alpha=0.3, cmap="coolwarm")
plt.scatter(X_test_2d[:, 0], X_test_2d[:, 1], c=y_test, cmap="coolwarm", edgecolors="k", s=30)
plt.xlabel("主成分 1")
plt.ylabel("主成分 2")
plt.title(f"SVM 决策边界 (PCA 降维, 准确率={accuracy:.4f})")
plt.tight_layout()
plt.savefig("svm_decision_boundary.png", dpi=150)
print("决策边界已保存: svm_decision_boundary.png")
''',
    ),
}


def get_templates() -> list[CodeTemplate]:
    """返回所有分类模板列表。"""
    return list(CLASSIFICATION_TEMPLATES.values())
