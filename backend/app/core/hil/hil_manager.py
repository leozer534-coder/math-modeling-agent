"""
HIL (Human-in-Loop) 核心管理器

处理工作流中的人机交互事件，支持：
- 异步/同步交互模式
- 超时和默认值处理
- WebSocket 和 Redis 消息发布
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.config.setting import settings
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class HILEventType(str, Enum):
    MODEL_SELECTION = "model_selection"
    PLAN_REVIEW = "plan_review"
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    QUALITY_CHECKPOINT = "quality_checkpoint"
    ERROR_RECOVERY = "error_recovery"
    AGENT_HANDOFF = "agent_handoff"
    RESULT_APPROVAL = "result_approval"
    CUSTOM = "custom"


class HILDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    SKIP = "skip"
    RETRY = "retry"
    ESCALATE = "escalate"
    TIMEOUT = "timeout"


@dataclass
class HILOption:
    id: str
    label: str
    description: str = ""
    is_default: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HILEvent:
    event_id: str
    event_type: HILEventType
    title: str
    description: str
    phase: str
    options: List[HILOption] = field(default_factory=list)
    current_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    allow_custom_input: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "phase": self.phase,
            "options": [
                {
                    "id": opt.id,
                    "label": opt.label,
                    "description": opt.description,
                    "is_default": opt.is_default,
                    "metadata": opt.metadata,
                }
                for opt in self.options
            ],
            "current_value": self.current_value,
            "metadata": self.metadata,
            "timeout_seconds": self.timeout_seconds,
            "allow_custom_input": self.allow_custom_input,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HILResponse:
    event_id: str
    decision: HILDecision
    selected_option_id: Optional[str] = None
    custom_value: Any = None
    user_comment: str = ""
    response_time: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HILResponse":
        return cls(
            event_id=data.get("event_id", ""),
            decision=HILDecision(data.get("decision", "approve")),
            selected_option_id=data.get("selected_option_id"),
            custom_value=data.get("custom_value"),
            user_comment=data.get("user_comment", ""),
            response_time=data.get("response_time", 0.0),
        )
    
    @classmethod
    def timeout_response(cls, event_id: str) -> "HILResponse":
        return cls(
            event_id=event_id,
            decision=HILDecision.TIMEOUT,
        )
    
    @classmethod
    def default_approve(cls, event_id: str) -> "HILResponse":
        return cls(
            event_id=event_id,
            decision=HILDecision.APPROVE,
        )


HILCallback = Callable[[HILEvent], Awaitable[HILResponse]]


class HILManager:
    
    def __init__(
        self,
        task_id: str,
        callback: Optional[HILCallback] = None,
        auto_approve: bool = False,
        default_timeout: Optional[int] = None,
        max_history: Optional[int] = None,
    ):
        self.task_id = task_id
        self.callback = callback
        self.auto_approve = auto_approve
        # 优先使用传入参数，否则从全局配置读取
        self.default_timeout = (
            default_timeout if default_timeout is not None
            else settings.HIL_RESPONSE_TIMEOUT
        )
        # 历史记录上限，优先使用传入参数，否则从全局配置读取
        self._max_history = (
            max_history if max_history is not None
            else settings.HIL_MAX_HISTORY
        )

        self._pending_events: Dict[str, HILEvent] = {}
        self._responses: Dict[str, HILResponse] = {}
        self._response_futures: Dict[str, asyncio.Future] = {}

        self._event_history: List[Dict[str, Any]] = []
        # 记录注册到全局注册表的时间，用于过期清理
        self._registered_at: float = 0.0

    async def cleanup(self):
        """清理资源并从全局注册表中移除"""
        # 取消所有挂起的 Future
        for event_id, future in list(self._response_futures.items()):
            if not future.done():
                future.cancel()
        self._response_futures.clear()
        self._pending_events.clear()
        # 从全局注册表移除（使用锁保护）
        await unregister_hil_manager(self.task_id)
        logger.debug("HILManager 已清理: task_id=%s", self.task_id)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        return False

    async def request_decision(
        self,
        event_type: HILEventType,
        title: str,
        description: str,
        phase: str,
        options: Optional[List[HILOption]] = None,
        current_value: Any = None,
        timeout: Optional[int] = None,
        allow_custom: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HILResponse:
        if self.auto_approve:
            event_id = str(uuid.uuid4())
            logger.info("HIL auto-approve: %s", title)
            return HILResponse.default_approve(event_id)
        
        event = HILEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            title=title,
            description=description,
            phase=phase,
            options=options or [],
            current_value=current_value,
            metadata=metadata or {},
            timeout_seconds=timeout or self.default_timeout,
            allow_custom_input=allow_custom,
        )
        
        self._pending_events[event.event_id] = event
        
        await self._publish_event(event)
        
        try:
            response = await self._wait_for_response(event)
        except asyncio.TimeoutError:
            # 超时后尝试使用默认选项继续执行，而非直接返回 TIMEOUT 终止流程
            response = self._build_timeout_response(event)
            logger.warning(
                "HIL 等待超时 (%ss): %s, 使用默认决策: %s",
                event.timeout_seconds, title, response.decision.value,
            )
            # 通过 WebSocket 通知用户超时及自动采用的默认决策
            await self._notify_timeout(event, response)
        finally:
            self._pending_events.pop(event.event_id, None)

        self._record_event(event, response)

        return response
    
    async def request_model_selection(
        self,
        phase: str,
        available_models: List[Dict[str, str]],
        recommended: Optional[str] = None,
    ) -> HILResponse:
        options = [
            HILOption(
                id=model["id"],
                label=model["name"],
                description=model.get("description", ""),
                is_default=(model["id"] == recommended),
            )
            for model in available_models
        ]
        
        return await self.request_decision(
            event_type=HILEventType.MODEL_SELECTION,
            title="选择建模方法",
            description="请选择用于本阶段的建模方法",
            phase=phase,
            options=options,
            current_value=recommended,
        )
    
    async def request_plan_review(
        self,
        phase: str,
        plan_content: str,
        plan_summary: str,
    ) -> HILResponse:
        options = [
            HILOption(id="approve", label="批准", description="继续执行此方案", is_default=True),
            HILOption(id="modify", label="修改", description="我要修改这个方案"),
            HILOption(id="reject", label="拒绝", description="重新生成方案"),
        ]
        
        return await self.request_decision(
            event_type=HILEventType.PLAN_REVIEW,
            title="方案审核",
            description=plan_summary,
            phase=phase,
            options=options,
            current_value=plan_content,
            allow_custom=True,
            metadata={"full_plan": plan_content},
        )
    
    async def request_error_recovery(
        self,
        phase: str,
        error_message: str,
        error_count: int,
        available_actions: List[str],
    ) -> HILResponse:
        action_map = {
            "retry": HILOption(id="retry", label="重试", description="再次尝试执行"),
            "skip": HILOption(id="skip", label="跳过", description="跳过此步骤继续"),
            "escalate": HILOption(id="escalate", label="升级", description="使用更强的模型处理"),
            "abort": HILOption(id="abort", label="终止", description="终止当前任务"),
        }
        
        options = [action_map[a] for a in available_actions if a in action_map]
        
        return await self.request_decision(
            event_type=HILEventType.ERROR_RECOVERY,
            title="错误恢复",
            description=f"遇到错误 (第{error_count}次): {error_message[:200]}",
            phase=phase,
            options=options,
            metadata={"error_message": error_message, "error_count": error_count},
        )
    
    async def request_agent_handoff_approval(
        self,
        phase: str,
        from_model: str,
        to_model: str,
        reason: str,
    ) -> HILResponse:
        options = [
            HILOption(id="approve", label="同意升级", description=f"升级到 {to_model}", is_default=True),
            HILOption(id="retry", label="再试一次", description=f"继续使用 {from_model}"),
            HILOption(id="skip", label="跳过", description="跳过此任务"),
        ]
        
        return await self.request_decision(
            event_type=HILEventType.AGENT_HANDOFF,
            title="模型升级确认",
            description=f"建议从 {from_model} 升级到 {to_model}。原因: {reason}",
            phase=phase,
            options=options,
            metadata={"from_model": from_model, "to_model": to_model, "reason": reason},
        )
    
    async def request_result_approval(
        self,
        phase: str,
        result_summary: str,
        quality_score: Optional[float] = None,
    ) -> HILResponse:
        options = [
            HILOption(id="approve", label="接受", description="接受此结果", is_default=True),
            HILOption(id="modify", label="修改", description="我要修改这个结果"),
            HILOption(id="regenerate", label="重新生成", description="重新执行此阶段"),
        ]
        
        metadata = {"result_summary": result_summary}
        if quality_score is not None:
            metadata["quality_score"] = quality_score
        
        return await self.request_decision(
            event_type=HILEventType.RESULT_APPROVAL,
            title="结果确认",
            description=f"请确认以下结果: {result_summary[:300]}",
            phase=phase,
            options=options,
            metadata=metadata,
            allow_custom=True,
        )
    
    async def submit_response(self, event_id: str, response: HILResponse):
        if event_id in self._response_futures:
            future = self._response_futures[event_id]
            if not future.done():
                future.set_result(response)
        
        self._responses[event_id] = response
    
    async def _publish_event(self, event: HILEvent):
        logger.info("HIL event published: %s (%s)", event.title, event.event_type.value)

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(
                content=f"[HIL] {event.title}: {event.description}",
                type="hil_request",
                hil_event=event.to_dict(),
            ),
        )

        # 注册到全局注册表，以便 WebSocket 路由能找到此实例（使用锁保护）
        await register_hil_manager(self.task_id, self)

        if self.callback:
            try:
                response = await self.callback(event)
                await self.submit_response(event.event_id, response)
            except Exception as e:
                logger.error("HIL callback error: %s", e)
    
    async def _wait_for_response(self, event: HILEvent) -> HILResponse:
        """等待用户响应，超时后抛出 asyncio.TimeoutError。"""
        if self.callback:
            if event.event_id in self._responses:
                return self._responses[event.event_id]

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._response_futures[event.event_id] = future

        try:
            response = await asyncio.wait_for(future, timeout=event.timeout_seconds)
            return response
        finally:
            self._response_futures.pop(event.event_id, None)

    def _build_timeout_response(self, event: HILEvent) -> HILResponse:
        """超时后构建友好的默认响应，优先选择标记为 is_default 的选项。

        策略优先级：
        1. 使用 options 中标记为 is_default=True 的选项，决策设为 APPROVE
        2. 如果没有默认选项但有可选项，使用第一个选项，决策设为 APPROVE
        3. 如果没有任何选项，回退为 APPROVE 决策（无选项ID）

        这样确保超时不会阻断工作流，而是以最安全的默认行为继续执行。
        """
        # 查找标记为默认的选项
        default_option: Optional[HILOption] = None
        for opt in event.options:
            if opt.is_default:
                default_option = opt
                break

        # 没有标记默认的，则使用第一个选项
        if default_option is None and event.options:
            default_option = event.options[0]

        if default_option is not None:
            return HILResponse(
                event_id=event.event_id,
                decision=HILDecision.APPROVE,
                selected_option_id=default_option.id,
                user_comment=f"系统超时自动选择默认选项: {default_option.label}",
            )

        # 无任何选项时，直接批准继续
        return HILResponse(
            event_id=event.event_id,
            decision=HILDecision.APPROVE,
            user_comment="系统超时自动批准",
        )

    async def _notify_timeout(self, event: HILEvent, response: HILResponse) -> None:
        """超时后通过 WebSocket 通知用户，告知自动采用的默认决策。"""
        # 构建用户友好的通知内容
        if response.selected_option_id:
            detail = f"已自动选择默认选项「{response.selected_option_id}」继续执行"
        else:
            detail = "已自动批准继续执行"

        timeout_msg = (
            f"[HIL 超时] {event.title}: "
            f"等待用户响应超过 {event.timeout_seconds} 秒，{detail}。"
        )

        try:
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(
                    content=timeout_msg,
                    type="warning",
                ),
            )
        except Exception as e:
            # 通知失败不应阻断主流程，仅记录日志
            logger.error("HIL 超时通知发送失败: %s", e)

    def _record_event(self, event: HILEvent, response: HILResponse) -> None:
        """记录交互事件，超过上限时删除最旧的记录。"""
        record = {
            "event": event.to_dict(),
            "response": {
                "decision": response.decision.value,
                "selected_option_id": response.selected_option_id,
                "custom_value": response.custom_value,
                "user_comment": response.user_comment,
                "response_time": response.response_time,
            },
            "timestamp": datetime.now().isoformat(),
        }
        self._event_history.append(record)

        # 超过历史记录上限时，移除最旧的记录
        if len(self._event_history) > self._max_history:
            overflow = len(self._event_history) - self._max_history
            self._event_history = self._event_history[overflow:]
            logger.debug(
                "HIL 历史记录已裁剪: 移除 %s 条最旧记录, 当前保留 %s 条",
                overflow, len(self._event_history),
            )

    def get_event_history(self) -> List[Dict[str, Any]]:
        """获取事件历史记录的副本。"""
        return self._event_history.copy()

    def get_pending_events(self) -> List[HILEvent]:
        """获取所有待响应的 HIL 事件列表。"""
        return list(self._pending_events.values())


# ==================== 全局 HILManager 注册表 ====================
# 用于 WebSocket 路由根据 task_id 找到对应的 HILManager 实例
_hil_registry: Dict[str, "HILManager"] = {}
# 异步锁，保护注册表的并发读写安全
_hil_lock: asyncio.Lock = asyncio.Lock()


async def register_hil_manager(task_id: str, manager: "HILManager") -> None:
    """将 HILManager 实例注册到全局注册表（线程安全）

    使用 asyncio.Lock 保护写操作，同时记录注册时间用于过期清理。
    幂等操作：对同一 task_id 重复注册只会更新时间戳，不会重复创建条目。
    """
    async with _hil_lock:
        manager._registered_at = time.time()
        _hil_registry[task_id] = manager
        logger.debug("HILManager 已注册: task_id=%s", task_id)


async def get_hil_manager(task_id: str) -> Optional["HILManager"]:
    """根据 task_id 获取对应的 HILManager 实例（线程安全）"""
    async with _hil_lock:
        return _hil_registry.get(task_id)


async def unregister_hil_manager(task_id: str) -> None:
    """任务结束时从注册表中移除 HILManager（线程安全）"""
    async with _hil_lock:
        removed = _hil_registry.pop(task_id, None)
        if removed:
            logger.debug("HILManager 已注销: task_id=%s", task_id)


async def cleanup_stale_managers(max_age_seconds: int = 3600) -> int:
    """清理超过指定时间未活动的 HILManager，防止内存泄漏

    Args:
        max_age_seconds: 最大存活时间（秒），默认 3600（1小时）

    Returns:
        本次清理移除的 HILManager 数量
    """
    now = time.time()
    stale_task_ids: List[str] = []

    async with _hil_lock:
        for task_id, manager in _hil_registry.items():
            age = now - manager._registered_at
            if age > max_age_seconds:
                stale_task_ids.append(task_id)

        for task_id in stale_task_ids:
            manager = _hil_registry.pop(task_id)
            # 取消该 manager 中所有挂起的 Future，避免协程永久挂起
            for future in manager._response_futures.values():
                if not future.done():
                    future.cancel()
            manager._response_futures.clear()
            manager._pending_events.clear()

    if stale_task_ids:
        logger.info(
            "已清理 %s 个过期 HILManager: %s",
            len(stale_task_ids), stale_task_ids,
        )

    return len(stale_task_ids)
