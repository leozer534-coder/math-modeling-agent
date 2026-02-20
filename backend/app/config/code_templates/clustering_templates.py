"""聚类模型代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

CLUSTERING_TEMPLATES = {
    "kmeans": CodeTemplate(
        name="K-means聚类",
        category="聚类",
        description="使用 sklearn KMeans 进行聚类分析，"
        "包含肘部法则确定最优 K 值、轮廓系数评估和聚类结果可视化。",
        applicable_models=["K-means", "KMeans", "K均值", "k-means聚类"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{K_RANGE_MAX}}": "搜索的最大聚类数，默认 10",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

# ===== 数据加载与预处理 =====
df = pd.read_csv("{{DATA_PATH}}")
X = df.select_dtypes(include=[np.number]).dropna()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ===== 肘部法则确定最优 K =====
k_range = range(2, {{K_RANGE_MAX}} + 1)
inertias = []
silhouette_scores = []

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    inertias.append(kmeans.inertia_)
    silhouette_scores.append(silhouette_score(X_scaled, labels))

best_k = list(k_range)[np.argmax(silhouette_scores)]
print(f"最优聚类数 K = {best_k} (轮廓系数最大)")

# ===== 肘部法则 + 轮廓系数可视化 =====
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].plot(list(k_range), inertias, "bo-")
axes[0].set_xlabel("聚类数 K")
axes[0].set_ylabel("惯性 (Inertia)")
axes[0].set_title("肘部法则")
axes[0].grid(True)

axes[1].plot(list(k_range), silhouette_scores, "rs-")
axes[1].set_xlabel("聚类数 K")
axes[1].set_ylabel("轮廓系数")
axes[1].set_title("轮廓系数")
axes[1].axvline(x=best_k, color="g", linestyle="--", label=f"最优 K={best_k}")
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig("kmeans_elbow_silhouette.png", dpi=150)
print("肘部法则与轮廓系数图已保存: kmeans_elbow_silhouette.png")

# ===== 使用最优 K 进行聚类 =====
kmeans_best = KMeans(n_clusters=best_k, random_state=42, n_init=10)
labels = kmeans_best.fit_predict(X_scaled)
df["cluster"] = labels

# 聚类结果可视化 (PCA 降至二维)
from sklearn.decomposition import PCA

pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_scaled)

plt.figure(figsize=(10, 7))
for c in range(best_k):
    mask = labels == c
    plt.scatter(X_2d[mask, 0], X_2d[mask, 1], label=f"簇 {c}", alpha=0.6, s=30)
centers_2d = pca.transform(kmeans_best.cluster_centers_)
plt.scatter(centers_2d[:, 0], centers_2d[:, 1], c="black", marker="X", s=200, label="聚类中心")
plt.xlabel("主成分 1")
plt.ylabel("主成分 2")
plt.title(f"K-means 聚类结果 (K={best_k})")
plt.legend()
plt.tight_layout()
plt.savefig("kmeans_clusters.png", dpi=150)
print("聚类结果已保存: kmeans_clusters.png")

# 各簇统计
for c in range(best_k):
    print(f"\\n簇 {c}: {(labels == c).sum()} 个样本")
    print(df[labels == c].describe().round(2))
''',
    ),
    "hierarchical": CodeTemplate(
        name="层次聚类",
        category="聚类",
        description="使用 scipy 层次聚类方法，"
        "包含树状图 (dendrogram) 可视化和距离矩阵热力图。",
        applicable_models=["层次聚类", "Hierarchical", "系统聚类", "Ward", "凝聚聚类"],
        dependencies=["scipy", "scikit-learn", "numpy", "pandas", "matplotlib", "seaborn"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{N_CLUSTERS}}": "聚类数量，默认 3",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt
import seaborn as sns

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
X = df.select_dtypes(include=[np.number]).dropna()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ===== 层次聚类 (Ward 方法) =====
Z = linkage(X_scaled, method="ward", metric="euclidean")

# ===== 树状图 =====
plt.figure(figsize=(14, 7))
dendrogram(
    Z,
    truncate_mode="lastp",
    p=30,  # 显示最后 30 个合并步骤
    leaf_rotation=90,
    leaf_font_size=8,
    color_threshold=Z[-({{N_CLUSTERS}} - 1), 2],  # 按聚类数着色
)
plt.xlabel("样本索引")
plt.ylabel("距离")
plt.title("层次聚类树状图 (Ward 方法)")
plt.axhline(y=Z[-({{N_CLUSTERS}} - 1), 2], color="r", linestyle="--", label=f"切割线 (K={{{{{N_CLUSTERS}}}}})")
plt.tight_layout()
plt.savefig("hierarchical_dendrogram.png", dpi=150)
print("树状图已保存: hierarchical_dendrogram.png")

# ===== 获取聚类标签 =====
labels = fcluster(Z, t={{N_CLUSTERS}}, criterion="maxclust")
df["cluster"] = labels
print(f"\\n聚类数: {{N_CLUSTERS}}")
for c in sorted(df["cluster"].unique()):
    print(f"  簇 {c}: {(labels == c).sum()} 个样本")

# ===== 距离矩阵热力图 =====
dist_matrix = squareform(pdist(X_scaled, metric="euclidean"))
order = np.argsort(labels)
dist_sorted = dist_matrix[np.ix_(order, order)]

plt.figure(figsize=(10, 8))
sns.heatmap(dist_sorted, cmap="YlOrRd", xticklabels=False, yticklabels=False)
plt.title("样本距离矩阵热力图 (按簇排序)")
plt.tight_layout()
plt.savefig("hierarchical_distance_heatmap.png", dpi=150)
print("距离矩阵热力图已保存: hierarchical_distance_heatmap.png")
''',
    ),
    "dbscan": CodeTemplate(
        name="DBSCAN密度聚类",
        category="聚类",
        description="使用 sklearn DBSCAN 进行基于密度的聚类分析，"
        "支持通过 K-距离图辅助选择 eps 参数和噪声点识别。",
        applicable_models=["DBSCAN", "密度聚类", "基于密度"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{EPS}}": "邻域半径，默认 0.5",
            "{{MIN_SAMPLES}}": "最小样本数，默认 5",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
X = df.select_dtypes(include=[np.number]).dropna()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ===== K-距离图辅助选择 eps =====
k = {{MIN_SAMPLES}}
nn = NearestNeighbors(n_neighbors=k)
nn.fit(X_scaled)
distances, _ = nn.kneighbors(X_scaled)
k_distances = np.sort(distances[:, -1])

plt.figure(figsize=(10, 5))
plt.plot(k_distances)
plt.xlabel("样本 (按距离排序)")
plt.ylabel(f"{k}-距离")
plt.title(f"K-距离图 (K={k})")
plt.grid(True)
plt.tight_layout()
plt.savefig("dbscan_k_distance.png", dpi=150)
print("K-距离图已保存: dbscan_k_distance.png")

# ===== DBSCAN 聚类 =====
dbscan = DBSCAN(eps={{EPS}}, min_samples={{MIN_SAMPLES}})
labels = dbscan.fit_predict(X_scaled)

n_clusters = len(set(labels) - {-1})
n_noise = (labels == -1).sum()
print(f"\\n聚类数: {n_clusters}")
print(f"噪声点数: {n_noise} ({n_noise / len(labels) * 100:.1f}%)")

# 轮廓系数 (排除噪声点)
if n_clusters >= 2:
    mask = labels != -1
    score = silhouette_score(X_scaled[mask], labels[mask])
    print(f"轮廓系数 (排除噪声): {score:.4f}")

# ===== 聚类结果可视化 =====
pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_scaled)

plt.figure(figsize=(10, 7))
unique_labels = sorted(set(labels))
for label in unique_labels:
    mask = labels == label
    if label == -1:
        plt.scatter(X_2d[mask, 0], X_2d[mask, 1], c="gray", marker="x",
                    s=20, alpha=0.5, label="噪声点")
    else:
        plt.scatter(X_2d[mask, 0], X_2d[mask, 1], label=f"簇 {label}",
                    alpha=0.6, s=30)
plt.xlabel("主成分 1")
plt.ylabel("主成分 2")
plt.title(f"DBSCAN 聚类结果 (eps={{{EPS}}}, min_samples={{{MIN_SAMPLES}}})")
plt.legend()
plt.tight_layout()
plt.savefig("dbscan_clusters.png", dpi=150)
print("聚类结果已保存: dbscan_clusters.png")
''',
    ),
    "gmm": CodeTemplate(
        name="GMM高斯混合聚类",
        category="聚类",
        description="使用 sklearn GaussianMixture 进行概率聚类，"
        "通过 BIC/AIC 准则选择最优组件数，并可视化概率密度。",
        applicable_models=["GMM", "高斯混合", "EM算法", "GaussianMixture"],
        dependencies=["scikit-learn", "numpy", "pandas", "matplotlib"],
        placeholders={
            "{{DATA_PATH}}": "数据文件路径，如 'data.csv'",
            "{{K_RANGE_MAX}}": "搜索的最大组件数，默认 10",
        },
        code='''import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# ===== 数据加载 =====
df = pd.read_csv("{{DATA_PATH}}")
X = df.select_dtypes(include=[np.number]).dropna()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ===== BIC/AIC 选择最优组件数 =====
k_range = range(2, {{K_RANGE_MAX}} + 1)
bic_scores = []
aic_scores = []

for k in k_range:
    gmm = GaussianMixture(n_components=k, covariance_type="full", random_state=42)
    gmm.fit(X_scaled)
    bic_scores.append(gmm.bic(X_scaled))
    aic_scores.append(gmm.aic(X_scaled))

best_k_bic = list(k_range)[np.argmin(bic_scores)]
best_k_aic = list(k_range)[np.argmin(aic_scores)]
print(f"BIC 最优组件数: {best_k_bic}")
print(f"AIC 最优组件数: {best_k_aic}")

# ===== BIC/AIC 对比图 =====
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(list(k_range), bic_scores, "bo-", label="BIC")
ax.plot(list(k_range), aic_scores, "rs-", label="AIC")
ax.axvline(x=best_k_bic, color="b", linestyle="--", alpha=0.5)
ax.set_xlabel("组件数 K")
ax.set_ylabel("信息准则得分")
ax.set_title("GMM 组件数选择 (BIC/AIC)")
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.savefig("gmm_bic_aic.png", dpi=150)
print("BIC/AIC 图已保存: gmm_bic_aic.png")

# ===== 使用最优 K 聚类 =====
best_k = best_k_bic
gmm_best = GaussianMixture(n_components=best_k, covariance_type="full", random_state=42)
gmm_best.fit(X_scaled)
labels = gmm_best.predict(X_scaled)
probs = gmm_best.predict_proba(X_scaled)

print(f"\\n使用 K={best_k} 的聚类结果:")
for c in range(best_k):
    count = (labels == c).sum()
    avg_prob = probs[labels == c, c].mean()
    print(f"  簇 {c}: {count} 个样本, 平均归属概率 {avg_prob:.4f}")

# ===== 聚类可视化 =====
pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_scaled)

plt.figure(figsize=(10, 7))
scatter = plt.scatter(X_2d[:, 0], X_2d[:, 1], c=labels, cmap="viridis", alpha=0.6, s=30)
plt.colorbar(scatter, label="簇标签")
plt.xlabel("主成分 1")
plt.ylabel("主成分 2")
plt.title(f"GMM 聚类结果 (K={best_k})")
plt.tight_layout()
plt.savefig("gmm_clusters.png", dpi=150)
print("聚类结果已保存: gmm_clusters.png")
''',
    ),
}


def get_templates() -> list[CodeTemplate]:
    """返回所有聚类模板列表。"""
    return list(CLUSTERING_TEMPLATES.values())
