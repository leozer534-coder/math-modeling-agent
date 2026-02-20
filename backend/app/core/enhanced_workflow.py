"""
增强型数学建模工作流 - 多阶段迭代优化系统

8 阶段设计:
1. COORDINATE - CoordinatorAgent 分析问题
2. RESEARCH - KnowledgeBase 查询（可选）
3. MODEL - ModelerAgent 设计方案
4. SETUP - 代码解释器初始化
5. SOLVE - CoderAgent + 反馈环路（失败可回传 Modeler revise）
6. REVIEW - Reviewer 5维度评分，低于阈值触发重做
7. WRITE - WriterAgent 撰写论文
8. FINALIZE - 保存结果 + 评测报告

安全机制:
- max_feedback_iterations=2
- max_workflow_iterations=2
- STAGE_TIMEOUT=600s
- WORKFLOW_TIMEOUT=3600s
- 崩溃时降级到标准模式
"""

import asyncio
import time
import traceback
from typing import Any, Optional

from app.config.setting import settings
from app.core.agents import CoderAgent, CoordinatorAgent, ModelerAgent, WriterAgent
from app.core.flows import Flows
from app.core.llm.llm_factory import LLMFactory
from app.core.math_model_workflow import (
    MathModelWorkFlow,
    PhaseResult,
    WorkflowPhase,
    WorkflowState,
)
from app.models.user_output import UserOutput
from app.schemas.A2A import CoderFeedbackToModeler, ReviewFeedback
from app.schemas.request import Problem
from app.schemas.response import ProgressMessage, SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.common_utils import create_work_dir, generate_data_summary, get_config_template
from app.utils.log_util import logger

class EnhancedWorkflowPhase(str):
    """增强工作流阶段常量"""
    COORDINATE = "coordinate"
    RESEARCH = "research"
    MODEL = "model"
    SETUP = "setup"
    SOLVE = "solve"
    REVIEW = "review"
    WRITE = "write"
    FINALIZE = "finalize"


class EnhancedMathModelWorkFlow:
    """
    增强型数学建模工作流

    在标准 MathModelWorkFlow 基础上增加:
    - 反馈环路: Coder 失败时可回传 Modeler 修改方案
    - 质量审核: Reviewer 评分低于阈值触发重做
    - 安全机制: 超时保护、最大迭代限制、降级兜底
    """

    # 安全限制
    MAX_FEEDBACK_ITERATIONS = 2  # 单个子任务最大反馈轮次
    MAX_WORKFLOW_ITERATIONS = 2  # 全局最大工作流迭代轮次
    STAGE_TIMEOUT = 600  # 单阶段超时（秒）
    WORKFLOW_TIMEOUT = 3600  # 工作流总超时（秒）
    REVIEW_PASS_THRESHOLD = 60.0  # 评审通过阈值（0-100）

    def __init__(self, agent_configs: dict | None = None):
        self.state: Optional[WorkflowState] = None
        self._code_interpreter = None
        self._agents: dict[str, Any] = {}
        self._llms: dict[str, Any] = {}
        self._workflow_start_time: float = 0.0
        self._current_iteration: int = 0
        # 用户级 API 配置（多租户隔离）
        self._agent_configs = agent_configs

    async def execute(self, problem: Problem):
        """
        执行增强型数学建模工作流

        Args:
            problem: 问题定义
        """
        task_id = problem.task_id
        work_dir = create_work_dir(task_id)

        self.state = WorkflowState(task_id=task_id)
        self._workflow_start_time = time.time()

        try:
            # 阶段 1: COORDINATE - 协调者分析问题
            coordinator_response = await self._execute_with_timeout(
                self._phase_coordinate(problem, task_id, work_dir),
                "COORDINATE"
            )
            questions = coordinator_response.questions
            ques_count = coordinator_response.ques_count

            # 阶段 2: RESEARCH - 知识库查询（尽力而为，不阻塞）
            research_context = await self._execute_with_timeout(
                self._phase_research(task_id, questions),
                "RESEARCH",
                optional=True
            )

            # 阶段 3: MODEL - 建模者设计方案
            modeler_response = await self._execute_with_timeout(
                self._phase_model(task_id, coordinator_response, research_context, work_dir),
                "MODEL"
            )

            # 阶段 4: SETUP - 环境设置
            setup_data = await self._execute_with_timeout(
                self._phase_setup(problem, task_id, work_dir, ques_count),
                "SETUP"
            )

            # 阶段 5: SOLVE - 代码求解 + 反馈环路
            solution_results = await self._execute_with_timeout(
                self._phase_solve_with_feedback(
                    problem, task_id, questions, modeler_response,
                    setup_data["flows"], setup_data["config_template"]
                ),
                "SOLVE",
                timeout=self.STAGE_TIMEOUT * 3  # 求解阶段给更多时间
            )

            # 阶段 6: REVIEW - 质量审核
            review_result = await self._execute_with_timeout(
                self._phase_review(
                    task_id, solution_results, questions, modeler_response,
                    problem, setup_data["flows"], setup_data["config_template"]
                ),
                "REVIEW",
                optional=True
            )

            # 阶段 7: WRITE - 论文写作
            await self._execute_with_timeout(
                self._phase_write(
                    problem, task_id, solution_results,
                    setup_data["flows"], setup_data["config_template"],
                    review_result
                ),
                "WRITE"
            )

            # 阶段 8: FINALIZE - 保存结果
            await self._execute_with_timeout(
                self._phase_finalize(task_id),
                "FINALIZE"
            )

            self.state.current_phase = WorkflowPhase.COMPLETED
            await self._send_progress(task_id, "增强工作流完成", 100)
            # 任务完成后清理文件锁，防止内存泄漏
            redis_manager.cleanup_task_lock(task_id)

        except Exception as e:
            logger.error("增强工作流执行失败: %s\n%s", e, traceback.format_exc())

            # 尝试降级到标准模式
            if self._should_fallback(e):
                logger.warning("增强工作流失败，降级到标准模式...")
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(
                        content="增强模式遇到问题，自动降级到标准模式继续执行...",
                        type="warning"
                    )
                )
                try:
                    await self._cleanup()
                    standard_workflow = MathModelWorkFlow(agent_configs=self._agent_configs)
                    await standard_workflow.execute(problem)
                    return
                except Exception as fallback_error:
                    logger.error("降级执行也失败: %s", fallback_error)

            self.state.current_phase = WorkflowPhase.FAILED
            await redis_manager.publish_message(
                task_id,
                SystemMessage(
                    content=f"任务执行失败: {str(e)[:200]}",
                    type="error"
                )
            )
            # 异常路径清理任务文件锁，防止内存泄漏
            redis_manager.cleanup_task_lock(task_id)
            raise

        finally:
            await self._cleanup()

    # ==================== 阶段实现 ====================

    async def _phase_coordinate(self, problem: Problem, task_id: str, work_dir: str):
        """阶段 1: 协调者分析问题"""
        await self._send_progress(task_id, "正在分析问题...", 5)

        llm_factory = LLMFactory(task_id, self._agent_configs)
        coordinator_llm, modeler_llm, coder_llm, writer_llm = llm_factory.get_all_llms()

        self._llms = {
            "coordinator": coordinator_llm,
            "modeler": modeler_llm,
            "coder": coder_llm,
            "writer": writer_llm,
        }

        coordinator_agent = CoordinatorAgent(task_id, coordinator_llm)
        self._agents["coordinator"] = coordinator_agent

        coordinator_response = await coordinator_agent.run(problem.ques_all)

        await self._send_progress(
            task_id,
            f"问题分析完成，共 {coordinator_response.ques_count} 个子问题",
            10
        )
        return coordinator_response

    async def _phase_research(self, task_id: str, questions: dict) -> Optional[dict]:
        """阶段 2: 知识库查询（可选）"""
        await self._send_progress(task_id, "正在查询知识库...", 12)

        research_context = {}
        try:
            # 尝试导入并使用知识库模块
            from app.core.knowledge_base import KnowledgeBase
            kb = KnowledgeBase()
            research_context = await kb.query_for_problem(questions)
            logger.info("知识库查询完成，获取 %s 条相关知识", len(research_context))
        except ImportError:
            logger.info("知识库模块未安装，跳过研究阶段")
        except Exception as e:
            logger.warning("知识库查询失败（非关键）: %s", e)

        await self._send_progress(task_id, "知识查询完成", 15)
        return research_context

    async def _phase_model(self, task_id: str, coordinator_response, research_context: Optional[dict], work_dir: str):
        """阶段 3: 建模者设计方案（注入研究上下文和数据摘要）"""
        await self._send_progress(task_id, "正在设计建模方案...", 18)

        modeler_agent = ModelerAgent(task_id, self._llms["modeler"])
        self._agents["modeler"] = modeler_agent

        # 生成数据摘要，为 Modeler 提供数据感知能力
        # generate_data_summary 是同步 I/O 函数，使用 to_thread 避免阻塞事件循环
        data_context = await asyncio.to_thread(generate_data_summary, work_dir)
        if data_context:
            logger.info("数据摘要已生成，长度: %d 字符", len(data_context))

        # 将研究上下文格式化为字符串，注入 Modeler
        research_str = None
        if research_context:
            try:
                import json
                research_str = json.dumps(research_context, ensure_ascii=False, indent=2)
                logger.info("注入研究上下文到 Modeler (%s 字符)", len(research_str))
            except Exception as e:
                logger.warning("研究上下文序列化失败: %s", e)

        modeler_response = await modeler_agent.run(
            coordinator_response,
            data_context=data_context,
            research_context=research_str,
        )

        await self._send_progress(task_id, "建模方案设计完成", 25)
        return modeler_response

    async def _phase_setup(self, problem: Problem, task_id: str, work_dir: str, ques_count: int):
        """阶段 4: 环境设置"""
        await self._send_progress(task_id, "正在准备执行环境...", 28)

        # 创建代码解释器
        notebook_serializer = NotebookSerializer(work_dir=work_dir)
        self._code_interpreter = await create_interpreter(
            kind="auto",
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
        )

        # 创建文献搜索器
        scholar = OpenAlexScholar(
            task_id=task_id,
            email=settings.OPENALEX_EMAIL
        )

        # 创建 Agent
        coder_agent = CoderAgent(
            task_id=task_id,
            model=self._llms["coder"],
            work_dir=work_dir,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            code_interpreter=self._code_interpreter,
        )
        self._agents["coder"] = coder_agent

        writer_agent = WriterAgent(
            task_id=task_id,
            model=self._llms["writer"],
            comp_template=problem.comp_template,
            format_output=problem.format_output,
            scholar=scholar,
        )
        self._agents["writer"] = writer_agent

        # 用户输出
        self._user_output = UserOutput(
            work_dir=work_dir,
            ques_count=ques_count,
            comp_template=problem.comp_template,
        )

        # 构建流程
        questions = self._agents["coordinator"]._last_response.questions \
            if hasattr(self._agents.get("coordinator", None), "_last_response") \
            else self.state.phase_results.get("coordinate", PhaseResult(
                phase=WorkflowPhase.COORDINATE, success=True
            )).data.questions

        flows = Flows(questions)
        config_template = get_config_template(problem.comp_template, problem.format_output)

        await self._send_progress(task_id, "执行环境准备完成", 32)

        return {
            "flows": flows,
            "config_template": config_template,
            "questions": questions,
        }

    async def _phase_solve_with_feedback(
        self, problem: Problem, task_id: str, questions: dict,
        modeler_response, flows: Flows, config_template: dict
    ):
        """
        阶段 5: 代码求解 + 反馈环路

        核心逻辑:
        - 每个子任务执行 CoderAgent
        - 如果 Coder 返回 needs_remodel=True，触发反馈环路
        - 反馈环路: 将错误信息发送给 Modeler 修订方案，再让 Coder 重新执行
        - 最大反馈轮次: MAX_FEEDBACK_ITERATIONS
        """
        solution_flows = flows.get_solution_flows(questions, modeler_response)

        total_steps = len(solution_flows)
        coder_agent = self._agents["coder"]
        modeler_agent = self._agents["modeler"]
        writer_agent = self._agents["writer"]

        solution_results = {}
        current_solution = modeler_response.questions_solution.copy()
        step_idx = 0

        for key, value in solution_flows.items():
            step_idx += 1
            progress = 32 + (step_idx / total_steps) * 30

            await self._send_progress(
                task_id,
                f"正在求解: {key} ({step_idx}/{total_steps})",
                progress,
                sub_phase="solve",
                iteration=0,
                max_iterations=self.MAX_FEEDBACK_ITERATIONS
            )

            # 检查工作流超时
            if self._is_workflow_timeout():
                logger.warning("工作流超时，跳过剩余子任务")
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(
                        content=f"工作流超时，{key} 及后续子任务将被跳过",
                        type="warning"
                    )
                )
                break

            try:
                # 反馈环路
                iteration = 0
                coder_response = None

                while iteration <= self.MAX_FEEDBACK_ITERATIONS:
                    # 执行 Coder（动态构建 prompt）
                    coder_prompt = Flows.build_coder_prompt(value)
                    coder_response = await coder_agent.run(
                        prompt=coder_prompt,
                        subtask_title=key
                    )

                    # 检查是否需要重新建模
                    if coder_response.needs_remodel and iteration < self.MAX_FEEDBACK_ITERATIONS:
                        logger.info(
                            f"子任务 {key} 需要重新建模 "
                            f"(反馈轮次 {iteration + 1}/{self.MAX_FEEDBACK_ITERATIONS})"
                        )

                        await self._send_progress(
                            task_id,
                            f"子任务 {key} 触发反馈环路，正在修订建模方案...",
                            progress,
                            sub_phase="feedback",
                            iteration=iteration + 1,
                            max_iterations=self.MAX_FEEDBACK_ITERATIONS
                        )

                        # 构造反馈信号
                        feedback = CoderFeedbackToModeler(
                            subtask_key=key,
                            error_summary=coder_response.error_summary or "代码执行失败",
                            failed_approach=current_solution.get(key, ""),
                            alternative_suggestion="请使用更简单、更可靠的方法",
                            retry_count=iteration + 1,
                        )

                        # 发送反馈给 Modeler 修订
                        revised_response = await modeler_agent.revise(
                            feedback, current_solution
                        )

                        # 更新方案
                        current_solution = revised_response.questions_solution
                        # 更新元数据，下一轮循环会通过 build_coder_prompt 重新构建 prompt
                        value["solution"] = current_solution.get(key, "")
                        if "question" in value:
                            value["question"] = questions.get(key, key)

                        iteration += 1
                        continue

                    # 不需要重新建模或已达最大反馈轮次，退出循环
                    break

                # 生成写作提示并执行写作
                writer_prompt = flows.get_writer_prompt(
                    key,
                    coder_response.code_response,
                    self._code_interpreter,
                    config_template
                )

                await self._send_progress(task_id, f"正在撰写: {key}", progress + 3)

                writer_response = await writer_agent.run(
                    writer_prompt,
                    available_images=coder_response.created_images,
                    sub_title=key,
                )

                self._user_output.set_res(key, writer_response)

                solution_results[key] = {
                    "coder_response": coder_response,
                    "writer_response": writer_response,
                    "success": True,
                    "feedback_iterations": iteration,
                }

            except Exception as e:
                logger.error("求解 %s 失败: %s", key, e)
                solution_results[key] = {
                    "success": False,
                    "error": str(e),
                }

                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(
                        content=f"子任务 {key} 求解遇到问题，已跳过",
                        type="warning"
                    )
                )

        # 关闭代码解释器
        if self._code_interpreter:
            await self._code_interpreter.cleanup()
            self._code_interpreter = None

        return solution_results

    async def _phase_review(
        self, task_id: str, solution_results: dict,
        questions: dict, modeler_response,
        problem: Problem, flows: Flows, config_template: dict
    ) -> Optional[ReviewFeedback]:
        """
        阶段 6: 质量审核

        使用 Reviewer 进行 5 维度评分:
        - 低于阈值时标记最弱子任务，供后续改进
        - 不在此阶段重做（避免过于激进），仅记录反馈
        """
        await self._send_progress(task_id, "正在进行质量审核...", 68)

        try:
            from app.core.agents.reviewer import Reviewer

            reviewer = Reviewer(
                task_id=task_id,
                model=self._llms.get("coordinator", self._llms["modeler"])
            )

            # 构造评审输入
            review_input = {}
            for key, result in solution_results.items():
                if result.get("success"):
                    coder_resp = result.get("coder_response")
                    review_input[key] = {
                        "code_response": coder_resp.code_response if coder_resp else "",
                        "has_images": bool(coder_resp.created_images) if coder_resp else False,
                        "feedback_iterations": result.get("feedback_iterations", 0),
                    }
                else:
                    review_input[key] = {
                        "code_response": f"失败: {result.get('error', '未知错误')}",
                        "has_images": False,
                        "feedback_iterations": 0,
                    }

            quality_review = await reviewer.execute(review_input)

            # 将 Reviewer 的 5 分制评分转换为 0-100 分制
            overall_score = quality_review.overall_rating * 20.0

            await self._send_progress(
                task_id,
                f"质量审核完成，评分: {overall_score:.0f}/100",
                72,
                quality_score=overall_score
            )

            # 构造 ReviewFeedback
            review_feedback = ReviewFeedback(
                overall_score=overall_score,
                dimension_scores={
                    "content": quality_review.content_quality.get("average_score", 3) * 20,
                    "methodology": quality_review.methodology_quality.get("average_score", 3) * 20,
                    "result": quality_review.result_quality.get("average_score", 3) * 20,
                    "writing": quality_review.writing_quality.get("average_score", 3) * 20,
                    "innovation": quality_review.innovation_assessment.get("average_score", 3) * 20,
                },
                weakest_subtasks=[
                    key for key, result in solution_results.items()
                    if not result.get("success")
                ],
                feedback={
                    key: result.get("error", "")
                    for key, result in solution_results.items()
                    if not result.get("success")
                },
                suggestions=[
                    s.get("suggestion", "")
                    for s in quality_review.suggestions_for_improvement
                ],
            )

            if overall_score < self.REVIEW_PASS_THRESHOLD:
                logger.warning(
                    f"质量评分 {overall_score:.0f} 低于阈值 {self.REVIEW_PASS_THRESHOLD}，"
                    f"最弱子任务: {review_feedback.weakest_subtasks}"
                )
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(
                        content=f"质量评分 {overall_score:.0f}/100 低于阈值，"
                                f"建议关注: {', '.join(review_feedback.weakest_subtasks[:3])}",
                        type="warning"
                    )
                )

            return review_feedback

        except ImportError:
            logger.info("Reviewer 模块不可用，跳过质量审核")
            return None
        except Exception as e:
            logger.warning("质量审核失败（非关键）: %s", e)
            return None

    async def _phase_write(
        self, problem: Problem, task_id: str,
        solution_results: dict, flows: Flows,
        config_template: dict, review_result: Optional[ReviewFeedback]
    ):
        """阶段 7: 论文写作"""
        await self._send_progress(task_id, "正在撰写论文其他部分...", 75)

        write_flows = flows.get_write_flows(
            self._user_output,
            config_template,
            problem.ques_all,
            comp_template=problem.comp_template,
        )

        writer_agent = self._agents["writer"]
        total_write_steps = len(write_flows)
        step_idx = 0

        for key, value in write_flows.items():
            step_idx += 1
            progress = 75 + (step_idx / total_write_steps) * 18

            await self._send_progress(task_id, f"正在撰写: {key}", progress)

            try:
                writer_response = await writer_agent.run(
                    prompt=value,
                    sub_title=key
                )
                self._user_output.set_res(key, writer_response)

            except Exception as e:
                logger.error("写作 %s 失败: %s", key, e)
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(
                        content=f"写作 {key} 遇到问题",
                        type="warning"
                    )
                )

        await self._send_progress(task_id, "论文撰写完成", 93)

    async def _phase_finalize(self, task_id: str):
        """阶段 8: 保存结果"""
        await self._send_progress(task_id, "正在保存结果...", 95)

        self._user_output.save_result()

        elapsed = time.time() - self._workflow_start_time

        logger.info(
            f"增强工作流完成: task_id={task_id}, "
            f"耗时={elapsed/60:.1f}分钟"
        )

        await redis_manager.publish_message(
            task_id,
            SystemMessage(
                content=f"增强工作流完成! 总用时: {elapsed/60:.1f}分钟",
                type="success"
            )
        )

    # ==================== 工具方法 ====================

    async def _execute_with_timeout(
        self, coro, phase_name: str,
        timeout: Optional[float] = None,
        optional: bool = False
    ):
        """
        带超时保护的阶段执行器

        Args:
            coro: 协程
            phase_name: 阶段名称
            timeout: 超时秒数（默认 STAGE_TIMEOUT）
            optional: 是否为可选阶段（失败不中断工作流）
        """
        effective_timeout = timeout or self.STAGE_TIMEOUT
        start_time = time.time()

        logger.info("开始执行阶段: %s (超时: %ss)", phase_name, effective_timeout)

        try:
            result = await asyncio.wait_for(coro, timeout=effective_timeout)

            duration = time.time() - start_time
            logger.info("阶段 %s 完成，耗时: %.2f秒", phase_name, duration)

            # 记录阶段结果
            if self.state:
                self.state.phase_results[phase_name] = PhaseResult(
                    phase=WorkflowPhase(phase_name) if phase_name in [p.value for p in WorkflowPhase] else WorkflowPhase.INIT,
                    success=True,
                    duration=duration,
                    data=result
                )
                self.state.phases_completed.append(phase_name)

            return result

        except asyncio.TimeoutError:
            logger.error("阶段 %s 超时 (%ss)", phase_name, effective_timeout)
            if optional:
                logger.warning("可选阶段 %s 超时，跳过", phase_name)
                return None
            raise TimeoutError(f"阶段 {phase_name} 执行超时 ({effective_timeout}s)")

        except Exception as e:
            logger.error("阶段 %s 失败: %s", phase_name, e)
            if optional:
                logger.warning("可选阶段 %s 失败，跳过: %s", phase_name, e)
                return None
            raise

    def _is_workflow_timeout(self) -> bool:
        """检查工作流是否已超时"""
        elapsed = time.time() - self._workflow_start_time
        return elapsed >= self.WORKFLOW_TIMEOUT

    def _should_fallback(self, error: Exception) -> bool:
        """判断是否应该降级到标准模式"""
        # 以下情况不降级: 用户取消、系统退出
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            return False
        # 其他情况都尝试降级
        return True

    async def _send_progress(
        self, task_id: str, message: str, percent: float,
        sub_phase: str = "", iteration: int = 0,
        max_iterations: int = 0, quality_score: float = 0.0
    ):
        """发送进度消息"""
        if self.state:
            self.state.update_progress(message, int(percent))

        await redis_manager.publish_message(
            task_id,
            SystemMessage(content=message, type="info")
        )

        try:
            elapsed = time.time() - self._workflow_start_time
            await redis_manager.publish_message(
                task_id,
                ProgressMessage(
                    percent=percent,
                    phase="enhanced",
                    message=message,
                    elapsed_time=elapsed,
                    sub_phase=sub_phase,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    quality_score=quality_score,
                )
            )
        except Exception as e:
            logger.debug("进度消息发送失败（不影响主流程）: %s", e)

    async def _cleanup(self):
        """清理资源"""
        try:
            if self._code_interpreter:
                await self._code_interpreter.cleanup()
                self._code_interpreter = None
        except Exception as e:
            logger.warning("清理代码解释器失败: %s", e)
