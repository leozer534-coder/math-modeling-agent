"""动态规划模型代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

DP_TEMPLATES = {
    "knapsack_01": CodeTemplate(
        name="0-1背包问题",
        category="动态规划",
        description="经典 0-1 背包问题的动态规划解法，包含 DP 表构建、"
        "回溯最优解方案和结果可视化。",
        applicable_models=["0-1背包", "背包问题", "Knapsack", "01背包"],
        dependencies=["numpy", "matplotlib", "pandas"],
        placeholders={
            "{{WEIGHTS}}": "物品重量列表，如 [2, 3, 4, 5, 9]",
            "{{VALUES}}": "物品价值列表，如 [3, 4, 5, 8, 10]",
            "{{CAPACITY}}": "背包容量，如 20",
            "{{ITEM_NAMES}}": "物品名称列表，如 ['A', 'B', 'C', 'D', 'E']",
        },
        code='''import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# ===== 问题参数 =====
weights = {{WEIGHTS}}
values = {{VALUES}}
capacity = {{CAPACITY}}
item_names = {{ITEM_NAMES}}

n = len(weights)
print("=" * 50)
print("0-1 背包问题 (动态规划)")
print(f"物品数: {n}, 背包容量: {capacity}")
print("=" * 50)

# ===== DP 求解 =====
dp = np.zeros((n + 1, capacity + 1), dtype=int)

for i in range(1, n + 1):
    for w in range(capacity + 1):
        if weights[i - 1] <= w:
            dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
        else:
            dp[i][w] = dp[i - 1][w]

max_value = dp[n][capacity]
print(f"\\n最大总价值: {max_value}")

# ===== 回溯最优解 =====
selected = []
w_remain = capacity
for i in range(n, 0, -1):
    if dp[i][w_remain] != dp[i - 1][w_remain]:
        selected.append(i - 1)
        w_remain -= weights[i - 1]
selected.reverse()

total_weight = sum(weights[i] for i in selected)
print(f"选择的物品: {[item_names[i] for i in selected]}")
print(f"总重量: {total_weight} / {capacity}")

# 详细方案
result_df = pd.DataFrame({
    "物品": item_names,
    "重量": weights,
    "价值": values,
    "是否选中": ["是" if i in selected else "否" for i in range(n)],
})
print("\\n详细方案:")
print(result_df.to_string(index=False))

# ===== 可视化 =====
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# DP 表热力图 (仅显示最后几行避免过密)
show_rows = min(n + 1, 10)
dp_show = dp[-show_rows:]
row_labels = [f"物品{i}" if i > 0 else "空" for i in range(n + 1)][-show_rows:]
col_step = max(1, capacity // 20)
col_indices = list(range(0, capacity + 1, col_step))
if capacity not in col_indices:
    col_indices.append(capacity)

ax0 = axes[0]
im = ax0.imshow(dp_show[:, col_indices], cmap="YlGnBu", aspect="auto")
ax0.set_yticks(range(show_rows))
ax0.set_yticklabels(row_labels)
ax0.set_xticks(range(len(col_indices)))
ax0.set_xticklabels(col_indices, rotation=45)
ax0.set_xlabel("容量")
ax0.set_ylabel("物品")
ax0.set_title("DP 表 (部分)")
plt.colorbar(im, ax=ax0, label="最大价值")

# 选择方案柱状图
colors = ["#2ecc71" if i in selected else "#bdc3c7" for i in range(n)]
axes[1].bar(item_names, values, color=colors, edgecolor="gray")
axes[1].set_xlabel("物品")
axes[1].set_ylabel("价值")
axes[1].set_title(f"0-1 背包选择方案 (最大价值={max_value})")
for i in selected:
    axes[1].annotate(f"w={weights[i]}", (item_names[i], values[i]),
                     textcoords="offset points", xytext=(0, 5), ha="center", fontsize=9)
axes[1].grid(True, alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig("knapsack_01_result.png", dpi=150)
print("\\n背包问题求解图已保存: knapsack_01_result.png")
''',
    ),
    "lcs": CodeTemplate(
        name="最长公共子序列",
        category="动态规划",
        description="使用动态规划求解最长公共子序列 (LCS) 问题，"
        "包含 DP 矩阵构建、回溯路径和结果可视化。",
        applicable_models=["LCS", "最长公共子序列", "子序列匹配", "序列比对"],
        dependencies=["numpy", "matplotlib"],
        placeholders={
            "{{SEQ_A}}": "序列 A，如 'ABCBDAB'",
            "{{SEQ_B}}": "序列 B，如 'BDCAB'",
        },
        code='''import numpy as np
import matplotlib.pyplot as plt

# ===== 输入序列 =====
seq_a = "{{SEQ_A}}"
seq_b = "{{SEQ_B}}"
m, n = len(seq_a), len(seq_b)

print("=" * 50)
print("最长公共子序列 (LCS)")
print(f"序列 A: {seq_a} (长度={m})")
print(f"序列 B: {seq_b} (长度={n})")
print("=" * 50)

# ===== DP 求解 =====
dp = np.zeros((m + 1, n + 1), dtype=int)

for i in range(1, m + 1):
    for j in range(1, n + 1):
        if seq_a[i - 1] == seq_b[j - 1]:
            dp[i][j] = dp[i - 1][j - 1] + 1
        else:
            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

lcs_length = dp[m][n]
print(f"\\nLCS 长度: {lcs_length}")

# ===== 回溯 LCS =====
lcs_chars = []
i, j = m, n
path = []  # 记录回溯路径
while i > 0 and j > 0:
    if seq_a[i - 1] == seq_b[j - 1]:
        lcs_chars.append(seq_a[i - 1])
        path.append((i, j, "diag"))
        i -= 1
        j -= 1
    elif dp[i - 1][j] >= dp[i][j - 1]:
        path.append((i, j, "up"))
        i -= 1
    else:
        path.append((i, j, "left"))
        j -= 1

lcs_chars.reverse()
lcs_str = "".join(lcs_chars)
print(f"LCS: {lcs_str}")

# ===== 可视化 DP 矩阵 =====
fig, ax = plt.subplots(figsize=(max(8, n + 2), max(6, m + 2)))

# 绘制 DP 矩阵
im = ax.imshow(dp, cmap="YlGnBu", aspect="equal")

# 标注数值
for i in range(m + 1):
    for j in range(n + 1):
        ax.text(j, i, str(dp[i][j]), ha="center", va="center", fontsize=10)

# 标注回溯路径
for (pi, pj, direction) in path:
    if direction == "diag":
        ax.add_patch(plt.Rectangle((pj - 0.5, pi - 0.5), 1, 1,
                     fill=False, edgecolor="red", linewidth=2.5))

# 坐标标签
col_labels = [" "] + list(seq_b)
row_labels = [" "] + list(seq_a)
ax.set_xticks(range(n + 1))
ax.set_xticklabels(col_labels, fontsize=11)
ax.set_yticks(range(m + 1))
ax.set_yticklabels(row_labels, fontsize=11)
ax.set_xlabel("序列 B")
ax.set_ylabel("序列 A")
ax.set_title(f"LCS DP 矩阵 (LCS='{lcs_str}', 长度={lcs_length})")
plt.colorbar(im, ax=ax, shrink=0.7)
plt.tight_layout()
plt.savefig("lcs_dp_matrix.png", dpi=150)
print("\\nLCS DP 矩阵已保存: lcs_dp_matrix.png")

# 序列对齐展示
print(f"\\n序列对齐:")
align_a, align_b = "", ""
ia, ib = 0, 0
lc = 0
for pos in range(max(m, n) + lcs_length):
    if lc < len(lcs_chars) and ia < m and ib < n and seq_a[ia] == lcs_chars[lc] and seq_b[ib] == lcs_chars[lc]:
        align_a += seq_a[ia]
        align_b += seq_b[ib]
        ia += 1
        ib += 1
        lc += 1
    elif ia < m and (lc >= len(lcs_chars) or seq_a[ia] != lcs_chars[lc]):
        align_a += seq_a[ia]
        align_b += "-"
        ia += 1
    elif ib < n:
        align_a += "-"
        align_b += seq_b[ib]
        ib += 1
    else:
        break
print(f"  A: {align_a}")
print(f"  B: {align_b}")
''',
    ),
    "resource_allocation": CodeTemplate(
        name="资源分配DP",
        category="动态规划",
        description="多阶段决策的资源分配问题，使用动态规划求解最优资源分配策略，"
        "输出各阶段的最优分配方案。",
        applicable_models=["资源分配", "多阶段决策", "DP资源", "资源优化"],
        dependencies=["numpy", "pandas", "matplotlib"],
        placeholders={
            "{{TOTAL_RESOURCE}}": "总资源量，如 10",
            "{{BENEFIT_TABLE}}": "收益表 (二维列表)，第i行第j列表示第i个项目分配j单位资源的收益",
            "{{PROJECT_NAMES}}": "项目名称列表，如 ['项目A', '项目B', '项目C']",
        },
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ===== 问题参数 =====
total_resource = {{TOTAL_RESOURCE}}
benefit_table = np.array({{BENEFIT_TABLE}})  # shape: (项目数, 最大资源+1)
project_names = {{PROJECT_NAMES}}

n_projects = len(project_names)
max_alloc = benefit_table.shape[1] - 1  # 每个项目最大可分配资源

print("=" * 50)
print("资源分配问题 (动态规划)")
print(f"总资源: {total_resource}, 项目数: {n_projects}")
print("=" * 50)

# 打印收益表
benefit_df = pd.DataFrame(
    benefit_table,
    index=project_names,
    columns=[f"分配{j}" for j in range(max_alloc + 1)],
)
print("\\n收益表:")
print(benefit_df.to_string())

# ===== DP 求解 =====
dp = np.zeros((n_projects + 1, total_resource + 1), dtype=float)
decision = np.zeros((n_projects + 1, total_resource + 1), dtype=int)

for i in range(1, n_projects + 1):
    for r in range(total_resource + 1):
        best_val = -1
        best_alloc = 0
        max_give = min(r, max_alloc)
        for k in range(max_give + 1):
            val = benefit_table[i - 1][k] + dp[i - 1][r - k]
            if val > best_val:
                best_val = val
                best_alloc = k
        dp[i][r] = best_val
        decision[i][r] = best_alloc

max_benefit = dp[n_projects][total_resource]
print(f"\\n最大总收益: {max_benefit:.2f}")

# ===== 回溯最优策略 =====
allocation = []
r_remain = total_resource
for i in range(n_projects, 0, -1):
    alloc = decision[i][r_remain]
    allocation.append(alloc)
    r_remain -= alloc
allocation.reverse()

print("\\n最优分配方案:")
result_df = pd.DataFrame({
    "项目": project_names,
    "分配资源": allocation,
    "对应收益": [benefit_table[i][allocation[i]] for i in range(n_projects)],
})
print(result_df.to_string(index=False))
print(f"总资源使用: {sum(allocation)} / {total_resource}")

# ===== 可视化 =====
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 分配方案柱状图
colors = plt.cm.Set2(np.linspace(0, 1, n_projects))
axes[0].bar(project_names, allocation, color=colors, edgecolor="gray")
for i, (alloc, benefit) in enumerate(zip(allocation, result_df["对应收益"])):
    axes[0].text(i, alloc + 0.1, f"收益={benefit:.0f}", ha="center", fontsize=9)
axes[0].set_xlabel("项目")
axes[0].set_ylabel("分配资源量")
axes[0].set_title(f"最优资源分配方案 (总收益={max_benefit:.0f})")
axes[0].grid(True, alpha=0.3, axis="y")

# 收益曲线
for i in range(n_projects):
    x_range = range(min(total_resource + 1, benefit_table.shape[1]))
    axes[1].plot(x_range, benefit_table[i, :len(x_range)], "o-", label=project_names[i])
axes[1].set_xlabel("分配资源量")
axes[1].set_ylabel("收益")
axes[1].set_title("各项目收益函数")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("resource_allocation_result.png", dpi=150)
print("\\n资源分配结果图已保存: resource_allocation_result.png")
''',
    ),
    "markov_chain": CodeTemplate(
        name="马尔可夫链",
        category="动态规划",
        description="马尔可夫链模型，包含转移概率矩阵定义、稳态分布计算、"
        "状态预测和转移概率可视化。",
        applicable_models=["马尔可夫", "Markov", "转移矩阵", "马尔可夫链", "随机过程"],
        dependencies=["numpy", "pandas", "matplotlib", "seaborn"],
        placeholders={
            "{{TRANSITION_MATRIX}}": "转移概率矩阵 (二维列表)，如 [[0.7, 0.2, 0.1], [0.3, 0.5, 0.2], [0.2, 0.3, 0.5]]",
            "{{STATE_NAMES}}": "状态名称列表，如 ['晴天', '多云', '雨天']",
            "{{INITIAL_STATE}}": "初始状态索引，如 0",
            "{{N_STEPS}}": "预测步数，默认 50",
        },
        code='''import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ===== 参数设置 =====
P = np.array({{TRANSITION_MATRIX}})
state_names = {{STATE_NAMES}}
initial_state = {{INITIAL_STATE}}
n_steps = {{N_STEPS}}
n_states = len(state_names)

print("=" * 50)
print("马尔可夫链分析")
print("=" * 50)

# 转移矩阵展示
P_df = pd.DataFrame(P, index=state_names, columns=state_names)
print("\\n转移概率矩阵:")
print(P_df.to_string())

# 验证行和为 1
row_sums = P.sum(axis=1)
print(f"\\n行和验证: {row_sums} (应全为 1.0)")

# ===== 稳态分布计算 =====
# 通过特征值分解: pi * P = pi, sum(pi) = 1
eigenvalues, eigenvectors = np.linalg.eig(P.T)
# 找到特征值为 1 的特征向量
idx = np.argmin(np.abs(eigenvalues - 1.0))
stationary = np.real(eigenvectors[:, idx])
stationary = stationary / stationary.sum()  # 归一化

print("\\n稳态分布:")
for name, prob in zip(state_names, stationary):
    print(f"  {name}: {prob:.4f}")

# ===== 状态预测 (多步转移) =====
state_probs = np.zeros((n_steps + 1, n_states))
state_probs[0, initial_state] = 1.0

for t in range(1, n_steps + 1):
    state_probs[t] = state_probs[t - 1] @ P

print(f"\\n从 '{state_names[initial_state]}' 出发:")
for step in [1, 5, 10, 20, n_steps]:
    if step <= n_steps:
        probs = state_probs[step]
        prob_str = ", ".join(f"{state_names[i]}={probs[i]:.4f}" for i in range(n_states))
        print(f"  第 {step:>3} 步: {prob_str}")

# ===== 可视化 =====
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 状态概率随时间变化
for i in range(n_states):
    axes[0].plot(range(n_steps + 1), state_probs[:, i], linewidth=1.5, label=state_names[i])
    axes[0].axhline(y=stationary[i], color="gray", linestyle=":", alpha=0.5)
axes[0].set_xlabel("时间步")
axes[0].set_ylabel("概率")
axes[0].set_title(f"状态概率演化 (初始: {state_names[initial_state]})")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# 转移矩阵热力图
sns.heatmap(P, annot=True, fmt=".2f", cmap="Blues", xticklabels=state_names,
            yticklabels=state_names, ax=axes[1], vmin=0, vmax=1)
axes[1].set_xlabel("转移到")
axes[1].set_ylabel("从")
axes[1].set_title("转移概率矩阵热力图")

plt.tight_layout()
plt.savefig("markov_chain_analysis.png", dpi=150)
print("\\n马尔可夫链分析图已保存: markov_chain_analysis.png")
''',
    ),
}


def get_templates() -> list[CodeTemplate]:
    """返回所有动态规划模板列表。"""
    return list(DP_TEMPLATES.values())
