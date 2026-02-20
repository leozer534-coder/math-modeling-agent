import re
from enum import Enum
from typing import Any, Dict, Optional

from app.core.llm.llm import LLM
from app.core.math_model_workflow import MathModelWorkFlow
from app.schemas.A2A import CoordinatorToModeler
from app.schemas.enums import WorkflowMode
from app.schemas.request import Problem
from app.utils.log_util import logger


# 延迟导入避免循环依赖
_EnhancedMathModelWorkFlow = None

def _get_enhanced_workflow_class():
    """延迟导入 EnhancedMathModelWorkFlow"""
    global _EnhancedMathModelWorkFlow
    if _EnhancedMathModelWorkFlow is None:
        from app.core.enhanced_workflow import EnhancedMathModelWorkFlow
        _EnhancedMathModelWorkFlow = EnhancedMathModelWorkFlow
    return _EnhancedMathModelWorkFlow


class WorkflowType(str, Enum):
    STANDARD = "standard"
    ENHANCED = "enhanced"


class ComplexityScore:
    """问题复杂度评估结果"""

    def __init__(self, score: float, factors: Dict[str, bool]):
        self.score = score          # 0.0 ~ 1.0
        self.factors = factors      # 各评估因子命中情况
        self.is_complex = score >= 0.4  # 阈值: 40% 以上视为复杂

    def __repr__(self) -> str:
        hit = [k for k, v in self.factors.items() if v]
        return f"ComplexityScore({self.score:.2f}, hit={hit})"


class WorkflowSelector:
    """
    工作流选择器

    支持三种模式:
    - STANDARD: 始终使用标准工作流 (4 核心 Agent)
    - ENHANCED / AWARD: 始终使用增强工作流 (专家 Agent 矩阵)
    - AUTO: 根据题目复杂度自动选择
    """

    # ==================== 复杂度评估因子 ====================
    # 每个因子的权重（总和不需要为 1，会归一化）
    _COMPLEXITY_FACTORS = {
        "long_problem":         0.15,   # 题目长度 > 3000 字
        "many_questions":       0.15,   # 问题数量 >= 4
        "optimization":         0.15,   # 涉及优化+约束
        "advanced_methods":     0.20,   # 涉及高级方法关键词
        "data_analysis":        0.10,   # 需要数据分析
        "multi_stage":          0.10,   # 多阶段/多步骤
        "requires_innovation":  0.15,   # 需要创新点
    }

    # 高级方法关键词
    _ADVANCED_KEYWORDS = [
        "多目标", "动态规划", "蒙特卡罗", "神经网络", "深度学习",
        "遗传算法", "模拟退火", "粒子群", "贝叶斯", "马尔可夫",
        "时间序列", "图论", "网络流", "博弈论", "随机过程",
        "偏微分方程", "有限元", "机器学习", "聚类", "回归分析",
        "multi-objective", "neural network", "deep learning",
        "Monte Carlo", "Bayesian", "Markov",
    ]

    # 创新相关关键词
    _INNOVATION_KEYWORDS = [
        "创新", "改进", "优化", "提升", "新方法", "新模型",
        "innovation", "novel", "improve", "enhance",
    ]

    @staticmethod
    def select(
        mode: WorkflowMode,
        problem: Optional[Problem] = None,
    ) -> WorkflowType:
        """
        根据模式和问题选择工作流类型。

        Args:
            mode: 工作流模式
            problem: 问题对象（AUTO 模式必须提供）

        Returns:
            WorkflowType: 选定的工作流类型
        """
        # ENHANCED 和 AWARD 都映射到增强工作流
        if mode in (WorkflowMode.ENHANCED, WorkflowMode.AWARD):
            logger.info("工作流选择: ENHANCED (显式指定)")
            return WorkflowType.ENHANCED

        if mode == WorkflowMode.STANDARD:
            logger.info("工作流选择: STANDARD (显式指定)")
            return WorkflowType.STANDARD

        # AUTO 模式: 根据复杂度自动选择
        if mode == WorkflowMode.AUTO:
            if not problem:
                logger.warning("AUTO 模式未提供 problem，降级为 STANDARD")
                return WorkflowType.STANDARD

            complexity = WorkflowSelector.assess_complexity(problem)
            chosen = WorkflowType.ENHANCED if complexity.is_complex else WorkflowType.STANDARD
            logger.info("工作流选择: %s (AUTO, %s)", chosen.value, complexity)
            return chosen

        # 未知模式降级为 STANDARD
        logger.warning("未知工作流模式 %s，降级为 STANDARD", mode)
        return WorkflowType.STANDARD

    @staticmethod
    def assess_complexity(problem: Problem) -> ComplexityScore:
        """
        评估问题复杂度。

        评估维度:
        1. 题目长度
        2. 问题数量
        3. 是否涉及优化+约束
        4. 是否需要高级方法
        5. 是否需要数据分析
        6. 是否多阶段问题
        7. 是否要求创新
        """
        ques_all = problem.ques_all or ""
        factors = {}

        # 1. 题目长度
        factors["long_problem"] = len(ques_all) > 3000

        # 2. 问题数量
        question_count = WorkflowSelector._count_questions(ques_all)
        factors["many_questions"] = question_count >= 4

        # 3. 优化 + 约束
        has_optimization = any(
            kw in ques_all for kw in ["优化", "最优", "最小化", "最大化", "optimize", "minimize", "maximize"]
        )
        has_constraint = any(
            kw in ques_all for kw in ["约束", "限制", "条件", "constraint", "subject to"]
        )
        factors["optimization"] = has_optimization and has_constraint

        # 4. 高级方法
        factors["advanced_methods"] = any(
            kw in ques_all for kw in WorkflowSelector._ADVANCED_KEYWORDS
        )

        # 5. 数据分析
        factors["data_analysis"] = any(
            kw in ques_all for kw in [
                "数据分析", "数据集", "样本", "统计", "回归", "分类", "聚类",
                "dataset", "data analysis", "regression", "classification",
            ]
        )

        # 6. 多阶段
        multi_stage_patterns = [
            r"第[一二三四五六七八九十\d]+[步阶段问]",
            r"step\s*\d",
            r"phase\s*\d",
        ]
        factors["multi_stage"] = any(
            re.search(p, ques_all, re.IGNORECASE) for p in multi_stage_patterns
        )

        # 7. 创新要求
        factors["requires_innovation"] = any(
            kw in ques_all for kw in WorkflowSelector._INNOVATION_KEYWORDS
        )

        # 加权打分
        total_weight = sum(WorkflowSelector._COMPLEXITY_FACTORS.values())
        score = sum(
            WorkflowSelector._COMPLEXITY_FACTORS[k]
            for k, v in factors.items()
            if v
        ) / total_weight

        return ComplexityScore(score=score, factors=factors)

    @staticmethod
    def _count_questions(text: str) -> int:
        """从题目文本中估算问题数量"""
        patterns = [
            r"问题\s*[一二三四五六七八九十\d]",
            r"Question\s*\d",
            r"^\s*\d+\.\s",   # 列表编号
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, text, re.MULTILINE | re.IGNORECASE))
        # 至少返回 "问题" 出现次数的粗略估计
        return max(count, text.count("问题"))

    @staticmethod
    async def create_and_run(
        workflow_type: WorkflowType,
        problem: Problem,
        model: Optional[LLM] = None,
        coordinator_data: Optional[CoordinatorToModeler] = None,
        agent_configs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if workflow_type == WorkflowType.STANDARD:
            return await WorkflowSelector._run_standard(
                problem, agent_configs=agent_configs
            )
        else:
            return await WorkflowSelector._run_enhanced(
                problem, model, coordinator_data, agent_configs=agent_configs
            )

    @staticmethod
    async def _run_standard(
        problem: Problem,
        agent_configs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info("使用标准工作流: task_id=%s", problem.task_id)
        workflow = MathModelWorkFlow(agent_configs=agent_configs)
        await workflow.execute(problem)
        return {
            "workflow_type": "standard",
            "task_id": problem.task_id,
            "status": workflow.state.current_phase.value if workflow.state else "unknown"
        }

    @staticmethod
    async def _run_enhanced(
        problem: Problem,
        model: Optional[LLM] = None,
        coordinator_data: Optional[CoordinatorToModeler] = None,
        agent_configs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info("使用增强工作流 (EnhancedMathModelWorkFlow): task_id=%s", problem.task_id)

        # 优先使用新的 EnhancedMathModelWorkFlow（自包含，不需要额外参数）
        try:
            EnhancedMathModelWorkFlowCls = _get_enhanced_workflow_class()
            workflow = EnhancedMathModelWorkFlowCls(agent_configs=agent_configs)
            await workflow.execute(problem)
            return {
                "workflow_type": "enhanced",
                "task_id": problem.task_id,
                "status": workflow.state.current_phase.value if workflow.state else "unknown"
            }
        except Exception as e:
            logger.warning("EnhancedMathModelWorkFlow 失败，降级到标准模式: %s", e)

            # 直接降级到标准模式（旧 WorkflowEngine 降级路径已移除）
            return await WorkflowSelector._run_standard(
                problem, agent_configs=agent_configs
            )


def get_workflow_for_mode(mode: WorkflowMode, problem: Problem) -> WorkflowType:
    return WorkflowSelector.select(mode, problem)
