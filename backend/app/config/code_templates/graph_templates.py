"""图论类代码模板"""
from app.config.code_templates.template_registry import CodeTemplate

GRAPH_TEMPLATES = {
    "tsp_solution": CodeTemplate(
        name="TSP 旅行商问题",
        category="图论",
        description="最近邻 + 2-opt 改进求解 TSP",
        applicable_models=["TSP", "旅行商", "路径优化", "tsp_vrp"],
        dependencies=["numpy", "matplotlib"],
        code='''import numpy as np
import matplotlib.pyplot as plt

# 距离矩阵 (n*n)
D = np.array([...])  # TODO: 替换
n = D.shape[0]

# 最近邻启发式
def nearest_neighbor(D, start=0):
    n = len(D)
    visited = [start]
    total = 0
    for _ in range(n - 1):
        cur = visited[-1]
        unvisited = [j for j in range(n) if j not in visited]
        nxt = min(unvisited, key=lambda j: D[cur, j])
        total += D[cur, nxt]
        visited.append(nxt)
    total += D[visited[-1], start]
    visited.append(start)
    return visited, total

# 2-opt 改进
def two_opt(route, D):
    n = len(route) - 1
    improved = True
    best = route[:]; best_d = sum(D[best[i], best[i+1]] for i in range(n))
    while improved:
        improved = False
        for i in range(1, n-1):
            for j in range(i+1, n):
                delta = D[best[i-1], best[j]] + D[best[i], best[j+1]] - D[best[i-1], best[i]] - D[best[j], best[j+1]]
                if delta < -1e-10:
                    best[i:j+1] = reversed(best[i:j+1])
                    best_d += delta; improved = True
    return best, best_d

# 多起点求解
best_route, best_dist = None, float("inf")
for s in range(n):
    route, dist = nearest_neighbor(D, s)
    route, dist = two_opt(route, D)
    if dist < best_dist:
        best_route, best_dist = route, dist

print(f"最优路线: {best_route}")
print(f"总距离: {best_dist:.4f}")
''',
    ),
    "shortest_path_tpl": CodeTemplate(
        name="最短路径求解",
        category="图论",
        description="Dijkstra / Floyd 最短路径算法",
        applicable_models=["最短路径", "Dijkstra", "Floyd", "shortest_path"],
        dependencies=["numpy", "scipy"],
        code='''import numpy as np
from scipy.sparse.csgraph import dijkstra, shortest_path
from scipy.sparse import csr_matrix

# 邻接矩阵 (0 或 inf 表示无边)
G = np.array([...])  # TODO: 替换
G[G == 0] = np.inf
np.fill_diagonal(G, 0)

# Dijkstra (单源)
source = 0  # TODO: 替换
distances, predecessors = dijkstra(csr_matrix(G), indices=source, return_predecessors=True)

# 输出结果
for target in range(len(G)):
    if target == source: continue
    path = []
    cur = target
    while cur != source and cur >= 0:
        path.append(cur)
        cur = predecessors[cur]
    path.append(source)
    path.reverse()
    print(f"{source} -> {target}: 距离={distances[target]:.2f}, 路径={path}")
''',
    ),
    "network_flow_tpl": CodeTemplate(
        name="网络流求解",
        category="图论",
        description="基于 networkx 的网络流求解，包含最大流 (Edmonds-Karp) 和最小费用最大流算法，"
        "输出流量分配、总流量和总费用。",
        applicable_models=["最大流", "最小费用流", "网络流", "max_flow", "min_cost_flow", "network_flow"],
        dependencies=["scipy", "numpy", "networkx"],
        code='''import numpy as np
import networkx as nx

# ========== 网络流求解 ==========

# ===== 1. 最大流问题 =====
print("=" * 55)
print("最大流问题求解")
print("=" * 55)

# 构建有向图 (节点编号从 0 开始)
G_maxflow = nx.DiGraph()

# 添加边及容量: (起点, 终点, 容量)
edges_with_capacity = [
    (0, 1, 10),
    (0, 2, 8),
    (1, 3, 5),
    (1, 4, 7),
    (2, 1, 3),
    (2, 4, 6),
    (3, 5, 10),
    (4, 3, 2),
    (4, 5, 9),
]  # TODO: 替换为实际边和容量

for u, v, cap in edges_with_capacity:
    G_maxflow.add_edge(u, v, capacity=cap)

source = 0   # TODO: 替换源点
sink = 5     # TODO: 替换汇点

# 使用 Edmonds-Karp 算法 (Ford-Fulkerson 的 BFS 实现) 求最大流
max_flow_value, flow_dict = nx.maximum_flow(G_maxflow, source, sink, flow_func=nx.algorithms.flow.edmonds_karp)

print(f"\\n源点: {source}, 汇点: {sink}")
print(f"最大流量: {max_flow_value}")
print(f"\\n各边流量分配:")
for u in flow_dict:
    for v, flow in flow_dict[u].items():
        if flow > 0:
            cap = G_maxflow[u][v]["capacity"]
            print(f"  {u} -> {v}: 流量={flow}/{cap}")

# ===== 2. 最小费用最大流问题 =====
print(f"\\n{'='*55}")
print("最小费用最大流问题求解")
print("=" * 55)

G_mincost = nx.DiGraph()

# 添加边: (起点, 终点, 容量, 单位费用)
edges_with_cost = [
    (0, 1, 10, 2),
    (0, 2, 8, 5),
    (1, 3, 5, 3),
    (1, 4, 7, 1),
    (2, 1, 3, 2),
    (2, 4, 6, 4),
    (3, 5, 10, 6),
    (4, 3, 2, 1),
    (4, 5, 9, 3),
]  # TODO: 替换为实际边、容量和单位费用

for u, v, cap, cost in edges_with_cost:
    G_mincost.add_edge(u, v, capacity=cap, weight=cost)

# 求最小费用最大流
mincost_flow_dict = nx.max_flow_min_cost(G_mincost, source, sink)
min_cost = nx.cost_of_flow(G_mincost, mincost_flow_dict)
mincost_flow_value = sum(mincost_flow_dict[source][v] for v in mincost_flow_dict[source])

print(f"\\n源点: {source}, 汇点: {sink}")
print(f"最大流量: {mincost_flow_value}")
print(f"最小总费用: {min_cost}")
print(f"\\n各边流量分配:")
for u in mincost_flow_dict:
    for v, flow in mincost_flow_dict[u].items():
        if flow > 0:
            cap = G_mincost[u][v]["capacity"]
            unit_cost = G_mincost[u][v]["weight"]
            print(f"  {u} -> {v}: 流量={flow}/{cap}, 单位费用={unit_cost}, 小计费用={flow * unit_cost}")

# ===== 3. 结果汇总 =====
print(f"\\n{'='*55}")
print("结果汇总")
print("=" * 55)
print(f"最大流: {max_flow_value}")
print(f"最小费用最大流: 流量={mincost_flow_value}, 费用={min_cost}")
''',
    ),
}
