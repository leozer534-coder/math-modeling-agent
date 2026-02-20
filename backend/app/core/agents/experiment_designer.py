"""
实验设计专家 - 设计科学的实验方案和验证策略
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.core.agents.model_selector import ModelRecommendation
from app.core.agents.problem_analyzer import ProblemAnalysis


@dataclass
class ExperimentPlan:
    """实验设计方案"""
    experimental_design: Dict[str, Any]
    validation_strategy: Dict[str, Any]
    data_splitting: Dict[str, Any]
    evaluation_metrics: List[Dict[str, Any]]
    experiment_steps: List[Dict[str, Any]]
    quality_assurance: Dict[str, Any]
    timeline_and_resources: Dict[str, Any]


class ExperimentDesigner(ExpertAgent):
    """实验设计专家Agent"""

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.EXPERIMENT_DESIGNER,
            max_reflections=2,
            max_chat_turns=12
        )

        # 实验设计知识库
        self.experiment_knowledge = self._load_experiment_knowledge()

    def get_system_prompt(self) -> str:
        return """
# 🧪 实验设计专家

你是一位资深的数学建模实验设计专家，精通各种实验设计方法、验证策略和评价指标体系。

## 📋 核心职责
1. **科学实验设计** - 设计完整的实验流程和验证方案
2. **数据分割策略** - 制定合理的数据训练/测试/验证分割方案
3. **评价指标选择** - 选择最适合的评价指标和评价方法
4. **验证策略制定** - 制定交叉验证、鲁棒性验证等策略
5. **质量控制** - 设计质量保证和改进机制

## 🧠 实验设计知识

### 数据分割策略
- **简单分割**: 70%训练, 30%测试
- **交叉验证**: K折交叉验证 (K=5,10)
- **时间序列分割**: 基于时间的分割，避免数据泄露
- **分层抽样**: 保持类别比例的分割
- **留出验证**: 训练/验证/测试三段分割

### 验证方法
- **K折交叉验证**: 减少方差，充分利用数据
- **留一交叉验证**: 适用于小数据集
- **分层K折**: 保持类别分布
- **时间序列交叉验证**: 考虑时间顺序
- **蒙特卡洛交叉验证**: 随机多次分割

### 评价指标体系

#### 回归问题
- **准确度指标**: MAE, MSE, RMSE, MAPE
- **拟合优度**: R², 调整R²
- **相对误差**: MRE, MAPE
- **残差分析**: 残差图, Q-Q图

#### 分类问题
- **准确率**: Accuracy, Precision, Recall, F1
- **混淆矩阵**: TP, TN, FP, FN
- **概率指标**: AUC-ROC, AUC-PR
- **多分类指标**: Macro-F1, Micro-F1, Weighted-F1

#### 聚类问题
- **内部指标**: 轮廓系数, Calinski-Harabasz指数
- **外部指标**: 调整互信息, 同质性, 完整性
- **相对指标**: Davies-Bouldin指数, Gap统计

#### 优化问题
- **目标函数值**: 最优值, 近似比
- **收敛性**: 迭代次数, 收敛速度
- **稳定性**: 解的稳定性, 敏感性
- **计算效率**: CPU时间, 内存占用

### 实验设计原则
1. **科学性** - 实验设计基于科学方法论
2. **可重复性** - 实验结果可重复验证
3. **可比性** - 不同方法之间可比较
4. **完整性** - 涵盖所有重要方面
5. **可行性** - 在约束条件下可实施

## 📝 输出要求

### 1. 实验设计JSON格式
```json
{
    "experimental_design": {
        "design_type": "实验设计类型",
        "methodology": "实验方法描述",
        "hypotheses": [
            {
                "hypothesis": "假设陈述",
                "test_method": "检验方法",
                "expected_outcome": "预期结果"
            }
        ]
    },
    "validation_strategy": {
        "primary_method": "主要验证方法",
        "secondary_methods": ["备选验证方法1", "备选验证方法2"],
        "robustness_checks": [
            {
                "check_type": "鲁棒性检查类型",
                "description": "检查描述",
                "success_criteria": "成功标准"
            }
        ],
        "sensitivity_analysis": {
            "parameters": ["敏感参数1", "敏感参数2"],
            "method": "敏感性分析方法",
            "expected_impact": "预期影响"
        }
    },
    "data_splitting": {
        "strategy": "分割策略",
        "train_ratio": 0.7,
        "validation_ratio": 0.15,
        "test_ratio": 0.15,
        "split_method": "分割方法",
        "stratification": "是否分层",
        "time_splitting": "时间分割说明"
    },
    "evaluation_metrics": [
        {
            "metric_name": "指标名称",
            "metric_type": "指标类型",
            "description": "指标描述",
            "formula": "计算公式",
            "interpretation": "结果解释",
            "target_value": "目标值",
            "weight": "权重"
        }
    ],
    "experiment_steps": [
        {
            "step_number": 1,
            "step_name": "步骤名称",
            "description": "步骤描述",
            "inputs": ["输入1", "输入2"],
            "outputs": ["输出1", "输出2"],
            "success_criteria": "成功标准",
            "expected_duration": "预期时间",
            "risks": ["风险1", "风险2"]
        }
    ],
    "quality_assurance": {
        "data_quality_checks": [
            {
                "check_type": "数据质量检查",
                "method": "检查方法",
                "threshold": "阈值标准"
            }
        ],
        "model_validation_checks": [
            {
                "check_type": "模型验证检查",
                "method": "检查方法",
                "pass_criteria": "通过标准"
            }
        ],
        "result_verification": "结果验证方法"
    },
    "timeline_and_resources": {
        "estimated_duration": "预估总时间",
        "key_milestones": [
            {
                "milestone": "里程碑",
                "expected_completion": "预期完成时间",
                "deliverables": ["交付物1", "交付物2"]
            }
        ],
        "resource_requirements": {
            "computational_resources": "计算资源需求",
            "software_requirements": ["软件1", "软件2"],
            "human_expertise": "所需专业技能"
        }
    }
}
```

### 2. 实施建议报告
- 实验执行要点
- 关键成功因素
- 潜在问题及解决方案

## 🚀 执行流程
1. 分析问题和模型需求
2. 设计核心实验方案
3. 制定验证策略
4. 选择评价指标
5. 规划实验步骤
6. 设计质量保证
7. 估算资源和时间
8. 自我反思优化

## ⚠️ 注意事项
- 实验设计要科学严谨
- 考虑数据泄露问题
- 选择合适的评价指标
- 制定可行的验证策略
- 识别并规避潜在风险

现在开始设计科学的实验方案！
        """

    def _load_experiment_knowledge(self) -> Dict[str, Any]:
        """加载实验设计知识库"""
        return {
            "data_splitting": {
                "time_series": {
                    "name": "时间序列分割",
                    "description": "按时间顺序分割，避免未来信息泄露",
                    "use_case": "时间序列预测、滚动预测"
                },
                "stratified": {
                    "name": "分层抽样分割",
                    "description": "保持类别比例的随机分割",
                    "use_case": "分类问题、不均衡数据"
                },
                "k_fold": {
                    "name": "K折交叉验证",
                    "description": "将数据分为K份，轮流作为验证集",
                    "use_case": "模型选择、超参数调优"
                }
            },
            "evaluation_metrics": {
                "regression": [
                    {"name": "MAE", "description": "平均绝对误差", "range": "0-∞"},
                    {"name": "RMSE", "description": "均方根误差", "range": "0-∞"},
                    {"name": "R²", "description": "决定系数", "range": "0-1"},
                    {"name": "MAPE", "description": "平均绝对百分比误差", "range": "0-100%"}
                ],
                "classification": [
                    {"name": "Accuracy", "description": "准确率", "range": "0-1"},
                    {"name": "Precision", "description": "精确率", "range": "0-1"},
                    {"name": "Recall", "description": "召回率", "range": "0-1"},
                    {"name": "F1-Score", "description": "F1分数", "range": "0-1"},
                    {"name": "AUC-ROC", "description": "ROC曲线下面积", "range": "0-1"}
                ],
                "clustering": [
                    {"name": "Silhouette Score", "description": "轮廓系数", "range": "-1-1"},
                    {"name": "Davies-Bouldin", "description": "DB指数", "range": "0-∞"},
                    {"name": "Calinski-Harabasz", "description": "CH指数", "range": "0-∞"}
                ]
            }
        }

    async def execute(
        self,
        problem_analysis: ProblemAnalysis,
        model_recommendation: ModelRecommendation
    ) -> ExperimentPlan:
        """执行实验设计"""
        await self.send_message("🧪 开始设计科学实验方案...", "info")
        self.state.current_stage = "designing"

        # 1. 分析实验需求
        experiment_requirements = await self._analyze_experiment_requirements(
            problem_analysis, model_recommendation
        )
        await self.send_message("📋 分析实验需求完成", "info")

        # 2. 设计核心实验方案
        experimental_design = await self._design_experimental_approach(experiment_requirements)
        await self.send_message("🎯 核心实验方案设计完成", "info")

        # 3. 制定验证策略
        validation_strategy = await self._design_validation_strategy(
            experimental_design, model_recommendation
        )
        await self.send_message("🔍 验证策略制定完成", "info")

        # 4. 设计数据分割方案
        data_splitting = await self._design_data_splitting(
            problem_analysis, experimental_design
        )
        await self.send_message("📊 数据分割方案设计完成", "info")

        # 5. 选择评价指标
        evaluation_metrics = await self._select_evaluation_metrics(
            problem_analysis, model_recommendation
        )
        await self.send_message("📈 评价指标选择完成", "info")

        # 6. 规划实验步骤
        experiment_steps = await self._plan_experiment_steps(
            experimental_design, validation_strategy
        )
        await self.send_message("📝 实验步骤规划完成", "info")

        # 7. 设计质量保证
        quality_assurance = await self._design_quality_assurance(experimental_design)
        await self.send_message("✅ 质量保证设计完成", "info")

        # 8. 估算资源和时间
        timeline_resources = await self._estimate_timeline_and_resources(experiment_steps)
        await self.send_message("⏰ 资源时间估算完成", "info")

        # 9. 生成完整实验计划
        experiment_plan = ExperimentPlan(
            experimental_design=experimental_design,
            validation_strategy=validation_strategy,
            data_splitting=data_splitting,
            evaluation_metrics=evaluation_metrics,
            experiment_steps=experiment_steps,
            quality_assurance=quality_assurance,
            timeline_and_resources=timeline_resources
        )

        # 10. 自我反思
        await self.reflect(
            json.dumps(experiment_plan.__dict__, ensure_ascii=False, indent=2, default=str),
            "设计科学的实验方案"
        )

        # 11. 质量评估
        await self.evaluate_quality(
            json.dumps(experiment_plan.__dict__, ensure_ascii=False, indent=2, default=str),
            "实验设计要科学、完整、可行"
        )

        await self.send_message("🎉 实验设计完成！", "success")
        self.state.current_stage = "completed"

        return experiment_plan

    async def _analyze_experiment_requirements(
        self, problem_analysis: ProblemAnalysis, model_recommendation: ModelRecommendation
    ) -> Dict[str, Any]:
        """分析实验需求"""
        requirement_prompt = f"""
        基于以下信息分析实验设计需求：

        问题分析：{json.dumps(problem_analysis.__dict__, ensure_ascii=False, default=str)}
        模型推荐：{json.dumps(model_recommendation.__dict__, ensure_ascii=False, default=str)}

        请分析以下需求：
        1. 实验类型和目标
        2. 数据特点和处理需求
        3. 验证的复杂度要求
        4. 评价的精确度要求
        5. 实施的约束条件

        以JSON格式输出：
        {{
            "experiment_type": "实验类型",
            "primary_objectives": ["主要目标1", "主要目标2"],
            "secondary_objectives": ["次要目标1", "次要目标2"],
            "data_characteristics": {{
                "volume": "数据量",
                "quality": "数据质量",
                "distribution": "数据分布",
                "features": "特征特点"
            }},
            "validation_requirements": {{
                "robustness_level": "鲁棒性要求（高/中/低）",
                "generalization_need": "泛化能力需求",
                "stability_requirement": "稳定性要求"
            }},
            "implementation_constraints": {
                "time_limit": "时间限制",
                "computational_resources": "计算资源限制",
                "accuracy_threshold": "准确度阈值"
            }
        }}
        """

        requirements = await self.think(requirement_prompt, use_tools=False)

        try:
            return json.loads(
                requirements.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "experiment_type": "建模验证",
                "primary_objectives": ["验证模型性能", "评估泛化能力"],
                "secondary_objectives": ["分析特征重要性", "确定最优参数"],
                "data_characteristics": {"volume": "中等", "quality": "良好"},
                "validation_requirements": {"robustness_level": "中"},
                "implementation_constraints": {"time_limit": "无"}
            }

    async def _design_experimental_approach(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """设计核心实验方案"""
        design_prompt = f"""
        基于以下实验需求，设计核心实验方案：

        实验需求：{json.dumps(requirements, ensure_ascii=False)}

        请设计：
        1. 实验设计类型和方法论
        2. 主要假设和检验方法
        3. 实验的科学依据

        以JSON格式输出：
        {{
            "design_type": "设计类型",
            "methodology": "方法论描述",
            "hypotheses": [
                {{
                    "hypothesis": "假设陈述",
                    "test_method": "检验方法",
                    "expected_outcome": "预期结果"
                }}
            ]
        }}
        """

        design = await self.think(design_prompt, use_tools=False)

        try:
            return json.loads(
                design.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "design_type": "对照实验",
                "methodology": "对照实验验证模型有效性",
                "hypotheses": [
                    {
                        "hypothesis": "模型能够有效解决问题",
                        "test_method": "统计分析",
                        "expected_outcome": "模型性能显著优于基线"
                    }
                ]
            }

    async def _design_validation_strategy(
        self, experimental_design: Dict[str, Any], model_recommendation: ModelRecommendation
    ) -> Dict[str, Any]:
        """设计验证策略"""
        validation_prompt = f"""
        设计验证策略：

        实验设计：{json.dumps(experimental_design, ensure_ascii=False)}
        模型推荐：{json.dumps(model_recommendation.__dict__, ensure_ascii=False, default=str)}

        请设计：
        1. 主要验证方法
        2. 备选验证方法
        3. 鲁棒性检查
        4. 敏感性分析

        以JSON格式输出：
        {{
            "primary_method": "主要验证方法",
            "secondary_methods": ["备选方法1", "备选方法2"],
            "robustness_checks": [
                {{
                    "check_type": "检查类型",
                    "description": "检查描述",
                    "success_criteria": "成功标准"
                }}
            ],
            "sensitivity_analysis": {{
                "parameters": ["参数1", "参数2"],
                "method": "分析方法",
                "expected_impact": "预期影响"
            }}
        }}
        """

        validation = await self.think(validation_prompt, use_tools=False)

        try:
            return json.loads(
                validation.replace("```json", "").replace("```", "").strip()
            )
        except json.JSONDecodeError:
            return {
                "primary_method": "交叉验证",
                "secondary_methods": ["留出验证", "自助法"],
                "robustness_checks": [
                    {
                        "check_type": "数据扰动测试",
                        "description": "测试模型对数据扰动的稳定性",
                        "success_criteria": "性能变化<5%"
                    }
                ],
                "sensitivity_analysis": {
                    "parameters": ["主要参数"],
                    "method": "参数扰动分析",
                    "expected_impact": "识别关键参数"
                }
            }

    async def _design_data_splitting(
        self, problem_analysis: ProblemAnalysis, experimental_design: Dict[str, Any]
    ) -> Dict[str, Any]:
        """设计数据分割方案"""
        # 根据问题类型选择合适的分割策略
        problem_type = problem_analysis.problem_type.lower()

        if "时间序列" in problem_type or "预测" in problem_type:
            splitting = {
                "strategy": "时间序列分割",
                "train_ratio": 0.7,
                "validation_ratio": 0.15,
                "test_ratio": 0.15,
                "split_method": "按时间顺序",
                "stratification": False,
                "time_splitting": "避免未来信息泄露"
            }
        elif "分类" in problem_type:
            splitting = {
                "strategy": "分层抽样分割",
                "train_ratio": 0.7,
                "validation_ratio": 0.15,
                "test_ratio": 0.15,
                "split_method": "保持类别比例",
                "stratification": True,
                "time_splitting": None
            }
        else:
            splitting = {
                "strategy": "随机分割",
                "train_ratio": 0.7,
                "validation_ratio": 0.15,
                "test_ratio": 0.15,
                "split_method": "完全随机",
                "stratification": False,
                "time_splitting": None
            }

        return splitting

    async def _select_evaluation_metrics(
        self, problem_analysis: ProblemAnalysis, model_recommendation: ModelRecommendation
    ) -> List[Dict[str, Any]]:
        """选择评价指标"""
        problem_type = problem_analysis.problem_type.lower()

        # 根据问题类型选择合适的指标
        if "预测" in problem_type or "回归" in problem_type:
            metrics = [
                {
                    "metric_name": "RMSE",
                    "metric_type": "回归指标",
                    "description": "均方根误差",
                    "formula": "√(Σ(y_pred - y_true)² / n)",
                    "interpretation": "越小越好，表示预测误差小",
                    "target_value": "最小化",
                    "weight": 0.4
                },
                {
                    "metric_name": "MAE",
                    "metric_type": "回归指标",
                    "description": "平均绝对误差",
                    "formula": "Σ|y_pred - y_true| / n",
                    "interpretation": "越小越好，表示预测准确",
                    "target_value": "最小化",
                    "weight": 0.3
                },
                {
                    "metric_name": "R²",
                    "metric_type": "回归指标",
                    "description": "决定系数",
                    "formula": "1 - Σ(y_pred - y_true)² / Σ(y_mean - y_true)²",
                    "interpretation": "越接近1越好，表示模型解释力强",
                    "target_value": "最大化",
                    "weight": 0.3
                }
            ]
        elif "分类" in problem_type:
            metrics = [
                {
                    "metric_name": "Accuracy",
                    "metric_type": "分类指标",
                    "description": "准确率",
                    "formula": "Σ(y_pred = y_true) / n",
                    "interpretation": "越接近1越好，表示分类准确",
                    "target_value": "最大化",
                    "weight": 0.3
                },
                {
                    "metric_name": "F1-Score",
                    "metric_type": "分类指标",
                    "description": "F1分数",
                    "formula": "2 × Precision × Recall / (Precision + Recall)",
                    "interpretation": "综合考虑精确率和召回率",
                    "target_value": "最大化",
                    "weight": 0.4
                },
                {
                    "metric_name": "AUC-ROC",
                    "metric_type": "分类指标",
                    "description": "ROC曲线下面积",
                    "formula": "曲线下面积积分",
                    "interpretation": "越接近1越好，表示分类能力强",
                    "target_value": "最大化",
                    "weight": 0.3
                }
            ]
        else:
            # 通用指标
            metrics = [
                {
                    "metric_name": "准确率",
                    "metric_type": "通用指标",
                    "description": "模型整体准确度",
                    "formula": "根据问题类型定义",
                    "interpretation": "根据问题类型解释",
                    "target_value": "最大化",
                    "weight": 1.0
                }
            ]

        return metrics

    async def _plan_experiment_steps(
        self, experimental_design: Dict[str, Any], validation_strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """规划实验步骤"""
        steps = [
            {
                "step_number": 1,
                "step_name": "数据预处理",
                "description": "清洗和预处理数据，处理缺失值和异常值",
                "inputs": ["原始数据"],
                "outputs": ["清洗后的数据"],
                "success_criteria": "数据质量检查通过",
                "expected_duration": "30分钟",
                "risks": ["数据质量问题", "特征工程错误"]
            },
            {
                "step_number": 2,
                "step_name": "特征工程",
                "description": "特征选择、变换和构造",
                "inputs": ["清洗后的数据"],
                "outputs": ["特征矩阵"],
                "success_criteria": "特征相关性合理",
                "expected_duration": "45分钟",
                "risks": ["特征选择不当", "特征泄露"]
            },
            {
                "step_number": 3,
                "step_name": "数据分割",
                "description": "按策略分割训练/验证/测试集",
                "inputs": ["特征矩阵", "标签"],
                "outputs": ["训练集", "验证集", "测试集"],
                "success_criteria": "分割策略正确执行",
                "expected_duration": "15分钟",
                "risks": ["数据泄露", "分割比例不当"]
            },
            {
                "step_number": 4,
                "step_name": "模型训练",
                "description": "在训练集上训练模型",
                "inputs": ["训练集"],
                "outputs": ["训练好的模型"],
                "success_criteria": "模型收敛且性能良好",
                "expected_duration": "60分钟",
                "risks": ["过拟合", "欠拟合", "训练失败"]
            },
            {
                "step_number": 5,
                "step_name": "模型验证",
                "description": "在验证集上验证模型性能",
                "inputs": ["训练好的模型", "验证集"],
                "outputs": ["验证结果"],
                "success_criteria": "验证指标达标",
                "expected_duration": "30分钟",
                "risks": ["验证集与训练集分布差异"]
            },
            {
                "step_number": 6,
                "step_name": "模型测试",
                "description": "在测试集上最终评估模型",
                "inputs": ["最终模型", "测试集"],
                "outputs": ["测试结果", "性能报告"],
                "success_criteria": "测试指标满足要求",
                "expected_duration": "30分钟",
                "risks": ["测试集特殊性", "性能不达标"]
            },
            {
                "step_number": 7,
                "step_name": "结果分析",
                "description": "分析结果，生成报告",
                "inputs": ["测试结果", "性能报告"],
                "outputs": ["分析报告", "改进建议"],
                "success_criteria": "分析全面深入",
                "expected_duration": "45分钟",
                "risks": ["分析不够深入", "结论错误"]
            }
        ]

        return steps

    async def _design_quality_assurance(self, experimental_design: Dict[str, Any]) -> Dict[str, Any]:
        """设计质量保证"""
        return {
            "data_quality_checks": [
                {
                    "check_type": "缺失值检查",
                    "method": "统计缺失值比例",
                    "threshold": "缺失值比例<5%"
                },
                {
                    "check_type": "异常值检测",
                    "method": "IQR方法或3σ原则",
                    "threshold": "异常值比例<1%"
                },
                {
                    "check_type": "数据一致性检查",
                    "method": "范围检查和逻辑检查",
                    "threshold": "所有数据符合要求"
                }
            ],
            "model_validation_checks": [
                {
                    "check_type": "交叉验证一致性",
                    "method": "K折交叉验证",
                    "pass_criteria": "各折性能差异<10%"
                },
                {
                    "check_type": "过拟合检测",
                    "method": "训练验证性能对比",
                    "pass_criteria": "验证性能不低于训练性能90%"
                }
            ],
            "result_verification": "通过多种方法验证结果的可靠性和有效性"
        }

    async def _estimate_timeline_and_resources(self, experiment_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """估算资源和时间"""
        total_duration = sum(
            int(step.get("expected_duration", "30").replace("分钟", ""))
            for step in experiment_steps
        )

        milestones = [
            {
                "milestone": "数据预处理完成",
                "expected_completion": "1小时",
                "deliverables": ["清洗后的数据", "数据质量报告"]
            },
            {
                "milestone": "模型训练完成",
                "expected_completion": "3小时",
                "deliverables": ["训练好的模型", "训练日志"]
            },
            {
                "milestone": "实验完成",
                "expected_completion": "5小时",
                "deliverables": ["测试结果", "性能报告"]
            },
            {
                "milestone": "分析报告完成",
                "expected_completion": "6小时",
                "deliverables": ["完整分析报告", "改进建议"]
            }
        ]

        return {
            "estimated_duration": f"{total_duration}分钟",
            "key_milestones": milestones,
            "resource_requirements": {
                "computational_resources": "中等计算资源",
                "software_requirements": ["Python", "scikit-learn", "pandas", "matplotlib"],
                "human_expertise": ["数据科学", "机器学习", "统计分析"]
            }
        }

    def get_experiment_summary(self) -> Dict[str, Any]:
        """获取实验设计摘要"""
        summary = self.get_summary()
        if self.state.quality_metrics:
            summary["quality_level"] = self.state.quality_metrics.get_level().name
        return summary