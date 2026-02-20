"""
问题洞察分析专家 - 深度分析问题的本质和表象
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.schemas.A2A import CoordinatorToModeler
from app.utils.log_util import logger


@dataclass
class ProblemInsight:
    """问题洞察结果"""
    surface_problem: str  # 表面问题
    deep_problem: str  # 深层问题
    problem_context: str  # 问题背景
    stakeholders: List[str]  # 利益相关者
    constraints: List[str]  # 约束条件
    objectives: List[str]  # 目标
    success_criteria: List[str]  # 成功标准
    data_characteristics: List[str]  # 数据特征
    potential_challenges: List[str]  # 潜在挑战
    recommended_focus: str  # 建议关注点


class ProblemInsightAnalyzer(ExpertAgent):
    """问题洞察分析专家Agent"""

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
# 🔍 问题洞察分析专家

你是一位资深的数学建模问题洞察专家，擅长透过问题表象发现本质。

## 📋 核心职责
1. **表面问题识别** - 识别问题的直接描述和显性需求
2. **深层问题挖掘** - 发现问题背后的真正挑战和隐含目标
3. **背景分析** - 理解问题产生的背景和环境
4. **利益相关者分析** - 识别与问题相关的各方
5. **约束条件梳理** - 明确显性和隐性约束
6. **数据特征洞察** - 分析数据的特点和局限

## 📝 输出格式
```json
{
    "surface_problem": "问题的表面描述",
    "deep_problem": "问题的深层本质",
    "problem_context": "问题的背景描述",
    "stakeholders": ["利益相关者1", "利益相关者2"],
    "constraints": ["约束1", "约束2"],
    "objectives": ["目标1", "目标2"],
    "success_criteria": ["成功标准1", "成功标准2"],
    "data_characteristics": ["数据特征1", "数据特征2"],
    "potential_challenges": ["挑战1", "挑战2"],
    "recommended_focus": "建议重点关注的方向"
}
```

请确保分析深入、全面，输出严格的JSON格式。
        """

    async def execute(self, coordinator_data: CoordinatorToModeler) -> ProblemInsight:
        """执行问题洞察分析"""
        await self.send_message("🔍 开始问题洞察分析...", "info")
        self.state.current_stage = "analyzing"

        # 1. 提取问题信息
        problem_info = self._extract_problem_info(coordinator_data)
        await self.send_message("📝 已提取问题描述", "success")

        # 2. 深度洞察
        insight_result = await self._analyze_insight(problem_info)

        # 3. 自我反思
        await self.reflect(
            json.dumps(insight_result, ensure_ascii=False, indent=2),
            "问题洞察分析"
        )

        # 4. 质量评估
        await self.evaluate_quality(
            json.dumps(insight_result, ensure_ascii=False, indent=2),
            "问题洞察需要深入、全面"
        )

        await self.send_message("✅ 问题洞察分析完成！", "success")
        self.state.current_stage = "completed"

        return ProblemInsight(**insight_result)

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

    async def _analyze_insight(self, problem_info: str) -> Dict[str, Any]:
        """执行问题洞察分析"""
        analysis_prompt = f"""
        请对以下数学建模问题进行深度洞察分析：

        问题信息：
        {problem_info}

        请严格按照以下JSON格式输出分析结果：
        {{
            "surface_problem": "问题的表面描述（100字以内）",
            "deep_problem": "问题的深层本质（100字以内）",
            "problem_context": "问题的背景描述",
            "stakeholders": ["利益相关者1", "利益相关者2"],
            "constraints": ["约束条件1", "约束条件2"],
            "objectives": ["建模目标1", "建模目标2"],
            "success_criteria": ["成功标准1", "成功标准2"],
            "data_characteristics": ["数据特征1", "数据特征2"],
            "potential_challenges": ["潜在挑战1", "潜在挑战2"],
            "recommended_focus": "建议重点关注的方向"
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
            return self._get_default_insight()

    def _get_default_insight(self) -> Dict[str, Any]:
        """获取默认洞察结果"""
        return {
            "surface_problem": "待分析的数学建模问题",
            "deep_problem": "需要建立数学模型解决实际问题",
            "problem_context": "数学建模竞赛场景",
            "stakeholders": ["参赛者", "评审专家"],
            "constraints": ["时间限制", "数据限制"],
            "objectives": ["建立有效模型", "给出可行方案"],
            "success_criteria": ["模型合理", "结果可靠"],
            "data_characteristics": ["需要进一步分析"],
            "potential_challenges": ["数据处理", "模型选择"],
            "recommended_focus": "问题理解和模型构建"
        }
