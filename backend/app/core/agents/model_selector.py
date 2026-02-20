"""
模型选择专家 - 智能推荐最适合的数学模型
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.core.agents.problem_analyzer import ProblemAnalysis


@dataclass
class ModelRecommendation:
    """模型推荐结果"""
    primary_model: Dict[str, Any]
    alternative_models: List[Dict[str, Any]]
    comparison_matrix: Dict[str, Any]
    selection_justification: str
    parameter_suggestions: Dict[str, Any]
    risks_and_mitigations: List[Dict[str, str]]


class ModelSelector(ExpertAgent):
    """模型选择专家Agent"""

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.MODEL_SELECTOR,
            max_reflections=2,
            max_chat_turns=10
        )

        # 模型知识库
        self.model_knowledge_base = self._load_model_knowledge()

    def get_system_prompt(self) -> str:
        return """
# 🎯 模型选择专家

你是一位资深的数学建模模型选择专家，精通各种数学模型的理论基础、适用场景、优缺点对比。

## 📋 核心职责
1. **智能模型推荐** - 基于问题特征推荐最适合的模型
2. **多方案对比** - 提供多个备选方案及详细对比
3. **适用性评估** - 评估每个模型的适用性和复杂度
4. **参数优化建议** - 提供关键参数的优化建议
5. **风险评估** - 识别使用风险和缓解措施

## 🧠 模型知识库（来自统一知识库，涵盖 30+ 模型）

### 优化模型
- **线性规划**: 目标函数和约束都是线性的优化问题
- **整数规划**: 决策变量要求为整数的优化问题
- **非线性规划**: 目标函数或约束包含非线性项
- **动态规划**: 多阶段决策问题的优化
- **多目标优化**: 同时优化多个冲突目标的问题

### 预测模型
- **时间序列**: ARIMA、指数平滑、LSTM
- **回归预测**: 线性回归、多项式回归、SVR、随机森林
- **神经网络**: MLP、CNN、RNN、Transformer
- **集成方法**: Random Forest、XGBoost、LightGBM

### 分类模型
- **传统分类**: 逻辑回归、决策树、SVM、KNN
- **集成分类**: 随机森林、AdaBoost、XGBoost
- **深度学习**: CNN、RNN、Transformer
- **概率分类**: 朴素贝叶斯、贝叶斯网络

### 聚类模型
- **划分聚类**: K-means、K-medoids
- **层次聚类**: AGNES、DIANA
- **密度聚类**: DBSCAN、OPTICS
- **网格聚类**: STING、CLIQUE

### 评价模型
- **层次分析法(AHP)**: 多准则决策分析
- **TOPSIS**: 逼近理想解排序法
- **熵权法**: 客观赋权方法
- **模糊综合评价**: 处理不确定性评价

### 动态规划模型
- **背包问题**: 资源分配、容量约束优化、装载问题
- **最短路径**: 路径规划、网络优化、物流配送（Dijkstra、Floyd）
- **序列决策**: 多阶段决策、库存管理、生产调度

### 博弈论模型
- **纳什均衡**: 竞争博弈、市场策略、多方决策
- **Stackelberg博弈**: 领导者-跟随者决策、定价策略、供应链博弈
- **演化博弈**: 群体行为演化、策略扩散、合作机制

### 随机过程模型
- **排队论**: 服务系统建模、等待时间分析、容量规划（M/M/1、M/M/c）
- **马尔可夫链**: 状态转移概率建模、长期稳态分析、信用评级
- **蒙特卡洛模拟**: 风险评估、不确定性量化、随机优化

## 📊 模型评估维度

### 1. 问题匹配度
- 模型是否适合问题类型
- 模型假设是否满足
- 数据要求是否匹配

### 2. 性能表现
- 准确性预测
- 计算复杂度
- 稳定性
- 可解释性

### 3. 实用性
- 实现难度
- 调参复杂度
- 计算资源需求
- 结果可解释性

### 4. 创新性
- 方法新颖性
- 思路独特性
- 改进空间

## 📝 输出要求

### 1. 模型推荐JSON格式
```json
{
    "primary_model": {
        "name": "主要推荐模型名称",
        "category": "模型类别",
        "description": "模型简要描述",
        "advantages": ["优势1", "优势2"],
        "disadvantages": ["劣势1", "劣势2"],
        "applicability": "适用性分析",
        "complexity": "复杂度等级（低/中/高）",
        "data_requirements": {
            "sample_size": "样本量要求",
            "data_type": "数据类型要求",
            "data_quality": "数据质量要求"
        },
        "expected_performance": "预期性能"
    },
    "alternative_models": [
        {
            "name": "备选模型名称",
            "category": "模型类别",
            "advantages": ["优势1", "优势2"],
            "disadvantages": ["劣势1", "劣势2"],
            "when_to_use": "使用场景",
            "complexity": "复杂度等级"
        }
    ],
    "comparison_matrix": {
        "models": ["模型1", "模型2", "模型3"],
        "criteria": ["准确性", "复杂度", "可解释性", "实现难度"],
        "scores": [
            [0.9, 0.7, 0.8, 0.6],
            [0.8, 0.8, 0.9, 0.7],
            [0.7, 0.6, 0.9, 0.8]
        ]
    },
    "selection_justification": "选择主模型的理由和依据",
    "parameter_suggestions": {
        "关键参数1": {
            "suggested_value": "建议值",
            "tuning_range": "调优范围",
            "impact": "参数影响"
        },
        "关键参数2": {
            "suggested_value": "建议值",
            "tuning_range": "调优范围",
            "impact": "参数影响"
        }
    },
    "risks_and_mitigations": [
        {
            "risk": "风险描述",
            "probability": "发生概率（高/中/低）",
            "impact": "影响程度（高/中/低）",
            "mitigation": "缓解措施"
        }
    ]
}
```

### 2. 选择建议报告
- 模型选择逻辑
- 关键决策因素
- 实施建议

## 🚀 执行流程
1. 分析问题特征
2. 检索相关知识库
3. 生成候选模型列表
4. 多维度对比评估
5. 选择最优模型
6. 提供备选方案
7. 自我反思优化

## ⚠️ 注意事项
- 模型推荐要有充分的理由
- 考虑实际实现的可行性
- 平衡性能和复杂性
- 提供足够的备选方案
- 识别潜在风险并提供缓解措施

现在开始为给定的数学建模问题选择最优模型！
        """

    def _load_model_knowledge(self) -> Dict[str, Any]:
        """从统一知识库加载模型知识"""
        try:
            from app.core.knowledge_base import knowledge_base

            # 将统一知识库的 ModelKnowledge 对象转换为 dict 格式
            # 按类别分组以保持与原有接口兼容
            categorized: Dict[str, Dict[str, Any]] = {}
            for model_key, model in knowledge_base.models.items():
                category_key = model.category.lower().replace("/", "_")
                group_key = f"{category_key}_models"
                if group_key not in categorized:
                    categorized[group_key] = {}
                categorized[group_key][model_key] = {
                    "name": model.name,
                    "category": model.category,
                    "complexity": model.complexity,
                    "data_requirements": model.data_requirements,
                    "applicable_problems": model.applicable_problems,
                }
            return categorized
        except ImportError:
            from app.utils.log_util import logger
            logger.warning("统一知识库不可用，使用空知识库")
            return {}

    async def execute(self, problem_analysis: ProblemAnalysis) -> ModelRecommendation:
        """执行模型选择"""
        await self.send_message("🎯 开始智能模型选择...", "info")
        self.state.current_stage = "selecting"

        # 1. 分析问题特征
        problem_features = await self._analyze_problem_features(problem_analysis)
        await self.send_message(f"📊 问题类型: {problem_analysis.problem_type}", "info")

        # 2. 生成候选模型
        candidate_models = await self._generate_candidate_models(problem_features)
        await self.send_message(f"🔍 找到 {len(candidate_models)} 个候选模型", "info")

        # 3. 多维度评估
        evaluation_results = await self._evaluate_models(candidate_models, problem_features)
        await self.send_message("⚖️ 完成模型评估", "info")

        # 4. 选择最优模型
        selection_result = await self._select_optimal_model(evaluation_results)
        await self.send_message(f"✅ 选择最优模型: {selection_result['primary_model']['name']}", "success")

        # 5. 生成完整推荐报告
        recommendation = await self._generate_recommendation(selection_result, problem_analysis)

        # 6. 自我反思
        await self.reflect(
            json.dumps(recommendation, ensure_ascii=False, indent=2),
            "智能选择最适合的数学模型"
        )

        # 7. 质量评估
        await self.evaluate_quality(
            json.dumps(recommendation, ensure_ascii=False, indent=2),
            "模型选择要基于充分的分析和对比"
        )

        await self.send_message("🎉 模型选择完成！", "success")
        self.state.current_stage = "completed"

        return ModelRecommendation(**recommendation)

    async def _analyze_problem_features(self, problem_analysis: ProblemAnalysis) -> Dict[str, Any]:
        """分析问题特征"""
        feature_prompt = f"""
        基于以下问题分析，提取关键特征用于模型选择：

        问题类型: {problem_analysis.problem_type}
        难度等级: {problem_analysis.difficulty_level}
        数据特征: {problem_analysis.data_characteristics}
        建模目标: {problem_analysis.modeling_objectives}
        约束条件: {problem_analysis.constraints}
        关键挑战: {problem_analysis.key_challenges}

        请提取以下特征：
        1. 问题本质特征
        2. 数据特点
        3. 性能要求
        4. 实现约束
        5. 风险考虑

        以JSON格式输出：
        {{
            "essential_features": ["特征1", "特征2"],
            "data_requirements": {{
                "sample_size": "样本量需求",
                "data_quality": "数据质量要求",
                "data_types": ["数据类型1", "数据类型2"]
            }},
            "performance_priorities": ["准确性", "效率", "可解释性"],
            "implementation_constraints": ["约束1", "约束2"],
            "risk_factors": ["风险1", "风险2"]
        }}
        """

        features = await self.think(feature_prompt, use_tools=False)

        try:
            return json.loads(
                features.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "essential_features": [problem_analysis.problem_type],
                "data_requirements": {"sample_size": "中等", "data_quality": "中等", "data_types": ["数值型"]},
                "performance_priorities": ["准确性", "效率"],
                "implementation_constraints": [],
                "risk_factors": []
            }

    async def _generate_candidate_models(self, problem_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成候选模型列表"""
        problem_type = problem_features.get("essential_features", ["通用"])[0]

        # 基于问题类型筛选模型
        candidates = []
        problem_type_lower = problem_type.lower()

        for category, models in self.model_knowledge_base.items():
            for model_key, model_info in models.items():
                # 简单的匹配逻辑
                if self._is_model_suitable(model_info, problem_type_lower):
                    candidates.append(model_info)

        # 如果没有找到合适的模型，添加通用模型
        if not candidates:
            # 无候选时从知识库取前两个模型作为通用降级
            all_models = []
            for category, models in self.model_knowledge_base.items():
                all_models.extend(models.values())
            candidates = all_models[:2] if all_models else [
                {"name": "线性回归", "category": "预测", "complexity": "低",
                 "data_requirements": {"sample_size": "中", "data_type": "数值型"},
                 "applicable_problems": ["预测", "回归分析"]}
            ]

        return candidates[:3]  # 返回最多3个候选模型

    def _is_model_suitable(self, model_info: Dict[str, Any], problem_type: str) -> bool:
        """判断模型是否适合问题类型"""
        # 类别关键词映射（中文问题类型 -> 模型类别匹配词）
        category_keywords = {
            "优化": ["optimization", "planning", "优化"],
            "预测": ["prediction", "forecasting", "time_series", "regression", "预测"],
            "分类": ["classification", "decision_tree", "分类"],
            "聚类": ["clustering", "聚类"],
            "评价": ["evaluation", "评价"],
            "动态规划": ["dynamic_programming", "动态规划"],
            "博弈": ["game_theory", "博弈论", "博弈"],
            "随机过程": ["stochastic", "随机过程", "随机"],
            "排队": ["queueing", "排队论", "排队"],
            "马尔可夫": ["markov", "马尔可夫"],
        }

        # 问题描述关键词映射（问题描述中的关键词 -> 模型类别）
        problem_keywords = {
            "动态规划": [
                "背包", "最短路", "路径规划", "多阶段", "状态转移",
                "递推", "序列决策", "库存管理", "调度", "装载",
                "knapsack", "shortest path", "dynamic programming",
                "DP", "阶段决策",
            ],
            "博弈": [
                "博弈", "均衡", "纳什", "对抗", "竞争策略",
                "主从", "领导者", "跟随者", "Stackelberg",
                "演化", "复制动态", "零和", "非合作",
                "game theory", "Nash", "evolutionary",
                "支付矩阵", "策略选择",
            ],
            "随机过程": [
                "排队", "等待时间", "服务系统", "到达率", "服务率",
                "M/M/1", "队列", "吞吐量", "容量规划",
                "马尔可夫", "状态转移概率", "转移矩阵", "稳态分布",
                "Markov", "平稳分布", "吸收态", "随机过程",
                "蒙特卡洛", "Monte Carlo", "随机模拟", "仿真",
                "不确定性", "风险评估", "概率估计",
                "queueing", "queue", "stochastic",
            ],
        }

        model_category = model_info.get("category", "").lower()
        applicable_problems = model_info.get("applicable_problems", [])
        model_specific_keywords = model_info.get("keywords", [])

        # 1. 检查类别匹配
        for key, values in category_keywords.items():
            if key in problem_type:
                if any(value in model_category for value in values):
                    return True

        # 2. 检查模型自带的关键词列表匹配
        if model_specific_keywords:
            if any(kw.lower() in problem_type for kw in model_specific_keywords):
                return True

        # 3. 检查问题描述关键词匹配（将问题描述映射到模型类别）
        for category, kw_list in problem_keywords.items():
            if any(kw.lower() in problem_type for kw in kw_list):
                if category in model_category or any(
                    category in cat for cat in [model_category]
                ):
                    return True

        # 4. 检查适用问题匹配
        return any(
            key in " ".join(applicable_problems).lower()
            for key in problem_type.split()
        )

    async def _evaluate_models(self, candidates: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """评估候选模型"""
        evaluation_prompt = f"""
        请评估以下候选模型：

        候选模型：{json.dumps(candidates, ensure_ascii=False)}

        问题特征：{json.dumps(features, ensure_ascii=False)}

        请从以下维度评估（0-1分）：
        - 问题匹配度
        - 预期性能
        - 实现难度
        - 可解释性
        - 稳定性

        以JSON格式输出：
        {{
            "evaluations": [
                {{
                    "model_name": "模型名称",
                    "scores": {{
                        "match_score": 0.0,
                        "performance_score": 0.0,
                        "implementation_score": 0.0,
                        "interpretability_score": 0.0,
                        "stability_score": 0.0
                    }},
                    "total_score": 0.0,
                    "analysis": "分析说明"
                }}
            ]
        }}
        """

        evaluation = await self.think(evaluation_prompt, use_tools=False)

        try:
            return json.loads(
                evaluation.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            # 返回默认评估
            return {
                "evaluations": [
                    {
                        "model_name": candidate.get("name", "未知模型"),
                        "scores": {
                            "match_score": 0.7,
                            "performance_score": 0.7,
                            "implementation_score": 0.7,
                            "interpretability_score": 0.7,
                            "stability_score": 0.7
                        },
                        "total_score": 0.7,
                        "analysis": "默认评估"
                    }
                    for candidate in candidates
                ]
            }

    async def _select_optimal_model(self, evaluation_results: Dict[str, Any]) -> Dict[str, Any]:
        """选择最优模型"""
        evaluations = evaluation_results.get("evaluations", [])

        if not evaluations:
            return {"primary_model": {}, "alternatives": []}

        # 按总分排序
        evaluations.sort(key=lambda x: x.get("total_score", 0), reverse=True)

        primary_model = evaluations[0]
        alternatives = evaluations[1:]

        return {
            "primary_model": primary_model,
            "alternatives": alternatives
        }

    async def _generate_recommendation(
        self, selection_result: Dict[str, Any], problem_analysis: ProblemAnalysis
    ) -> Dict[str, Any]:
        """生成完整的推荐报告"""
        recommendation = {
            "primary_model": selection_result.get("primary_model", {}),
            "alternative_models": selection_result.get("alternatives", []),
            "comparison_matrix": await self._generate_comparison_matrix(selection_result),
            "selection_justification": await self._generate_justification(
                selection_result, problem_analysis
            ),
            "parameter_suggestions": await self._generate_parameter_suggestions(
                selection_result.get("primary_model", {})
            ),
            "risks_and_mitigations": await self._analyze_risks(
                selection_result.get("primary_model", {}), problem_analysis
            )
        }

        return recommendation

    async def _generate_comparison_matrix(self, selection_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成对比矩阵"""
        models = []
        scores = []

        primary = selection_result.get("primary_model", {})
        alternatives = selection_result.get("alternatives", [])

        all_models = [primary] + alternatives

        for model in all_models:
            models.append(model.get("model_name", "未知模型"))
            model_scores = model.get("scores", {})
            scores.append([
                model_scores.get("match_score", 0.5),
                model_scores.get("performance_score", 0.5),
                model_scores.get("interpretability_score", 0.5),
                model_scores.get("implementation_score", 0.5)
            ])

        return {
            "models": models,
            "criteria": ["问题匹配度", "预期性能", "可解释性", "实现难度"],
            "scores": scores
        }

    async def _generate_justification(
        self, selection_result: Dict[str, Any], problem_analysis: ProblemAnalysis
    ) -> str:
        """生成选择理由"""
        primary_model = selection_result.get("primary_model", {})
        justification_prompt = f"""
        基于以下信息，生成模型选择的详细理由：

        选择的主模型：{json.dumps(primary_model, ensure_ascii=False)}
        问题分析：{problem_analysis.problem_type}
        难度等级：{problem_analysis.difficulty_level}

        请生成200字以内的选择理由，包括：
        1. 为什么选择这个模型
        2. 这个模型如何满足问题需求
        3. 相比其他模型的优势
        """

        return await self.think(justification_prompt, use_tools=False)

    async def _generate_parameter_suggestions(self, primary_model: Dict[str, Any]) -> Dict[str, Any]:
        """生成参数建议"""
        model_name = primary_model.get("model_name", "未知模型")

        suggestions = {
            "linear_programming": {
                "求解器": {"suggested_value": "scipy.optimize.linprog", "tuning_range": "", "impact": "选择合适的求解器"}
            },
            "random_forest": {
                "n_estimators": {"suggested_value": "100", "tuning_range": "50-200", "impact": "控制树的数量"},
                "max_depth": {"suggested_value": "None", "tuning_range": "5-20", "impact": "控制树的深度"}
            },
            "svm": {
                "C": {"suggested_value": "1.0", "tuning_range": "0.1-10", "impact": "控制惩罚系数"},
                "kernel": {"suggested_value": "rbf", "tuning_range": "linear, rbf, poly", "impact": "选择核函数"}
            }
        }

        return suggestions.get(model_name.lower(), {})

    async def _analyze_risks(
        self, primary_model: Dict[str, Any], problem_analysis: ProblemAnalysis
    ) -> List[Dict[str, str]]:
        """分析风险和缓解措施"""
        risk_prompt = f"""
        分析使用以下模型的潜在风险：

        模型：{json.dumps(primary_model, ensure_ascii=False)}
        问题难度：{problem_analysis.difficulty_level}
        关键挑战：{problem_analysis.key_challenges}

        请识别2-3个主要风险，并提供缓解措施：
        {{
            "risks": [
                {{
                    "risk": "风险描述",
                    "probability": "高/中/低",
                    "impact": "高/中/低",
                    "mitigation": "缓解措施"
                }}
            ]
        }}
        """

        try:
            risk_analysis = await self.think(risk_prompt, use_tools=False)
            result = json.loads(
                risk_analysis.replace("```json", "").replace("```", "").strip()
            )
            return result.get("risks", [])
        except (json.JSONDecodeError, KeyError, TypeError):
            return [
                {
                    "risk": "模型过拟合",
                    "probability": "中",
                    "impact": "中",
                    "mitigation": "使用交叉验证和正则化"
                }
            ]

    def get_recommendation_summary(self) -> Dict[str, Any]:
        """获取推荐摘要"""
        summary = self.get_summary()
        if self.state.quality_metrics:
            summary["quality_level"] = self.state.quality_metrics.get_level().name
        return summary