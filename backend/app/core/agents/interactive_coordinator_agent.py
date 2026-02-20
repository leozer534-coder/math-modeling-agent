"""
交互式协调者 - 增强用户参与度的智能协调者
核心功能：
1. 渐进式问题分析和用户确认
2. 智能提问获取关键信息
3. 实时反馈和调整机制
4. 分段式建模思路展示
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts.interactive_prompts import INTERACTIVE_COORDINATOR_PROMPT
from app.schemas.A2A import CoordinatorToModeler
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


@dataclass
class ModelingStep:
    """建模步骤"""
    step_id: str
    title: str
    description: str
    user_input_required: bool
    current_status: str = "pending"
    user_response: Optional[str] = None
    ai_suggestion: Optional[str] = None


@dataclass
class InteractivePlan:
    """交互式建模计划"""
    problem_summary: str
    key_questions: List[str]
    suggested_approaches: List[str]
    steps: List[ModelingStep]
    confidence_level: float


class InteractiveCoordinatorAgent(Agent):
    """交互式协调者智能体"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 50,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = INTERACTIVE_COORDINATOR_PROMPT
        self.modeling_plan = None
        self.current_step = 0

    async def run(self, ques_all: str) -> InteractivePlan:
        """执行交互式协调者的核心任务。

        委托给 analyze_problem_interactively() 完成交互式问题分析。

        Args:
            ques_all: 用户提交的完整问题描述

        Returns:
            InteractivePlan: 交互式建模计划
        """
        return await self.analyze_problem_interactively(ques_all)

    async def analyze_problem_interactively(self, ques_all: str) -> InteractivePlan:
        """交互式问题分析"""
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )

        # 发送分析开始消息
        await redis_manager.publish_message(
            self.task_id,
            {
                "type": "analysis_start",
                "content": "🔍 开始分析问题，请稍候...",
                "step": "problem_analysis"
            }
        )

        await self.append_chat_history({
            "role": "user",
            "content": f"请分析这个数学建模问题并提供交互式建模计划：\n\n{ques_all}"
        })

        # 初步分析
        response = await self.model.chat(
            history=self.chat_history,
            agent_name=self.__class__.__name__,
        )

        try:
            analysis_result = json.loads(response.choices[0].message.content)

            # 构建交互式计划
            plan = InteractivePlan(
                problem_summary=analysis_result.get("problem_summary", ""),
                key_questions=analysis_result.get("key_questions", []),
                suggested_approaches=analysis_result.get("suggested_approaches", []),
                steps=self._build_modeling_steps(analysis_result.get("suggested_steps", [])),
                confidence_level=analysis_result.get("confidence_level", 0.8)
            )

            self.modeling_plan = plan

            # 发送分析结果给用户确认
            await self._send_analysis_for_confirmation(plan)

            return plan

        except (json.JSONDecodeError, KeyError) as e:
            logger.error("问题分析失败: %s", e)
            raise RuntimeError(f"无法解析问题分析结果: {str(e)}")

    def _build_modeling_steps(self, suggested_steps: List[Dict]) -> List[ModelingStep]:
        """构建建模步骤"""
        steps = []
        for i, step in enumerate(suggested_steps):
            steps.append(ModelingStep(
                step_id=f"step_{i+1}",
                title=step.get("title", f"步骤 {i+1}"),
                description=step.get("description", ""),
                user_input_required=step.get("user_input_required", False),
                ai_suggestion=step.get("ai_suggestion", "")
            ))
        return steps

    async def _send_analysis_for_confirmation(self, plan: InteractivePlan):
        """发送分析结果给用户确认"""
        confirmation_message = {
            "type": "analysis_complete",
            "content": "📋 问题分析完成，请确认建模计划",
            "data": {
                "problem_summary": plan.problem_summary,
                "key_questions": plan.key_questions,
                "suggested_approaches": plan.suggested_approaches,
                "confidence_level": plan.confidence_level,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "title": step.title,
                        "description": step.description,
                        "user_input_required": step.user_input_required,
                        "ai_suggestion": step.ai_suggestion
                    }
                    for step in plan.steps
                ]
            }
        }

        await redis_manager.publish_message(self.task_id, confirmation_message)

    async def process_user_feedback(self, user_feedback: Dict[str, Any]) -> CoordinatorToModeler:
        """处理用户反馈并生成最终建模指令"""

        # 发送处理开始消息
        await redis_manager.publish_message(
            self.task_id,
            {
                "type": "processing_feedback",
                "content": "🔄 正在根据您的反馈调整建模计划...",
                "step": "feedback_processing"
            }
        )

        # 将用户反馈整合到计划中
        await self._integrate_user_feedback(user_feedback)

        # 生成最终建模指令
        final_questions = await self._generate_final_questions()

        # 发送确认消息
        await redis_manager.publish_message(
            self.task_id,
            {
                "type": "plan_confirmed",
                "content": "✅ 建模计划已确认，开始执行建模任务！",
                "final_plan": final_questions
            }
        )

        return CoordinatorToModeler(
            questions=final_questions,
            ques_count=len(final_questions.get("questions", {}))
        )

    async def _integrate_user_feedback(self, user_feedback: Dict[str, Any]):
        """整合用户反馈到建模计划中"""

        feedback_prompt = f"""
        用户提供了以下反馈，请相应调整建模计划：

        用户反馈：
        {json.dumps(user_feedback, ensure_ascii=False, indent=2)}

        原始计划：
        问题摘要：{self.modeling_plan.problem_summary}
        建议方法：{self.modeling_plan.suggested_approaches}

        请提供调整后的建模思路，确保：
        1. 充分考虑用户的选择和建议
        2. 保持建模的合理性和完整性
        3. 提供具体的执行步骤
        """

        await self.append_chat_history({"role": "user", "content": feedback_prompt})

        response = await self.model.chat(
            history=self.chat_history,
            agent_name=self.__class__.__name__,
        )

        # 更新计划
        try:
            updated_plan = json.loads(response.choices[0].message.content)
            self.modeling_plan.suggested_approaches = updated_plan.get("adjusted_approaches",
                                                                    self.modeling_plan.suggested_approaches)
        except json.JSONDecodeError:
            logger.warning("用户反馈整合失败，使用原始计划")

    async def _generate_final_questions(self) -> Dict[str, Any]:
        """生成最终建模问题"""

        final_prompt = f"""
        基于以下确认的建模计划，生成最终的具体建模问题：

        问题摘要：{self.modeling_plan.problem_summary}
        选择的方法：{self.modeling_plan.suggested_approaches}

        请生成结构化的建模问题，包含：
        1. 问题重述和关键信息
        2. 建模目标和约束条件
        3. 具体的建模步骤要求
        4. 预期的输出形式

        请以标准JSON格式返回。
        """

        await self.append_chat_history({"role": "user", "content": final_prompt})

        response = await self.model.chat(
            history=self.chat_history,
            agent_name=self.__class__.__name__,
        )

        try:
            final_questions = json.loads(response.choices[0].message.content)
            return final_questions
        except json.JSONDecodeError:
            # 降级处理，返回基本结构
            return {
                "questions": {
                    "problem_statement": self.modeling_plan.problem_summary,
                    "modeling_approach": self.modeling_plan.suggested_approaches[0] if self.modeling_plan.suggested_approaches else "数据分析",
                    "objectives": ["建立数学模型", "求解最优解", "结果分析"]
                },
                "ques_count": 1
            }

    async def request_missing_info(self, missing_info_type: str) -> str:
        """请求缺失的关键信息"""

        request_prompts = {
            "data_info": "我需要了解您提供的数据文件的具体信息。请描述：\n1. 数据包含哪些字段\n2. 数据的格式和规模\n3. 数据的含义和单位",
            "constraints": "请提供问题的具体约束条件，例如：\n1. 变量的取值范围\n2. 资源限制\n3. 特殊要求",
            "objectives": "请明确建模的具体目标，例如：\n1. 需要优化什么指标\n2. 预期得到什么样的结果\n3. 结果的精度要求",
            "preferences": "您对建模方法有什么偏好或要求吗？\n1. 是否有特定的模型类型偏好\n2. 对复杂度的要求\n3. 是否需要考虑实时性"
        }

        prompt = request_prompts.get(missing_info_type, "请提供更多相关信息以帮助建模")

        await redis_manager.publish_message(
            self.task_id,
            {
                "type": "info_request",
                "content": f"❓ {prompt}",
                "request_type": missing_info_type
            }
        )

        return prompt