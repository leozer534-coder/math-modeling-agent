"""
Agent 注册表

提供所有 Agent 的分组注册、统一导入和懒加载支持。
非实验性 Agent 在模块加载时立即导入；实验性 Agent 通过懒加载代理按需导入。
"""

from typing import Any

from .agent import Agent
from .coder_agent import CoderAgent
from .coordinator_agent import CoordinatorAgent
from .expert_agent import AgentRole, ExpertAgent, QualityMetrics
from .modeler_agent import ModelerAgent
from .writer_agent import WriterAgent

# 增强 Agent 导入
from .abstract_generator import AbstractGenerator
from .benchmark_analysis_agent import BenchmarkAnalysisAgent
from .data_understanding_expert import DataUnderstandingExpert
from .experiment_designer import ExperimentDesigner
from .interactive_coordinator_agent import InteractiveCoordinatorAgent
from .model_selector import ModelSelector
from .problem_analyzer import ProblemAnalyzer
from .problem_insight_analyzer import ProblemInsightAnalyzer
from .reviewer import Reviewer
from .smart_modeler_with_innovation import SmartModelerWithInnovation
from .validation_expert import ValidationExpert


# ============================================================
# Agent 分组注册表
# ============================================================

CORE_AGENTS: dict[str, type] = {
    "coordinator": CoordinatorAgent,
    "modeler": ModelerAgent,
    "coder": CoderAgent,
    "writer": WriterAgent,
}

ANALYSIS_AGENTS: dict[str, type] = {
    "problem_analyzer": ProblemAnalyzer,
    "problem_insight_analyzer": ProblemInsightAnalyzer,
    "data_understanding_expert": DataUnderstandingExpert,
}

MODELING_AGENTS: dict[str, type] = {
    "model_selector": ModelSelector,
    "smart_modeler": SmartModelerWithInnovation,
    "experiment_designer": ExperimentDesigner,
}

CODING_AGENTS: dict[str, type] = {}

WRITING_AGENTS: dict[str, type] = {
    "abstract_generator": AbstractGenerator,
}

VALIDATION_AGENTS: dict[str, type] = {
    "validation_expert": ValidationExpert,
    "reviewer": Reviewer,
    "benchmark_analyzer": BenchmarkAnalysisAgent,
}

INTERACTIVE_AGENTS: dict[str, type] = {
    "interactive_coordinator": InteractiveCoordinatorAgent,
}

# 全量注册表（不含实验性 Agent）
ALL_AGENTS: dict[str, type] = {
    **CORE_AGENTS,
    **ANALYSIS_AGENTS,
    **MODELING_AGENTS,
    **CODING_AGENTS,
    **WRITING_AGENTS,
    **VALIDATION_AGENTS,
    **INTERACTIVE_AGENTS,
}


# ============================================================
# 实验性 Agent 懒加载代理
# ============================================================


class _LazyExperimentalAgents:
    """实验性 Agent 懒加载代理，仅在访问值时才真正导入。"""

    def __init__(self) -> None:
        self._loaded: dict[str, type] | None = None

    def _ensure_loaded(self) -> None:
        if self._loaded is None:
            from .experimental import get_experimental_agents_dict

            self._loaded = get_experimental_agents_dict()

    def __len__(self) -> int:
        from .experimental import _REGISTRY_KEY_TO_CLASS

        return len(_REGISTRY_KEY_TO_CLASS)

    def keys(self):
        """返回注册表键。"""
        from .experimental import _REGISTRY_KEY_TO_CLASS

        return _REGISTRY_KEY_TO_CLASS.keys()

    def values(self):
        """懒加载后返回所有 Agent 类。"""
        self._ensure_loaded()
        return self._loaded.values()

    def items(self):
        """懒加载后返回所有 (key, AgentClass) 对。"""
        self._ensure_loaded()
        return self._loaded.items()

    def __getitem__(self, key: str) -> type:
        self._ensure_loaded()
        return self._loaded[key]

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, key: str) -> bool:
        from .experimental import _REGISTRY_KEY_TO_CLASS

        return key in _REGISTRY_KEY_TO_CLASS


EXPERIMENTAL_AGENTS = _LazyExperimentalAgents()


def get_all_agents_with_experimental() -> dict[str, type]:
    """获取包含实验性 Agent 的全量注册表。"""
    from .experimental import get_experimental_agents_dict

    return {**ALL_AGENTS, **get_experimental_agents_dict()}


# ============================================================
# 模块级 __getattr__：支持向后兼容的实验性 Agent 导入
# ============================================================


def __getattr__(name: str) -> Any:
    """支持 ``from app.core.agents import CompetitionExpertWriter`` 等懒加载导入。"""
    from .experimental import _EXPERIMENTAL_AGENT_REGISTRY, get_experimental_agent

    if name in _EXPERIMENTAL_AGENT_REGISTRY:
        return get_experimental_agent(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 基础设施
    "Agent",
    "ExpertAgent",
    "AgentRole",
    "QualityMetrics",
    # 核心 Agent
    "CoordinatorAgent",
    "ModelerAgent",
    "CoderAgent",
    "WriterAgent",
    # 增强 Agent
    "ProblemAnalyzer",
    "ProblemInsightAnalyzer",
    "DataUnderstandingExpert",
    "ModelSelector",
    "SmartModelerWithInnovation",
    "ExperimentDesigner",
    "AbstractGenerator",
    "ValidationExpert",
    "Reviewer",
    "BenchmarkAnalysisAgent",
    "InteractiveCoordinatorAgent",
    # 分组注册表
    "CORE_AGENTS",
    "ANALYSIS_AGENTS",
    "MODELING_AGENTS",
    "CODING_AGENTS",
    "WRITING_AGENTS",
    "VALIDATION_AGENTS",
    "INTERACTIVE_AGENTS",
    "ALL_AGENTS",
    "EXPERIMENTAL_AGENTS",
    # 工具函数
    "get_all_agents_with_experimental",
]
