import json
from dataclasses import dataclass

from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import MODELER_PROMPT, build_modeler_prompt
from app.schemas.A2A import (
    CoderFeedbackToModeler,
    CoordinatorToModeler,
    ModelerToCoder,
    ModelSolution,
)
from app.utils.json_parser import clean_json_string
from app.utils.log_util import logger


@dataclass(frozen=True)
class _FallbackModelSpec:
    """降级方案中单个题型的模型推荐规格。"""

    model_name: str
    model_category: str
    python_libraries: tuple[str, ...]
    evaluation_metrics: tuple[str, ...]
    baseline: str
    improved: str
    steps: tuple[str, ...]
    math_formulation: str
    visualization: str


# 根据 ques_type 关键词匹配的经典模型推荐映射表
_FALLBACK_MODEL_MAP: dict[str, _FallbackModelSpec] = {
    "预测": _FallbackModelSpec(
        model_name="ARIMA + 随机森林",
        model_category="prediction",
        python_libraries=("statsmodels", "sklearn", "pandas", "matplotlib"),
        evaluation_metrics=("MAE", "RMSE", "MAPE", "R2"),
        baseline="ARIMA 时间序列模型",
        improved="随机森林回归 + 特征工程",
        steps=(
            "对时间序列数据进行平稳性检验（ADF 检验），必要时差分处理",
            "使用 ACF/PACF 图确定 ARIMA(p,d,q) 阶数，拟合基线模型",
            "提取滞后特征、滑动窗口统计量，训练随机森林回归作为改进模型",
            "使用交叉验证对比两种模型的预测精度，选择最优模型",
            "绘制预测曲线与实际值对比图、残差分析图",
        ),
        math_formulation=(
            "ARIMA(p,d,q): (1-sum(phi_i*B^i))(1-B)^d * Y_t = "
            "(1+sum(theta_j*B^j)) * epsilon_t"
        ),
        visualization="时间序列趋势图、预测对比图、残差分布图、ACF/PACF 图",
    ),
    "forecast": _FallbackModelSpec(
        model_name="ARIMA + 随机森林",
        model_category="prediction",
        python_libraries=("statsmodels", "sklearn", "pandas", "matplotlib"),
        evaluation_metrics=("MAE", "RMSE", "MAPE", "R2"),
        baseline="ARIMA 时间序列模型",
        improved="随机森林回归 + 特征工程",
        steps=(
            "对时间序列数据进行平稳性检验（ADF 检验），必要时差分处理",
            "使用 ACF/PACF 图确定 ARIMA(p,d,q) 阶数，拟合基线模型",
            "提取滞后特征、滑动窗口统计量，训练随机森林回归作为改进模型",
            "使用交叉验证对比两种模型的预测精度，选择最优模型",
            "绘制预测曲线与实际值对比图、残差分析图",
        ),
        math_formulation=(
            "ARIMA(p,d,q): (1-sum(phi_i*B^i))(1-B)^d * Y_t = "
            "(1+sum(theta_j*B^j)) * epsilon_t"
        ),
        visualization="时间序列趋势图、预测对比图、残差分布图、ACF/PACF 图",
    ),
    "优化": _FallbackModelSpec(
        model_name="线性规划 + 遗传算法",
        model_category="optimization",
        python_libraries=("scipy", "deap", "pulp", "numpy", "matplotlib"),
        evaluation_metrics=("目标函数值", "约束满足率", "求解时间", "收敛曲线"),
        baseline="线性规划（scipy.optimize.linprog）",
        improved="遗传算法（DEAP 框架）全局优化",
        steps=(
            "明确决策变量、目标函数和约束条件，建立数学规划模型",
            "使用 scipy.optimize.linprog 或 pulp 求解线性规划基线",
            "若问题为非线性/组合优化，使用 DEAP 遗传算法求解",
            "对比基线与改进方案的目标函数值和求解效率",
            "绘制目标函数收敛曲线和可行域示意图",
        ),
        math_formulation=(
            "min f(x) s.t. A_eq @ x = b_eq, A_ub @ x <= b_ub, "
            "x_lb <= x <= x_ub"
        ),
        visualization="可行域示意图、收敛曲线、决策变量灵敏度热力图",
    ),
    "optimize": _FallbackModelSpec(
        model_name="线性规划 + 遗传算法",
        model_category="optimization",
        python_libraries=("scipy", "deap", "pulp", "numpy", "matplotlib"),
        evaluation_metrics=("目标函数值", "约束满足率", "求解时间", "收敛曲线"),
        baseline="线性规划（scipy.optimize.linprog）",
        improved="遗传算法（DEAP 框架）全局优化",
        steps=(
            "明确决策变量、目标函数和约束条件，建立数学规划模型",
            "使用 scipy.optimize.linprog 或 pulp 求解线性规划基线",
            "若问题为非线性/组合优化，使用 DEAP 遗传算法求解",
            "对比基线与改进方案的目标函数值和求解效率",
            "绘制目标函数收敛曲线和可行域示意图",
        ),
        math_formulation=(
            "min f(x) s.t. A_eq @ x = b_eq, A_ub @ x <= b_ub, "
            "x_lb <= x <= x_ub"
        ),
        visualization="可行域示意图、收敛曲线、决策变量灵敏度热力图",
    ),
    "分类": _FallbackModelSpec(
        model_name="逻辑回归 + 随机森林分类器",
        model_category="classification",
        python_libraries=("sklearn", "pandas", "numpy", "matplotlib", "seaborn"),
        evaluation_metrics=("Accuracy", "Precision", "Recall", "F1-Score", "AUC-ROC"),
        baseline="逻辑回归（sklearn.linear_model.LogisticRegression）",
        improved="随机森林分类器 + 特征选择",
        steps=(
            "数据预处理：缺失值填充、类别编码、标准化/归一化",
            "使用逻辑回归建立分类基线模型，计算基础评估指标",
            "使用随机森林分类器，结合特征重要性进行特征选择",
            "通过 5 折交叉验证对比模型性能，绘制 ROC 曲线",
            "输出混淆矩阵和分类报告，分析错分样本特征",
        ),
        math_formulation=(
            "Logistic: P(Y=1|X) = 1/(1+exp(-(w^T*X+b))), "
            "损失函数: -sum(y_i*log(p_i)+(1-y_i)*log(1-p_i))"
        ),
        visualization="ROC 曲线、混淆矩阵热力图、特征重要性柱状图",
    ),
    "classify": _FallbackModelSpec(
        model_name="逻辑回归 + 随机森林分类器",
        model_category="classification",
        python_libraries=("sklearn", "pandas", "numpy", "matplotlib", "seaborn"),
        evaluation_metrics=("Accuracy", "Precision", "Recall", "F1-Score", "AUC-ROC"),
        baseline="逻辑回归（sklearn.linear_model.LogisticRegression）",
        improved="随机森林分类器 + 特征选择",
        steps=(
            "数据预处理：缺失值填充、类别编码、标准化/归一化",
            "使用逻辑回归建立分类基线模型，计算基础评估指标",
            "使用随机森林分类器，结合特征重要性进行特征选择",
            "通过 5 折交叉验证对比模型性能，绘制 ROC 曲线",
            "输出混淆矩阵和分类报告，分析错分样本特征",
        ),
        math_formulation=(
            "Logistic: P(Y=1|X) = 1/(1+exp(-(w^T*X+b))), "
            "损失函数: -sum(y_i*log(p_i)+(1-y_i)*log(1-p_i))"
        ),
        visualization="ROC 曲线、混淆矩阵热力图、特征重要性柱状图",
    ),
    "聚类": _FallbackModelSpec(
        model_name="K-Means + 层次聚类",
        model_category="classification",
        python_libraries=("sklearn", "scipy", "pandas", "matplotlib", "seaborn"),
        evaluation_metrics=(
            "轮廓系数",
            "Calinski-Harabasz 指数",
            "Davies-Bouldin 指数",
            "SSE 肘部法则",
        ),
        baseline="K-Means 聚类",
        improved="层次聚类（Ward 方法）+ 轮廓系数优化",
        steps=(
            "数据标准化处理，消除量纲影响",
            "使用肘部法则和轮廓系数确定最佳聚类数 K",
            "运行 K-Means 聚类作为基线方案",
            "使用层次聚类（Ward 链接）对比分析，绘制树状图",
            "对聚类结果进行可视化（降维至 2D）和统计特征描述",
        ),
        math_formulation=(
            "K-Means: min sum_k sum_{x in C_k} ||x - mu_k||^2, "
            "轮廓系数: s(i) = (b(i)-a(i))/max(a(i),b(i))"
        ),
        visualization="聚类散点图（PCA 降维）、肘部法则图、树状图、轮廓系数图",
    ),
    "cluster": _FallbackModelSpec(
        model_name="K-Means + 层次聚类",
        model_category="classification",
        python_libraries=("sklearn", "scipy", "pandas", "matplotlib", "seaborn"),
        evaluation_metrics=(
            "轮廓系数",
            "Calinski-Harabasz 指数",
            "Davies-Bouldin 指数",
            "SSE 肘部法则",
        ),
        baseline="K-Means 聚类",
        improved="层次聚类（Ward 方法）+ 轮廓系数优化",
        steps=(
            "数据标准化处理，消除量纲影响",
            "使用肘部法则和轮廓系数确定最佳聚类数 K",
            "运行 K-Means 聚类作为基线方案",
            "使用层次聚类（Ward 链接）对比分析，绘制树状图",
            "对聚类结果进行可视化（降维至 2D）和统计特征描述",
        ),
        math_formulation=(
            "K-Means: min sum_k sum_{x in C_k} ||x - mu_k||^2, "
            "轮廓系数: s(i) = (b(i)-a(i))/max(a(i),b(i))"
        ),
        visualization="聚类散点图（PCA 降维）、肘部法则图、树状图、轮廓系数图",
    ),
    "回归": _FallbackModelSpec(
        model_name="多元线性回归 + Ridge 回归",
        model_category="fitting",
        python_libraries=("sklearn", "statsmodels", "pandas", "matplotlib"),
        evaluation_metrics=("R2", "Adjusted R2", "RMSE", "MAE", "AIC/BIC"),
        baseline="多元线性回归（OLS）",
        improved="Ridge 回归 + 交叉验证调参",
        steps=(
            "检查多重共线性（VIF 分析），必要时进行特征选择",
            "使用 statsmodels OLS 拟合多元线性回归，分析回归系数显著性",
            "使用 Ridge 回归引入 L2 正则化，通过交叉验证选择最优 alpha",
            "对比两种模型的拟合优度和泛化能力",
            "绘制残差分析图、预测-实际散点图、系数重要性图",
        ),
        math_formulation=(
            "OLS: min ||Y - X*beta||^2, "
            "Ridge: min ||Y - X*beta||^2 + alpha*||beta||^2"
        ),
        visualization="残差图、Q-Q 图、预测-实际散点图、回归系数柱状图",
    ),
    "regression": _FallbackModelSpec(
        model_name="多元线性回归 + Ridge 回归",
        model_category="fitting",
        python_libraries=("sklearn", "statsmodels", "pandas", "matplotlib"),
        evaluation_metrics=("R2", "Adjusted R2", "RMSE", "MAE", "AIC/BIC"),
        baseline="多元线性回归（OLS）",
        improved="Ridge 回归 + 交叉验证调参",
        steps=(
            "检查多重共线性（VIF 分析），必要时进行特征选择",
            "使用 statsmodels OLS 拟合多元线性回归，分析回归系数显著性",
            "使用 Ridge 回归引入 L2 正则化，通过交叉验证选择最优 alpha",
            "对比两种模型的拟合优度和泛化能力",
            "绘制残差分析图、预测-实际散点图、系数重要性图",
        ),
        math_formulation=(
            "OLS: min ||Y - X*beta||^2, "
            "Ridge: min ||Y - X*beta||^2 + alpha*||beta||^2"
        ),
        visualization="残差图、Q-Q 图、预测-实际散点图、回归系数柱状图",
    ),
    "评价": _FallbackModelSpec(
        model_name="TOPSIS + 熵权法",
        model_category="evaluation",
        python_libraries=("numpy", "pandas", "matplotlib", "seaborn"),
        evaluation_metrics=("综合评价得分", "指标权重分布", "排名一致性", "灵敏度"),
        baseline="TOPSIS 综合评价法",
        improved="熵权法客观赋权 + TOPSIS 排序",
        steps=(
            "构建评价指标体系，明确正向/负向指标，建立决策矩阵",
            "使用熵权法计算各指标的客观权重",
            "对决策矩阵进行标准化处理（极差法或向量法）",
            "使用 TOPSIS 方法计算各方案与正负理想解的贴近度，排序",
            "绘制权重分布图、雷达图和排名结果柱状图",
        ),
        math_formulation=(
            "TOPSIS 贴近度: C_i = D_i^- / (D_i^+ + D_i^-), "
            "熵权: w_j = (1-e_j) / sum(1-e_j)"
        ),
        visualization="雷达图、权重分布饼图、排名柱状图、热力图",
    ),
    "evaluate": _FallbackModelSpec(
        model_name="TOPSIS + 熵权法",
        model_category="evaluation",
        python_libraries=("numpy", "pandas", "matplotlib", "seaborn"),
        evaluation_metrics=("综合评价得分", "指标权重分布", "排名一致性", "灵敏度"),
        baseline="TOPSIS 综合评价法",
        improved="熵权法客观赋权 + TOPSIS 排序",
        steps=(
            "构建评价指标体系，明确正向/负向指标，建立决策矩阵",
            "使用熵权法计算各指标的客观权重",
            "对决策矩阵进行标准化处理（极差法或向量法）",
            "使用 TOPSIS 方法计算各方案与正负理想解的贴近度，排序",
            "绘制权重分布图、雷达图和排名结果柱状图",
        ),
        math_formulation=(
            "TOPSIS 贴近度: C_i = D_i^- / (D_i^+ + D_i^-), "
            "熵权: w_j = (1-e_j) / sum(1-e_j)"
        ),
        visualization="雷达图、权重分布饼图、排名柱状图、热力图",
    ),
    "关联": _FallbackModelSpec(
        model_name="灰色关联分析 + Pearson 相关",
        model_category="evaluation",
        python_libraries=("numpy", "scipy", "pandas", "matplotlib", "seaborn"),
        evaluation_metrics=("灰色关联度", "Pearson 相关系数", "p 值", "Spearman 系数"),
        baseline="Pearson 相关性分析",
        improved="灰色关联分析（GRA）",
        steps=(
            "数据预处理与无量纲化（均值化或初值化）",
            "计算 Pearson 和 Spearman 相关系数矩阵，检验显著性",
            "使用灰色关联分析计算各因素与参考序列的关联度",
            "综合两种方法的结论，识别关键影响因素",
            "绘制相关性热力图和灰色关联度排序图",
        ),
        math_formulation=(
            "灰色关联系数: xi_i(k) = (Delta_min + rho*Delta_max) / "
            "(Delta_i(k) + rho*Delta_max), rho=0.5"
        ),
        visualization="相关性热力图、灰色关联度柱状图、散点矩阵图",
    ),
    "correlation": _FallbackModelSpec(
        model_name="灰色关联分析 + Pearson 相关",
        model_category="evaluation",
        python_libraries=("numpy", "scipy", "pandas", "matplotlib", "seaborn"),
        evaluation_metrics=("灰色关联度", "Pearson 相关系数", "p 值", "Spearman 系数"),
        baseline="Pearson 相关性分析",
        improved="灰色关联分析（GRA）",
        steps=(
            "数据预处理与无量纲化（均值化或初值化）",
            "计算 Pearson 和 Spearman 相关系数矩阵，检验显著性",
            "使用灰色关联分析计算各因素与参考序列的关联度",
            "综合两种方法的结论，识别关键影响因素",
            "绘制相关性热力图和灰色关联度排序图",
        ),
        math_formulation=(
            "灰色关联系数: xi_i(k) = (Delta_min + rho*Delta_max) / "
            "(Delta_i(k) + rho*Delta_max), rho=0.5"
        ),
        visualization="相关性热力图、灰色关联度柱状图、散点矩阵图",
    ),
    "规划": _FallbackModelSpec(
        model_name="整数规划",
        model_category="optimization",
        python_libraries=("scipy", "pulp", "numpy", "matplotlib"),
        evaluation_metrics=("目标函数最优值", "约束满足率", "求解时间", "间隙率"),
        baseline="PuLP 混合整数线性规划",
        improved="分支定界法 + 松弛求解对比",
        steps=(
            "将问题抽象为整数规划模型：定义决策变量（整数/0-1）",
            "明确目标函数（最大化/最小化）和所有约束条件",
            "使用 PuLP 或 scipy.optimize.milp 建模求解",
            "分析松弛解与整数解的差距（间隙率）",
            "绘制可行解分布图和目标函数灵敏度分析图",
        ),
        math_formulation=(
            "min c^T*x s.t. A*x <= b, x_i in Z (整数), "
            "或 x_i in {0,1} (0-1 规划)"
        ),
        visualization="可行域图、目标函数等高线图、灵敏度分析柱状图",
    ),
    "planning": _FallbackModelSpec(
        model_name="整数规划",
        model_category="optimization",
        python_libraries=("scipy", "pulp", "numpy", "matplotlib"),
        evaluation_metrics=("目标函数最优值", "约束满足率", "求解时间", "间隙率"),
        baseline="PuLP 混合整数线性规划",
        improved="分支定界法 + 松弛求解对比",
        steps=(
            "将问题抽象为整数规划模型：定义决策变量（整数/0-1）",
            "明确目标函数（最大化/最小化）和所有约束条件",
            "使用 PuLP 或 scipy.optimize.milp 建模求解",
            "分析松弛解与整数解的差距（间隙率）",
            "绘制可行解分布图和目标函数灵敏度分析图",
        ),
        math_formulation=(
            "min c^T*x s.t. A*x <= b, x_i in Z (整数), "
            "或 x_i in {0,1} (0-1 规划)"
        ),
        visualization="可行域图、目标函数等高线图、灵敏度分析柱状图",
    ),
    "模拟": _FallbackModelSpec(
        model_name="蒙特卡洛模拟",
        model_category="probability",
        python_libraries=("numpy", "scipy", "pandas", "matplotlib"),
        evaluation_metrics=("置信区间", "收敛性", "期望值", "标准差", "分位数"),
        baseline="基础蒙特卡洛随机模拟",
        improved="拉丁超立方抽样 + 方差缩减技术",
        steps=(
            "明确不确定性变量及其概率分布（正态、均匀、泊松等）",
            "设计模拟实验方案，确定模拟次数（建议 >= 10000 次）",
            "运行蒙特卡洛模拟，记录每次模拟的结果",
            "统计分析模拟结果：均值、标准差、置信区间、分位数",
            "绘制结果分布直方图、累积分布曲线和收敛性分析图",
        ),
        math_formulation=(
            "E[f(X)] ≈ (1/N) * sum_{i=1}^{N} f(X_i), "
            "95% CI: mean +/- 1.96*std/sqrt(N)"
        ),
        visualization="结果分布直方图、累积分布函数图、收敛性曲线图",
    ),
    "simulate": _FallbackModelSpec(
        model_name="蒙特卡洛模拟",
        model_category="probability",
        python_libraries=("numpy", "scipy", "pandas", "matplotlib"),
        evaluation_metrics=("置信区间", "收敛性", "期望值", "标准差", "分位数"),
        baseline="基础蒙特卡洛随机模拟",
        improved="拉丁超立方抽样 + 方差缩减技术",
        steps=(
            "明确不确定性变量及其概率分布（正态、均匀、泊松等）",
            "设计模拟实验方案，确定模拟次数（建议 >= 10000 次）",
            "运行蒙特卡洛模拟，记录每次模拟的结果",
            "统计分析模拟结果：均值、标准差、置信区间、分位数",
            "绘制结果分布直方图、累积分布曲线和收敛性分析图",
        ),
        math_formulation=(
            "E[f(X)] ≈ (1/N) * sum_{i=1}^{N} f(X_i), "
            "95% CI: mean +/- 1.96*std/sqrt(N)"
        ),
        visualization="结果分布直方图、累积分布函数图、收敛性曲线图",
    ),
    "图论": _FallbackModelSpec(
        model_name="最短路径 + 网络流",
        model_category="graph",
        python_libraries=("networkx", "numpy", "matplotlib"),
        evaluation_metrics=("最短路径长度", "最大流值", "连通性", "度分布"),
        baseline="Dijkstra 最短路径算法",
        improved="网络流 + 图论综合分析",
        steps=(
            "根据问题构建图/网络模型，定义节点、边和权重",
            "使用 NetworkX 构建图对象，计算基本图特征",
            "根据问题类型选择算法：Dijkstra/Floyd/最大流/最小生成树",
            "分析关键节点（介数中心性）和关键路径",
            "可视化网络拓扑结构和求解结果",
        ),
        math_formulation=(
            "最短路径: d(s,t) = min sum_{(i,j) in P} w_{ij}, "
            "最大流: max f s.t. 流量守恒和容量约束"
        ),
        visualization="网络拓扑图、最短路径高亮图、流量分配图",
    ),
    "graph": _FallbackModelSpec(
        model_name="最短路径 + 网络流",
        model_category="graph",
        python_libraries=("networkx", "numpy", "matplotlib"),
        evaluation_metrics=("最短路径长度", "最大流值", "连通性", "度分布"),
        baseline="Dijkstra 最短路径算法",
        improved="网络流 + 图论综合分析",
        steps=(
            "根据问题构建图/网络模型，定义节点、边和权重",
            "使用 NetworkX 构建图对象，计算基本图特征",
            "根据问题类型选择算法：Dijkstra/Floyd/最大流/最小生成树",
            "分析关键节点（介数中心性）和关键路径",
            "可视化网络拓扑结构和求解结果",
        ),
        math_formulation=(
            "最短路径: d(s,t) = min sum_{(i,j) in P} w_{ij}, "
            "最大流: max f s.t. 流量守恒和容量约束"
        ),
        visualization="网络拓扑图、最短路径高亮图、流量分配图",
    ),
    "微分方程": _FallbackModelSpec(
        model_name="常微分方程数值求解",
        model_category="ode",
        python_libraries=("scipy", "numpy", "matplotlib", "sympy"),
        evaluation_metrics=("数值精度", "稳定性", "步长收敛性", "误差范数"),
        baseline="scipy.integrate.odeint (LSODA)",
        improved="RK45 + 自适应步长控制",
        steps=(
            "建立微分方程模型，明确状态变量和初始/边界条件",
            "使用 scipy.integrate.solve_ivp 进行数值求解（RK45 方法）",
            "验证数值解的精度：对比不同步长的求解结果",
            "进行参数灵敏度分析，观察关键参数变化对解的影响",
            "绘制状态变量随时间变化曲线和相空间图",
        ),
        math_formulation=(
            "dy/dt = f(t, y), y(t_0) = y_0, "
            "RK4: y_{n+1} = y_n + (h/6)(k1+2k2+2k3+k4)"
        ),
        visualization="时间演化曲线、相平面图、参数灵敏度图",
    ),
    "ode": _FallbackModelSpec(
        model_name="常微分方程数值求解",
        model_category="ode",
        python_libraries=("scipy", "numpy", "matplotlib", "sympy"),
        evaluation_metrics=("数值精度", "稳定性", "步长收敛性", "误差范数"),
        baseline="scipy.integrate.odeint (LSODA)",
        improved="RK45 + 自适应步长控制",
        steps=(
            "建立微分方程模型，明确状态变量和初始/边界条件",
            "使用 scipy.integrate.solve_ivp 进行数值求解（RK45 方法）",
            "验证数值解的精度：对比不同步长的求解结果",
            "进行参数灵敏度分析，观察关键参数变化对解的影响",
            "绘制状态变量随时间变化曲线和相空间图",
        ),
        math_formulation=(
            "dy/dt = f(t, y), y(t_0) = y_0, "
            "RK4: y_{n+1} = y_n + (h/6)(k1+2k2+2k3+k4)"
        ),
        visualization="时间演化曲线、相平面图、参数灵敏度图",
    ),
    "概率": _FallbackModelSpec(
        model_name="概率统计分析",
        model_category="probability",
        python_libraries=("scipy", "numpy", "pandas", "matplotlib"),
        evaluation_metrics=("置信区间", "假设检验 p 值", "效应量", "统计功效"),
        baseline="描述性统计 + 假设检验",
        improved="贝叶斯推断 + Bootstrap 重采样",
        steps=(
            "计算描述性统计量：均值、方差、偏度、峰度",
            "进行分布拟合检验（K-S 检验、Shapiro-Wilk 检验）",
            "根据问题选择合适的假设检验（t 检验、卡方检验、ANOVA）",
            "计算置信区间和效应量，评估统计显著性",
            "绘制分布拟合图、箱线图和假设检验可视化",
        ),
        math_formulation=(
            "假设检验: H0 vs H1, t = (X_bar - mu_0)/(s/sqrt(n)), "
            "置信区间: X_bar +/- t_{alpha/2} * s/sqrt(n)"
        ),
        visualization="概率分布拟合图、箱线图、QQ 图、假设检验图",
    ),
    "博弈": _FallbackModelSpec(
        model_name="博弈论分析",
        model_category="game",
        python_libraries=("numpy", "scipy", "nashpy", "matplotlib"),
        evaluation_metrics=("纳什均衡", "帕累托效率", "支付矩阵", "策略稳定性"),
        baseline="支付矩阵 + 纳什均衡求解",
        improved="演化博弈 + 复制动态方程",
        steps=(
            "识别博弈参与者、策略集合和支付函数",
            "构建支付矩阵，分析占优策略",
            "求解纳什均衡（纯策略和混合策略）",
            "分析均衡的稳定性和帕累托最优性",
            "绘制博弈树/支付矩阵热力图/演化动态相图",
        ),
        math_formulation=(
            "纳什均衡: 对所有 i, u_i(s_i*, s_{-i}*) >= u_i(s_i, s_{-i}*), "
            "混合策略: max_p p^T*A*q"
        ),
        visualization="支付矩阵热力图、博弈树、演化动态相图",
    ),
}

# 默认降级模型（当 ques_type 无法匹配任何关键词时使用）
_FALLBACK_DEFAULT_SPEC = _FallbackModelSpec(
    model_name="多元线性回归 + 可视化分析",
    model_category="fitting",
    python_libraries=("sklearn", "pandas", "numpy", "matplotlib", "seaborn"),
    evaluation_metrics=("R2", "RMSE", "MAE", "可视化对比"),
    baseline="多元线性回归 + 描述性统计",
    improved="正则化回归 + 综合可视化分析",
    steps=(
        "对数据进行描述性统计和缺失值分析",
        "计算变量间的相关系数矩阵，识别关键特征",
        "使用多元线性回归建立基线模型，评估拟合效果",
        "根据数据特征选择改进方法（正则化/非线性变换/交叉验证）",
        "生成全面的可视化结果：散点图、热力图、回归拟合图",
    ),
    math_formulation=(
        "Y = X*beta + epsilon, min ||Y - X*beta||^2, "
        "R2 = 1 - SS_res/SS_tot"
    ),
    visualization="散点矩阵图、相关性热力图、回归拟合图、残差图",
)


class ModelerAgent(Agent):
    """数学建模方案设计Agent，负责为每个问题生成结构化建模方案。"""

    MAX_RETRIES = 3  # 最大重试次数

    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = MODELER_PROMPT

    async def run(
        self, coordinator_to_modeler: CoordinatorToModeler, **kwargs
    ) -> ModelerToCoder:
        """运行建模Agent，生成结构化建模方案。

        Args:
            coordinator_to_modeler: Coordinator 传递的结构化问题
            **kwargs: 额外参数
                - data_context: str, 数据文件描述和EDA摘要（可选）

        Returns:
            ModelerToCoder: 结构化建模方案
        """
        # 提取问题类型和关键词用于知识库匹配
        problem_type, keywords = self._extract_problem_info(
            coordinator_to_modeler
        )

        # 构建增强 prompt（注入知识库推荐）
        enhanced_prompt = self._build_prompt(problem_type, keywords)

        # 构建用户消息
        user_content = self._build_user_message(
            coordinator_to_modeler, **kwargs
        )

        # 带重试的 LLM 调用
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # 每次重试清空历史，确保干净的上下文
                self.chat_history.clear()

                await self.append_chat_history(
                    {"role": "system", "content": enhanced_prompt}
                )
                await self.append_chat_history(
                    {"role": "user", "content": user_content}
                )

                response = await self.model.chat(
                    history=self.chat_history,
                    agent_name=self.__class__.__name__,
                )

                raw_content = response.choices[0].message.content
                result = self._parse_and_validate(
                    raw_content, coordinator_to_modeler.ques_count
                )
                logger.info("ModelerAgent 第 %s 次尝试成功", attempt)
                return result

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(
                    "ModelerAgent 第 %s/%s 次尝试失败: %s",
                    attempt,
                    self.MAX_RETRIES,
                    e,
                )
                if attempt >= self.MAX_RETRIES:
                    logger.error(
                        "ModelerAgent 超过最大重试次数，使用降级方案"
                    )
                    return self._fallback_response(coordinator_to_modeler)

                # 将错误信息注入下一次请求
                user_content = self._build_retry_message(
                    coordinator_to_modeler, str(e), **kwargs
                )

        # 不应到达此处
        raise RuntimeError("ModelerAgent 意外的流程终止")

    # ==================== 辅助方法 ====================

    def _extract_problem_info(
        self, coordinator_to_modeler: CoordinatorToModeler
    ) -> tuple[str, list[str]]:
        """从 Coordinator 响应中提取问题类型和关键词。"""
        problem_type = ""
        keywords: list[str] = []
        if (
            hasattr(coordinator_to_modeler, "questions")
            and coordinator_to_modeler.questions
        ):
            questions = coordinator_to_modeler.questions
            if isinstance(questions, dict):
                title = questions.get("title", "")
                background = questions.get("background", "")
                problem_type = f"{title} {background}"[:200]
                # 提取类型标签作为关键词（中文友好）
                for key, value in questions.items():
                    if key.endswith("_type") and isinstance(value, str):
                        keywords.append(value)
                    elif (
                        key.startswith("ques")
                        and key != "ques_count"
                        and not key.endswith("_type")
                        and isinstance(value, str)
                    ):
                        # 截取问题描述前20字符作为关键词
                        keywords.append(value[:20])
        # 从竞赛战略中提取创新方向关键词
        if coordinator_to_modeler.strategy:
            keywords.extend(
                coordinator_to_modeler.strategy.innovation_opportunities[:3]
            )
        return problem_type, keywords[:20]

    def _build_prompt(
        self, problem_type: str, keywords: list[str]
    ) -> str:
        """构建增强版建模提示词。"""
        try:
            return build_modeler_prompt(
                problem_type=problem_type,
                keywords=keywords if keywords else None,
            )
        except Exception as e:
            logger.warning(
                "build_modeler_prompt 失败，使用默认 v2.0 prompt: %s", e
            )
            return self.system_prompt

    def _build_user_message(
        self, coordinator_to_modeler: CoordinatorToModeler, **kwargs
    ) -> str:
        """构建发送给 LLM 的用户消息。"""
        parts = [
            json.dumps(
                coordinator_to_modeler.questions, ensure_ascii=False
            )
        ]

        # === 注入 Coordinator 战略分析字段 ===
        strategy_parts: list[str] = []

        if coordinator_to_modeler.sub_difficulty:
            difficulty_str = ", ".join(
                f"{k}: {v}"
                for k, v in coordinator_to_modeler.sub_difficulty.items()
            )
            strategy_parts.append(f"各子问题难度: {difficulty_str}")

        if coordinator_to_modeler.problem_relations:
            relations = []
            for r in coordinator_to_modeler.problem_relations:
                relations.append(
                    f"{r.from_ques}→{r.to_ques}({r.relation}: {r.description})"
                )
            strategy_parts.append(
                f"子问题关联: {'; '.join(relations)}"
            )

        if coordinator_to_modeler.strategy:
            s = coordinator_to_modeler.strategy
            if s.priority_order:
                strategy_parts.append(
                    f"解题优先级: {' > '.join(s.priority_order)}"
                )
            if s.scoring_focus:
                strategy_parts.append(f"得分重点: {s.scoring_focus}")
            if s.innovation_opportunities:
                strategy_parts.append(
                    f"创新方向: {', '.join(s.innovation_opportunities)}"
                )
            if s.risk_assessment:
                risks = [
                    f"{r.question}({r.risk}风险: {r.reason})"
                    for r in s.risk_assessment
                ]
                strategy_parts.append(f"风险评估: {'; '.join(risks)}")

        if strategy_parts:
            parts.append(
                "\n\n## 竞赛战略分析\n" + "\n".join(f"- {p}" for p in strategy_parts)
            )

        # 注入数据上下文（阶段2会使用）
        data_context = kwargs.get("data_context")
        if data_context:
            parts.append(f"\n\n## 数据上下文\n{data_context}")

        return "\n".join(parts)

    def _build_retry_message(
        self,
        coordinator_to_modeler: CoordinatorToModeler,
        error: str,
        **kwargs,
    ) -> str:
        """构建重试时的用户消息，包含错误反馈。"""
        base_msg = self._build_user_message(
            coordinator_to_modeler, **kwargs
        )
        return (
            f"{base_msg}\n\n"
            f"上次输出格式错误: {error}\n"
            f"请严格按照要求输出合法的单层 JSON 结构，"
            f"确保包含 eda, ques1~ques{coordinator_to_modeler.ques_count}"
            f", sensitivity_analysis 等必要键。"
        )

    def _parse_and_validate(
        self, raw_content: str, ques_count: int
    ) -> ModelerToCoder:
        """解析和验证 LLM 输出的 JSON。

        Args:
            raw_content: LLM 返回的原始文本
            ques_count: 问题数量，用于验证必要键

        Returns:
            ModelerToCoder: 解析后的结构化建模方案

        Raises:
            ValueError: 内容为空或类型不符
            json.JSONDecodeError: JSON 格式错误
            KeyError: 缺少必要的键
        """
        if not raw_content:
            raise ValueError("LLM 返回内容为空")

        # 清理 markdown 标记和不可见控制字符
        json_str = clean_json_string(raw_content)

        # 解析 JSON
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            raise ValueError(
                f"期望 dict 类型，实际为 {type(parsed).__name__}"
            )

        # 验证必要的键
        required_keys = {"eda", "sensitivity_analysis"}
        for i in range(1, ques_count + 1):
            required_keys.add(f"ques{i}")

        missing_keys = required_keys - set(parsed.keys())
        if missing_keys:
            raise KeyError(f"缺少必要的键: {missing_keys}")

        # 提取假设列表（v2.0 新增字段）
        assumptions = parsed.pop("assumptions", [])
        if isinstance(assumptions, str):
            assumptions = [assumptions]

        # 将每个方案文本转换为 ModelSolution
        questions_solution: dict[str, str | ModelSolution] = {}
        for key, value in parsed.items():
            if isinstance(value, str):
                questions_solution[key] = ModelSolution.from_text(value)
            else:
                # LLM 返回了嵌套 dict 而非字符串
                # 优先尝试 JSON 序列化后使用 from_text 解析
                try:
                    text_value = json.dumps(value, ensure_ascii=False)
                    questions_solution[key] = ModelSolution.from_text(text_value)
                except Exception as e:
                    logger.warning(
                        "解析嵌套 ModelSolution 失败，降级为字符串: key=%s, error=%s",
                        key,
                        e,
                    )
                    questions_solution[key] = str(value)

        return ModelerToCoder(
            questions_solution=questions_solution,
            assumptions=assumptions,
        )

    async def revise(
        self,
        original_response: ModelerToCoder,
        feedback: CoderFeedbackToModeler,
        coordinator_to_modeler: CoordinatorToModeler,
        **kwargs,
    ) -> ModelerToCoder:
        """根据 Coder 反馈修订指定子问题的建模方案。

        Args:
            original_response: 原始建模方案
            feedback: Coder 的反馈信息
            coordinator_to_modeler: 原始问题上下文
            **kwargs: 额外参数（如 data_context）

        Returns:
            ModelerToCoder: 修订后的完整建模方案
        """
        revision_prompt = self._build_revision_prompt(
            original_response, feedback, coordinator_to_modeler
        )

        self.chat_history.clear()
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history(
            {"role": "user", "content": revision_prompt}
        )

        try:
            response = await self.model.chat(
                history=self.chat_history,
                agent_name=self.__class__.__name__,
            )
            raw_content = response.choices[0].message.content
            revised = self._parse_and_validate(
                raw_content, coordinator_to_modeler.ques_count
            )
            logger.info(
                "ModelerAgent 修订成功: 子任务 %s", feedback.subtask_key
            )
            return revised
        except Exception as e:
            logger.warning(
                "ModelerAgent 修订失败，保留原始方案: %s", e
            )
            return original_response

    def _build_revision_prompt(
        self,
        original_response: ModelerToCoder,
        feedback: CoderFeedbackToModeler,
        coordinator_to_modeler: CoordinatorToModeler,
    ) -> str:
        """构建修订请求的 prompt。"""
        original_solution = original_response.get_solution_text(
            feedback.subtask_key
        )
        questions_json = json.dumps(
            coordinator_to_modeler.questions, ensure_ascii=False
        )

        return (
            f"## 原始问题\n{questions_json}\n\n"
            f"## 失败的子任务: {feedback.subtask_key}\n"
            f"### 原始方案\n{original_solution}\n\n"
            f"### 执行错误摘要\n{feedback.error_summary}\n\n"
            f"### 失败的方法\n{feedback.failed_approach}\n\n"
            f"### Coder 建议的替代方向\n{feedback.alternative_suggestion}\n\n"
            f"## 修订要求\n"
            f"请针对子任务 {feedback.subtask_key} 提供修订后的建模方案。\n"
            f"要求：\n"
            f"1. 避免使用已失败的方法: {feedback.failed_approach}\n"
            f"2. 选择更鲁棒、更简单的替代模型\n"
            f"3. 保持其他子任务的方案不变\n"
            f"4. 输出完整的 JSON（包含所有子任务的方案）\n\n"
            f"请严格按照要求输出合法的单层 JSON 结构，"
            f"确保包含 eda, ques1~ques{coordinator_to_modeler.ques_count}"
            f", sensitivity_analysis 等必要键。"
        )

    # ==================== 降级方案 ====================

    @staticmethod
    def _match_fallback_spec(ques_type: str) -> _FallbackModelSpec:
        """根据 ques_type 文本匹配最合适的降级模型规格。

        遍历 _FALLBACK_MODEL_MAP 的所有键，检查 ques_type 中是否包含
        该关键词（大小写不敏感）。首次命中即返回；全部未命中则返回默认规格。

        Args:
            ques_type: Coordinator 提取的问题类型字符串。

        Returns:
            匹配到的 _FallbackModelSpec 实例。
        """
        ques_type_lower = ques_type.lower()
        for keyword, spec in _FALLBACK_MODEL_MAP.items():
            if keyword in ques_type_lower:
                return spec
        return _FALLBACK_DEFAULT_SPEC

    @staticmethod
    def _build_fallback_solution_text(
        ques_text: str,
        ques_type: str,
        spec: _FallbackModelSpec,
    ) -> str:
        """根据降级模型规格生成完整的建模方案文本。

        生成的文本包含：推荐模型、建议求解步骤、评估指标、数学公式和
        可视化规划，格式与正常 Modeler 输出保持一致。

        Args:
            ques_text: 问题原文描述。
            ques_type: 问题类型标签。
            spec: 匹配到的降级模型规格。

        Returns:
            格式化的建模方案文本。
        """
        steps_text = "\n".join(
            f"  {idx}. {step}" for idx, step in enumerate(spec.steps, 1)
        )
        metrics_text = "、".join(spec.evaluation_metrics)
        libs_text = "、".join(spec.python_libraries)

        return (
            f"## 问题描述\n{ques_text}\n\n"
            f"## 问题类型\n{ques_type}\n\n"
            f"## 推荐模型\n{spec.model_name}（{spec.model_category}）\n\n"
            f"## 基线方案\n{spec.baseline}\n\n"
            f"## 改进方案\n{spec.improved}\n\n"
            f"## 数学形式化\n{spec.math_formulation}\n\n"
            f"## 建议求解步骤\n{steps_text}\n\n"
            f"## 评估指标\n{metrics_text}\n\n"
            f"## 所需 Python 库\n{libs_text}\n\n"
            f"## 可视化规划\n{spec.visualization}\n\n"
            f"[MODEL_CONFIG]\n"
            f"model_name: {spec.model_name}\n"
            f"model_category: {spec.model_category}\n"
            f"approach_baseline: {spec.baseline}\n"
            f"approach_improved: {spec.improved}\n"
            f"mathematical_formulation: {spec.math_formulation}\n"
            f"evaluation_metrics: {', '.join(spec.evaluation_metrics)}\n"
            f"python_libraries: {', '.join(spec.python_libraries)}\n"
            f"visualization_plan: {spec.visualization}\n"
            f"[/MODEL_CONFIG]"
        )

    def _build_fallback_model_solution(
        self,
        ques_text: str,
        ques_type: str,
    ) -> ModelSolution:
        """为单个子问题构建降级 ModelSolution 结构化对象。

        结合映射表推荐的模型信息，生成与正常 Modeler 输出格式一致的
        ModelSolution 实例，确保下游 Coder 能无差别地处理。

        Args:
            ques_text: 问题原文描述。
            ques_type: 问题类型标签。

        Returns:
            填充完整的 ModelSolution 实例。
        """
        spec = self._match_fallback_spec(ques_type)
        solution_text = self._build_fallback_solution_text(
            ques_text, ques_type, spec
        )

        logger.info(
            "降级方案为问题类型 '%s' 匹配到模型: %s",
            ques_type,
            spec.model_name,
        )

        return ModelSolution(
            model_name=spec.model_name,
            model_category=spec.model_category,
            approach_baseline=spec.baseline,
            approach_improved=spec.improved,
            approach_innovative="",
            mathematical_formulation=spec.math_formulation,
            evaluation_metrics=list(spec.evaluation_metrics),
            python_libraries=list(spec.python_libraries),
            data_requirements="请根据数据文件自动识别所需的数据格式和字段",
            visualization_plan=spec.visualization,
            solution_text=solution_text,
        )

    def _fallback_response(
        self, coordinator_to_modeler: CoordinatorToModeler
    ) -> ModelerToCoder:
        """当所有重试都失败时，生成结构化的降级建模方案。

        根据每个子问题的 ques_type 从 _FALLBACK_MODEL_MAP 中匹配推荐模型，
        生成包含具体建模步骤、评估指标和 Python 库的 ModelSolution 对象，
        确保 Coder 能获得有效的建模指导。
        """
        logger.warning("使用降级方案生成建模响应")
        ques_count = coordinator_to_modeler.ques_count
        questions = coordinator_to_modeler.questions

        # EDA 也生成结构化对象
        eda_solution = ModelSolution(
            model_name="探索性数据分析",
            model_category="evaluation",
            approach_baseline="描述性统计 + 缺失值分析",
            approach_improved="相关性分析 + 分布检验 + 数据可视化",
            mathematical_formulation="统计量: mean, std, median, skew, kurtosis",
            evaluation_metrics=["完整性", "分布类型", "异常值比例", "相关系数"],
            python_libraries=["pandas", "numpy", "matplotlib", "seaborn"],
            data_requirements="读取全部数据文件，自动识别数据类型",
            visualization_plan="缺失值热力图、分布直方图、相关性热力图、箱线图",
            solution_text=(
                "对数据进行全面的探索性分析：\n"
                "1. 加载所有数据文件，检查数据维度和类型\n"
                "2. 计算描述性统计量（均值、标准差、中位数、偏度、峰度）\n"
                "3. 分析缺失值分布，选择合适的填充策略\n"
                "4. 计算变量间的相关系数矩阵（Pearson/Spearman）\n"
                "5. 绘制数据分布、箱线图和相关性热力图\n"
                "6. 检测异常值（IQR 方法或 Z-score 方法）"
            ),
        )

        solution: dict[str, str | ModelSolution] = {"eda": eda_solution}

        for i in range(1, ques_count + 1):
            ques_text = questions.get(f"ques{i}", f"问题{i}")
            ques_type = questions.get(f"ques{i}_type", "其他")
            solution[f"ques{i}"] = self._build_fallback_model_solution(
                ques_text, ques_type
            )

        # 敏感性分析也生成结构化对象
        solution["sensitivity_analysis"] = ModelSolution(
            model_name="参数敏感性分析",
            model_category="evaluation",
            approach_baseline="单因素敏感性分析",
            approach_improved="Morris 方法 + Sobol 全局敏感性分析",
            mathematical_formulation=(
                "单因素: delta_Y/delta_X_i, "
                "Sobol 一阶指数: S_i = V(E[Y|X_i]) / V(Y)"
            ),
            evaluation_metrics=[
                "敏感性指数",
                "参数变化率",
                "结果波动范围",
                "一阶/总阶 Sobol 指数",
            ],
            python_libraries=["numpy", "matplotlib", "SALib"],
            visualization_plan="龙卷风图、参数-结果响应曲线、Sobol 指数柱状图",
            solution_text=(
                "对关键参数进行敏感性分析：\n"
                "1. 识别模型中的关键参数及其合理变化范围\n"
                "2. 使用单因素分析法逐一改变参数，观察输出变化\n"
                "3. 计算各参数的敏感性指数，排序影响程度\n"
                "4. 绘制龙卷风图展示各参数的影响大小\n"
                "5. 给出参数选择的鲁棒性结论和建议"
            ),
        )

        # 生成通用的模型假设列表
        assumptions = [
            "假设数据文件中的数据是准确可靠的",
            "假设数据样本具有代表性，能反映总体特征",
            "假设各变量之间的关系在观测期内保持稳定",
        ]

        return ModelerToCoder(
            questions_solution=solution,
            assumptions=assumptions,
        )
