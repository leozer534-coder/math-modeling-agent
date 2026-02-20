"""
Human-in-Loop (HIL) 人机交互模块

提供工作流中关键决策点的用户交互功能：
1. 模型选择确认
2. 方案审核和修改
3. 参数调整
4. 质量检查点
"""

from app.core.hil.hil_manager import (
    HILDecision,
    HILEvent,
    HILEventType,
    HILManager,
    HILOption,
    HILResponse,
    cleanup_stale_managers,
    get_hil_manager,
    register_hil_manager,
    unregister_hil_manager,
)


__all__ = [
    "HILManager",
    "HILEvent",
    "HILEventType",
    "HILResponse",
    "HILDecision",
    "HILOption",
    "get_hil_manager",
    "register_hil_manager",
    "unregister_hil_manager",
    "cleanup_stale_managers",
]
