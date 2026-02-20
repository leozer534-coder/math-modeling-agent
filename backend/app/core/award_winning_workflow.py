"""
获奖级增强工作流引擎 - Award-Winning Enhanced Workflow
整合所有新功能，实现从问题到获奖论文的全流程自动化

整合模块：
1. ResearchCoordinator - 背景研究
2. AssumptionGenerator - 假设生成
3. MultiModelStrategy - 多模型策略
4. SensitivityAnalyzer - 敏感性分析
5. AutoValidator - 自动验证
6. QualityChecker - 质量闸门
7. AbstractGenerator - 摘要生成
8. LaTeXGenerator - LaTeX输出
"""
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.config.setting import settings
from app.core.agents import CoderAgent, CoordinatorAgent, ModelerAgent, WriterAgent
from app.core.agents.abstract_generator import (
    AbstractGenerator,
    AbstractLanguage,
    AbstractStyle,
)
from app.core.flows import Flows
from app.core.hil import HILDecision, HILManager
from app.core.knowledge_base import knowledge_base
from app.core.llm.llm_factory import LLMFactory
from app.core.memory import MemoryManager, create_memory_manager
from app.core.modeling.auto_validator import AutoValidator
from app.core.modeling.multi_model_strategy import MultiModelPlan, MultiModelStrategy
from app.core.modeling.sensitivity_analyzer import (
    SensitivityAnalyzer,
    SensitivityReport,
)
from app.core.paper.latex_export import generate_latex_from_markdown
from app.core.quality.quality_gates import GateResult, QualityChecker
from app.core.research.assumption_generator import (
    AssumptionGenerator,
    GeneratedAssumption,
)
from app.core.research.research_coordinator import ResearchCoordinator, ResearchType
from app.core.workflow_enhancer import WorkflowEnhancer, create_workflow_enhancer
from app.models.user_output import UserOutput
from app.schemas.A2A import CoderFeedbackToModeler, WriterResponse
from app.schemas.request import Problem
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.utils.common_utils import create_work_dir, get_config_template
from app.utils.log_util import logger


class EnhancedWorkflowPhase(str, Enum):
    INIT = "init"
    RESEARCH = "research"
    ASSUMPTIONS = "assumptions"
    COORDINATE = "coordinate"
    MODEL_STRATEGY = "model_strategy"
    MODEL = "model"
    SETUP = "setup"
    SOLVE = "solve"
    VALIDATE = "validate"
    SENSITIVITY = "sensitivity"
    QUALITY_CHECK = "quality_check"
    ABSTRACT = "abstract"
    WRITE = "write"
    LATEX = "latex"
    FINALIZE = "finalize"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EnhancedPhaseResult:
    phase: EnhancedWorkflowPhase
    success: bool
    duration: float = 0.0
    error: Optional[str] = None
    data: Any = None


@dataclass
class EnhancedWorkflowState:
    task_id: str
    current_phase: EnhancedWorkflowPhase = EnhancedWorkflowPhase.INIT
    phases_completed: List[str] = field(default_factory=list)
    phase_results: Dict[str, EnhancedPhaseResult] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    total_steps: int = 0
    completed_steps: int = 0
    current_step_name: str = ""
    
    enable_research: bool = True
    enable_assumptions: bool = True
    enable_model_strategy: bool = True
    enable_sensitivity: bool = True
    enable_validation: bool = True
    enable_quality_check: bool = True
    enable_abstract: bool = True
    enable_latex: bool = True
    paper_language: str = "zh"
    
    assumptions: List[GeneratedAssumption] = field(default_factory=list)
    model_plan: Optional[MultiModelPlan] = None
    sensitivity_report: Optional[SensitivityReport] = None
    quality_results: Dict[str, GateResult] = field(default_factory=dict)
    
    def update_progress(self, step_name: str, completed: Optional[int] = None):
        self.current_step_name = step_name
        if completed is not None:
            self.completed_steps = completed
    
    def get_progress_percent(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "current_phase": self.current_phase.value,
            "phases_completed": self.phases_completed,
            "progress_percent": self.get_progress_percent(),
            "elapsed_time": self.get_elapsed_time(),
            "current_step": self.current_step_name,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
        }


class AwardWinningWorkflow:
    
    task_id: str
    work_dir: str
    ques_count: int = 0
    questions: Dict[str, Any] = {}
    
    def __init__(
        self,
        enable_research: bool = True,
        enable_assumptions: bool = True,
        enable_model_strategy: bool = True,
        enable_sensitivity: bool = True,
        enable_validation: bool = True,
        enable_quality_check: bool = True,
        enable_abstract: bool = True,
        enable_latex: bool = True,
        paper_language: str = "zh",
        enable_hil: bool = False,
        hil_auto_approve: bool = True,
        hil_timeout: int = 300,
        agent_configs: dict | None = None,
    ):
        self._code_interpreter = None
        self._agents: Dict[str, Any] = {}
        self._llms: Dict[str, Any] = {}

        self.enable_research = enable_research
        self.enable_assumptions = enable_assumptions
        self.enable_model_strategy = enable_model_strategy
        self.enable_sensitivity = enable_sensitivity
        self.enable_validation = enable_validation
        self.enable_quality_check = enable_quality_check
        self.enable_abstract = enable_abstract
        self.enable_latex = enable_latex
        self.paper_language = paper_language

        self.enable_hil = enable_hil
        self.hil_auto_approve = hil_auto_approve
        self.hil_timeout = hil_timeout
        self._hil_manager: Optional[HILManager] = None

        self.state: Optional[EnhancedWorkflowState] = None

        self.research_report = None
        self.killer_abstract = None
        self._validation_results: Dict[str, Any] = {}
        self._quality_results: Dict[str, GateResult] = {}
        self._sensitivity_suggestion: str = ""
        self._quality_summary_appended = False

        self._assumption_generator: Optional[AssumptionGenerator] = None
        self._model_strategy: Optional[MultiModelStrategy] = None
        self._sensitivity_analyzer: Optional[SensitivityAnalyzer] = None
        self._auto_validator: Optional[AutoValidator] = None
        self._quality_checker: Optional[QualityChecker] = None

        # 记忆系统
        self._memory_manager: Optional[MemoryManager] = None
        self._enable_memory: bool = True  # 是否启用记忆系统

        # 工作流增强器
        self._workflow_enhancer: Optional[WorkflowEnhancer] = None

        # 用户级 API 配置（多租户隔离）
        self._agent_configs = agent_configs
        self._enable_enhancement: bool = True  # 是否启用工作流增强
    
    async def execute(self, problem: Problem):
        self.task_id = problem.task_id
        self.work_dir = create_work_dir(self.task_id)
        self._problem_description = problem.ques_all  # 保存问题描述用于记忆系统
        
        if self.enable_hil:
            self._hil_manager = HILManager(
                task_id=self.task_id,
                auto_approve=self.hil_auto_approve,
                default_timeout=self.hil_timeout,
            )
        
        # 初始化记忆系统
        if self._enable_memory:
            self._memory_manager = create_memory_manager(
                task_id=self.task_id,
                storage_path=f"{self.work_dir}/memory"
            )
            # 检索历史建模经验
            try:
                experience = await self._memory_manager.get_experience_for_problem(
                    problem_type="math_modeling",
                    problem_description=problem.ques_all[:500]
                )
                if experience.get("similar_cases"):
                    logger.info("发现 %s 个类似案例", len(experience['similar_cases']))
            except Exception as e:
                logger.warning("检索历史经验失败: %s", e)
        
        # 初始化工作流增强器
        if self._enable_enhancement:
            self._workflow_enhancer = create_workflow_enhancer(self._memory_manager)
            # 增强问题分析
            try:
                enhancement = await self._workflow_enhancer.enhance_problem_analysis(
                    problem_description=problem.ques_all,
                    problem_type="math_modeling"
                )
                if enhancement and enhancement.improvements:
                    logger.info("问题分析增强: %s", ', '.join(enhancement.improvements))
            except Exception as e:
                logger.warning("问题分析增强失败: %s", e)
        
        self.state = EnhancedWorkflowState(
            task_id=self.task_id,
            enable_research=self.enable_research,
            enable_assumptions=self.enable_assumptions,
            enable_model_strategy=self.enable_model_strategy,
            enable_sensitivity=self.enable_sensitivity,
            enable_validation=self.enable_validation,
            enable_quality_check=self.enable_quality_check,
            enable_abstract=self.enable_abstract,
            enable_latex=self.enable_latex,
            paper_language=self.paper_language
        )
        
        try:
            if self.enable_research:
                await self._execute_phase(
                    EnhancedWorkflowPhase.RESEARCH,
                    self._phase_research,
                    problem
                )
            
            if self.enable_assumptions:
                await self._execute_phase(
                    EnhancedWorkflowPhase.ASSUMPTIONS,
                    self._phase_assumptions,
                    problem
                )
            
            await self._execute_phase(
                EnhancedWorkflowPhase.COORDINATE,
                self._phase_coordinate,
                problem
            )
            
            if self.enable_model_strategy:
                await self._execute_phase(
                    EnhancedWorkflowPhase.MODEL_STRATEGY,
                    self._phase_model_strategy,
                    problem
                )
            
            modeler_response = await self._execute_phase(
                EnhancedWorkflowPhase.MODEL,
                self._phase_model
            )
            
            await self._execute_phase(
                EnhancedWorkflowPhase.SETUP,
                self._phase_setup,
                problem
            )
            
            solution_results = await self._execute_phase(
                EnhancedWorkflowPhase.SOLVE,
                self._phase_solve,
                problem,
                modeler_response
            )
            
            if self.enable_validation:
                await self._execute_phase(
                    EnhancedWorkflowPhase.VALIDATE,
                    self._phase_validate,
                    solution_results
                )
            
            if self.enable_sensitivity:
                await self._execute_phase(
                    EnhancedWorkflowPhase.SENSITIVITY,
                    self._phase_sensitivity,
                    problem,
                    modeler_response
                )
            
            if self.enable_quality_check:
                await self._execute_phase(
                    EnhancedWorkflowPhase.QUALITY_CHECK,
                    self._phase_quality_check,
                    solution_results
                )
            
            if self.enable_abstract:
                await self._execute_phase(
                    EnhancedWorkflowPhase.ABSTRACT,
                    self._phase_abstract,
                    problem,
                    modeler_response,
                    solution_results
                )
            
            await self._execute_phase(
                EnhancedWorkflowPhase.WRITE,
                self._phase_write,
                problem,
                solution_results
            )
            
            if self.enable_latex:
                await self._execute_phase(
                    EnhancedWorkflowPhase.LATEX,
                    self._phase_latex,
                    problem
                )
            
            await self._execute_phase(
                EnhancedWorkflowPhase.FINALIZE,
                self._phase_finalize
            )
            
            self.state.current_phase = EnhancedWorkflowPhase.COMPLETED
            await self._send_progress("任务完成", 100)
            
        except Exception as e:
            self.state.current_phase = EnhancedWorkflowPhase.FAILED
            logger.error("工作流执行失败: %s\n%s", e, traceback.format_exc())
            
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(
                    content=f"任务执行失败: {str(e)[:200]}",
                    type="error"
                )
            )
            raise
        
        finally:
            await self._cleanup()
    
    async def _execute_phase(
        self,
        phase: EnhancedWorkflowPhase,
        handler,
        *args,
        **kwargs
    ) -> Any:
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")
            
        self.state.current_phase = phase
        start_time = time.time()
        
        logger.info("开始执行阶段: %s", phase.value)
        
        try:
            result = await handler(*args, **kwargs)
            
            duration = time.time() - start_time
            phase_result = EnhancedPhaseResult(
                phase=phase,
                success=True,
                duration=duration,
                data=result
            )
            self.state.phase_results[phase.value] = phase_result
            self.state.phases_completed.append(phase.value)
            
            logger.info("阶段 %s 完成，耗时: %.2f秒", phase.value, duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            phase_result = EnhancedPhaseResult(
                phase=phase,
                success=False,
                duration=duration,
                error=str(e)
            )
            self.state.phase_results[phase.value] = phase_result
            
            logger.error("阶段 %s 失败: %s", phase.value, e)
            raise
    
    async def _phase_research(self, problem: Problem):
        await self._send_progress("正在进行背景研究...", 3)
        
        llm_factory = LLMFactory(self.task_id, self._agent_configs)
        coordinator_llm, _, _, _ = llm_factory.get_all_llms()
        
        research_coordinator = ResearchCoordinator(
            task_id=self.task_id,
            model=coordinator_llm,
            openalex_email=getattr(settings, 'OPENALEX_EMAIL', None),
            enable_web_search=True,
            enable_rag=True
        )
        
        self.research_report = await research_coordinator.execute(
            problem_description=problem.ques_all,
            research_focus=[
                ResearchType.BACKGROUND,
                ResearchType.METHODOLOGY,
                ResearchType.DATA_SOURCE
            ],
            max_sources=15
        )
        
        await self._send_progress(
            f"背景研究完成，发现 {len(self.research_report.citations)} 个可用来源",
            8
        )
        
        return self.research_report
    
    async def _phase_assumptions(self, problem: Problem):
        await self._send_progress("正在生成模型假设...", 6)
        
        llm_factory = LLMFactory(self.task_id, self._agent_configs)
        coordinator_llm, _, _, _ = llm_factory.get_all_llms()
        
        self._assumption_generator = AssumptionGenerator(run_id=self.task_id)
        
        data_description = getattr(problem, 'data_description', None)
        
        assumptions = await self._assumption_generator.generate_all_assumptions(
            problem_description=problem.ques_all,
            problem_type="optimization",
            data_description=data_description,
            max_assumptions=8
        )
        
        if self.state:
            self.state.assumptions = assumptions
        
        if self._hil_manager and assumptions:
            hil_response = await self._hil_manager.request_plan_review(
                phase="assumptions",
                plan_content="\n".join([f"- {a.statement}" for a in assumptions]),
                plan_summary=f"生成了 {len(assumptions)} 条模型假设，请确认",
            )
            if hil_response.decision == HILDecision.REJECT:
                logger.info("用户拒绝假设，将重新生成")
                return await self._phase_assumptions(problem)
        
        await self._send_progress(
            f"假设生成完成，共 {len(assumptions)} 条假设",
            9
        )
        
        return assumptions
    
    async def _phase_coordinate(self, problem: Problem):
        await self._send_progress("正在分析问题...", 10)
        
        llm_factory = LLMFactory(self.task_id, self._agent_configs)
        coordinator_llm, modeler_llm, coder_llm, writer_llm = llm_factory.get_all_llms()
        
        self._llms = {
            "coordinator": coordinator_llm,
            "modeler": modeler_llm,
            "coder": coder_llm,
            "writer": writer_llm,
        }
        
        research_context = ""
        if self.research_report:
            research_context = "\n\n背景研究发现的关键洞察:\n" + "\n".join(
                f"- {insight}" for insight in self.research_report.key_insights[:5]
            )
        
        coordinator_agent = CoordinatorAgent(self.task_id, coordinator_llm)
        self._agents["coordinator"] = coordinator_agent
        
        enhanced_question = problem.ques_all + research_context
        coordinator_response = await coordinator_agent.run(enhanced_question)
        
        self.questions = coordinator_response.questions
        self.ques_count = coordinator_response.ques_count
        
        await self._send_progress(
            f"问题分析完成，共 {self.ques_count} 个子问题",
            15
        )
        
        return coordinator_response
    
    async def _phase_model_strategy(self, problem: Problem):
        await self._send_progress("正在生成多模型策略...", 17)
        
        self._model_strategy = MultiModelStrategy(run_id=self.task_id)
        
        data_description = getattr(problem, 'data_description', None)
        
        model_plan = await self._model_strategy.generate_multi_model_plan(
            problem_description=problem.ques_all,
            data_description=data_description,
            max_models=5
        )
        
        if self.state:
            self.state.model_plan = model_plan
        
        await self._send_progress(
            f"多模型策略生成完成：基线模型 + {len(model_plan.improvements)} 个改进模型",
            19
        )
        
        return model_plan
    
    async def _phase_model(self):
        """建模阶段（注入研究上下文 + 知识库上下文）"""
        await self._send_progress("正在设计建模方案...", 20)

        modeler_agent = ModelerAgent(
            self.task_id,
            self._llms["modeler"]
        )
        self._agents["modeler"] = modeler_agent

        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        coordinator_response = self.state.phase_results["coordinate"].data

        # 收集研究上下文（知识库 + 研究报告）
        research_parts = []

        # 1. 知识库上下文（修复：之前返回值被丢弃）
        kb_context = self._get_knowledge_base_context(coordinator_response)
        if kb_context:
            research_parts.append("### 知识库推荐\n" + kb_context)

        # 2. 研究报告上下文（修复：之前 self.research_report 未被读取）
        if hasattr(self, "research_report") and self.research_report:
            try:
                # research_report 可能是对象或字典，提取关键信息
                report = self.research_report
                if hasattr(report, "key_insights"):
                    research_parts.append(
                        "### 文献研究发现\n" + "\n".join(
                            f"- {insight}" for insight in report.key_insights[:10]
                        )
                    )
                if hasattr(report, "methodology_suggestions"):
                    research_parts.append(
                        "### 方法论建议\n" + "\n".join(
                            f"- {s}" for s in report.methodology_suggestions[:5]
                        )
                    )
                if hasattr(report, "summary"):
                    research_parts.append("### 研究摘要\n" + str(report.summary)[:2000])
                elif isinstance(report, dict):
                    import json
                    research_parts.append(
                        "### 研究报告\n" + json.dumps(report, ensure_ascii=False, indent=2)[:2000]
                    )
            except Exception as e:
                logger.warning("提取研究报告上下文失败: %s", e)

        research_context = "\n\n".join(research_parts) if research_parts else None

        if research_context:
            logger.info("注入研究上下文到 Modeler (%s 字符)", len(research_context))

        modeler_response = await modeler_agent.run(
            coordinator_response,
            research_context=research_context,
        )

        await self._send_progress("建模方案设计完成", 30)

        return modeler_response
    
    def _get_knowledge_base_context(self, coordinator_response) -> str:
        try:
            problem_type = getattr(coordinator_response, 'problem_type', 'optimization')
            
            models = knowledge_base.search_model(problem_type, [])
            metrics = knowledge_base.get_evaluation_metrics(problem_type)
            knowledge_base.get_best_practices(problem_type)
            
            context_parts = []
            
            if models:
                context_parts.append("推荐模型:")
                for model in models[:3]:
                    context_parts.append(f"  - {model.name}: {model.description}")
            
            if metrics:
                context_parts.append("推荐评价指标:")
                for metric in metrics[:3]:
                    context_parts.append(f"  - {metric.name}")
            
            return "\n".join(context_parts)
        except Exception as e:
            logger.warning("获取知识库上下文失败: %s", e)
            return ""
    
    async def _phase_setup(self, problem: Problem):
        await self._send_progress("正在准备执行环境...", 35)
        
        notebook_serializer = NotebookSerializer(work_dir=self.work_dir)
        self._code_interpreter = await create_interpreter(
            kind="auto",
            task_id=self.task_id,
            work_dir=self.work_dir,
            notebook_serializer=notebook_serializer,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
        )
        
        from app.tools.openalex_scholar import OpenAlexScholar
        openalex_email = getattr(settings, 'OPENALEX_EMAIL', None) or "default@example.com"
        scholar = OpenAlexScholar(
            task_id=self.task_id,
            email=openalex_email
        )
        
        coder_agent = CoderAgent(
            task_id=problem.task_id,
            model=self._llms["coder"],
            work_dir=self.work_dir,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            code_interpreter=self._code_interpreter,
        )
        self._agents["coder"] = coder_agent
        
        writer_agent = WriterAgent(
            task_id=problem.task_id,
            model=self._llms["writer"],
            comp_template=problem.comp_template,
            format_output=problem.format_output,
            scholar=scholar,
        )
        self._agents["writer"] = writer_agent
        
        self._user_output = UserOutput(
            work_dir=self.work_dir,
            ques_count=self.ques_count,
            comp_template=problem.comp_template,
        )
        
        await self._send_progress("执行环境准备完成", 40)
    
    async def _phase_solve(self, problem: Problem, modeler_response):
        flows = Flows(self.questions)
        solution_flows = flows.get_solution_flows(self.questions, modeler_response)
        config_template = get_config_template(problem.comp_template, problem.format_output)

        total_solution_steps = len(solution_flows)
        if self.state:
            self.state.total_steps = total_solution_steps * 2

        coder_agent = self._agents["coder"]
        writer_agent = self._agents["writer"]
        modeler_agent = self._agents["modeler"]

        # 反馈环路配置
        max_remodel_attempts = 2

        # 跨问题上下文：收集已完成问题的代码输出
        completed_outputs: Dict[str, str] = {}

        solution_results = {}
        step_idx = 0

        for key, flow_meta in solution_flows.items():
            step_idx += 1
            progress = 40 + (step_idx / total_solution_steps) * 30

            await self._send_progress(f"正在求解: {key}", progress)

            try:
                # 动态构建跨问题上下文
                context = Flows.build_cross_question_context(completed_outputs)

                # 动态构建 coder_prompt（注入上下文）
                coder_prompt = Flows.build_coder_prompt(flow_meta, context=context)
                coder_response = await coder_agent.run(
                    prompt=coder_prompt,
                    subtask_title=key
                )

                # 反馈环路：检查 Coder 是否请求重新建模
                remodel_attempt = 0
                while (
                    coder_response.needs_remodel
                    and remodel_attempt < max_remodel_attempts
                ):
                    remodel_attempt += 1
                    logger.info(
                        f"子任务 {key} 需要重新建模 "
                        f"(第 {remodel_attempt}/{max_remodel_attempts} 次)"
                    )

                    await self._send_progress(
                        f"正在为 {key} 重新设计方案... "
                        f"(尝试 {remodel_attempt}/{max_remodel_attempts})",
                        progress
                    )

                    # 1. 构造反馈信号
                    feedback = CoderFeedbackToModeler(
                        subtask_key=key,
                        error_summary=(
                            coder_response.error_summary or "代码执行多次失败"
                        ),
                        failed_approach=coder_response.code_response or "",
                        alternative_suggestion="请使用更简单、更可靠的数学方法",
                        retry_count=remodel_attempt,
                    )

                    # 2. 调用 Modeler 修订方案
                    revised_modeler_response = await modeler_agent.revise(
                        feedback=feedback,
                        original_solution=modeler_response.questions_solution,
                    )

                    # 3. 用修订后的方案 + 跨问题上下文重新构建 prompt
                    revised_meta = {
                        "type": flow_meta["type"],
                        "solution": revised_modeler_response.questions_solution.get(
                            key if key != "sensitivity_analysis" else "sensitivity_analysis",
                            ""
                        ),
                    }
                    if flow_meta["type"] == "question":
                        revised_meta["question"] = self.questions.get(key, "")

                    revised_prompt = Flows.build_coder_prompt(
                        revised_meta, context=context
                    )

                    # 4. 重置 Coder 计数器
                    coder_agent.reset_counters()

                    # 5. 用修订后的方案重新执行 Coder
                    await self._send_progress(
                        f"正在用新方案重新求解: {key}", progress
                    )
                    coder_response = await coder_agent.run(
                        prompt=revised_prompt,
                        subtask_title=key
                    )

                    # 更新 modeler_response 供后续子任务参考
                    modeler_response = revised_modeler_response

                # 收集本题的代码输出，供后续问题使用
                try:
                    if self._code_interpreter is not None:
                        code_output = self._code_interpreter.get_code_output(key)
                        if code_output:
                            completed_outputs[key] = code_output
                except Exception:
                    logger.debug("获取 %s 的代码输出用于上下文注入时失败，跳过", key)

                if self._code_interpreter is None:
                    raise RuntimeError("Code interpreter not initialized")

                writer_prompt = flows.get_writer_prompt(
                    key,
                    coder_response.code_response,
                    self._code_interpreter,
                    config_template
                )

                await self._send_progress(f"正在撰写: {key}", progress + 5)

                writer_response = await writer_agent.run(
                    writer_prompt,
                    available_images=coder_response.created_images,
                    sub_title=key,
                )

                self._user_output.set_res(key, writer_response)

                solution_results[key] = {
                    "coder_response": coder_response,
                    "writer_response": writer_response,
                    "remodel_attempts": remodel_attempt,
                    "success": True,
                }

                if self.state:
                    self.state.completed_steps += 1

            except Exception as e:
                logger.error("求解 %s 失败: %s", key, e)
                solution_results[key] = {
                    "success": False,
                    "error": str(e),
                }

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(
                        content=f"警告: {key} 求解遇到问题，已跳过",
                        type="warning"
                    )
                )

        if self._code_interpreter:
            await self._code_interpreter.cleanup()
            self._code_interpreter = None

        return {
            "results": solution_results,
            "flows": flows,
            "config_template": config_template,
        }
    
    async def _phase_validate(self, solution_results: Dict[str, Any]):
        await self._send_progress("正在进行模型验证...", 68)
        
        self._auto_validator = AutoValidator(knowledge_base)
        
        validation_results = {}
        
        for key, result in solution_results.get("results", {}).items():
            if result.get("success"):
                try:
                    coder_response = result.get("coder_response")
                    if coder_response and hasattr(coder_response, 'model_data'):
                        model_data = coder_response.model_data
                        if model_data and 'X' in model_data and 'y' in model_data:
                            report = await self._auto_validator.validate_model(
                                model_id=key,
                                X=model_data['X'],
                                y=model_data['y']
                            )
                            validation_results[key] = report
                except Exception as e:
                    logger.warning("验证 %s 失败: %s", key, e)
        
        self._validation_results = validation_results

        await self._send_progress(
            f"模型验证完成，验证了 {len(validation_results)} 个模型",
            70
        )
        
        return validation_results
    
    async def _phase_sensitivity(self, problem: Problem, modeler_response):
        await self._send_progress("正在进行敏感性分析...", 71)
        
        self._sensitivity_analyzer = SensitivityAnalyzer(run_id=self.task_id)
        
        parameters, suggestion = await self._sensitivity_analyzer.auto_analyze(
            problem_description=problem.ques_all,
            parameters_description=str(modeler_response) if modeler_response else "",
            base_output=1.0
        )
        
        self._sensitivity_suggestion = suggestion
        if parameters:
            logger.info("敏感性分析识别了 %s 个参数", len(parameters))
        
        await self._send_progress("敏感性分析完成", 72)
        
        return {"parameters": parameters, "suggestion": suggestion}
    
    async def _phase_quality_check(self, solution_results: Dict[str, Any]):
        await self._send_progress("正在进行质量检查...", 73)
        
        self._quality_checker = QualityChecker()
        
        quality_results: Dict[str, GateResult] = {}
        
        for key, result in solution_results.get("results", {}).items():
            if result.get("success"):
                coder_response = result.get("coder_response")
                if coder_response and hasattr(coder_response, 'code_response'):
                    code = str(coder_response.code_response)
                    quality_results[f"{key}_code"] = self._quality_checker.check_code(code)
        
        paper_content = ""
        if hasattr(self, '_user_output') and self._user_output:
            paper_content = str(self._user_output)
        
        if paper_content:
            quality_results["paper"] = self._quality_checker.check_paper(paper_content)
        
        self._quality_results = quality_results
        if self.state:
            self.state.quality_results = quality_results
        
        passed_count = sum(1 for r in quality_results.values() if r.passed)
        total_count = len(quality_results)
        
        await self._send_progress(
            f"质量检查完成: {passed_count}/{total_count} 项通过",
            74
        )
        
        return quality_results
    
    async def _phase_abstract(
        self, 
        problem: Problem, 
        modeler_response, 
        solution_results: Dict[str, Any]
    ):
        await self._send_progress("正在生成杀手级摘要...", 72)
        
        abstract_style = AbstractStyle.MCM_ICM if self.paper_language == "en" else AbstractStyle.CUMCM
        abstract_lang = AbstractLanguage.ENGLISH if self.paper_language == "en" else AbstractLanguage.CHINESE
        
        abstract_generator = AbstractGenerator(
            task_id=self.task_id,
            model=self._llms["writer"],
            style=abstract_style,
            language=abstract_lang,
            generate_bilingual=(self.paper_language == "zh")
        )
        
        innovation_points = []
        if hasattr(modeler_response, 'innovations'):
            innovation_points = modeler_response.innovations
        
        self.killer_abstract = await abstract_generator.execute(
            problem_description=problem.ques_all,
            modeling_results={"modeler_response": str(modeler_response)},
            code_results=solution_results.get("results"),
            innovation_points=innovation_points,
            validation_results=None
        )
        
        await self._send_progress(
            f"摘要生成完成，质量评分: {self.killer_abstract.quality_assessment.overall_score:.1f}/100",
            75
        )
        
        return self.killer_abstract
    
    async def _phase_write(self, problem: Problem, solution_data: dict):
        await self._send_progress("正在撰写论文其他部分...", 77)

        flows = solution_data["flows"]
        config_template = solution_data["config_template"]

        award_context = self._build_award_context()
        
        write_flows = flows.get_write_flows(
            self._user_output,
            config_template,
            problem.ques_all,
            comp_template=problem.comp_template,
        )

        if "analysisQues" in write_flows and award_context["analysis"]:
            write_flows["analysisQues"] += f"\n\n【获奖补充要求】\n{award_context['analysis']}"
        if "modelAssumption" in write_flows and award_context["assumptions"]:
            write_flows["modelAssumption"] += f"\n\n【获奖补充要求】\n{award_context['assumptions']}"
        if "judge" in write_flows and award_context["innovation_benchmark"]:
            write_flows["judge"] += f"\n\n【创新与改进补充要求】\n{award_context['innovation_benchmark']}"
        if "judge" in write_flows and award_context["judge"]:
            write_flows["judge"] += f"\n\n【获奖补充要求】\n{award_context['judge']}"

        writer_agent = self._agents["writer"]
        total_write_steps = len(write_flows)
        
        step_idx = 0
        for key, value in write_flows.items():
            step_idx += 1
            progress = 77 + (step_idx / total_write_steps) * 15
            
            await self._send_progress(f"正在撰写: {key}", progress)
            
            try:
                writer_response = await writer_agent.run(
                    prompt=value,
                    sub_title=key
                )
                self._user_output.set_res(key, writer_response)
                
            except Exception as e:
                logger.error("写作 %s 失败: %s", key, e)
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(
                        content=f"警告: {key} 写作遇到问题",
                        type="warning"
                    )
                )
        
        await self._send_progress("论文撰写完成", 92)

        paper_quality = await self._run_paper_quality_review()
        if paper_quality:
            self._quality_results["paper"] = paper_quality
            if not paper_quality.passed:
                await self._refine_paper_sections(writer_agent, paper_quality)
                refined_quality = await self._run_paper_quality_review()
                if refined_quality:
                    self._quality_results["paper_refined"] = refined_quality

        self._append_quality_summary_to_judge()
    
    async def _phase_latex(self, problem: Problem):
        await self._send_progress("正在生成LaTeX论文...", 94)

        # 提取 Markdown 内容
        markdown_content = ""
        if hasattr(self._user_output, 'get_result_to_save'):
            try:
                markdown_content = self._user_output.get_result_to_save()
            except Exception as e:
                logger.warning("获取论文 Markdown 内容失败，使用空内容: %s", e)
                markdown_content = ""

        # 从 killer_abstract 提取摘要和关键词
        abstract_text = ""
        keywords = None
        if self.killer_abstract:
            abstract_text = self.killer_abstract.abstract_text
            keywords = getattr(self.killer_abstract, 'keywords', None) or None

        latex_path = generate_latex_from_markdown(
            markdown_content=markdown_content,
            output_path=f"{self.work_dir}/paper.tex",
            comp_template=problem.comp_template,
            title=problem.title,
            abstract=abstract_text,
            keywords=keywords,
            team_control_number=problem.team_control_number,
            problem_choice=problem.problem_choice,
        )

        await self._send_progress("LaTeX论文生成完成", 96)

        return latex_path
    
    async def _phase_finalize(self):
        await self._send_progress("正在保存结果...", 98)
        
        self._user_output.save_result()
        
        if self.state:
            elapsed = self.state.get_elapsed_time()
            stats = self._get_execution_stats()
            
            logger.info("工作流完成统计: %s", stats)
            
            # 保存建模经验到记忆系统
            if self._memory_manager:
                try:
                    # 收集经验信息
                    models_used = []
                    if self.state.model_plan:
                        models_used.append(self.state.model_plan.baseline.name)
                        models_used.extend([m.name for m in self.state.model_plan.improvements])
                    
                    lessons = []
                    if self._validation_results:
                        lessons.append(f"验证了 {len(self._validation_results)} 个模型")
                    if self._quality_results:
                        passed = sum(1 for r in self._quality_results.values() if r.passed)
                        lessons.append(f"质量检查通过率: {passed}/{len(self._quality_results)}")
                    if self._sensitivity_suggestion:
                        lessons.append(f"敏感性分析建议: {self._sensitivity_suggestion[:100]}")
                    
                    # 确定结果状态
                    outcome = "success" if stats.get("success_rate", 0) > 0.7 else "partial"
                    
                    await self._memory_manager.save_modeling_experience(
                        problem_type="math_modeling",
                        problem_description=getattr(self, '_problem_description', '未知问题')[:500],
                        solution_approach=str(models_used),
                        models_used=models_used,
                        outcome=outcome,
                        lessons=lessons
                    )
                    logger.info("建模经验已保存到记忆系统")
                except Exception as e:
                    logger.warning("保存建模经验失败: %s", e)
            
            summary_parts = [f"任务完成！总用时: {elapsed/60:.1f}分钟"]
            
            if self.enable_research and self.research_report:
                summary_parts.append(f"发现 {len(self.research_report.citations)} 个文献来源")
            
            if self.enable_abstract and self.killer_abstract:
                summary_parts.append(f"摘要质量: {self.killer_abstract.quality_assessment.overall_score:.0f}分")
            
            if self.enable_latex:
                summary_parts.append("已生成LaTeX论文")
            
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(
                    content="✅ " + "，".join(summary_parts),
                    type="success"
                )
            )

    
    async def _send_progress(self, message: str, percent: float):
        if self.state:
            self.state.update_progress(message, int(percent))
        
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content=message, type="info")
        )
    
    def _get_execution_stats(self) -> dict:
        if self.state is None:
            return {}
            
        stats = {
            "total_time": self.state.get_elapsed_time(),
            "phases": {},
            "features": {
                "research_enabled": self.enable_research,
                "abstract_enabled": self.enable_abstract,
                "latex_enabled": self.enable_latex,
            }
        }
        
        for phase_name, result in self.state.phase_results.items():
            stats["phases"][phase_name] = {
                "duration": result.duration,
                "success": result.success,
            }
        
        return stats

    def _build_award_context(self) -> Dict[str, str]:
        research_insights = []
        if self.research_report and getattr(self.research_report, "key_insights", None):
            research_insights = self.research_report.key_insights[:6]

        assumptions_text = ""
        if self.state and self.state.assumptions:
            assumptions_text = "可用假设要点：\n" + "\n".join(
                f"- {a.statement}" for a in self.state.assumptions[:6]
            )

        model_strategy_text = ""
        if self.state and self.state.model_plan:
            baseline = self.state.model_plan.baseline.name
            improvements = [m.name for m in self.state.model_plan.improvements]
            innovations = [m.name for m in self.state.model_plan.innovations]
            metrics = ", ".join(self.state.model_plan.evaluation_metrics)
            model_strategy_text = (
                f"模型对比策略：基线模型 {baseline}；"
                f"改进模型 {', '.join(improvements) if improvements else '无'}；"
                f"创新模型 {', '.join(innovations) if innovations else '无'}。"
                f"评估指标：{metrics}。"
            )

        validation_text = ""
        if self._validation_results:
            validation_text = f"模型验证覆盖 {len(self._validation_results)} 个模型，需在文中给出验证结论与局限。"

        quality_text = ""
        if self._quality_results:
            passed_count = sum(1 for r in self._quality_results.values() if r.passed)
            total_count = len(self._quality_results)
            quality_text = f"质量闸门结果：{passed_count}/{total_count} 项通过，需解释改进方向。"

        sensitivity_text = ""
        if self._sensitivity_suggestion:
            sensitivity_text = f"敏感性分析结论：{self._sensitivity_suggestion}"

        analysis_parts = []
        if research_insights:
            analysis_parts.append("研究洞察：\n" + "\n".join(f"- {i}" for i in research_insights))
        if model_strategy_text:
            analysis_parts.append(model_strategy_text)

        innovation_parts = []
        if model_strategy_text:
            innovation_parts.append(model_strategy_text)
        if research_insights:
            innovation_parts.append("创新灵感来源：\n" + "\n".join(f"- {i}" for i in research_insights[:3]))

        judge_parts = [p for p in [validation_text, sensitivity_text, quality_text] if p]
        if model_strategy_text:
            judge_parts.append("创新点突出：强调创新模型/策略的独特性与收益，并与基线对标。")

        return {
            "analysis": "\n".join(analysis_parts),
            "assumptions": assumptions_text,
            "innovation_benchmark": "\n".join(innovation_parts),
            "judge": "\n".join(judge_parts),
        }

    async def _run_paper_quality_review(self) -> Optional[GateResult]:
        if not hasattr(self, "_user_output") or not self._user_output:
            return None

        try:
            paper_content = self._user_output.get_result_to_save()
            checker = QualityChecker()
            return checker.check_paper(paper_content)
        except Exception as e:
            logger.warning("论文质量检查失败: %s", e)
            return None

    async def _refine_paper_sections(
        self,
        writer_agent: WriterAgent,
        paper_quality: GateResult,
    ) -> None:
        if not hasattr(self, "_user_output") or not self._user_output:
            return

        issues = "\n".join(f"- {issue}" for issue in paper_quality.issues)
        suggestions = "\n".join(f"- {suggestion}" for suggestion in paper_quality.suggestions)
        target_sections = [
            "firstPage",
            "analysisQues",
            "judge",
        ]

        for key in target_sections:
            current = self._user_output.get_res().get(key, {}).get("response_content")
            if not current:
                continue

            prompt = f"""你是数学建模竞赛论文润色专家。

请基于以下质量问题与建议，对【{key}】部分进行二次优化：

质量问题：
{issues or "无"}

改进建议：
{suggestions or "无"}

原文内容：
{current}

要求：
1. 保持章节结构与原有标题风格
2. 增强结果导向与数值表达
3. 补充创新点与对标结论
4. 语言凝练，避免重复
"""

            try:
                writer_response = await writer_agent.run(prompt=prompt, sub_title=f"refine_{key}")
                self._user_output.set_res(key, writer_response)
            except Exception as e:
                logger.warning("润色 %s 失败: %s", key, e)

    def _append_quality_summary_to_judge(self) -> None:
        if self._quality_summary_appended:
            return
        if not hasattr(self, "_user_output") or not self._user_output:
            return

        summary = self._build_quality_summary()
        if not summary:
            return

        current = self._user_output.get_res().get("judge", {})
        current_text = current.get("response_content")
        if not current_text:
            return

        merged = f"{current_text}\n\n{summary}"
        writer_response = WriterResponse(
            response_content=merged,
            footnotes=current.get("footnotes"),
        )
        self._user_output.set_res("judge", writer_response)
        self._quality_summary_appended = True

    def _build_quality_summary(self) -> str:
        quality = None
        if "paper_refined" in self._quality_results:
            quality = self._quality_results.get("paper_refined")
        elif "paper" in self._quality_results:
            quality = self._quality_results.get("paper")

        if not quality:
            return ""

        issues = quality.issues[:3] if quality.issues else []
        suggestions = quality.suggestions[:3] if quality.suggestions else []

        lines = ["## 质量自检与改进"]
        if quality.passed:
            lines.append("论文结构与表达自检通过，整体质量满足提交要求。")
        else:
            lines.append("论文已完成自检优化，仍需关注以下易错点：")
            for issue in issues:
                lines.append(f"- {issue}")

        if suggestions:
            lines.append("改进要点：")
            for suggestion in suggestions:
                lines.append(f"- {suggestion}")

        return "\n".join(lines)
    
    async def _cleanup(self):
        try:
            if self._code_interpreter:
                await self._code_interpreter.cleanup()
                self._code_interpreter = None
        except Exception as e:
            logger.warning("清理代码解释器失败: %s", e)
