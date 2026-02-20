from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import COORDINATOR_PROMPT
import json
from app.utils.log_util import logger
from app.schemas.A2A import (
    CoordinatorToModeler,
    CompetitionStrategy,
    ProblemRelation,
)
from app.utils.json_parser import clean_json_string


class CoordinatorAgent(Agent):
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = COORDINATOR_PROMPT

    async def run(self, ques_all: str) -> CoordinatorToModeler:
        """用户输入问题，使用 LLM 格式化并提取竞赛战略信息。"""
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history({"role": "user", "content": ques_all})

        # max_attempts 表示最大尝试次数（首次调用 + 重试），语义清晰
        max_attempts = 4
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.model.chat(
                    history=self.chat_history,
                    agent_name=self.__class__.__name__,
                )
                json_str = response.choices[0].message.content

                # 清理 JSON 字符串（使用公共工具函数）
                json_str = clean_json_string(json_str)

                if not json_str:
                    raise ValueError("返回的 JSON 字符串为空")

                questions = json.loads(json_str)
                ques_count = questions["ques_count"]
                logger.info("questions:%s", questions)

                # 提取新增可选字段（向后兼容，缺失时使用默认值）
                extra_fields = self._extract_extra_fields(questions)

                return CoordinatorToModeler(
                    questions=questions,
                    ques_count=ques_count,
                    **extra_fields,
                )

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                last_error = e
                logger.warning(
                    "解析失败 (第 %d/%d 次尝试): %s",
                    attempt, max_attempts, e,
                )

                if attempt >= max_attempts:
                    logger.error("超过最大尝试次数，放弃解析")
                    raise RuntimeError(f"无法解析模型响应: {str(e)}")

                # 添加错误反馈提示，使用 user 角色而非 system 角色
                error_prompt = f"上次响应格式错误: {str(e)}。请严格输出JSON格式"
                await self.append_chat_history({
                    "role": "user",
                    "content": error_prompt
                })

        # 理论上不可达，但作为防御性编程保留
        raise RuntimeError(
            f"CoordinatorAgent 意外的流程终止: {last_error}"
        )

    @staticmethod
    def _extract_extra_fields(questions: dict) -> dict:
        """从 LLM 返回的 JSON 中提取新增可选字段。

        所有字段均为可选，解析失败时静默跳过，确保向后兼容。
        """
        extra: dict = {}

        # 整体难度
        if "difficulty" in questions:
            extra["difficulty"] = questions["difficulty"]

        # 数据描述
        if "data_description" in questions:
            extra["data_description"] = questions["data_description"]

        # 子问题级别难度
        if "sub_difficulty" in questions and isinstance(
            questions["sub_difficulty"], dict
        ):
            extra["sub_difficulty"] = questions["sub_difficulty"]

        # 子问题关联关系
        if "problem_relations" in questions and isinstance(
            questions["problem_relations"], list
        ):
            try:
                extra["problem_relations"] = [
                    ProblemRelation(**rel)
                    for rel in questions["problem_relations"]
                ]
            except Exception as e:
                logger.warning("解析 problem_relations 失败，跳过: %s", e)

        # 竞赛战略分析
        if "strategy" in questions and isinstance(
            questions["strategy"], dict
        ):
            try:
                extra["strategy"] = CompetitionStrategy(
                    **questions["strategy"]
                )
            except Exception as e:
                logger.warning("解析 strategy 失败，跳过: %s", e)

        return extra
