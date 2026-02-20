"""
交互式数学建模工作流
核心特点：
1. 渐进式执行，每个阶段都有用户确认
2. 实时反馈中间结果
3. 允许用户调整和纠正
4. 错误时可以回退到上一步
"""
import asyncio
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.config.setting import settings
from app.core.agents import CoderAgent, ModelerAgent, WriterAgent
from app.core.agents.interactive_coordinator_agent import (
    InteractiveCoordinatorAgent,
    InteractivePlan,
)
from app.core.flows import Flows
from app.core.llm.llm_factory import LLMFactory
from app.models.user_output import UserOutput
from app.schemas.request import Problem
from app.schemas.A2A import CoderFeedbackToModeler
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.common_utils import create_work_dir, generate_data_summary, get_config_template
from app.utils.log_util import logger
from app.core.prompts import CODER_PROMPT as _BASE_CODER_PROMPT
from app.core.prompts.base_prompts import build_coder_prompt_with_templates


class WorkflowStage(str, Enum):
    """工作流阶段"""
    INIT = "init"
    ANALYSIS = "analysis"
    MODELING = "modeling"
    CODING = "coding"
    WRITING = "writing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class UserAction(str, Enum):
    """用户操作类型"""
    CONFIRM = "confirm"
    CANCEL = "cancel"
    ROLLBACK = "rollback"
    MODIFY = "modify"
    SKIP = "skip"
    RETRY = "retry"


@dataclass
class StageHistory:
    """阶段历史记录"""
    stage: WorkflowStage
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    user_feedback: dict = field(default_factory=dict)


class InteractiveWorkflowState:
    """工作流状态管理"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.current_stage = WorkflowStage.INIT
        self.history: list[StageHistory] = []
        self.pending_user_input = False
        self.user_feedback: dict = {}
        self.start_time = time.time()

    def save_stage(self, stage: WorkflowStage, data: dict[str, Any], feedback: dict = None):
        """保存阶段状态"""
        self.history.append(StageHistory(
            stage=stage,
            data=data,
            user_feedback=feedback or {}
        ))
        self.current_stage = stage
        logger.info("阶段保存: %s", stage.value)

    def rollback(self) -> Optional[StageHistory]:
        """回退到上一个阶段"""
        if len(self.history) > 1:
            self.history.pop()
            last = self.history[-1]
            self.current_stage = last.stage
            logger.info("回退到阶段: %s", last.stage.value)
            return last
        return None

    def can_rollback(self) -> bool:
        """是否可以回退"""
        return len(self.history) > 1

    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return time.time() - self.start_time

    def get_stage_data(self, stage: WorkflowStage) -> Optional[Any]:
        """获取指定阶段的数据"""
        for h in reversed(self.history):
            if h.stage == stage:
                return h.data
        return None


class _NullCodeInterpreter:
    """空代码解释器代理，用于写作阶段。

    交互式工作流中编码阶段结束后 code_interpreter 已被清理，
    但 Flows.get_writer_prompt() 需要调用 code_interpreter.get_code_output(key)。
    本类提供兼容接口，始终返回空字符串。
    """

    def get_code_output(self, section: str) -> str:
        """返回空代码输出。"""
        return ""


class InteractiveMathModelWorkflow:
    """交互式数学建模工作流"""

    # 用户操作等待超时配置
    DEFAULT_TIMEOUT = 1800  # 30分钟
    INITIAL_POLL_INTERVAL = 1.0  # 初始轮询间隔
    MAX_POLL_INTERVAL = 5.0  # 最大轮询间隔

    def __init__(self, agent_configs: dict | None = None):
        self.state: Optional[InteractiveWorkflowState] = None
        self.interactive_plan: Optional[InteractivePlan] = None
        self.code_interpreter = None
        self._llms = {}
        # 缓存协调者实例，避免将 Agent 对象存入 StageHistory
        self._coordinator: Optional[InteractiveCoordinatorAgent] = None
        # 用户级 API 配置（多租户隔离）
        self._agent_configs = agent_configs

    async def execute(self, problem: Problem):
        """执行交互式工作流"""
        task_id = problem.task_id
        work_dir = create_work_dir(task_id)

        # 初始化状态
        self.state = InteractiveWorkflowState(task_id)

        # 初始化LLM
        llm_factory = LLMFactory(task_id, self._agent_configs)
        coordinator_llm, modeler_llm, coder_llm, writer_llm = llm_factory.get_all_llms()
        self._llms = {
            "coordinator": coordinator_llm,
            "modeler": modeler_llm,
            "coder": coder_llm,
            "writer": writer_llm,
        }

        try:
            # ============= 阶段 1: 交互式问题分析 =============
            await self._stage_1_interactive_analysis(
                task_id, problem.ques_all, coordinator_llm
            )

            # 等待用户确认
            user_response = await self._wait_for_user_action(
                "analysis_confirmed",
                timeout=self.DEFAULT_TIMEOUT
            )
            await self._handle_user_response(user_response, WorkflowStage.ANALYSIS)

            # ============= 阶段 2: 建模方案设计（带用户反馈）=============
            modeling_response = await self._stage_2_modeling_with_feedback(
                task_id, modeler_llm, work_dir
            )

            # 显示建模方案给用户
            await self._show_modeling_plan(modeling_response)

            # 等待用户确认建模方案
            user_response = await self._wait_for_user_action(
                "modeling_confirmed",
                timeout=self.DEFAULT_TIMEOUT
            )
            await self._handle_user_response(user_response, WorkflowStage.MODELING)

            # ============= 阶段 3: 渐进式代码执行 =============
            await self._stage_3_progressive_coding(
                task_id, work_dir, coder_llm, modeling_response,
                modeler_llm=modeler_llm,
            )

            # ============= 阶段 4: 论文撰写 =============
            await self._stage_4_writing(
                task_id, work_dir, writer_llm, problem, modeling_response
            )

            # ============= 质量评审阶段 =============
            if settings.ENABLE_REVIEW:
                try:
                    await redis_manager.publish_message(
                        task_id,
                        SystemMessage(
                            content="质量评审中...", type="info"
                        ),
                    )

                    from app.core.agents.reviewer import Reviewer

                    reviewer = Reviewer(task_id=task_id, model=writer_llm)
                    await reviewer.setup()

                    # 从写作阶段结果中获取 user_output
                    writing_data = self.state.get_stage_data(
                        WorkflowStage.WRITING
                    )
                    user_output = (
                        writing_data.get("output") if writing_data else None
                    )

                    if user_output:
                        modeling_results = {
                            "paper_content": user_output.get_result_to_save(),
                            "sections": [
                                k
                                for k in user_output.seq
                                if k in user_output.res
                            ],
                            "metrics": getattr(
                                user_output, "metrics_store", {}
                            ),
                            "model_comparison": getattr(
                                user_output, "model_comparison_data", ""
                            ),
                            "ques_count": user_output.ques_count,
                        }

                        quality_review = await reviewer.execute(
                            modeling_results
                        )

                        # 保存评审报告
                        import json as _json

                        review_report_path = os.path.join(
                            work_dir, "quality_review.json"
                        )
                        review_dict: dict = {}
                        if hasattr(quality_review, "__dict__"):
                            review_dict = {
                                k: (
                                    v.value if hasattr(v, "value") else v
                                )
                                for k, v in quality_review.__dict__.items()
                            }
                        with open(
                            review_report_path, "w", encoding="utf-8"
                        ) as f:
                            _json.dump(
                                review_dict,
                                f,
                                ensure_ascii=False,
                                indent=2,
                                default=str,
                            )

                        # 发送评审结果到前端
                        overall_rating = getattr(
                            quality_review, "overall_rating", 0
                        )
                        review_status = getattr(
                            quality_review, "review_status", None
                        )
                        status_text = (
                            review_status.value
                            if hasattr(review_status, "value")
                            else str(review_status)
                        )

                        await redis_manager.publish_message(
                            task_id,
                            SystemMessage(
                                content=(
                                    f"论文质量评审完成: {status_text}"
                                    f"（{overall_rating}/5）"
                                ),
                                type=(
                                    "success"
                                    if overall_rating
                                    >= settings.REVIEW_MIN_SCORE
                                    else "warning"
                                ),
                            ),
                        )

                        # 如果评分低于阈值，记录关键问题（不阻塞流程）
                        critical_issues = getattr(
                            quality_review, "critical_issues", []
                        )
                        if critical_issues:
                            issues_summary = "; ".join(
                                (
                                    issue.get("description", str(issue))[
                                        :100
                                    ]
                                    if isinstance(issue, dict)
                                    else str(issue)[:100]
                                )
                                for issue in critical_issues[:3]
                            )
                            logger.warning(
                                "评审发现关键问题: %s", issues_summary
                            )

                        logger.info(
                            "质量评审完成: 评分=%d/5, 状态=%s, 关键问题=%d个",
                            overall_rating,
                            status_text,
                            len(critical_issues),
                        )

                except Exception as review_err:
                    logger.warning(
                        "质量评审阶段失败（不影响论文输出）: %s", review_err
                    )
                    await redis_manager.publish_message(
                        task_id,
                        SystemMessage(
                            content="质量评审跳过（评审过程出错）",
                            type="warning",
                        ),
                    )

            self.state.current_stage = WorkflowStage.COMPLETED
            elapsed = self.state.get_elapsed_time()

            await redis_manager.publish_message(
                task_id,
                SystemMessage(
                    content=f"🎉 所有任务完成！总用时: {elapsed/60:.1f}分钟",
                    type="success"
                )
            )
            # 任务完成后清理文件锁，防止内存泄漏
            redis_manager.cleanup_task_lock(task_id)

        except UserCancellationError:
            self.state.current_stage = WorkflowStage.CANCELLED
            await redis_manager.publish_message(
                task_id,
                SystemMessage(content="⚠️ 用户取消了任务", type="warning")
            )
            # 用户取消时也清理文件锁
            redis_manager.cleanup_task_lock(task_id)
        except TimeoutError as e:
            self.state.current_stage = WorkflowStage.FAILED
            await redis_manager.publish_message(
                task_id,
                SystemMessage(content=f"⏰ 操作超时: {str(e)}", type="error")
            )
            # 超时异常时清理文件锁
            redis_manager.cleanup_task_lock(task_id)
        except Exception as e:
            self.state.current_stage = WorkflowStage.FAILED
            logger.error("工作流执行失败: %s", e)
            await redis_manager.publish_message(
                task_id,
                SystemMessage(content=f"❌ 执行失败: {str(e)}", type="error")
            )
            # 异常路径清理文件锁，防止内存泄漏
            redis_manager.cleanup_task_lock(task_id)
            raise
        finally:
            # 清理资源
            await self._cleanup()

    async def _cleanup(self):
        """清理资源"""
        if self.code_interpreter:
            try:
                await self.code_interpreter.cleanup()
            except Exception as e:
                logger.warning("清理代码解释器失败: %s", e)
            self.code_interpreter = None

    async def _stage_1_interactive_analysis(
        self, task_id: str, ques_all: str, coordinator_llm
    ):
        """阶段1：交互式问题分析"""
        await self._send_stage_start(
            task_id,
            WorkflowStage.ANALYSIS,
            "🎯 第1阶段：智能问题分析",
            "AI正在分析问题，并将提供多种建模方案供您选择"
        )

        # 创建交互式协调者
        interactive_coordinator = InteractiveCoordinatorAgent(task_id, coordinator_llm)

        # 进行交互式分析
        self.interactive_plan = await interactive_coordinator.analyze_problem_interactively(ques_all)

        # 将协调者保存为实例属性，避免将 Agent 对象存入 StageHistory
        self._coordinator = interactive_coordinator

        # 保存分析阶段（仅保存可序列化数据）
        self.state.save_stage(WorkflowStage.ANALYSIS, {
            "plan": self.interactive_plan,
        })

        # 发送智能提问
        await self._send_intelligent_questions(self.interactive_plan)

    async def _send_stage_start(
        self, task_id: str, stage: WorkflowStage, title: str, description: str
    ):
        """发送阶段开始消息"""
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content=title, type="info")
        )

        # 发送详细的阶段信息（前端可以用来显示进度）
        stage_info = {
            "type": "stage_start",
            "stage": stage.value,
            "title": title,
            "description": description,
            "elapsed_time": self.state.get_elapsed_time() if self.state else 0
        }
        await redis_manager.set_json(
            f"task:{task_id}:current_stage",
            stage_info,
            expire=3600
        )

    async def _send_intelligent_questions(self, plan: InteractivePlan):
        """发送智能提问以获取更多信息"""
        if not plan.key_questions:
            return

        questions_data = {
            "type": "clarification_needed",
            "content": "💡 为了提供更好的建模方案，请回答以下问题：",
            "questions": [
                {
                    "id": f"q_{i}",
                    "question": q,
                    "optional": False
                }
                for i, q in enumerate(plan.key_questions)
            ]
        }

        await redis_manager.publish_message(
            self.state.task_id,
            SystemMessage(content=questions_data["content"], type="info")
        )

        # 保存问题到Redis供前端获取
        await redis_manager.set_json(
            f"task:{self.state.task_id}:pending_questions",
            questions_data,
            expire=3600
        )

    async def _wait_for_user_action(
        self,
        action_type: str,
        timeout: int = None
    ) -> dict:
        """
        等待用户操作

        Args:
            action_type: 期望的操作类型
            timeout: 超时时间（秒）

        Returns:
            用户操作数据
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        action_key = f"user_action:{self.state.task_id}"

        # 发送等待确认消息
        await redis_manager.publish_message(
            self.state.task_id,
            SystemMessage(content="⏳ 等待您的确认...", type="info")
        )

        # 保存等待状态
        await redis_manager.set_json(
            f"task:{self.state.task_id}:waiting",
            {
                "waiting_for": action_type,
                "can_rollback": self.state.can_rollback(),
                "can_cancel": True,
                "can_edit": True,
                "timeout": timeout,
                "started_at": time.time()
            },
            expire=timeout + 60
        )

        self.state.pending_user_input = True
        start_time = time.time()
        poll_count = 0
        current_interval = self.INITIAL_POLL_INTERVAL

        try:
            while self.state.pending_user_input:
                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"等待用户确认超时 ({action_type})")

                # 检查用户操作
                action_data = await redis_manager.get_json(action_key)

                if action_data:
                    # 清除已读取的操作
                    await redis_manager.delete(action_key)
                    self.state.pending_user_input = False
                    return action_data

                await asyncio.sleep(current_interval)
                poll_count += 1
                # 前 10 次保持初始间隔，之后指数退避
                if poll_count > 10 and current_interval < self.MAX_POLL_INTERVAL:
                    current_interval = min(
                        current_interval * 1.5, self.MAX_POLL_INTERVAL
                    )

        finally:
            # 清除等待状态
            await redis_manager.delete(f"task:{self.state.task_id}:waiting")

        return {"action": UserAction.CONFIRM.value}

    async def _handle_user_response(self, response: dict, stage: WorkflowStage):
        """处理用户响应"""
        action = response.get("action", UserAction.CONFIRM.value)

        if action == UserAction.CANCEL.value:
            raise UserCancellationError("用户取消了操作")

        elif action == UserAction.ROLLBACK.value:
            previous = self.state.rollback()
            if previous:
                await redis_manager.publish_message(
                    self.state.task_id,
                    SystemMessage(
                        content=f"⏪ 回退到: {previous.stage.value}",
                        type="info"
                    )
                )
                # 重新执行该阶段
                raise RollbackError(previous.stage)
            else:
                await redis_manager.publish_message(
                    self.state.task_id,
                    SystemMessage(content="❌ 无法回退，已经是第一步", type="error")
                )

        elif action == UserAction.MODIFY.value:
            # 保存用户修改
            self.state.user_feedback = response.get("modifications", {})

        elif action == UserAction.CONFIRM.value:
            # 保存用户反馈
            self.state.user_feedback = response.get("feedback", {})

    async def _stage_2_modeling_with_feedback(self, task_id: str, modeler_llm, work_dir: str):
        """阶段2：带反馈的建模方案设计"""
        await self._send_stage_start(
            task_id,
            WorkflowStage.MODELING,
            "📐 第2阶段：设计建模方案",
            "基于您的反馈，设计详细的建模方案"
        )

        # 获取用户反馈
        user_feedback = self.state.user_feedback

        # 从实例属性获取协调者（不再从 stage data 中取）
        coordinator = self._coordinator
        if not coordinator:
            raise ValueError("缺少协调者实例")

        # 处理用户反馈并生成建模指令
        modeling_instructions = await coordinator.process_user_feedback(user_feedback)
        # 缓存为实例属性，供反馈闭环阶段使用
        self._modeling_instructions = modeling_instructions

        # 生成数据摘要，为 Modeler 提供数据感知
        data_context = await asyncio.to_thread(generate_data_summary, work_dir)
        if data_context:
            logger.info("数据摘要已生成，长度: %d 字符", len(data_context))
        # 缓存数据上下文，供反馈闭环阶段使用
        self._data_context = data_context

        # 创建建模者
        modeler_agent = ModelerAgent(task_id, modeler_llm)
        modeler_response = await modeler_agent.run(modeling_instructions, data_context=data_context)

        # 保存建模阶段
        self.state.save_stage(WorkflowStage.MODELING, {
            "instructions": modeling_instructions,
            "response": modeler_response
        })

        return modeler_response

    async def _show_modeling_plan(self, modeling_response):
        """展示建模方案给用户"""
        plan_data = {
            "type": "modeling_plan",
            "content": "📋 建模方案设计完成",
            "plan": {
                "questions": getattr(modeling_response, 'questions_solution', {}),
                "approach": "详细的建模方法和步骤",
                "expected_results": "预期的输出形式和指标"
            },
            "actions": [
                {"id": "confirm", "label": "确认并继续", "variant": "default"},
                {"id": "modify", "label": "修改方案", "variant": "outline"},
                {"id": "cancel", "label": "取消", "variant": "ghost"}
            ]
        }

        await redis_manager.publish_message(
            self.state.task_id,
            SystemMessage(content=plan_data["content"], type="info")
        )

        # 保存方案供前端显示
        await redis_manager.set_json(
            f"task:{self.state.task_id}:modeling_plan",
            plan_data,
            expire=3600
        )

    async def _stage_3_progressive_coding(
        self, task_id: str, work_dir: str, coder_llm, modeling_response,
        modeler_llm=None,
    ):
        """阶段3：渐进式代码执行（含 Coder-Modeler 反馈闭环）"""
        await self._send_stage_start(
            task_id,
            WorkflowStage.CODING,
            "💻 第3阶段：渐进式代码执行",
            "分步骤执行建模代码，实时展示结果"
        )

        # 创建代码解释器
        notebook_serializer = NotebookSerializer(work_dir=work_dir)
        self.code_interpreter = await create_interpreter(
            kind="auto",
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
        )

        # 提取所有模型名称用于代码模板匹配
        model_names: list[str] = []
        ques_count = 0
        if hasattr(modeling_response, 'questions_solution'):
            for k in modeling_response.questions_solution:
                if k.startswith("ques"):
                    ques_count += 1
        for i in range(1, ques_count + 1):
            config = modeling_response.get_model_config(f"ques{i}")
            if config and config.model_name:
                model_names.append(config.model_name)

        # 构建增强的 Coder system prompt（注入匹配的代码模板）
        enhanced_coder_prompt = None
        if model_names:
            try:
                enhanced_coder_prompt = build_coder_prompt_with_templates(
                    _BASE_CODER_PROMPT, model_names=model_names
                )
                logger.info("代码模板注入成功，匹配模型: %s", model_names)
            except Exception as e:
                logger.warning("代码模板注入失败，使用默认 prompt: %s", e)

        # 创建代码执行者
        coder_agent = CoderAgent(
            task_id=task_id,
            model=coder_llm,
            work_dir=work_dir,
            code_interpreter=self.code_interpreter,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            system_prompt=enhanced_coder_prompt,
        )

        # 从建模响应中提取解决方案
        questions_solution = getattr(modeling_response, 'questions_solution', {})

        # 从建模指令中提取子任务
        flows = Flows(questions_solution)
        solution_flows = flows.get_solution_flows(questions_solution, modeling_response)

        # 分步执行
        results = {}
        total_steps = len(solution_flows)

        # 跨问题结果上下文：积累前序问题的关键结果供后续问题参考
        cross_question_context: dict[str, str] = {}
        eda_data_files: list[str] = []  # EDA阶段产出的清洗后数据文件
        MAX_CROSS_CONTEXT_TOTAL_CHARS = 5000

        for idx, (key, value) in enumerate(solution_flows.items(), 1):
            # 发送当前步骤
            await redis_manager.publish_message(
                task_id,
                SystemMessage(
                    content=f"⚙️ 正在执行 ({idx}/{total_steps}): {key}",
                    type="info"
                )
            )

            try:
                # 执行代码（使用新的元数据格式动态构建 prompt）
                coder_prompt = value["coder_prompt"]

                # 如果是 ques 类型且有前序结果，注入跨问题上下文
                if (
                    key.startswith("ques")
                    or key == "sensitivity_analysis"
                    or key == "model_comparison"
                ) and cross_question_context:
                    try:
                        context_text = Flows.build_cross_question_context(
                            cross_question_context
                        )
                        coder_prompt = f"{coder_prompt}\n\n{context_text}"
                    except Exception as ctx_err:
                        logger.warning("跨问题上下文注入失败，跳过: %s", ctx_err)

                # 注入 EDA 清洗数据文件路径（独立于跨问题上下文）
                if eda_data_files and (
                    key.startswith("ques")
                    or key == "sensitivity_analysis"
                    or key == "model_comparison"
                ):
                    files_list = "\n".join(f"  - {f}" for f in eda_data_files[:10])
                    coder_prompt += (
                        f"\n\n【EDA阶段产出的清洗数据文件（请优先使用，避免重复清洗）】\n"
                        f"{files_list}\n"
                    )

                coder_response = await coder_agent.run(
                    prompt=coder_prompt,
                    subtask_title=key
                )

                # === Coder-Modeler 反馈闭环 ===
                MAX_FEEDBACK_ITERATIONS = 2
                feedback_count = 0
                while (
                    getattr(coder_response, "failed", False)
                    and feedback_count < MAX_FEEDBACK_ITERATIONS
                    and modeler_llm is not None
                ):
                    feedback_count += 1
                    logger.warning(
                        "Coder 求解 %s 失败（第 %d 次），触发 Modeler 修订",
                        key, feedback_count,
                    )

                    await redis_manager.publish_message(
                        task_id,
                        SystemMessage(
                            content=f"代码手求解{key}失败，反馈给建模手修订方案（第{feedback_count}次）",
                            type="warning",
                        ),
                    )

                    # 构建反馈
                    feedback = CoderFeedbackToModeler(
                        subtask_key=key,
                        error_summary=(
                            getattr(coder_response, "code_response", "") or ""
                        )[:500],
                        failed_approach=value.get("coder_prompt", "")[:200],
                        retry_count=feedback_count,
                    )

                    # 获取缓存的建模指令（CoordinatorToModeler）
                    coordinator_to_modeler = getattr(
                        self, "_modeling_instructions", None
                    )
                    if coordinator_to_modeler is None:
                        logger.warning(
                            "缺少 CoordinatorToModeler，跳过 Modeler 修订"
                        )
                        break

                    # 创建 Modeler 实例并请求修订
                    modeler_agent = ModelerAgent(task_id, modeler_llm)
                    data_context = getattr(self, "_data_context", None)
                    revised_response = await modeler_agent.revise(
                        original_response=modeling_response,
                        feedback=feedback,
                        coordinator_to_modeler=coordinator_to_modeler,
                        data_context=data_context,
                    )

                    # 选择性合并：仅替换失败子任务的方案，保护其他子任务
                    revised_key = feedback.subtask_key
                    if revised_key in revised_response.questions_solution:
                        modeling_response.questions_solution[revised_key] = (
                            revised_response.questions_solution[revised_key]
                        )
                        logger.info(
                            "选择性合并: 仅替换 %s 的建模方案", revised_key
                        )
                    else:
                        modeling_response = revised_response
                        logger.warning(
                            "修订响应中未找到 %s 的方案，使用完整替换",
                            revised_key,
                        )

                    # 重建该子任务的 coder prompt
                    revised_flows = flows.get_solution_flows(
                        questions_solution, modeling_response
                    )
                    if key in revised_flows:
                        coder_prompt = revised_flows[key]["coder_prompt"]

                    await redis_manager.publish_message(
                        task_id,
                        SystemMessage(
                            content=f"建模手已修订{key}方案，代码手重新求解",
                        ),
                    )

                    # 重新执行 Coder
                    coder_response = await coder_agent.run(
                        prompt=coder_prompt,
                        subtask_title=key,
                    )

                # 根据最终结果发送消息
                if getattr(coder_response, "failed", False):
                    await redis_manager.publish_message(
                        task_id,
                        SystemMessage(
                            content=f"代码手求解{key}最终失败，使用降级结果继续",
                            type="error",
                        ),
                    )
                else:
                    await redis_manager.publish_message(
                        task_id,
                        SystemMessage(
                            content=f"✅ {key} 执行完成",
                            type="success"
                        )
                    )

                # === 结果验证与指标提取 ===
                code_output_text = self.code_interpreter.get_code_output(key)
                if not code_output_text:
                    logger.debug("子任务 %s 没有代码输出记录，跳过指标提取", key)
                    code_output_text = None

                # EDA 阶段完成后收集清洗数据文件
                if key == "eda":
                    try:
                        eda_data_files = self.code_interpreter.get_created_data_files("eda")
                        if eda_data_files:
                            logger.info("EDA 产出数据文件: %s", eda_data_files)
                    except Exception as e:
                        logger.warning("收集 EDA 数据文件失败: %s", e)

                extracted_metrics: dict = {}
                if code_output_text:
                    metrics = Flows.extract_metrics_from_code_output(code_output_text)
                    figures = Flows.extract_figures_from_code_output(code_output_text)
                    result_summaries = Flows.extract_result_summaries(code_output_text)

                    if metrics:
                        logger.info("子任务 %s 提取到指标: %s", key, metrics)
                        extracted_metrics = metrics
                    if figures:
                        logger.info("子任务 %s 提取到 %d 张图表", key, len(figures))
                    if result_summaries:
                        logger.info("子任务 %s 提取到结果摘要: %s", key, result_summaries)

                # 积累跨问题上下文（ques 和 eda 类型参与生产）
                if key.startswith("ques") or key == "eda":
                    try:
                        context_parts_list: list[str] = []
                        if coder_response.code_response:
                            context_parts_list.append(
                                coder_response.code_response[:800]
                            )
                        if code_output_text and extracted_metrics:
                            metrics_str = ", ".join(
                                f"{k}={v}" for k, v in extracted_metrics.items()
                            )
                            context_parts_list.append(f"评估指标: {metrics_str}")
                        if context_parts_list:
                            new_context = "\n".join(context_parts_list)
                            current_total = sum(
                                len(v) for v in cross_question_context.values()
                            )
                            if (
                                current_total + len(new_context)
                                > MAX_CROSS_CONTEXT_TOTAL_CHARS
                            ):
                                remaining = (
                                    MAX_CROSS_CONTEXT_TOTAL_CHARS - current_total
                                )
                                if remaining > 200:
                                    new_context = new_context[:remaining]
                                    logger.warning(
                                        "跨问题上下文即将超限，截断 %s 至 %d 字符",
                                        key, remaining,
                                    )
                                else:
                                    new_context = None
                            if new_context:
                                cross_question_context[key] = new_context
                                logger.info(
                                    "已积累 %s 的跨问题上下文（%d 字符）",
                                    key, len(new_context),
                                )
                    except Exception as ctx_acc_err:
                        logger.warning(
                            "积累 %s 跨问题上下文失败: %s", key, ctx_acc_err
                        )

                results[key] = {
                    "response": coder_response,
                    "success": True,
                    "metrics": extracted_metrics,
                }

            except Exception as e:
                logger.error("执行 %s 失败: %s", key, e)

                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(
                        content=f"⚠️ {key} 执行失败，已跳过",
                        type="warning"
                    )
                )

                results[key] = {
                    "error": str(e),
                    "success": False
                }

        # 保存编码阶段
        self.state.save_stage(WorkflowStage.CODING, {"results": results})

        # 清理解释器
        if self.code_interpreter:
            await self.code_interpreter.cleanup()
            self.code_interpreter = None

    async def _stage_4_writing(
        self,
        task_id: str,
        work_dir: str,
        writer_llm,
        problem: Problem,
        modeling_response,
    ):
        """阶段4：论文撰写（含前置/后置章节）

        重构后的写作阶段包含两个子阶段：
          4a - 为每个成功的编码子任务（eda/quesN/sensitivity/comparison）撰写求解部分
          4b - 撰写前置章节（标题摘要、问题重述、问题分析、模型假设、符号说明）
               和后置章节（模型评价、结论与建议）

        Args:
            task_id: 任务ID
            work_dir: 工作目录
            writer_llm: Writer 使用的 LLM 实例
            problem: 问题描述对象
            modeling_response: 建模阶段输出的 ModelerToCoder 响应
        """
        await self._send_stage_start(
            task_id,
            WorkflowStage.WRITING,
            "✍️ 第4阶段：撰写建模报告",
            "基于建模结果撰写完整竞赛级论文"
        )

        # 从历史中获取编码阶段结果
        coding_data = self.state.get_stage_data(WorkflowStage.CODING)
        if not coding_data:
            raise ValueError("缺少编码阶段数据")

        results = coding_data.get("results", {})
        successful_results = {k: v for k, v in results.items() if v.get("success")}

        # === 构建 Flows 所需的 questions 字典 ===
        # 优先从协调者获取（包含 background + quesN），其次从建模响应中提取
        questions: dict[str, str] = {}
        if self._coordinator:
            questions = getattr(self._coordinator, 'questions', {})
        if not questions:
            questions_solution = getattr(modeling_response, 'questions_solution', {})
            questions = dict(questions_solution)
        # 确保 background 键存在，get_writer_prompt 内部会访问 self.questions["background"]
        if "background" not in questions:
            questions["background"] = problem.ques_all

        flows = Flows(questions)
        config_template = get_config_template(problem.comp_template, problem.format_output)
        # 编码阶段结束后 code_interpreter 已被清理，使用空代理兼容 get_writer_prompt 接口
        null_interpreter = _NullCodeInterpreter()

        # === 统计 quesN 数量，用于 UserOutput 初始化正确的章节序列 ===
        ques_count = sum(
            1 for k in questions if k.startswith("ques") and k[4:].isdigit()
        )

        # 创建写作者
        scholar = OpenAlexScholar(task_id=task_id, email=settings.OPENALEX_EMAIL)
        writer_agent = WriterAgent(
            task_id=task_id,
            model=writer_llm,
            comp_template=problem.comp_template,
            format_output=problem.format_output,
            scholar=scholar,
        )

        # 构建用户输出（ques_count 决定 _init_seq 中 ques1..N 的数量）
        user_output = UserOutput(
            work_dir=work_dir,
            ques_count=ques_count,
            comp_template=problem.comp_template,
        )

        # === 从编码结果中提取指标并注入 user_output ===
        for key, result_data in successful_results.items():
            coder_resp = result_data.get("response")
            if not coder_resp:
                continue
            # 尝试从 code_response 文本中提取结构化指标
            code_response_text = getattr(coder_resp, 'code_response', '') or ''
            if code_response_text:
                metrics = Flows.extract_metrics_from_code_output(code_response_text)
                if metrics:
                    user_output.set_metrics(key, metrics)
                    logger.info("子任务 %s 提取到指标: %s", key, metrics)

        # === 阶段 4a: 为每个成功的编码子任务撰写求解部分 ===
        for key, result_data in successful_results.items():
            coder_response = result_data.get("response")
            if not coder_response:
                continue

            await redis_manager.publish_message(
                task_id,
                SystemMessage(content=f"📝 正在撰写: {key}", type="info")
            )

            try:
                # === Coder 失败时的 Writer 降级策略 ===
                if getattr(coder_response, "failed", False):
                    _degraded_parts = [
                        f"## 写作任务：{key}（降级模式）\n",
                        (
                            "**重要提示**：本问题的代码求解未能成功完成。\n"
                            "请仅基于建模手的方案撰写【模型建立】部分，"
                            "包括：\n"
                            "1. 理论描述和数学公式推导\n"
                            "2. 算法步骤和流程说明\n"
                            "3. 模型的适用条件和假设\n\n"
                            "**禁止事项**：\n"
                            "- 不要编造任何数值结果、表格数据或图表引用\n"
                            "- 不要假装有计算结果\n"
                            "- 在章节末尾注明'由于计算资源限制，"
                            "本问题的数值求解结果待补充'\n"
                        ),
                    ]
                    # 从建模方案中提取该子任务的方法论描述
                    _mc = (
                        modeling_response.get_model_config(key)
                        if modeling_response
                        else None
                    )
                    if _mc:
                        _method_parts: list[str] = []
                        if _mc.model_name:
                            _method_parts.append(
                                f"模型名称: {_mc.model_name}"
                            )
                        if _mc.model_category:
                            _method_parts.append(
                                f"模型类别: {_mc.model_category}"
                            )
                        if getattr(_mc, "approach_baseline", None):
                            _method_parts.append(
                                f"基准方法: {_mc.approach_baseline}"
                            )
                        if getattr(_mc, "approach_improved", None):
                            _method_parts.append(
                                f"改进方法: {_mc.approach_improved}"
                            )
                        if _method_parts:
                            _degraded_parts.append(
                                "\n### 建模方案\n"
                                + "\n".join(_method_parts)
                                + "\n"
                            )

                    _template = config_template.get(key, "")
                    if _template:
                        _degraded_parts.append(
                            f"\n### 参考模板格式\n{_template}\n"
                        )

                    writer_prompt = "\n".join(_degraded_parts)
                    logger.info(
                        "子任务 %s Coder 失败，使用降级 Writer prompt",
                        key,
                    )
                else:
                    # 使用 flows.get_writer_prompt 构建完整 prompt（含建模方案、图表、指标注入）
                    writer_prompt = flows.get_writer_prompt(
                        key,
                        getattr(coder_response, 'code_response', '') or '',
                        null_interpreter,
                        config_template,
                        modeler_response=modeling_response,
                    )

                # 图片文件存在性验证
                raw_images = getattr(coder_response, 'created_images', [])
                validated_images = []
                if raw_images:
                    for img_path in raw_images:
                        full_path = (
                            os.path.join(work_dir, img_path)
                            if not os.path.isabs(img_path)
                            else img_path
                        )
                        if os.path.isfile(full_path):
                            validated_images.append(img_path)
                        else:
                            logger.warning("图片文件不存在，跳过: %s", img_path)

                writer_response = await writer_agent.run(
                    writer_prompt,
                    available_images=validated_images if validated_images else None,
                    sub_title=key,
                )
                user_output.set_res(key, writer_response)

                # 增量持久化
                try:
                    user_output.save_result()
                    logger.debug("子任务 %s 增量保存成功", key)
                except Exception as save_err:
                    logger.warning("子任务 %s 增量保存失败: %s", key, save_err)

            except Exception as e:
                logger.error("撰写 %s 失败: %s", key, e)
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(content=f"⚠️ 撰写 {key} 失败", type="warning")
                )

        # === 指标汇总注入写作上下文 ===
        comparison_summary = user_output.generate_comparison_summary()
        if comparison_summary:
            logger.info("生成模型对比摘要")
            user_output.model_comparison_data = comparison_summary

        # === 阶段 4b: 撰写前置/后置章节 ===
        write_flows = flows.get_write_flows(
            user_output,
            config_template,
            problem.ques_all,
            modeler_response=modeling_response,
            comp_template=problem.comp_template,
        )

        total_write_steps = len(write_flows)
        for idx, (key, value) in enumerate(write_flows.items()):
            await redis_manager.publish_message(
                task_id,
                SystemMessage(
                    content=f"📝 正在撰写: {key}（{idx + 1}/{total_write_steps}）",
                    type="info"
                )
            )

            try:
                # 注入已完成章节摘要，保持论文连贯性
                completed_summaries = user_output.get_completed_chapter_summaries(
                    max_per_chapter=150, max_total=2000
                )
                if completed_summaries:
                    value += (
                        f"\n\n【前序已完成章节摘要（请保持论述连贯性和术语一致性）】\n"
                        f"{completed_summaries}\n"
                    )

                writer_response = await writer_agent.run(prompt=value, sub_title=key)
                user_output.set_res(key, writer_response)

                # 增量持久化
                try:
                    user_output.save_result()
                except Exception as save_err:
                    logger.warning("写作章节 %s 增量保存失败: %s", key, save_err)

            except Exception as e:
                logger.error("撰写章节 %s 失败: %s", key, e)
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(content=f"⚠️ 撰写 {key} 失败", type="warning")
                )

        # 最终保存完整论文
        user_output.save_result()

        # 保存写作阶段状态
        self.state.save_stage(WorkflowStage.WRITING, {"output": user_output})

    # ============= 用户操作处理方法 =============

    async def handle_user_action(self, task_id: str, action: dict):
        """
        处理前端发送的用户操作

        Args:
            task_id: 任务ID
            action: 用户操作数据
        """
        action_key = f"user_action:{task_id}"
        await redis_manager.set_json(action_key, action, expire=300)
        logger.info("收到用户操作: task=%s, action=%s", task_id, action)


class UserCancellationError(Exception):
    """用户取消操作异常"""
    pass


class RollbackError(Exception):
    """回滚异常"""
    def __init__(self, stage: WorkflowStage):
        self.stage = stage
        super().__init__(f"回滚到阶段: {stage.value}")
