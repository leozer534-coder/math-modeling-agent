"""
Multi-Model Strategy - 多模型策略器
=====================================

功能：
1. 根据问题类型推荐合适的模型组合
2. 实现"从简单到复杂"的建模策略
3. 支持模型性能对比分析
4. 自动选择最优模型

关键特性：
- 渐进式建模：基线模型 → 改进模型 → 创新变体
- 模型知识库：内置常见问题的模型推荐
- 自动评估：根据数据特征选择合适模型
"""

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.core.llm.llm_gateway import chat_completion
from app.schemas.contracts import (
    ComplexityLevel,
    ModelRecommendation,
    MultiModelPlan,
)
from app.utils.log_util import logger


class ProblemCategory(Enum):
    """问题类型分类"""

    OPTIMIZATION = "optimization"  # 优化问题
    PREDICTION = "prediction"  # 预测问题
    CLASSIFICATION = "classification"  # 分类问题
    CLUSTERING = "clustering"  # 聚类问题
    EVALUATION = "evaluation"  # 评价问题
    SCHEDULING = "scheduling"  # 调度问题
    PATH_PLANNING = "path_planning"  # 路径规划
    RESOURCE_ALLOCATION = "resource_allocation"  # 资源分配
    DYNAMIC_SYSTEM = "dynamic_system"  # 动态系统
    GAME_THEORY = "game_theory"  # 博弈论


class DataCharacteristic(Enum):
    """数据特征"""

    TIME_SERIES = "time_series"  # 时间序列
    CROSS_SECTIONAL = "cross_sectional"  # 横截面
    PANEL = "panel"  # 面板数据
    SPATIAL = "spatial"  # 空间数据
    NETWORK = "network"  # 网络数据
    HIGH_DIMENSIONAL = "high_dimensional"  # 高维
    SPARSE = "sparse"  # 稀疏
    IMBALANCED = "imbalanced"  # 不平衡


@dataclass
class ModelInfo:
    """模型信息"""

    id: str
    name: str
    category: str
    complexity: ComplexityLevel
    description: str
    advantages: List[str]
    disadvantages: List[str]
    applicable_scenarios: List[str]
    data_requirements: Dict[str, str]
    key_parameters: List[str]
    python_implementation: str  # 推荐的Python库/实现方式
    validation_methods: List[str]


# 模型知识库
MODEL_KNOWLEDGE_BASE: Dict[str, List[ModelInfo]] = {
    "optimization": [
        ModelInfo(
            id="lp",
            name="线性规划 (LP)",
            category="optimization",
            complexity="simple",
            description="用于目标函数和约束均为线性的优化问题",
            advantages=["求解效率高", "全局最优解", "理论成熟"],
            disadvantages=["仅适用于线性问题", "对非线性关系建模能力差"],
            applicable_scenarios=["资源分配", "生产计划", "运输问题"],
            data_requirements={"minimum_samples": "无特殊要求", "data_type": "数值型"},
            key_parameters=["决策变量", "目标函数系数", "约束条件"],
            python_implementation="scipy.optimize.linprog 或 pulp",
            validation_methods=["对偶检验", "敏感性分析"],
        ),
        ModelInfo(
            id="milp",
            name="混合整数线性规划 (MILP)",
            category="optimization",
            complexity="moderate",
            description="包含整数变量的线性规划问题",
            advantages=["可处理离散决策", "建模能力强"],
            disadvantages=["求解时间可能较长", "大规模问题困难"],
            applicable_scenarios=["选址问题", "车辆路径", "排班调度"],
            data_requirements={"minimum_samples": "无特殊要求", "data_type": "数值型"},
            key_parameters=["整数变量", "二元变量", "大M约束"],
            python_implementation="pulp, gurobi, ortools",
            validation_methods=["gap分析", "可行性检验"],
        ),
        ModelInfo(
            id="nlp",
            name="非线性规划 (NLP)",
            category="optimization",
            complexity="complex",
            description="目标函数或约束包含非线性项",
            advantages=["建模灵活", "可处理复杂关系"],
            disadvantages=["可能陷入局部最优", "求解难度大"],
            applicable_scenarios=["工程设计", "参数优化", "曲线拟合"],
            data_requirements={"minimum_samples": "无特殊要求", "data_type": "数值型"},
            key_parameters=["初始点", "收敛阈值", "步长"],
            python_implementation="scipy.optimize.minimize, cyipopt",
            validation_methods=["多起点验证", "KKT条件检验"],
        ),
        ModelInfo(
            id="ga",
            name="遗传算法 (GA)",
            category="optimization",
            complexity="complex",
            description="模拟自然进化的启发式优化算法",
            advantages=["全局搜索能力强", "适用于复杂问题", "无需梯度信息"],
            disadvantages=["参数敏感", "收敛速度可能慢", "无法保证最优"],
            applicable_scenarios=["组合优化", "参数调优", "多目标优化"],
            data_requirements={"minimum_samples": "无特殊要求", "data_type": "任意"},
            key_parameters=["种群大小", "交叉率", "变异率", "迭代次数"],
            python_implementation="deap, geatpy",
            validation_methods=["收敛曲线分析", "多次运行统计"],
        ),
    ],
    "prediction": [
        ModelInfo(
            id="lr",
            name="线性回归",
            category="prediction",
            complexity="simple",
            description="假设因变量与自变量之间存在线性关系",
            advantages=["简单直观", "可解释性强", "计算效率高"],
            disadvantages=["仅适用于线性关系", "对异常值敏感"],
            applicable_scenarios=["趋势预测", "因素分析", "基线模型"],
            data_requirements={"minimum_samples": "30+", "data_type": "数值型"},
            key_parameters=["特征选择", "正则化系数"],
            python_implementation="sklearn.linear_model.LinearRegression",
            validation_methods=["R²", "RMSE", "残差分析"],
        ),
        ModelInfo(
            id="rf_reg",
            name="随机森林回归",
            category="prediction",
            complexity="moderate",
            description="基于决策树集成的回归方法",
            advantages=["非线性建模", "特征重要性", "抗过拟合"],
            disadvantages=["可解释性较差", "大数据集训练慢"],
            applicable_scenarios=["复杂预测", "特征筛选", "稳健预测"],
            data_requirements={"minimum_samples": "100+", "data_type": "数值型/类别型"},
            key_parameters=["树数量", "最大深度", "最小样本分裂"],
            python_implementation="sklearn.ensemble.RandomForestRegressor",
            validation_methods=["交叉验证", "特征重要性分析", "OOB误差"],
        ),
        ModelInfo(
            id="xgb",
            name="XGBoost",
            category="prediction",
            complexity="moderate",
            description="梯度提升决策树的高效实现",
            advantages=["高精度", "处理缺失值", "正则化"],
            disadvantages=["参数调优复杂", "内存占用大"],
            applicable_scenarios=["竞赛首选", "结构化数据", "特征工程后"],
            data_requirements={"minimum_samples": "100+", "data_type": "数值型"},
            key_parameters=["学习率", "最大深度", "正则化参数"],
            python_implementation="xgboost.XGBRegressor",
            validation_methods=["交叉验证", "早停法", "学习曲线"],
        ),
        ModelInfo(
            id="lstm",
            name="LSTM神经网络",
            category="prediction",
            complexity="complex",
            description="长短期记忆网络，适合序列数据",
            advantages=["捕捉长期依赖", "序列建模强"],
            disadvantages=["需要大量数据", "训练时间长", "解释困难"],
            applicable_scenarios=["时间序列预测", "股价预测", "需求预测"],
            data_requirements={"minimum_samples": "500+", "data_type": "时间序列"},
            key_parameters=["隐藏层维度", "层数", "dropout"],
            python_implementation="tensorflow.keras.layers.LSTM / pytorch",
            validation_methods=["时序交叉验证", "滚动预测"],
        ),
    ],
    "evaluation": [
        ModelInfo(
            id="topsis",
            name="TOPSIS法",
            category="evaluation",
            complexity="simple",
            description="基于理想解的多属性决策方法",
            advantages=["直观易懂", "计算简单", "结果可解释"],
            disadvantages=["对权重敏感", "假设线性关系"],
            applicable_scenarios=["方案比选", "绩效评价", "综合排名"],
            data_requirements={"minimum_samples": "5+对象", "data_type": "数值型"},
            key_parameters=["指标权重", "正负向指标"],
            python_implementation="自定义实现 / topsis-python",
            validation_methods=["权重敏感性", "排名稳定性"],
        ),
        ModelInfo(
            id="ahp",
            name="层次分析法 (AHP)",
            category="evaluation",
            complexity="simple",
            description="通过两两比较确定权重的方法",
            advantages=["结合定性定量", "层次清晰", "权重合理"],
            disadvantages=["主观性强", "一致性检验", "指标不宜过多"],
            applicable_scenarios=["权重确定", "决策分析", "因素评价"],
            data_requirements={"minimum_samples": "专家判断", "data_type": "比较矩阵"},
            key_parameters=["判断矩阵", "一致性比率"],
            python_implementation="ahpy / 自定义实现",
            validation_methods=["一致性检验CR<0.1"],
        ),
        ModelInfo(
            id="entropy_weight",
            name="熵权法",
            category="evaluation",
            complexity="simple",
            description="基于信息熵客观确定权重",
            advantages=["客观", "数据驱动", "无需专家"],
            disadvantages=["依赖数据质量", "忽略专家知识"],
            applicable_scenarios=["客观赋权", "数据充分场景"],
            data_requirements={"minimum_samples": "10+对象", "data_type": "数值型"},
            key_parameters=["标准化方法"],
            python_implementation="自定义实现",
            validation_methods=["权重合理性检验"],
        ),
        ModelInfo(
            id="grey_relation",
            name="灰色关联分析",
            category="evaluation",
            complexity="moderate",
            description="基于序列相似性的评价方法",
            advantages=["样本量要求低", "适合不完全信息"],
            disadvantages=["分辨系数主观", "结果对标准化敏感"],
            applicable_scenarios=["小样本评价", "因素分析", "排序"],
            data_requirements={"minimum_samples": "4+对象", "data_type": "数值型"},
            key_parameters=["分辨系数", "参考序列"],
            python_implementation="自定义实现",
            validation_methods=["分辨系数敏感性"],
        ),
    ],
    "classification": [
        ModelInfo(
            id="logistic",
            name="逻辑回归",
            category="classification",
            complexity="simple",
            description="基于sigmoid函数的二分类模型",
            advantages=["可解释性强", "概率输出", "效率高"],
            disadvantages=["线性决策边界", "多分类需扩展"],
            applicable_scenarios=["二分类", "风险预测", "基线模型"],
            data_requirements={"minimum_samples": "50+每类", "data_type": "数值型"},
            key_parameters=["正则化类型", "正则化强度"],
            python_implementation="sklearn.linear_model.LogisticRegression",
            validation_methods=["AUC-ROC", "混淆矩阵", "精确率/召回率"],
        ),
        ModelInfo(
            id="rf_clf",
            name="随机森林分类",
            category="classification",
            complexity="moderate",
            description="基于决策树集成的分类方法",
            advantages=["非线性", "特征重要性", "处理高维"],
            disadvantages=["模型较大", "训练时间"],
            applicable_scenarios=["多分类", "特征筛选", "不平衡数据"],
            data_requirements={"minimum_samples": "100+", "data_type": "混合型"},
            key_parameters=["树数量", "最大深度", "类权重"],
            python_implementation="sklearn.ensemble.RandomForestClassifier",
            validation_methods=["交叉验证", "混淆矩阵", "F1分数"],
        ),
        ModelInfo(
            id="svm",
            name="支持向量机 (SVM)",
            category="classification",
            complexity="moderate",
            description="基于最大间隔的分类方法",
            advantages=["高维有效", "核技巧", "泛化好"],
            disadvantages=["大数据慢", "参数敏感", "难解释"],
            applicable_scenarios=["小样本", "高维数据", "文本分类"],
            data_requirements={"minimum_samples": "50+", "data_type": "数值型"},
            key_parameters=["核函数", "C参数", "gamma"],
            python_implementation="sklearn.svm.SVC",
            validation_methods=["交叉验证", "支持向量分析"],
        ),
    ],
    "clustering": [
        ModelInfo(
            id="kmeans",
            name="K-Means聚类",
            category="clustering",
            complexity="simple",
            description="基于距离的划分式聚类",
            advantages=["简单高效", "可扩展", "易理解"],
            disadvantages=["需预设K", "对异常值敏感", "仅适合凸形"],
            applicable_scenarios=["客户分群", "图像分割", "数据压缩"],
            data_requirements={"minimum_samples": "每簇10+", "data_type": "数值型"},
            key_parameters=["簇数K", "初始化方法", "距离度量"],
            python_implementation="sklearn.cluster.KMeans",
            validation_methods=["轮廓系数", "肘部法则", "CH指数"],
        ),
        ModelInfo(
            id="dbscan",
            name="DBSCAN",
            category="clustering",
            complexity="moderate",
            description="基于密度的聚类算法",
            advantages=["自动确定簇数", "发现异常值", "任意形状"],
            disadvantages=["参数敏感", "高维困难", "密度不均失效"],
            applicable_scenarios=["异常检测", "地理聚类", "任意形状簇"],
            data_requirements={"minimum_samples": "100+", "data_type": "数值型"},
            key_parameters=["eps", "min_samples"],
            python_implementation="sklearn.cluster.DBSCAN",
            validation_methods=["轮廓系数", "核心点比例"],
        ),
        ModelInfo(
            id="hierarchical",
            name="层次聚类",
            category="clustering",
            complexity="moderate",
            description="自底向上或自顶向下的聚类方法",
            advantages=["无需预设K", "树状图直观", "可解释"],
            disadvantages=["计算复杂度高", "不可逆", "大数据困难"],
            applicable_scenarios=["分类体系构建", "生物分类", "文档聚类"],
            data_requirements={"minimum_samples": "50-1000", "data_type": "数值型"},
            key_parameters=["链接方式", "距离度量", "截断点"],
            python_implementation="sklearn.cluster.AgglomerativeClustering",
            validation_methods=["树状图分析", "Cophenetic相关"],
        ),
    ],
}


class MultiModelStrategy:
    """多模型策略器"""

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.knowledge_base = MODEL_KNOWLEDGE_BASE

    async def analyze_problem(
        self,
        problem_description: str,
        data_description: Optional[str] = None,
    ) -> Tuple[ProblemCategory, List[DataCharacteristic]]:
        """
        分析问题类型和数据特征

        Args:
            problem_description: 问题描述
            data_description: 数据描述

        Returns:
            (问题类型, 数据特征列表)
        """
        prompt = f"""分析以下数学建模问题的类型和数据特征：

## 问题描述
{problem_description}

## 数据描述
{data_description or "未提供"}

请以JSON格式返回：
{{
    "problem_category": "optimization/prediction/classification/clustering/evaluation/scheduling/path_planning/resource_allocation/dynamic_system/game_theory",
    "data_characteristics": ["time_series", "cross_sectional", "panel", "spatial", "network", "high_dimensional", "sparse", "imbalanced"],
    "reasoning": "分析理由"
}}"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，擅长分析问题类型和数据特征。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            run_id=self.run_id,
            agent_id="model_strategy",
        )

        try:
            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response.content[json_start:json_end])

                try:
                    category = ProblemCategory(
                        data.get("problem_category", "prediction")
                    )
                except ValueError:
                    category = ProblemCategory.PREDICTION

                characteristics = []
                for char in data.get("data_characteristics", []):
                    try:
                        characteristics.append(DataCharacteristic(char))
                    except ValueError:
                        continue

                return category, characteristics
        except json.JSONDecodeError:
            logger.warning("Failed to parse problem analysis")

        return ProblemCategory.PREDICTION, []

    def get_model_recommendations(
        self,
        problem_category: ProblemCategory,
        data_characteristics: List[DataCharacteristic],
        complexity_preference: Optional[ComplexityLevel] = None,
    ) -> List[ModelInfo]:
        """
        获取模型推荐

        Args:
            problem_category: 问题类型
            data_characteristics: 数据特征
            complexity_preference: 复杂度偏好

        Returns:
            推荐的模型列表
        """
        category_key = problem_category.value
        models = self.knowledge_base.get(category_key, [])

        if not models:
            # 降级到通用预测模型
            models = self.knowledge_base.get("prediction", [])

        # 根据复杂度偏好筛选
        if complexity_preference:
            filtered = [m for m in models if m.complexity == complexity_preference]
            if filtered:
                models = filtered

        return models

    async def generate_multi_model_plan(
        self,
        problem_description: str,
        data_description: Optional[str] = None,
        max_models: int = 5,
    ) -> MultiModelPlan:
        """
        生成多模型策略计划

        Args:
            problem_description: 问题描述
            data_description: 数据描述
            max_models: 最大模型数量

        Returns:
            多模型计划
        """
        # 1. 分析问题
        category, characteristics = await self.analyze_problem(
            problem_description, data_description
        )

        # 2. 获取模型推荐
        all_models = self.get_model_recommendations(category, characteristics)

        # 3. 按复杂度分组
        simple_models = [m for m in all_models if m.complexity == "simple"]
        moderate_models = [m for m in all_models if m.complexity == "moderate"]
        complex_models = [m for m in all_models if m.complexity == "complex"]

        # 4. 选择基线模型（最简单的）
        baseline = self._create_recommendation(
            simple_models[0] if simple_models else all_models[0],
            "作为基线模型，提供性能下限参考",
        )

        # 5. 选择改进模型
        improvements: List[ModelRecommendation] = []
        for model in moderate_models[:2]:
            improvements.append(
                self._create_recommendation(model, "在基线基础上提升性能")
            )

        # 6. 选择创新变体
        innovations: List[ModelRecommendation] = []
        for model in complex_models[:1]:
            innovations.append(self._create_recommendation(model, "探索更高性能上限"))

        # 7. 生成对比策略
        comparison_strategy = await self._generate_comparison_strategy(
            baseline, improvements, innovations, category
        )

        # 8. 确定评估指标
        evaluation_metrics = self._get_evaluation_metrics(category)

        return MultiModelPlan(
            problem_id=self.run_id,
            baseline=baseline,
            improvements=improvements,
            innovations=innovations,
            comparison_strategy=comparison_strategy,
            evaluation_metrics=evaluation_metrics,
            expected_timeline={
                "baseline": 1.0,
                "improvements": 2.0,
                "innovations": 3.0,
                "comparison": 1.0,
            },
            fallback_plan="若复杂模型效果不佳，回退至基线模型并分析原因",
        )

    def _create_recommendation(
        self, model: ModelInfo, rationale_prefix: str
    ) -> ModelRecommendation:
        """创建模型推荐"""
        return ModelRecommendation(
            model_id=model.id,
            name=model.name,
            category=model.category,
            complexity=model.complexity,
            rationale=f"{rationale_prefix}。{model.description}",
            expected_performance={},
            implementation_complexity=model.python_implementation,
            data_requirements=model.data_requirements,
            key_parameters=model.key_parameters,
            validation_methods=model.validation_methods,
            common_pitfalls=model.disadvantages,
        )

    async def _generate_comparison_strategy(
        self,
        baseline: ModelRecommendation,
        improvements: List[ModelRecommendation],
        innovations: List[ModelRecommendation],
        category: ProblemCategory,
    ) -> str:
        """生成模型对比策略"""
        all_models = [baseline] + improvements + innovations
        model_names = [m.name for m in all_models]

        prompt = f"""为以下模型生成对比分析策略：

问题类型: {category.value}
模型列表: {", ".join(model_names)}

请生成一段简洁的对比策略描述（100字以内），包括：
1. 对比维度
2. 对比方法
3. 最终选择标准"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，擅长设计模型对比方案。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            run_id=self.run_id,
            agent_id="model_strategy",
        )

        return response.content.strip()[:300]

    def _get_evaluation_metrics(self, category: ProblemCategory) -> List[str]:
        """根据问题类型获取评估指标"""
        metrics_map: Dict[ProblemCategory, List[str]] = {
            ProblemCategory.OPTIMIZATION: [
                "目标函数值",
                "约束满足程度",
                "求解时间",
                "解的稳定性",
            ],
            ProblemCategory.PREDICTION: [
                "RMSE",
                "MAE",
                "R²",
                "MAPE",
            ],
            ProblemCategory.CLASSIFICATION: [
                "准确率",
                "精确率",
                "召回率",
                "F1分数",
                "AUC-ROC",
            ],
            ProblemCategory.CLUSTERING: [
                "轮廓系数",
                "CH指数",
                "DB指数",
            ],
            ProblemCategory.EVALUATION: [
                "区分度",
                "一致性",
                "稳定性",
            ],
        }

        return metrics_map.get(category, ["准确性", "稳定性", "可解释性"])

    def format_plan_for_paper(self, plan: MultiModelPlan) -> str:
        """将模型计划格式化为论文格式"""
        lines: List[str] = []

        lines.append("## 模型建立\n")

        # 基线模型
        lines.append("### 基线模型\n")
        lines.append(f"**{plan.baseline.name}**\n")
        lines.append(f"{plan.baseline.rationale}\n")

        # 改进模型
        if plan.improvements:
            lines.append("\n### 模型改进\n")
            for i, model in enumerate(plan.improvements, 1):
                lines.append(f"**改进方案{i}: {model.name}**\n")
                lines.append(f"{model.rationale}\n")

        # 创新变体
        if plan.innovations:
            lines.append("\n### 创新拓展\n")
            for model in plan.innovations:
                lines.append(f"**{model.name}**\n")
                lines.append(f"{model.rationale}\n")

        # 对比策略
        lines.append("\n### 模型对比策略\n")
        lines.append(f"{plan.comparison_strategy}\n")

        # 评估指标
        lines.append("\n### 评估指标\n")
        lines.append(
            f"采用以下指标评估模型性能: {', '.join(plan.evaluation_metrics)}\n"
        )

        return "\n".join(lines)


# 便捷函数
async def generate_model_plan(
    problem_description: str,
    data_description: Optional[str] = None,
    run_id: Optional[str] = None,
) -> MultiModelPlan:
    """
    便捷函数：生成多模型策略计划

    Args:
        problem_description: 问题描述
        data_description: 数据描述
        run_id: 运行ID

    Returns:
        多模型计划
    """
    strategy = MultiModelStrategy(run_id=run_id)
    return await strategy.generate_multi_model_plan(
        problem_description=problem_description,
        data_description=data_description,
    )
