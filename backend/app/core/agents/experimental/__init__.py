"""
实验性 Agent 子包（懒加载）
============================

包含未集成到当前工作流的实验性 Agent，按需导入以减少启动时间和内存占用。

使用方式::

    # 方式一：通过懒加载函数按需导入
    from app.core.agents.experimental import get_experimental_agent
    cls = get_experimental_agent("HyperparameterTuningMaster")

    # 方式二：直接从子模块导入
    from app.core.agents.experimental.hyperparameter_tuning_master import HyperparameterTuningMaster

包含的实验性 Agent:
- HyperparameterTuningMaster: 超参数调优大师
- PerformanceOptimizer: 性能优化器
- CompetitionExpertWriter: 竞赛风格写作师
- InnovationHighlighter: 创新亮点突出师
- ResultInterpretationExpert: 结果解释专家
- PatternDiscoveryEngine: 规律发现引擎
"""

from typing import Any


# 实验性 Agent 名称 -> 模块路径的映射表（用于懒加载）
_EXPERIMENTAL_AGENT_REGISTRY: dict[str, tuple[str, str]] = {
    "HyperparameterTuningMaster": (
        "app.core.agents.experimental.hyperparameter_tuning_master",
        "HyperparameterTuningMaster",
    ),
    "PerformanceOptimizer": (
        "app.core.agents.experimental.performance_optimizer",
        "PerformanceOptimizer",
    ),
    "CompetitionExpertWriter": (
        "app.core.agents.experimental.competition_expert_writer",
        "CompetitionExpertWriter",
    ),
    "InnovationHighlighter": (
        "app.core.agents.experimental.innovation_highlighter",
        "InnovationHighlighter",
    ),
    "ResultInterpretationExpert": (
        "app.core.agents.experimental.result_interpretation_expert",
        "ResultInterpretationExpert",
    ),
    "PatternDiscoveryEngine": (
        "app.core.agents.experimental.pattern_discovery_engine",
        "PatternDiscoveryEngine",
    ),
}

# 注册表 key -> Agent 类名的映射（与旧 EXPERIMENTAL_AGENTS 字典兼容）
_REGISTRY_KEY_TO_CLASS: dict[str, str] = {
    "competition_writer": "CompetitionExpertWriter",
    "innovation_highlighter": "InnovationHighlighter",
    "hyperparameter_tuner": "HyperparameterTuningMaster",
    "pattern_discovery_engine": "PatternDiscoveryEngine",
    "performance_optimizer": "PerformanceOptimizer",
    "result_interpreter": "ResultInterpretationExpert",
}


def get_experimental_agent(class_name: str) -> type:
    """
    按需加载实验性 Agent 类。

    Args:
        class_name: Agent 类名，如 "HyperparameterTuningMaster"

    Returns:
        对应的 Agent 类

    Raises:
        KeyError: 未知的 Agent 类名
        ImportError: 模块导入失败
    """
    if class_name not in _EXPERIMENTAL_AGENT_REGISTRY:
        available = ", ".join(sorted(_EXPERIMENTAL_AGENT_REGISTRY.keys()))
        raise KeyError(
            f"未知的实验性 Agent: {class_name!r}，"
            f"可用的实验性 Agent: {available}"
        )

    module_path, attr_name = _EXPERIMENTAL_AGENT_REGISTRY[class_name]
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


def get_experimental_agents_dict() -> dict[str, type]:
    """
    懒加载所有实验性 Agent 并返回注册表字典。

    与旧的 EXPERIMENTAL_AGENTS 字典格式兼容，但仅在调用时才真正导入。

    Returns:
        {registry_key: AgentClass} 字典
    """
    result: dict[str, type] = {}
    for key, class_name in _REGISTRY_KEY_TO_CLASS.items():
        result[key] = get_experimental_agent(class_name)
    return result


def list_experimental_agents() -> list[str]:
    """返回所有可用的实验性 Agent 类名列表。"""
    return sorted(_EXPERIMENTAL_AGENT_REGISTRY.keys())


def __getattr__(name: str) -> Any:
    """
    模块级 __getattr__，支持 ``from app.core.agents.experimental import XxxAgent`` 的懒加载。

    当通过属性访问（如 import）请求某个实验性 Agent 类时，自动按需导入。
    """
    if name in _EXPERIMENTAL_AGENT_REGISTRY:
        return get_experimental_agent(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "get_experimental_agent",
    "get_experimental_agents_dict",
    "list_experimental_agents",
    # 以下类名通过 __getattr__ 懒加载支持
    "HyperparameterTuningMaster",
    "PerformanceOptimizer",
    "CompetitionExpertWriter",
    "InnovationHighlighter",
    "ResultInterpretationExpert",
    "PatternDiscoveryEngine",
]
