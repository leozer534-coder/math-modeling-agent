"""
代码模板注册与检索系统
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


# ---------------------------------------------------------------------------
# 中文模型名称别名映射表
# ---------------------------------------------------------------------------
# 用于增强中文模型名的匹配能力。
# 键: 中文别名（或其他无法通过现有子串匹配命中的名称）
# 值: 对应已有模板 applicable_models 中的规范关键词元组
#
# 设计原则:
#   1. 仅收录「现有子串匹配无法命中」的别名，避免冗余
#   2. 一个别名可映射到多个关键词（如 "图论" 对应多类图论模板）
#   3. 匹配时不区分大小写
# ---------------------------------------------------------------------------
_MODEL_ALIASES: dict[str, tuple[str, ...]] = {
    # === 优化类 ===
    "帕累托": ("Pareto",),
    "帕累托最优": ("Pareto",),
    "帕累托前沿": ("Pareto",),
    "蒙特卡罗": ("蒙特卡洛",),  # 不同音译写法
    "蒙特卡罗模拟": ("蒙特卡洛",),
    "蒙特卡罗方法": ("蒙特卡洛",),
    "非线性优化": ("非线性规划",),  # "非线性优化"与"非线性规划"互不为子串
    "约束优化": ("线性规划", "非线性规划", "整数规划"),
    "数学规划": ("线性规划", "非线性规划", "整数规划"),
    "运筹优化": ("线性规划", "非线性规划", "整数规划"),
    "组合优化": ("遗传算法", "模拟退火", "粒子群", "TSP"),
    "启发式算法": ("遗传算法", "模拟退火", "粒子群"),
    "元启发式算法": ("遗传算法", "模拟退火", "粒子群"),
    "智能优化算法": ("遗传算法", "模拟退火", "粒子群"),
    "智能优化": ("遗传算法", "模拟退火", "粒子群"),
    "进化算法": ("遗传算法",),
    "进化计算": ("遗传算法",),
    # === 预测类 ===
    "自回归积分滑动平均": ("ARIMA",),
    "差分自回归移动平均": ("ARIMA",),
    "自回归移动平均": ("ARIMA",),  # ARMA 的常见中文称呼
    "时序预测": ("时间序列",),  # "时序"与"时间序列"互不为子串
    "时序分析": ("时间序列",),
    "霍尔特温特斯": ("Holt-Winters",),
    "三次指数平滑": ("Holt-Winters",),
    "深度学习": ("神经网络",),
    "多层感知机": ("MLP",),
    "反向传播": ("BP神经网络",),
    "长短时记忆网络": ("LSTM",),  # "长短时"与"长短期"互不为子串
    "LSTM预测": ("LSTM",),
    "循环神经网络预测": ("LSTM", "GRU"),  # "循环神经网络"已可命中，但加"预测"后不一定
    "随机森林回归": ("Random Forest",),
    "随机森林分类": ("Random Forest",),
    "RF模型": ("Random Forest",),
    # === 评价类 ===
    "逼近理想解排序": ("TOPSIS",),
    "优劣解距离法": ("TOPSIS",),
    "理想解法": ("TOPSIS",),
    "熵值法": ("熵权法",),
    "信息熵": ("熵权法",),
    "因子分析": ("PCA",),
    "模糊数学": ("模糊评价",),
    "效率评价": ("DEA",),
    "效率分析": ("DEA",),  # "效率分析"与"数据包络分析"/"DEA"互不为子串
    "多属性决策": ("TOPSIS", "AHP", "VIKOR"),
    "多指标决策": ("TOPSIS", "AHP", "VIKOR"),
    "多指标评价": ("TOPSIS", "AHP", "VIKOR"),
    "权重确定": ("AHP", "熵权法"),
    "赋权方法": ("AHP", "熵权法"),
    "主观赋权": ("AHP",),
    # === 图论类 ===
    "图论": ("TSP", "最短路径", "网络流"),
    "图论分析": ("TSP", "最短路径", "网络流"),
    "图论模型": ("TSP", "最短路径", "网络流"),
    "最优路径": ("最短路径", "TSP"),  # "最优路径"与"路径优化"/"最短路径"互不为子串
    "迪杰斯特拉": ("Dijkstra",),
    "狄克斯特拉": ("Dijkstra",),
    "弗洛伊德": ("Floyd",),
    "弗洛伊德算法": ("Floyd",),
    # === 分类类 ===
    "逻辑斯蒂回归": ("逻辑回归",),
    "逻辑斯谛回归": ("逻辑回归",),
    # === 聚类类 ===
    "聚类分析": ("K-means", "层次聚类", "DBSCAN", "GMM"),
    "聚类算法": ("K-means", "层次聚类", "DBSCAN", "GMM"),
    "期望最大化": ("EM算法",),
    "期望最大化算法": ("EM算法",),
    # === 统计类 ===
    "方差分析": ("ANOVA",),
    "自助法": ("Bootstrap",),
    "等待线理论": ("排队论",),
    "相关性分析": ("灰色关联",),  # "相关性分析"与"灰色关联"互不为子串
    "灰色理论": ("灰色关联", "灰色预测"),  # "灰色理论"与"灰色关联"/"灰色预测"互不为子串
    "正态检验": ("假设检验",),  # "正态检验"与"假设检验"互不为子串
    "正态性检验": ("假设检验",),
    "显著性分析": ("假设检验",),  # 与"显著性检验"不同写法
    "概率推断": ("贝叶斯",),
    # === 微分方程类 ===
    "传染病动力学": ("SIR", "SEIR"),  # "传染病动力学"与"传染病模型"互不为子串
    "传染病传播": ("SIR", "SEIR"),
    "种群模型": ("Lotka-Volterra",),  # "种群模型"与"种群动力学"互不为子串
    # === 动态规划类 ===
    "动态规划": ("背包问题", "资源分配", "LCS"),
    "动态规划模型": ("背包问题", "资源分配", "LCS"),
    "动态规划算法": ("背包问题", "资源分配", "LCS"),
    "马氏链": ("马尔可夫",),
    # === 博弈论类 ===
    "博弈分析": ("博弈论", "Nash"),
    "纳什博弈": ("Nash",),
    "Stackelberg": ("博弈论",),
    "斯塔克尔伯格": ("Stackelberg",),
    # === 集成学习类 ===
    "模型融合": ("Stacking", "ensemble"),
    "Bagging": ("Random Forest", "ensemble"),
    "Boosting": ("XGBoost", "LightGBM"),
    # === 拟合/回归类 ===
    "多项式": ("多项式拟合", "多项式回归"),
    "数据拟合": ("多项式拟合", "曲线拟合"),
    "函数拟合": ("曲线拟合",),
    "最小二乘拟合": ("多项式拟合", "线性回归"),
    "least squares": ("OLS", "线性回归"),
    "回归分析": ("多元线性回归", "岭回归", "Lasso"),
    "L1正则化": ("Lasso",),
    "L2正则化": ("岭回归",),
    "特征选择回归": ("Lasso", "elastic net"),
    "BP网络": ("BP神经网络", "MLP"),
    "人工神经网络": ("BP神经网络", "MLP"),
    "ANN": ("BP神经网络", "MLP"),
    "前馈神经网络": ("BP神经网络", "MLP"),
    # === 英文全称（无法通过现有关键词子串匹配命中的） ===
    "Dynamic Programming": ("背包问题", "资源分配", "LCS"),
    "Graph Theory": ("TSP", "最短路径", "网络流"),
    "Analytic Hierarchy Process": ("AHP",),
    "Principal Component Analysis": ("PCA",),
}


@dataclass(frozen=True)
class CodeTemplate:
    """代码模板"""
    name: str
    category: str
    description: str
    applicable_models: list[str]  # 对应知识库模型名关键词
    code: str                     # 含占位符的完整可运行代码
    dependencies: list[str]       # 所需 Python 包
    placeholders: dict[str, str] = field(default_factory=dict)  # 占位符说明


class TemplateRegistry:
    """代码模板注册中心"""

    def __init__(self) -> None:
        self._templates: Dict[str, CodeTemplate] = {}
        self._load_builtin_templates()

    def register(self, template_id: str, template: CodeTemplate) -> None:
        """注册模板"""
        self._templates[template_id] = template

    @staticmethod
    def _resolve_aliases(model_name: str) -> list[str]:
        """通过别名映射表解析模型名称，返回额外的搜索关键词。

        对输入的模型名称与别名表进行双向子串匹配，
        命中后返回对应的规范关键词列表，供 search 方法使用。

        Args:
            model_name: 用户输入的模型名称

        Returns:
            通过别名解析出的额外规范关键词列表（小写）
        """
        model_lower = model_name.lower()
        extra_keywords: list[str] = []
        for alias, keywords in _MODEL_ALIASES.items():
            alias_lower = alias.lower()
            if alias_lower in model_lower or model_lower in alias_lower:
                extra_keywords.extend(kw.lower() for kw in keywords)
        return extra_keywords

    def search(self, model_name: str) -> list[CodeTemplate]:
        """根据模型名称搜索匹配模板

        支持英文名称、中文名称及中文别名的模糊匹配，不区分大小写。
        匹配流程:
          1. 使用原始名称与模板关键词进行双向子串匹配
          2. 通过别名映射表将输入解析为规范关键词后再次匹配

        Args:
            model_name: 模型名称（支持模糊匹配）

        Returns:
            匹配的模板列表
        """
        model_lower = model_name.lower()
        # 收集所有搜索词：原始名称 + 别名解析得到的规范关键词
        search_terms = [model_lower]
        search_terms.extend(self._resolve_aliases(model_name))

        results = []
        for template in self._templates.values():
            matched = False
            for keyword in template.applicable_models:
                kw_lower = keyword.lower()
                for term in search_terms:
                    if kw_lower in term or term in kw_lower:
                        matched = True
                        break
                if matched:
                    break
            if matched:
                results.append(template)
        return results

    def get_template_for_prompt(
        self,
        model_names: list[str],
        max_chars: int = 3000,
    ) -> str:
        """为多个模型生成可注入 prompt 的模板参考文本

        Args:
            model_names: 模型名称列表
            max_chars: 最大字符数

        Returns:
            格式化的代码模板参考文本
        """
        seen_ids: set[str] = set()
        matched: list[CodeTemplate] = []

        for name in model_names:
            for t in self.search(name):
                tid = t.name
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    matched.append(t)

        if not matched:
            return ""

        sections = ["## 参考代码模板\n以下是经过验证的代码框架，请根据实际数据调整使用：\n"]
        total_len = len(sections[0])

        for t in matched[:5]:  # 最多 5 个模板
            section = f"\n### {t.name} ({t.category})\n{t.description}\n```python\n{t.code}\n```\n"
            if total_len + len(section) > max_chars:
                break
            sections.append(section)
            total_len += len(section)

        return "\n".join(sections)

    def list_categories(self) -> list[str]:
        """列出所有模板类别"""
        return list(set(t.category for t in self._templates.values()))

    def _load_builtin_templates(self) -> None:
        """加载内置模板"""
        from app.config.code_templates.optimization_templates import OPTIMIZATION_TEMPLATES
        from app.config.code_templates.prediction_templates import PREDICTION_TEMPLATES
        from app.config.code_templates.evaluation_templates import EVALUATION_TEMPLATES
        from app.config.code_templates.graph_templates import GRAPH_TEMPLATES
        from app.config.code_templates.validation_templates import VALIDATION_TEMPLATES
        from app.config.code_templates.classification_templates import CLASSIFICATION_TEMPLATES
        from app.config.code_templates.clustering_templates import CLUSTERING_TEMPLATES
        from app.config.code_templates.ode_templates import ODE_TEMPLATES
        from app.config.code_templates.statistics_templates import STATISTICS_TEMPLATES
        from app.config.code_templates.dp_templates import DP_TEMPLATES
        from app.config.code_templates.game_theory_templates import GAME_THEORY_TEMPLATES
        from app.config.code_templates.fitting_templates import FITTING_TEMPLATES
        from app.config.code_templates.regression_templates import REGRESSION_TEMPLATES

        all_templates = {
            **OPTIMIZATION_TEMPLATES,
            **PREDICTION_TEMPLATES,
            **EVALUATION_TEMPLATES,
            **GRAPH_TEMPLATES,
            **VALIDATION_TEMPLATES,
            **CLASSIFICATION_TEMPLATES,
            **CLUSTERING_TEMPLATES,
            **ODE_TEMPLATES,
            **STATISTICS_TEMPLATES,
            **DP_TEMPLATES,
            **GAME_THEORY_TEMPLATES,
            **FITTING_TEMPLATES,
            **REGRESSION_TEMPLATES,
        }
        for tid, template in all_templates.items():
            self._templates[tid] = template


# 全局单例
template_registry = TemplateRegistry()
