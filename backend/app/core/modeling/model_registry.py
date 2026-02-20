"""
Model Registry - 模型注册中心
==============================

功能：
1. 扩展现有 knowledge_base.py
2. 模型版本管理
3. 模型性能历史记录
4. 模型适用场景索引
5. 智能模型匹配

关键特性：
- 扩展而非替换现有知识库
- 支持性能追踪
- 新增图论、博弈论等模型
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.knowledge_base import (
    MathModelingKnowledgeBase,
    ModelKnowledge,
    knowledge_base as default_knowledge_base,
)
from app.schemas.contracts import ModelRecommendation
from app.utils.log_util import logger


@dataclass
class ModelVersion:
    """模型版本"""

    version: str
    created_at: str
    parameters: Dict[str, Any]
    performance_history: List[Dict[str, Any]]
    notes: str


@dataclass
class PerformanceRecord:
    """性能记录"""

    record_id: str
    problem_id: str
    metrics: Dict[str, float]
    recorded_at: str
    notes: str = ""


@dataclass
class ExtendedModelKnowledge:
    """扩展模型知识 - 在 ModelKnowledge 基础上增加更多信息"""

    # 基础信息（来自 ModelKnowledge）
    model_id: str
    name: str
    category: str
    description: str
    applicable_problems: List[str]
    advantages: List[str]
    disadvantages: List[str]
    complexity: str  # 低/中/高
    implementation_difficulty: str
    data_requirements: Dict[str, str]
    key_parameters: List[str]
    validation_methods: List[str]
    common_pitfalls: List[str]

    # 扩展信息
    versions: List[ModelVersion] = field(default_factory=list)
    performance_benchmarks: Dict[str, float] = field(default_factory=dict)
    applicable_data_types: List[str] = field(default_factory=list)
    required_packages: List[str] = field(default_factory=list)
    example_code: str = ""
    tags: List[str] = field(default_factory=list)
    related_models: List[str] = field(default_factory=list)

    @classmethod
    def from_model_knowledge(
        cls, model_id: str, mk: ModelKnowledge
    ) -> "ExtendedModelKnowledge":
        """从 ModelKnowledge 创建"""
        return cls(
            model_id=model_id,
            name=mk.name,
            category=mk.category,
            description=mk.description,
            applicable_problems=mk.applicable_problems,
            advantages=mk.advantages,
            disadvantages=mk.disadvantages,
            complexity=mk.complexity,
            implementation_difficulty=mk.implementation_difficulty,
            data_requirements=mk.data_requirements,
            key_parameters=mk.key_parameters,
            validation_methods=mk.validation_methods,
            common_pitfalls=mk.common_pitfalls,
        )


# 新增模型定义（按路线图要求）
NEW_MODELS: Dict[str, ExtendedModelKnowledge] = {
    # ==================== 图论模型 ====================
    "shortest_path": ExtendedModelKnowledge(
        model_id="shortest_path",
        name="最短路径算法",
        category="图论",
        description="在加权图中寻找两节点间最短路径的算法，包括Dijkstra、Floyd-Warshall、Bellman-Ford等",
        applicable_problems=["路径规划", "物流配送", "网络路由", "导航系统"],
        advantages=["理论成熟", "算法多样", "可处理大规模网络"],
        disadvantages=["需要完整图结构", "负权边需特殊处理"],
        complexity="中",
        implementation_difficulty="低",
        data_requirements={"graph_type": "有向/无向图", "edge_weights": "边权重"},
        key_parameters=["起点", "终点", "边权重"],
        validation_methods=["路径验证", "最优性检验"],
        common_pitfalls=["负权环", "图不连通", "权重选择不当"],
        required_packages=["networkx", "scipy.sparse.csgraph"],
        example_code="nx.dijkstra_path(G, source, target)",
        tags=["图论", "路径", "优化"],
        applicable_data_types=["network", "spatial"],
    ),
    "minimum_spanning_tree": ExtendedModelKnowledge(
        model_id="minimum_spanning_tree",
        name="最小生成树",
        category="图论",
        description="在连通加权图中找到边权和最小的生成树，包括Prim和Kruskal算法",
        applicable_problems=["网络设计", "电路布线", "管道铺设", "通信网络"],
        advantages=["全局最优解", "算法高效", "结果直观"],
        disadvantages=["仅适用于无向图", "权重必须非负"],
        complexity="低",
        implementation_difficulty="低",
        data_requirements={"graph_type": "无向连通图", "edge_weights": "非负权重"},
        key_parameters=["边集合", "边权重"],
        validation_methods=["树结构验证", "权重和验证"],
        common_pitfalls=["图不连通", "重边处理"],
        required_packages=["networkx", "scipy.sparse.csgraph"],
        example_code="nx.minimum_spanning_tree(G)",
        tags=["图论", "生成树", "优化"],
        applicable_data_types=["network"],
    ),
    "network_flow": ExtendedModelKnowledge(
        model_id="network_flow",
        name="网络流",
        category="图论",
        description="研究网络中流的最优分配问题，包括最大流、最小费用流等",
        applicable_problems=["供应链优化", "交通流量", "任务分配", "二分图匹配"],
        advantages=["建模能力强", "可处理复杂约束"],
        disadvantages=["建模较复杂", "大规模问题计算量大"],
        complexity="高",
        implementation_difficulty="中",
        data_requirements={
            "graph_type": "有向图",
            "capacity": "容量约束",
            "demand": "需求",
        },
        key_parameters=["源点", "汇点", "容量", "费用"],
        validation_methods=["流量守恒检验", "容量约束检验"],
        common_pitfalls=["容量设置不当", "源汇点选择"],
        required_packages=["networkx", "ortools"],
        example_code="nx.maximum_flow(G, source, sink)",
        tags=["图论", "网络流", "优化"],
        applicable_data_types=["network"],
    ),
    "graph_coloring": ExtendedModelKnowledge(
        model_id="graph_coloring",
        name="图着色",
        category="图论",
        description="用最少颜色为图的顶点着色，使相邻顶点颜色不同",
        applicable_problems=["排课问题", "频率分配", "寄存器分配", "地图着色"],
        advantages=["模型直观", "应用广泛"],
        disadvantages=["NP难问题", "大规模问题难以精确求解"],
        complexity="高",
        implementation_difficulty="高",
        data_requirements={"graph_type": "无向图", "adjacency": "邻接关系"},
        key_parameters=["颜色数", "约束条件"],
        validation_methods=["冲突检测", "颜色数验证"],
        common_pitfalls=["颜色数设置过少", "启发式解非最优"],
        required_packages=["networkx"],
        example_code="nx.greedy_color(G)",
        tags=["图论", "着色", "组合优化"],
        applicable_data_types=["network"],
    ),
    # ==================== 动态规划 ====================
    "dynamic_programming": ExtendedModelKnowledge(
        model_id="dynamic_programming",
        name="动态规划",
        category="优化",
        description="通过将问题分解为子问题并存储子问题解来避免重复计算的优化方法",
        applicable_problems=["序列决策", "资源分配", "路径优化", "背包问题"],
        advantages=["避免重复计算", "可得到全局最优", "适用范围广"],
        disadvantages=["状态定义困难", "维度灾难", "边界条件复杂"],
        complexity="中",
        implementation_difficulty="高",
        data_requirements={"structure": "可分解为子问题", "overlap": "子问题重叠"},
        key_parameters=["状态定义", "转移方程", "边界条件"],
        validation_methods=["子问题验证", "最优性原理检验"],
        common_pitfalls=["状态定义不当", "转移方程错误", "边界遗漏"],
        required_packages=["numpy"],
        example_code="dp[i] = max(dp[i-1], dp[i-2] + value[i])",
        tags=["动态规划", "优化", "递归"],
        applicable_data_types=["sequence", "numerical"],
    ),
    "knapsack": ExtendedModelKnowledge(
        model_id="knapsack",
        name="背包问题",
        category="优化",
        description="在容量限制下选择物品使总价值最大化的组合优化问题",
        applicable_problems=["资源分配", "投资组合", "货物装载", "预算分配"],
        advantages=["模型经典", "算法成熟", "可扩展性好"],
        disadvantages=["0-1背包为NP难", "多维背包复杂度高"],
        complexity="中",
        implementation_difficulty="中",
        data_requirements={
            "items": "物品集合",
            "weights": "重量",
            "values": "价值",
            "capacity": "容量",
        },
        key_parameters=["物品权重", "物品价值", "背包容量"],
        validation_methods=["容量约束检验", "最优性验证"],
        common_pitfalls=["浮点精度", "大规模问题效率"],
        required_packages=["numpy", "ortools"],
        example_code="from ortools.algorithms import knapsack_solver",
        tags=["背包", "组合优化", "动态规划"],
        applicable_data_types=["numerical"],
    ),
    # ==================== 博弈论 ====================
    "game_theory": ExtendedModelKnowledge(
        model_id="game_theory",
        name="博弈论",
        category="决策",
        description="研究多个决策主体之间策略互动的数学理论",
        applicable_problems=["竞争策略", "定价博弈", "资源争夺", "拍卖设计"],
        advantages=["考虑多方互动", "理论框架完善"],
        disadvantages=["信息假设严格", "均衡计算复杂"],
        complexity="高",
        implementation_difficulty="高",
        data_requirements={
            "players": "参与者",
            "strategies": "策略集",
            "payoffs": "收益矩阵",
        },
        key_parameters=["参与者数", "策略空间", "收益函数"],
        validation_methods=["均衡验证", "稳定性分析"],
        common_pitfalls=["均衡不唯一", "混合策略处理"],
        required_packages=["nashpy", "gambit"],
        example_code="import nashpy as nash; game = nash.Game(A, B)",
        tags=["博弈论", "决策", "均衡"],
        applicable_data_types=["matrix", "numerical"],
    ),
    "nash_equilibrium": ExtendedModelKnowledge(
        model_id="nash_equilibrium",
        name="纳什均衡",
        category="决策",
        description="博弈论中各参与者都采取最优反应策略的稳定状态",
        applicable_problems=["市场竞争", "军备竞赛", "公共品提供", "交通均衡"],
        advantages=["稳定性强", "可预测性好"],
        disadvantages=["可能不存在纯策略均衡", "多个均衡难选择"],
        complexity="高",
        implementation_difficulty="高",
        data_requirements={"payoff_matrix": "收益矩阵", "strategy_sets": "策略集"},
        key_parameters=["收益矩阵", "策略空间"],
        validation_methods=["最优反应检验", "偏离收益计算"],
        common_pitfalls=["均衡不唯一", "混合策略计算"],
        required_packages=["nashpy", "scipy.optimize"],
        example_code="game.support_enumeration()",
        tags=["纳什均衡", "博弈论", "决策"],
        applicable_data_types=["matrix"],
    ),
    # ==================== 其他重要模型 ====================
    "grey_prediction": ExtendedModelKnowledge(
        model_id="grey_prediction",
        name="灰色预测 (GM)",
        category="预测",
        description="基于灰色系统理论的预测方法，适用于小样本、贫信息数据",
        applicable_problems=["趋势预测", "系统分析", "小样本预测", "发展预测"],
        advantages=["样本要求少", "计算简单", "短期预测效果好"],
        disadvantages=["长期预测精度下降", "对异常值敏感"],
        complexity="低",
        implementation_difficulty="低",
        data_requirements={"sample_size": "4+", "trend": "单调趋势"},
        key_parameters=["累加阶数", "预测步长"],
        validation_methods=["后验差检验", "关联度分析"],
        common_pitfalls=["非单调数据", "样本量过少"],
        required_packages=["numpy"],
        example_code="# GM(1,1) 模型实现",
        tags=["灰色预测", "小样本", "趋势"],
        applicable_data_types=["time_series", "numerical"],
    ),
    "markov_chain": ExtendedModelKnowledge(
        model_id="markov_chain",
        name="马尔可夫链",
        category="随机过程",
        description="描述状态间转移的随机过程，具有无记忆性",
        applicable_problems=["状态预测", "排队系统", "市场份额", "设备维护"],
        advantages=["理论完善", "计算可行", "直观易懂"],
        disadvantages=["无记忆假设限制", "状态空间爆炸"],
        complexity="中",
        implementation_difficulty="中",
        data_requirements={"states": "状态空间", "transitions": "转移概率"},
        key_parameters=["状态空间", "转移矩阵"],
        validation_methods=["转移矩阵验证", "平稳分布检验"],
        common_pitfalls=["状态划分不当", "转移概率估计"],
        required_packages=["numpy", "scipy.linalg"],
        example_code="stationary = np.linalg.eig(P.T)[1][:,0]",
        tags=["马尔可夫", "随机过程", "状态转移"],
        applicable_data_types=["categorical", "sequence"],
    ),
    "monte_carlo": ExtendedModelKnowledge(
        model_id="monte_carlo",
        name="蒙特卡洛模拟",
        category="模拟",
        description="通过大量随机抽样来估计数学期望或概率的方法",
        applicable_problems=["风险分析", "积分计算", "不确定性量化", "期权定价"],
        advantages=["适用范围广", "可处理复杂系统", "精度可控"],
        disadvantages=["计算量大", "收敛速度慢", "随机数质量要求高"],
        complexity="中",
        implementation_difficulty="低",
        data_requirements={"distribution": "概率分布", "parameters": "分布参数"},
        key_parameters=["模拟次数", "随机种子", "分布假设"],
        validation_methods=["收敛性检验", "置信区间"],
        common_pitfalls=["模拟次数不足", "分布假设错误"],
        required_packages=["numpy", "scipy.stats"],
        example_code="np.random.seed(42); samples = np.random.normal(0, 1, 10000)",
        tags=["蒙特卡洛", "模拟", "随机"],
        applicable_data_types=["numerical"],
    ),
    "queuing_theory": ExtendedModelKnowledge(
        model_id="queuing_theory",
        name="排队论",
        category="运筹学",
        description="研究排队系统中顾客等待和服务过程的数学理论",
        applicable_problems=["服务系统设计", "资源配置", "交通流分析", "产能规划"],
        advantages=["理论成熟", "指标完善", "可解析求解"],
        disadvantages=["分布假设严格", "复杂系统难以解析"],
        complexity="中",
        implementation_difficulty="中",
        data_requirements={
            "arrival_rate": "到达率",
            "service_rate": "服务率",
            "servers": "服务台数",
        },
        key_parameters=["λ(到达率)", "μ(服务率)", "c(服务台数)"],
        validation_methods=["稳态验证", "性能指标计算"],
        common_pitfalls=["稳态条件不满足", "分布假设错误"],
        required_packages=["numpy", "scipy.stats"],
        example_code="# M/M/c 模型计算",
        tags=["排队论", "运筹学", "服务系统"],
        applicable_data_types=["numerical"],
    ),
    "differential_equations": ExtendedModelKnowledge(
        model_id="differential_equations",
        name="微分方程",
        category="动力系统",
        description="描述变量变化率关系的数学方程，用于建模动态系统",
        applicable_problems=["传染病传播", "人口增长", "物理系统", "化学反应"],
        advantages=["描述动态过程", "理论深刻", "可解释性强"],
        disadvantages=["非线性难以解析", "参数估计困难"],
        complexity="高",
        implementation_difficulty="高",
        data_requirements={"initial_conditions": "初始条件", "parameters": "系统参数"},
        key_parameters=["方程参数", "初始条件", "边界条件"],
        validation_methods=["数值验证", "稳定性分析", "相图分析"],
        common_pitfalls=["刚性问题", "参数敏感", "数值不稳定"],
        required_packages=["scipy.integrate", "numpy"],
        example_code="from scipy.integrate import odeint",
        tags=["微分方程", "动力系统", "连续"],
        applicable_data_types=["time_series", "continuous"],
    ),
    "topsis": ExtendedModelKnowledge(
        model_id="topsis",
        name="TOPSIS法",
        category="评价",
        description="基于理想解和负理想解距离的多属性决策方法",
        applicable_problems=["方案评价", "综合排名", "选址决策", "供应商选择"],
        advantages=["直观易懂", "计算简单", "可处理多指标"],
        disadvantages=["对权重敏感", "假设线性关系"],
        complexity="低",
        implementation_difficulty="低",
        data_requirements={"decision_matrix": "决策矩阵", "weights": "权重向量"},
        key_parameters=["指标权重", "正负向指标"],
        validation_methods=["敏感性分析", "排名稳定性"],
        common_pitfalls=["权重确定主观", "指标量纲不一致"],
        required_packages=["numpy"],
        example_code="# TOPSIS 评价实现",
        tags=["TOPSIS", "评价", "多属性决策"],
        applicable_data_types=["numerical", "matrix"],
    ),
    "entropy_weight": ExtendedModelKnowledge(
        model_id="entropy_weight",
        name="熵权法",
        category="评价",
        description="基于信息熵客观确定指标权重的方法",
        applicable_problems=["权重确定", "综合评价", "指标筛选"],
        advantages=["客观", "数据驱动", "无需专家"],
        disadvantages=["依赖数据质量", "忽略专家知识", "对异常值敏感"],
        complexity="低",
        implementation_difficulty="低",
        data_requirements={"data_matrix": "数据矩阵", "indicators": "指标列表"},
        key_parameters=["标准化方法"],
        validation_methods=["权重合理性检验", "敏感性分析"],
        common_pitfalls=["数据标准化不当", "指标区分度低"],
        required_packages=["numpy"],
        example_code="# 熵权法计算",
        tags=["熵权法", "权重", "客观赋权"],
        applicable_data_types=["numerical", "matrix"],
    ),
}


class ModelRegistry:
    """模型注册中心"""

    def __init__(
        self,
        base_kb: Optional[MathModelingKnowledgeBase] = None,
    ):
        """
        初始化模型注册中心

        Args:
            base_kb: 基础知识库，默认使用全局知识库
        """
        self.base_kb = base_kb or default_knowledge_base
        self._registry: Dict[str, ExtendedModelKnowledge] = {}
        self._performance_history: Dict[str, List[PerformanceRecord]] = {}

        # 加载基础模型
        self._load_base_models()

        # 加载新增模型
        self._load_new_models()

    def _load_base_models(self) -> None:
        """从基础知识库加载模型"""
        for model_id, model_knowledge in self.base_kb.models.items():
            self._registry[model_id] = ExtendedModelKnowledge.from_model_knowledge(
                model_id, model_knowledge
            )

    def _load_new_models(self) -> None:
        """加载新增模型"""
        for model_id, model in NEW_MODELS.items():
            self._registry[model_id] = model

    def register_model(self, model: ExtendedModelKnowledge) -> str:
        """
        注册新模型

        Args:
            model: 扩展模型知识

        Returns:
            模型ID
        """
        if not model.model_id:
            model.model_id = f"model_{uuid.uuid4().hex[:8]}"

        self._registry[model.model_id] = model
        logger.info("Registered model: %s (%s)", model.model_id, model.name)
        return model.model_id

    def get_model(self, model_id: str) -> Optional[ExtendedModelKnowledge]:
        """
        获取模型

        Args:
            model_id: 模型ID

        Returns:
            模型知识，不存在则返回 None
        """
        return self._registry.get(model_id)

    def list_models(
        self,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[ExtendedModelKnowledge]:
        """
        列出模型

        Args:
            category: 按类别筛选
            complexity: 按复杂度筛选
            tags: 按标签筛选

        Returns:
            模型列表
        """
        models = list(self._registry.values())

        if category:
            models = [m for m in models if m.category == category]

        if complexity:
            models = [m for m in models if m.complexity == complexity]

        if tags:
            models = [m for m in models if any(t in m.tags for t in tags)]

        return models

    def search_by_scenario(
        self,
        scenario: str,
        constraints: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[ModelRecommendation]:
        """
        根据场景搜索合适的模型

        Args:
            scenario: 应用场景描述
            constraints: 约束条件
            top_k: 返回数量

        Returns:
            模型推荐列表
        """
        constraints = constraints or {}
        scenario_lower = scenario.lower()

        scored_models: List[Tuple[float, ExtendedModelKnowledge]] = []

        for model in self._registry.values():
            score = 0.0

            # 匹配适用问题
            for problem in model.applicable_problems:
                if (
                    problem.lower() in scenario_lower
                    or scenario_lower in problem.lower()
                ):
                    score += 2.0

            # 匹配标签
            for tag in model.tags:
                if tag.lower() in scenario_lower:
                    score += 1.0

            # 匹配描述
            if scenario_lower in model.description.lower():
                score += 0.5

            # 复杂度约束
            max_complexity = constraints.get("max_complexity")
            if max_complexity:
                complexity_order = {"低": 1, "中": 2, "高": 3}
                if complexity_order.get(model.complexity, 3) > complexity_order.get(
                    max_complexity, 3
                ):
                    score -= 1.0

            if score > 0:
                scored_models.append((score, model))

        # 排序并取前k个
        scored_models.sort(key=lambda x: x[0], reverse=True)
        top_models = scored_models[:top_k]

        # 转换为 ModelRecommendation
        recommendations: List[ModelRecommendation] = []
        for score, model in top_models:
            rec = ModelRecommendation(
                model_id=model.model_id,
                name=model.name,
                category=model.category,
                complexity=model.complexity,  # type: ignore
                rationale=f"匹配场景: {scenario}。{model.description}",
                expected_performance=model.performance_benchmarks,
                implementation_complexity=model.implementation_difficulty,
                data_requirements=model.data_requirements,
                key_parameters=model.key_parameters,
                validation_methods=model.validation_methods,
                common_pitfalls=model.common_pitfalls,
            )
            recommendations.append(rec)

        return recommendations

    def record_performance(
        self,
        model_id: str,
        metrics: Dict[str, float],
        problem_id: str,
        notes: str = "",
    ) -> None:
        """
        记录模型性能

        Args:
            model_id: 模型ID
            metrics: 性能指标
            problem_id: 问题ID
            notes: 备注
        """
        if model_id not in self._performance_history:
            self._performance_history[model_id] = []

        record = PerformanceRecord(
            record_id=f"pr_{uuid.uuid4().hex[:8]}",
            problem_id=problem_id,
            metrics=metrics,
            recorded_at=datetime.now().isoformat(),
            notes=notes,
        )

        self._performance_history[model_id].append(record)
        logger.info("Recorded performance for %s: %s", model_id, metrics)

    def get_performance_history(
        self,
        model_id: str,
    ) -> List[PerformanceRecord]:
        """
        获取模型性能历史

        Args:
            model_id: 模型ID

        Returns:
            性能记录列表
        """
        return self._performance_history.get(model_id, [])

    def compare_models(
        self,
        model_ids: List[str],
    ) -> Dict[str, Any]:
        """
        比较多个模型

        Args:
            model_ids: 模型ID列表

        Returns:
            比较结果
        """
        comparison: Dict[str, Any] = {
            "models": [],
            "summary": {},
        }

        for model_id in model_ids:
            model = self.get_model(model_id)
            if model:
                model_info = {
                    "model_id": model_id,
                    "name": model.name,
                    "category": model.category,
                    "complexity": model.complexity,
                    "advantages": model.advantages,
                    "disadvantages": model.disadvantages,
                    "performance_history": [
                        {"metrics": r.metrics, "problem_id": r.problem_id}
                        for r in self.get_performance_history(model_id)
                    ],
                }
                comparison["models"].append(model_info)

        # 生成摘要
        if comparison["models"]:
            comparison["summary"] = {
                "total_models": len(comparison["models"]),
                "categories": list(set(m["category"] for m in comparison["models"])),
                "complexity_distribution": {
                    c: sum(1 for m in comparison["models"] if m["complexity"] == c)
                    for c in ["低", "中", "高"]
                },
            }

        return comparison

    def get_model_count(self) -> int:
        """获取注册模型总数"""
        return len(self._registry)

    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(set(m.category for m in self._registry.values()))


# 全局注册中心实例
model_registry = ModelRegistry()


# 便捷函数
def search_models(
    scenario: str,
    top_k: int = 5,
) -> List[ModelRecommendation]:
    """
    便捷函数：搜索模型

    Args:
        scenario: 应用场景
        top_k: 返回数量

    Returns:
        模型推荐列表
    """
    return model_registry.search_by_scenario(scenario, top_k=top_k)


def get_model_info(model_id: str) -> Optional[ExtendedModelKnowledge]:
    """
    便捷函数：获取模型信息

    Args:
        model_id: 模型ID

    Returns:
        模型知识
    """
    return model_registry.get_model(model_id)
