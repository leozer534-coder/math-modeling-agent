"""评价类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

EVALUATION_TEMPLATES = {
    "ahp_topsis": CodeTemplate(
        name="AHP-TOPSIS 综合评价",
        category="评价",
        description="层次分析法确定权重 + TOPSIS 排序的组合评价方法",
        applicable_models=["AHP", "TOPSIS", "层次分析", "综合评价"],
        dependencies=["numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt

# ========== AHP 权重计算 ==========
# 构造比较矩阵 (n*n, 正互反矩阵)
comparison_matrix = np.array([
    [1,   3,   5],
    [1/3, 1,   2],
    [1/5, 1/2, 1],
])  # TODO: 替换为实际比较矩阵

eigenvalues, eigenvectors = np.linalg.eig(comparison_matrix)
max_idx = np.argmax(eigenvalues.real)
weights = eigenvectors[:, max_idx].real
weights = weights / weights.sum()

# 一致性检验
n = len(comparison_matrix)
lambda_max = eigenvalues[max_idx].real
CI = (lambda_max - n) / (n - 1) if n > 1 else 0
RI_table = {
    1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
    7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49, 11: 1.51,
    12: 1.54, 13: 1.56, 14: 1.58, 15: 1.59,
}
RI = RI_table.get(n, 1.59)
CR = CI / RI if RI > 0 else 0
is_consistent = CR < 0.1
print(f"AHP 权重: {weights}")
print(f"最大特征值 lambda_max = {lambda_max:.4f}")
print(f"一致性指标 CI = {CI:.4f}, RI = {RI}")
print(f"一致性比率 CR = {CR:.4f} ({'通过' if is_consistent else '未通过, 请调整比较矩阵'})")

# ========== TOPSIS 排序 ==========
# 决策矩阵 (m个方案 * n个指标)
decision_matrix = np.array([
    [8, 7, 6],
    [6, 9, 5],
    [9, 6, 8],
])  # TODO: 替换
benefit_criteria = [True, True, True]  # 各指标是否越大越好

# 归一化 (零除保护)
norms = np.sqrt((decision_matrix ** 2).sum(axis=0))
norms[norms == 0] = 1
R = decision_matrix / norms
V = R * weights

# 理想解
pos_ideal = np.where(benefit_criteria, V.max(axis=0), V.min(axis=0))
neg_ideal = np.where(benefit_criteria, V.min(axis=0), V.max(axis=0))

d_pos = np.sqrt(((V - pos_ideal) ** 2).sum(axis=1))
d_neg = np.sqrt(((V - neg_ideal) ** 2).sum(axis=1))
scores = d_neg / (d_pos + d_neg + 1e-10)
rankings = np.argsort(-scores) + 1

for i, (s, r) in enumerate(zip(scores, rankings)):
    print(f"方案 {i+1}: 贴近度={s:.4f}, 排名={r}")
''',
    ),
    "entropy_weight_tpl": CodeTemplate(
        name="熵权法客观赋权",
        category="评价",
        description="基于信息熵计算指标客观权重",
        applicable_models=["熵权法", "entropy_weight", "客观赋权"],
        dependencies=["numpy"],
        code='''import numpy as np

# 决策矩阵 (m个样本 * n个指标)
X = np.array([...])  # TODO: 替换

m, n = X.shape

# 极差归一化
X_min, X_max = X.min(axis=0), X.max(axis=0)
ranges = X_max - X_min
ranges[ranges == 0] = 1
P = (X - X_min) / ranges

# 计算比重
P_sum = P.sum(axis=0)
P_sum[P_sum == 0] = 1
P_ratio = P / P_sum

# 计算信息熵
k = 1 / np.log(m)
P_safe = np.where(P_ratio > 0, P_ratio, 1)
entropy = -k * (P_ratio * np.log(P_safe)).sum(axis=0)

# 权重
divergence = 1 - entropy
weights = divergence / divergence.sum()
print(f"熵权法权重: {weights}")
''',
    ),
    "fuzzy_evaluation_tpl": CodeTemplate(
        name="模糊综合评价",
        category="评价",
        description="基于模糊数学的综合评价方法，支持多等级隶属度合成",
        applicable_models=["模糊评价", "fuzzy_evaluation", "模糊综合评价"],
        dependencies=["numpy"],
        code='''import numpy as np

# ========== 模糊综合评价 ==========
# 评价等级
levels = ["优", "良", "中", "差"]  # TODO: 替换

# 因素权重向量 (n 个因素)
weights = np.array([0.3, 0.3, 0.2, 0.2])  # TODO: 替换

# 模糊评价矩阵 R (n个因素 * m个等级的隶属度)
R = np.array([
    [0.5, 0.3, 0.2, 0.0],
    [0.4, 0.4, 0.1, 0.1],
    [0.3, 0.3, 0.3, 0.1],
    [0.2, 0.5, 0.2, 0.1],
])  # TODO: 替换，每行之和应为 1

# 模糊合成 (加权平均型)
w = weights.reshape(1, -1)
B = (w @ R).flatten()

# 归一化
b_sum = B.sum()
if b_sum > 0:
    B = B / b_sum

best_idx = int(np.argmax(B))
print("模糊综合评价结果向量:", np.round(B, 4))
for level, score in zip(levels, B):
    print(f"  {level}: {score:.4f}")
print(f"最终评价等级: {levels[best_idx]} (隶属度={B[best_idx]:.4f})")
''',
    ),
    "pca_analysis_tpl": CodeTemplate(
        name="PCA 主成分分析",
        category="评价",
        description="主成分分析进行降维和特征提取",
        applicable_models=["PCA", "主成分分析", "降维"],
        dependencies=["sklearn", "numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# 数据矩阵 (m个样本 * n个特征)
X = np.array([...])  # TODO: 替换

# 标准化
X_scaled = StandardScaler().fit_transform(X)

# 全量 PCA 确定主成分数
pca_full = PCA()
pca_full.fit(X_scaled)
cumvar = np.cumsum(pca_full.explained_variance_ratio_)

# 按累计方差贡献率 >= 85% 确定主成分数
variance_threshold = 0.85  # TODO: 可调整
n_components = int(np.searchsorted(cumvar, variance_threshold) + 1)
n_components = min(n_components, X.shape[1])

# 降维
pca = PCA(n_components=n_components)
X_transformed = pca.fit_transform(X_scaled)
loadings = pca.components_.T * np.sqrt(pca.explained_variance_)

print(f"保留 {n_components} 个主成分，累计方差贡献率: {cumvar[n_components-1]:.4f}")
for i, ratio in enumerate(pca.explained_variance_ratio_):
    print(f"  PC{i+1}: 方差贡献率={ratio:.4f}, 累计={cumvar[i]:.4f}")

# 可视化碎石图
plt.figure(figsize=(8, 5))
plt.bar(range(1, len(pca_full.explained_variance_ratio_)+1),
        pca_full.explained_variance_ratio_, alpha=0.6, label="各主成分")
plt.step(range(1, len(cumvar)+1), cumvar, where="mid", label="累计", color="red")
plt.axhline(y=variance_threshold, color="gray", linestyle="--", label=f"阈值={variance_threshold}")
plt.xlabel("主成分序号"); plt.ylabel("方差贡献率")
plt.title("PCA 碎石图"); plt.legend(); plt.grid(True, alpha=0.3)
plt.tight_layout(); plt.savefig("pca_scree_plot.png", dpi=150)
print("PCA 碎石图已保存: pca_scree_plot.png")
''',
    ),
    "dea_analysis_tpl": CodeTemplate(
        name="DEA 数据包络分析",
        category="评价",
        description="CCR/BCC 模型评价决策单元效率",
        applicable_models=["DEA", "数据包络分析", "data_envelopment_analysis"],
        dependencies=["scipy", "numpy"],
        code='''import numpy as np
from scipy.optimize import linprog

# 输入/输出矩阵 (n个DMU)
inputs = np.array([...])   # TODO: m个输入指标, shape=(n, m)
outputs = np.array([...])  # TODO: s个输出指标, shape=(n, s)

n_dmu = len(inputs)
efficiencies = []

for k in range(n_dmu):
    m, s = inputs.shape[1], outputs.shape[1]
    # CCR 对偶形式: min theta s.t. X*lambda <= theta*x_k, Y*lambda >= y_k, lambda >= 0
    c = np.zeros(n_dmu + 1)
    c[-1] = 1  # 最小化 theta

    A_ub_full = np.vstack([
        np.hstack([inputs.T, -inputs[k].reshape(-1, 1)]),
        np.hstack([-outputs.T, np.zeros((s, 1))])
    ])
    b_ub_full = np.concatenate([np.zeros(m), -outputs[k]])

    bounds = [(0, None)] * n_dmu + [(None, None)]
    res = linprog(c, A_ub=A_ub_full, b_ub=b_ub_full, bounds=bounds, method="highs")
    efficiencies.append(res.fun if res.success else 1.0)

for i, eff in enumerate(efficiencies):
    status = "(有效)" if abs(eff - 1.0) < 0.001 else "(无效)"
    print(f"DMU {i+1}: 效率={eff:.4f} {status}")
''',
    ),
    "vikor_tpl": CodeTemplate(
        name="VIKOR 多准则决策",
        category="评价",
        description="VIKOR 折中排序法，通过群体效用值和个体遗憾值进行多准则决策排序，"
        "包含可接受优势和决策稳定性条件检验。",
        applicable_models=["VIKOR", "多准则决策", "折中排序"],
        dependencies=["numpy"],
        code='''import numpy as np

# ========== VIKOR 多准则决策 ==========
# 决策矩阵 (m个方案 * n个指标)
decision_matrix = np.array([
    [8, 7, 6, 9],
    [6, 9, 5, 7],
    [9, 6, 8, 8],
    [7, 8, 7, 6],
])  # TODO: 替换为实际决策矩阵

# 指标权重 (n个指标, 权重之和应为1)
weights = np.array([0.3, 0.25, 0.25, 0.2])  # TODO: 替换为实际权重

# 各指标是否为效益型 (越大越好); False 表示成本型 (越小越好)
benefit_criteria = [True, True, True, True]  # TODO: 替换

# 决策机制系数 v: v=0.5 表示协商一致, v>0.5 偏向群体效用, v<0.5 偏向个体遗憾
v = 0.5  # TODO: 可调整

m, n = decision_matrix.shape
X = decision_matrix.astype(float)

print("=" * 55)
print("VIKOR 多准则决策分析报告")
print("=" * 55)
print(f"方案数: {m}, 指标数: {n}")
print(f"权重: {weights}")
print(f"决策机制系数 v = {v}")

# ===== 确定各指标的理想值和负理想值 =====
f_star = np.zeros(n)  # 各指标最优值
f_minus = np.zeros(n)  # 各指标最差值

for j in range(n):
    if benefit_criteria[j]:
        f_star[j] = X[:, j].max()
        f_minus[j] = X[:, j].min()
    else:
        f_star[j] = X[:, j].min()
        f_minus[j] = X[:, j].max()

print(f"\\n理想值 f*:  {f_star}")
print(f"负理想值 f-: {f_minus}")

# ===== 计算归一化距离矩阵 =====
denom = f_star - f_minus
denom[denom == 0] = 1e-10  # 防止除零
D = (f_star - X) / denom  # 归一化距离, shape=(m, n)

# ===== 计算群体效用值 S 和个体遗憾值 R =====
S = np.zeros(m)  # 群体效用值 (加权曼哈顿距离)
R = np.zeros(m)  # 个体遗憾值 (加权切比雪夫距离)

for i in range(m):
    S[i] = np.sum(weights * D[i, :])
    R[i] = np.max(weights * D[i, :])

S_star, S_minus = S.min(), S.max()
R_star, R_minus = R.min(), R.max()

print(f"\\n群体效用值 S: {np.round(S, 4)}")
print(f"个体遗憾值 R: {np.round(R, 4)}")

# ===== 计算折中排序值 Q =====
Q = np.zeros(m)
s_range = S_minus - S_star if S_minus != S_star else 1e-10
r_range = R_minus - R_star if R_minus != R_star else 1e-10

for i in range(m):
    Q[i] = v * (S[i] - S_star) / s_range + (1 - v) * (R[i] - R_star) / r_range

print(f"折中排序值 Q: {np.round(Q, 4)}")

# ===== 排序 =====
rank_S = np.argsort(S) + 1
rank_R = np.argsort(R) + 1
rank_Q = np.argsort(Q) + 1

# 按 Q 值排序的方案索引
sorted_indices = np.argsort(Q)

print(f"\\n{'方案':<8}{'S值':<12}{'S排名':<8}{'R值':<12}{'R排名':<8}{'Q值':<12}{'Q排名':<8}")
print("-" * 68)
for i in range(m):
    print(f"方案{i+1:<4}{S[i]:<12.4f}{rank_S[i]:<8}{R[i]:<12.4f}{rank_R[i]:<8}{Q[i]:<12.4f}{rank_Q[i]:<8}")

# ===== 条件检验 =====
print(f"\\n{'='*55}")
print("条件检验")
print("=" * 55)

best = sorted_indices[0]  # Q 值最小的方案
second = sorted_indices[1]  # Q 值第二小的方案

# 条件 C1: 可接受优势
DQ = 1.0 / (m - 1)
advantage = Q[second] - Q[best]
c1_pass = advantage >= DQ
print(f"\\n[C1] 可接受优势条件:")
print(f"  Q({second+1}) - Q({best+1}) = {advantage:.4f} >= DQ = {DQ:.4f} ? {'通过' if c1_pass else '不通过'}")

# 条件 C2: 决策稳定性 (Q最优方案同时也应在S或R排序中最优)
c2_pass = (rank_S[best] == 1) or (rank_R[best] == 1)
print(f"[C2] 决策稳定性条件:")
print(f"  方案{best+1} 的 S排名={rank_S[best]}, R排名={rank_R[best]} -> {'通过' if c2_pass else '不通过'}")

# ===== 最终结论 =====
print(f"\\n{'='*55}")
print("最终结论")
print("=" * 55)
if c1_pass and c2_pass:
    print(f"方案{best+1} 为折中最优解。")
elif not c1_pass:
    # 不满足可接受优势, 输出折中集合
    compromise_set = [sorted_indices[0]]
    for k in range(1, m):
        if Q[sorted_indices[k]] - Q[best] < DQ:
            compromise_set.append(sorted_indices[k])
        else:
            break
    print(f"不满足可接受优势条件, 折中解集合: {['方案'+str(idx+1) for idx in compromise_set]}")
elif not c2_pass:
    print(f"不满足决策稳定性条件, 折中解集合: [方案{best+1}, 方案{second+1}]")
''',
    ),
}
