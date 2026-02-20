"""
增强型Agent基类 - 支持反思、工具调用和专业知识
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.core.llm.llm import LLM
from app.utils.log_util import logger


class AgentRole(Enum):
    """Agent角色枚举"""
    # 原有角色
    PROBLEM_ANALYZER = "问题分析专家"
    MODEL_SELECTOR = "模型选择专家"
    EXPERIMENT_DESIGNER = "实验设计专家"
    DATA_ANALYST = "数据分析专家"
    MODELING_EXPERT = "建模专家"
    CODE_ENGINEER = "代码工程师"
    VALIDATION_EXPERT = "验证专家"
    ACADEMIC_WRITER = "学术写作专家"
    REVIEWER = "质量评审专家"

    # Phase 1: 论文写作增强
    COMPETITION_EXPERT_WRITER = "竞赛评审风格写作师"
    INNOVATION_HIGHLIGHTER = "创新亮点突出师"
    PAPER_REFINEMENT_MASTER = "论文精化大师"

    # Phase 2: 问题理解深化
    PROBLEM_INSIGHT_ANALYZER = "问题洞察分析师"
    DATA_UNDERSTANDING_EXPERT = "数据理解专家"
    BACKGROUND_RESEARCH_AGENT = "背景研究专家"

    # Phase 3: 建模创新能力
    SMART_MODELER_INNOVATOR = "智能建模创新者"
    METHOD_INNOVATION_LAB = "方法创新实验室"
    HYBRID_MODEL_FUSION = "混合模型融合引擎"

    # Phase 4: 代码优化与结果分析
    HYPERPARAMETER_TUNING_MASTER = "超参数调优大师"
    PERFORMANCE_OPTIMIZER = "性能优化器"
    RESULT_INTERPRETATION_EXPERT = "结果解释专家"
    BENCHMARK_ANALYSIS_AGENT = "对标分析专家"
    PATTERN_DISCOVERY_ENGINE = "规律发现引擎"


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = 5    # 优秀
    GOOD = 4         # 良好
    AVERAGE = 3      # 一般
    POOR = 2         # 较差
    FAILED = 1       # 失败


@dataclass
class QualityMetrics:
    """质量评估指标"""
    completeness: float  # 完整性 (0-1)
    correctness: float   # 正确性 (0-1)
    depth: float         # 深度 (0-1)
    clarity: float       # 清晰度 (0-1)
    innovation: float    # 创新性 (0-1)

    def get_average(self) -> float:
        """获取平均分"""
        return (self.completeness + self.correctness + self.depth +
                self.clarity + self.innovation) / 5

    def get_level(self) -> QualityLevel:
        """获取质量等级"""
        avg = self.get_average()
        if avg >= 0.9:
            return QualityLevel.EXCELLENT
        elif avg >= 0.8:
            return QualityLevel.GOOD
        elif avg >= 0.6:
            return QualityLevel.AVERAGE
        elif avg >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAILED


@dataclass
class AgentState:
    """Agent状态"""
    role: AgentRole
    task_id: str
    start_time: datetime
    current_stage: str
    context: Dict[str, Any]
    quality_metrics: Optional[QualityMetrics] = None
    reflections: List[str] = None
    tools_used: List[str] = None

    def __post_init__(self):
        if self.reflections is None:
            self.reflections = []
        if self.tools_used is None:
            self.tools_used = []


class ExpertAgent(ABC):
    """增强型专家Agent基类"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        role: AgentRole,
        max_reflections: int = 3,
        max_chat_turns: int = 15,
    ):
        self.task_id = task_id
        self.model = model
        self.role = role
        self.max_reflections = max_reflections
        self.max_chat_turns = max_chat_turns

        # 状态管理
        self.state = AgentState(
            role=role,
            task_id=task_id,
            start_time=datetime.now(),
            current_stage="initialized",
            context={},
        )

        # 对话历史
        self.chat_history: List[Dict] = []
        self.current_chat_turns = 0

        # 工具系统
        self.available_tools: Dict[str, Callable] = {}
        self.knowledge_base = None  # 知识库引用

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词 - 子类必须实现"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行任务 - 子类必须实现"""
        pass

    async def setup(self) -> None:
        """Agent初始化设置"""
        logger.info("%s 初始化中...", self.role.value)

        # 设置系统提示
        await self.append_chat_history({
            "role": "system",
            "content": self.get_system_prompt()
        })

        # 加载领域知识
        await self.load_domain_knowledge()

        self.state.current_stage = "ready"
        logger.info("%s 初始化完成", self.role.value)

    async def load_domain_knowledge(self) -> None:
        """加载领域知识"""
        try:
            from app.core.knowledge_base import knowledge_base
            self.knowledge_base = knowledge_base
            logger.debug("%s: 已加载统一知识库 (%s 个模型)", self.role.value, len(knowledge_base.models))
        except ImportError:
            logger.warning("%s: 知识库加载失败，继续运行", self.role.value)

    def register_tool(self, name: str, tool_func: Callable) -> None:
        """注册工具"""
        self.available_tools[name] = tool_func
        logger.debug("注册工具: %s", name)

    async def append_chat_history(self, message: Dict) -> None:
        """添加对话历史"""
        self.chat_history.append(message)

    # AgentRole -> AgentType 映射表
    _ROLE_TO_AGENT_TYPE = None

    @classmethod
    def _get_role_agent_type_map(cls):
        """懒加载角色到 AgentType 的映射"""
        if cls._ROLE_TO_AGENT_TYPE is None:
            from app.schemas.enums import AgentType
            cls._ROLE_TO_AGENT_TYPE = {
                AgentRole.REVIEWER: AgentType.REVIEWER,
                AgentRole.PROBLEM_ANALYZER: AgentType.ANALYZER,
                AgentRole.PROBLEM_INSIGHT_ANALYZER: AgentType.ANALYZER,
                AgentRole.DATA_UNDERSTANDING_EXPERT: AgentType.ANALYZER,
                AgentRole.BACKGROUND_RESEARCH_AGENT: AgentType.ANALYZER,
                AgentRole.MODEL_SELECTOR: AgentType.MODELER,
                AgentRole.SMART_MODELER_INNOVATOR: AgentType.MODELER,
                AgentRole.METHOD_INNOVATION_LAB: AgentType.MODELER,
                AgentRole.HYBRID_MODEL_FUSION: AgentType.MODELER,
                AgentRole.EXPERIMENT_DESIGNER: AgentType.MODELER,
                AgentRole.MODELING_EXPERT: AgentType.MODELER,
                AgentRole.CODE_ENGINEER: AgentType.CODER,
                AgentRole.HYPERPARAMETER_TUNING_MASTER: AgentType.OPTIMIZER,
                AgentRole.PERFORMANCE_OPTIMIZER: AgentType.OPTIMIZER,
                AgentRole.VALIDATION_EXPERT: AgentType.VALIDATOR,
                AgentRole.BENCHMARK_ANALYSIS_AGENT: AgentType.VALIDATOR,
                AgentRole.RESULT_INTERPRETATION_EXPERT: AgentType.ANALYZER,
                AgentRole.PATTERN_DISCOVERY_ENGINE: AgentType.ANALYZER,
                AgentRole.DATA_ANALYST: AgentType.ANALYZER,
                AgentRole.ACADEMIC_WRITER: AgentType.WRITER,
                AgentRole.COMPETITION_EXPERT_WRITER: AgentType.WRITER,
                AgentRole.INNOVATION_HIGHLIGHTER: AgentType.WRITER,
                AgentRole.PAPER_REFINEMENT_MASTER: AgentType.WRITER,
            }
        return cls._ROLE_TO_AGENT_TYPE

    async def send_message(self, content: str, msg_type: str = "info") -> None:
        """发送消息到前端"""
        from app.schemas.response import AgentMessage
        from app.schemas.enums import AgentType
        from app.services.redis_manager import redis_manager

        try:
            role_map = self._get_role_agent_type_map()
            agent_type = role_map.get(self.role, AgentType.SYSTEM)
            agent_msg = AgentMessage(
                agent_type=agent_type,
                content=content,
            )
            await redis_manager.publish_message(self.task_id, agent_msg)
        except Exception as e:
            logger.error("发送消息失败: %s", e)

    async def think(self, prompt: str, use_tools: bool = True) -> str:
        """思考处理"""
        self.current_chat_turns += 1

        if self.current_chat_turns > self.max_chat_turns:
            raise RuntimeError(f"超过最大对话次数: {self.max_chat_turns}")

        await self.append_chat_history({
            "role": "user",
            "content": prompt
        })

        try:
            response = await self.model.chat(
                history=self.chat_history,
                tools=self.available_tools if use_tools else None,
                tool_choice="auto" if use_tools else None,
                agent_name=self.role.name,
            )

            content = response.choices[0].message.content
            await self.append_chat_history({
                "role": "assistant",
                "content": content
            })

            return content

        except Exception as e:
            logger.error("思考过程出错: %s", e)
            raise

    async def reflect(self, work_result: str, original_task: str) -> str:
        """自我反思"""
        if len(self.state.reflections) >= self.max_reflections:
            logger.warning("达到最大反思次数: %s", self.max_reflections)
            return work_result

        reflection_prompt = f"""
        请对你的工作结果进行自我反思：

        原始任务: {original_task}

        当前结果: {work_result}

        请从以下维度反思：
        1. 完整性 - 是否完成了所有要求的任务？
        2. 正确性 - 结果是否合理和正确？
        3. 深度 - 分析是否足够深入？
        4. 创新性 - 是否有独到的见解？

        如果发现问题，请提供改进建议。如果没有问题，请简单确认结果。
        """

        try:
            reflection_result = await self.think(reflection_prompt, use_tools=False)
            self.state.reflections.append(reflection_result)

            # 记录反思过程
            await self.send_message(f"🤔 {self.role.value} 自我反思中...", "info")
            await self.send_message(f"反思结果: {reflection_result}", "info")

            return reflection_result

        except Exception as e:
            logger.error("反思过程出错: %s", e)
            return work_result

    async def evaluate_quality(self, work_result: str, task_requirements: str) -> QualityMetrics:
        """评估工作质量"""
        evaluation_prompt = f"""
        请对以下工作进行质量评估：

        任务要求: {task_requirements}

        工作结果: {work_result}

        请从以下5个维度评分（0-1之间的小数）：
        1. completeness (完整性): 是否完成了所有要求
        2. correctness (正确性): 结果是否正确合理
        3. depth (深度): 分析是否有足够的深度
        4. clarity (清晰度): 表达是否清晰易懂
        5. innovation (创新性): 是否有创新性的观点

        请以JSON格式返回评估结果：
        {{
            "completeness": 0.0,
            "correctness": 0.0,
            "depth": 0.0,
            "clarity": 0.0,
            "innovation": 0.0,
            "justification": "简要说明评分理由"
        }}
        """

        try:
            evaluation = await self.think(evaluation_prompt, use_tools=False)

            # 解析评估结果
            evaluation_data = json.loads(
                evaluation.replace("```json", "").replace("```", "").strip()
            )

            metrics = QualityMetrics(
                completeness=evaluation_data["completeness"],
                correctness=evaluation_data["correctness"],
                depth=evaluation_data["depth"],
                clarity=evaluation_data["clarity"],
                innovation=evaluation_data["innovation"]
            )

            self.state.quality_metrics = metrics
            await self.send_message(
                f"📊 质量评估: {metrics.get_average():.2f} ({metrics.get_level().name})",
                "info"
            )

            return metrics

        except Exception as e:
            logger.error("质量评估失败: %s", e)
            # 返回默认评估
            return QualityMetrics(0.7, 0.7, 0.7, 0.7, 0.6)

    async def should_improve(self, metrics: QualityMetrics) -> bool:
        """判断是否需要改进"""
        threshold = 0.7  # 质量阈值

        # 如果任何维度低于阈值，或者平均分低于阈值，则需要改进
        return (
            metrics.completeness < threshold or
            metrics.correctness < threshold or
            metrics.depth < threshold or
            metrics.clarity < threshold or
            metrics.get_average() < threshold
        )

    def update_context(self, key: str, value: Any) -> None:
        """更新上下文"""
        self.state.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self.state.context.get(key, default)

    async def cleanup(self) -> None:
        """清理资源"""
        self.state.current_stage = "completed"
        logger.info("%s 任务完成", self.role.value)

    def get_summary(self) -> Dict[str, Any]:
        """获取工作总结"""
        return {
            "role": self.role.value,
            "task_id": self.task_id,
            "execution_time": (datetime.now() - self.state.start_time).total_seconds(),
            "chat_turns": self.current_chat_turns,
            "reflections_count": len(self.state.reflections),
            "quality_metrics": self.state.quality_metrics,
            "tools_used": self.state.tools_used,
            "context_keys": list(self.state.context.keys()),
        }