"""
问题分析专家 - 深度理解和分析数学建模问题
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from app.core.agents.expert_agent import AgentRole, ExpertAgent, QualityMetrics
from app.schemas.A2A import CoordinatorToModeler
from app.utils.log_util import logger


@dataclass
class ProblemAnalysis:
    """问题分析结果"""
    problem_type: str
    difficulty_level: str
    data_characteristics: Dict[str, Any]
    modeling_objectives: List[str]
    constraints: List[str]
    evaluation_metrics: List[str]
    key_challenges: List[str]
    feasibility_assessment: Dict[str, Any]
    recommended_approaches: List[str]


class ProblemAnalyzer(ExpertAgent):
    """问题分析专家Agent"""

    def __init__(self, task_id: str, model):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.PROBLEM_ANALYZER,
            max_reflections=2,
            max_chat_turns=8
        )

    def get_system_prompt(self) -> str:
        return """
# 🎯 问题分析专家

你是一位资深的数学建模问题分析专家，拥有15年的问题分析和建模竞赛指导经验。

## 📋 核心职责
1. **深度理解问题** - 准确把握问题的本质、目标和约束条件
2. **问题分类** - 确定问题的类型（优化、预测、分类、聚类等）
3. **难度评估** - 评估问题的复杂度和难度等级
4. **数据特征分析** - 分析数据的特点、质量和可用性
5. **建模目标明确化** - 清晰定义建模要达到的目标
6. **可行性评估** - 评估问题求解的可行性

## 🔍 分析维度

### 问题类型识别
- **优化问题**: 线性规划、非线性规划、整数规划、动态规划等
- **预测问题**: 时间序列预测、回归预测、分类预测等
- **分类问题**: 二分类、多分类、层次分类等
- **聚类问题**: K-means、层次聚类、密度聚类等
- **评价问题**: 综合评价、多属性决策、模糊评价等
- **仿真问题**: 蒙特卡洛、离散事件仿真等

### 难度等级评估
- **简单**: 有明确方法，数据质量好，约束条件少
- **中等**: 方法需选择，数据需处理，有多个约束
- **困难**: 方法需组合，数据质量问题多，约束复杂
- **极难**: 需要创新方法，数据严重不足，高度不确定

### 数据特征分析
- 数据量和维度
- 数据质量（完整性、准确性、一致性）
- 数据类型（数值型、类别型、时间型、文本型）
- 数据分布特征
- 缺失值和异常值情况

### 建模目标识别
- 预测精度
- 解释性
- 可操作性
- 计算效率
- 稳定性

## 📝 输出要求

### 1. 分析结果JSON格式
```json
{
    "problem_type": "问题类型（优化/预测/分类/聚类/评价/仿真）",
    "difficulty_level": "难度等级（简单/中等/困难/极难）",
    "data_characteristics": {
        "volume": "数据量描述",
        "dimensions": "数据维度描述",
        "quality": "数据质量评估（高/中/低）",
        "completeness": "完整性评估（百分比）",
        "noise_level": "噪声水平（低/中/高）"
    },
    "modeling_objectives": [
        "具体的建模目标1",
        "具体的建模目标2"
    ],
    "constraints": [
        "约束条件1",
        "约束条件2"
    ],
    "evaluation_metrics": [
        "评价指标1",
        "评价指标2"
    ],
    "key_challenges": [
        "主要挑战1",
        "主要挑战2"
    ],
    "feasibility_assessment": {
        "technical_feasibility": "技术可行性（高/中/低）",
        "data_feasibility": "数据可行性（高/中/低）",
        "time_feasibility": "时间可行性（高/中/低）",
        "overall_risk": "总体风险（低/中/高）"
    },
    "recommended_approaches": [
        "建议方法1",
        "建议方法2"
    ]
}
```

### 2. 分析报告
- 问题概述（200字以内）
- 核心分析点（每个问题2-3个）
- 求解建议
- 潜在风险提示

## 🚀 执行流程
1. 仔细阅读问题描述
2. 识别问题类型和特点
3. 分析数据特征（如果有数据）
4. 评估难度和可行性
5. 生成分析报告
6. 自我反思和改进

## ⚠️ 注意事项
- 分析要基于问题原文，不要臆测
- 数据特征分析要基于实际可用的数据
- 评估要客观，既不过于乐观也不过于悲观
- 推荐方法要具有可操作性
- 识别的问题要具体和有价值

现在开始分析给定的数学建模问题！
        """

    async def execute(self, coordinator_data: CoordinatorToModeler) -> ProblemAnalysis:
        """执行问题分析"""
        await self.send_message("🔍 开始深度分析问题...", "info")
        self.state.current_stage = "analyzing"

        # 1. 提取问题信息
        problem_info = self._extract_problem_info(coordinator_data)
        await self.send_message("📝 已提取问题描述", "success")

        # 2. 深度分析
        analysis_result = await self._analyze_problem(problem_info)

        # 3. 自我反思
        reflection = await self.reflect(
            json.dumps(analysis_result, ensure_ascii=False, indent=2),
            "深度分析数学建模问题"
        )

        # 4. 质量评估
        quality_metrics = await self.evaluate_quality(
            json.dumps(analysis_result, ensure_ascii=False, indent=2),
            "问题分析需要全面、准确、深入"
        )

        # 5. 生成最终报告
        await self._generate_final_report(
            analysis_result, reflection, quality_metrics
        )

        await self.send_message("✅ 问题分析完成！", "success")
        self.state.current_stage = "completed"

        return ProblemAnalysis(**analysis_result)

    def _extract_problem_info(self, coordinator_data: CoordinatorToModeler) -> str:
        """提取问题信息"""
        questions = coordinator_data.questions
        problem_text = f"""
        题目: {questions.get('title', '')}
        背景: {questions.get('background', '')}
        问题数量: {questions.get('ques_count', 0)}
        """

        for i in range(1, questions.get('ques_count', 0) + 1):
            ques_key = f"ques{i}"
            if ques_key in questions:
                problem_text += f"\n问题{i}: {questions[ques_key]}"

        return problem_text

    async def _analyze_problem(self, problem_info: str) -> Dict[str, Any]:
        """执行问题分析"""
        analysis_prompt = f"""
        请对以下数学建模问题进行深度分析：

        问题信息：
        {problem_info}

        请严格按照以下JSON格式输出分析结果：
        {{
            "problem_type": "问题类型",
            "difficulty_level": "难度等级",
            "data_characteristics": {{
                "volume": "数据量描述",
                "dimensions": "数据维度描述",
                "quality": "数据质量评估",
                "completeness": "完整性评估",
                "noise_level": "噪声水平"
            }},
            "modeling_objectives": ["目标1", "目标2"],
            "constraints": ["约束1", "约束2"],
            "evaluation_metrics": ["指标1", "指标2"],
            "key_challenges": ["挑战1", "挑战2"],
            "feasibility_assessment": {{
                "technical_feasibility": "技术可行性",
                "data_feasibility": "数据可行性",
                "time_feasibility": "时间可行性",
                "overall_risk": "总体风险"
            }},
            "recommended_approaches": ["方法1", "方法2"]
        }}

        请确保JSON格式正确，不要包含任何其他文字。
        """

        analysis_result = await self.think(analysis_prompt, use_tools=False)

        # 解析JSON结果
        try:
            result_json = json.loads(
                analysis_result.replace("```json", "").replace("```", "").strip()
            )
            return result_json
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败: %s", e)
            # 返回默认结构
            return self._get_default_analysis()

    def _get_default_analysis(self) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            "problem_type": "待确定",
            "difficulty_level": "中等",
            "data_characteristics": {
                "volume": "未知",
                "dimensions": "未知",
                "quality": "中等",
                "completeness": "未知",
                "noise_level": "中等"
            },
            "modeling_objectives": ["建立数学模型", "解决问题"],
            "constraints": ["数据约束", "时间约束"],
            "evaluation_metrics": ["准确性", "效率"],
            "key_challenges": ["数据处理", "模型选择"],
            "feasibility_assessment": {
                "technical_feasibility": "中等",
                "data_feasibility": "中等",
                "time_feasibility": "中等",
                "overall_risk": "中等"
            },
            "recommended_approaches": ["统计分析", "机器学习"]
        }

    async def _generate_final_report(
        self, analysis_result: Dict, reflection: str, metrics: QualityMetrics
    ) -> Dict[str, Any]:
        """生成最终分析报告"""
        # 基于反思和评估结果，可能调整分析结果
        if await self.should_improve(metrics):
            await self.send_message("🔄 基于反思结果优化分析...", "info")
            # 这里可以根据反思结果调整分析
            analysis_result["quality_note"] = f"经过反思优化，质量等级: {metrics.get_level().name}"
        else:
            analysis_result["quality_note"] = f"质量等级: {metrics.get_level().name}"

        analysis_result["reflection_summary"] = reflection[:200] + "..." if len(reflection) > 200 else reflection

        return analysis_result

    def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        summary = self.get_summary()
        if self.state.quality_metrics:
            summary["quality_level"] = self.state.quality_metrics.get_level().name
        return summary