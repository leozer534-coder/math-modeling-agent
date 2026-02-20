"""
错误恢复与进度管理 - Error Recovery & Progress Management
============================================================

增强用户体验的核心模块

功能：
1. 智能错误分类与恢复
2. 自动重试机制（指数退避）
3. 阶段断点恢复
4. 统一进度事件发射
"""

import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.utils.log_util import logger


# ================== 错误分类 ==================


class ErrorSeverity(str, Enum):
    """错误严重程度"""

    LOW = "low"  # 可忽略
    MEDIUM = "medium"  # 需要重试
    HIGH = "high"  # 需要人工干预
    FATAL = "fatal"  # 致命错误


class ErrorCategory(str, Enum):
    """错误类别"""

    NETWORK = "network"  # 网络错误
    API = "api"  # API 调用错误
    CODE_EXECUTION = "code"  # 代码执行错误
    RESOURCE = "resource"  # 资源不足
    TIMEOUT = "timeout"  # 超时
    VALIDATION = "validation"  # 验证错误
    UNKNOWN = "unknown"  # 未知错误


class RecoveryAction(str, Enum):
    """恢复操作"""

    RETRY = "retry"  # 直接重试
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # 退避重试
    SKIP = "skip"  # 跳过当前步骤
    FALLBACK = "fallback"  # 使用备选方案
    ABORT = "abort"  # 中止执行
    MANUAL = "manual"  # 需人工处理


@dataclass
class ErrorInfo:
    """错误信息"""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: str = ""
    occurred_at: str = field(default_factory=lambda: datetime.now().isoformat())
    recoverable: bool = True
    suggested_action: RecoveryAction = RecoveryAction.RETRY


@dataclass
class RecoveryResult:
    """恢复结果"""

    success: bool
    action_taken: RecoveryAction
    attempts: int
    error_info: Optional[ErrorInfo] = None
    result_data: Any = None


# ================== 错误分类器 ==================


class ErrorClassifier:
    """
    错误分类器

    自动识别错误类型并建议恢复策略
    """

    # 异常类型到类别的直接映射（优先级最高）
    ERROR_TYPE_MAP = {
        TimeoutError: ErrorCategory.TIMEOUT,
        ConnectionError: ErrorCategory.NETWORK,
        MemoryError: ErrorCategory.RESOURCE,
        ValueError: ErrorCategory.VALIDATION,
        TypeError: ErrorCategory.VALIDATION,
        KeyError: ErrorCategory.CODE_EXECUTION,
        AttributeError: ErrorCategory.CODE_EXECUTION,
        ImportError: ErrorCategory.CODE_EXECUTION,
        ModuleNotFoundError: ErrorCategory.CODE_EXECUTION,
        SyntaxError: ErrorCategory.CODE_EXECUTION,
        NameError: ErrorCategory.CODE_EXECUTION,
        OSError: ErrorCategory.RESOURCE,
    }

    # 错误关键词映射（用于未知类型的错误）
    ERROR_PATTERNS = {
        ErrorCategory.TIMEOUT: ["timeout", "timed out", "deadline exceeded"],
        ErrorCategory.NETWORK: [
            "connection",
            "refused",
            "unreachable",
            "network",
            "socket",
            "dns",
            "ssl",
        ],
        ErrorCategory.API: [
            "api",
            "rate limit",
            "quota",
            "unauthorized",
            "forbidden",
            "400",
            "401",
            "403",
            "429",
            "500",
            "502",
            "503",
        ],
        ErrorCategory.CODE_EXECUTION: [
            "syntax",
            "indentation",
            "import",
            "module",
            "attribute",
            "name error",
            "type error",
            "value error",
            "key error",
        ],
        ErrorCategory.RESOURCE: [
            "memory",
            "disk",
            "cpu",
            "out of memory",
            "no space",
            "resource exhausted",
        ],
        ErrorCategory.VALIDATION: [
            "validation",
            "invalid",
            "required",
            "missing",
            "format",
        ],
    }

    # 恢复策略映射
    RECOVERY_MAP = {
        ErrorCategory.NETWORK: (ErrorSeverity.LOW, RecoveryAction.RETRY_WITH_BACKOFF),
        ErrorCategory.API: (ErrorSeverity.MEDIUM, RecoveryAction.RETRY_WITH_BACKOFF),
        ErrorCategory.CODE_EXECUTION: (ErrorSeverity.HIGH, RecoveryAction.FALLBACK),
        ErrorCategory.RESOURCE: (ErrorSeverity.FATAL, RecoveryAction.ABORT),
        ErrorCategory.TIMEOUT: (
            ErrorSeverity.MEDIUM,
            RecoveryAction.RETRY_WITH_BACKOFF,
        ),
        ErrorCategory.VALIDATION: (ErrorSeverity.LOW, RecoveryAction.SKIP),
        ErrorCategory.UNKNOWN: (ErrorSeverity.HIGH, RecoveryAction.MANUAL),
    }

    @classmethod
    def classify(cls, error: Exception) -> ErrorInfo:
        """
        分类错误

        Args:
            error: 异常对象

        Returns:
            错误信息
        """
        import uuid

        error_message = str(error).lower()

        # 1. 首先检查异常类型的直接映射（最优先）
        category = None
        for exc_type, cat in cls.ERROR_TYPE_MAP.items():
            if isinstance(error, exc_type):
                category = cat
                break

        # 2. 如果没有直接类型匹配，使用关键词匹配
        if category is None:
            category = ErrorCategory.UNKNOWN
            for cat, patterns in cls.ERROR_PATTERNS.items():
                if any(p in error_message for p in patterns):
                    category = cat
                    break

        # 获取恢复策略
        severity, action = cls.RECOVERY_MAP.get(
            category, (ErrorSeverity.HIGH, RecoveryAction.MANUAL)
        )

        # 致命错误不可恢复
        recoverable = severity != ErrorSeverity.FATAL

        return ErrorInfo(
            error_id=f"err_{uuid.uuid4().hex[:8]}",
            category=category,
            severity=severity,
            message=str(error),
            details=traceback.format_exc(),
            recoverable=recoverable,
            suggested_action=action,
        )


# ================== 重试管理器 ==================


class RetryManager:
    """
    重试管理器

    支持指数退避的重试机制
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs,
    ) -> RecoveryResult:
        """
        带重试执行异步函数

        Args:
            func: 要执行的异步函数
            on_retry: 重试回调

        Returns:
            恢复结果
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                return RecoveryResult(
                    success=True,
                    action_taken=RecoveryAction.RETRY
                    if attempt > 1
                    else RecoveryAction.RETRY,
                    attempts=attempt,
                    result_data=result,
                )
            except Exception as e:
                last_error = e
                error_info = ErrorClassifier.classify(e)

                logger.warning(
                    "执行失败 (尝试 %d/%d) [%s]: %s",
                    attempt, self.max_retries, error_info.category.value, e,
                )

                if on_retry:
                    on_retry(attempt, e)

                # 最后一次不等待
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info("等待 %.1fs 后重试...", delay)
                    await asyncio.sleep(delay)

        # 所有重试失败
        error_info = ErrorClassifier.classify(last_error) if last_error else None
        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.ABORT,
            attempts=self.max_retries,
            error_info=error_info,
        )

    def _calculate_delay(self, attempt: int) -> float:
        """计算退避延迟"""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay)


# ================== 错误恢复管理器 ==================


class ErrorRecoveryManager:
    """
    错误恢复管理器

    集中管理错误处理和恢复策略
    """

    def __init__(self):
        self.retry_manager = RetryManager()
        self._error_history: List[ErrorInfo] = []
        self._fallback_handlers: Dict[ErrorCategory, Callable] = {}

    def register_fallback(
        self, category: ErrorCategory, handler: Callable[[ErrorInfo], Any]
    ) -> None:
        """注册备选处理器"""
        self._fallback_handlers[category] = handler

    async def handle_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """
        处理错误

        Args:
            error: 异常
            context: 上下文信息

        Returns:
            恢复结果
        """
        error_info = ErrorClassifier.classify(error)
        self._error_history.append(error_info)

        logger.error("错误 [%s]: %s", error_info.category.value, error_info.message)

        # 根据建议操作处理
        if error_info.suggested_action == RecoveryAction.SKIP:
            return RecoveryResult(
                success=True,
                action_taken=RecoveryAction.SKIP,
                attempts=0,
                error_info=error_info,
            )

        if error_info.suggested_action == RecoveryAction.FALLBACK:
            handler = self._fallback_handlers.get(error_info.category)
            if handler:
                try:
                    result = handler(error_info)
                    return RecoveryResult(
                        success=True,
                        action_taken=RecoveryAction.FALLBACK,
                        attempts=1,
                        result_data=result,
                    )
                except Exception as e:
                    logger.error("备选处理也失败: %s", e)

        return RecoveryResult(
            success=False,
            action_taken=error_info.suggested_action,
            attempts=0,
            error_info=error_info,
        )

    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误统计"""
        by_category = {}
        by_severity = {}

        for error in self._error_history:
            by_category[error.category.value] = (
                by_category.get(error.category.value, 0) + 1
            )
            by_severity[error.severity.value] = (
                by_severity.get(error.severity.value, 0) + 1
            )

        return {
            "total_errors": len(self._error_history),
            "by_category": by_category,
            "by_severity": by_severity,
            "recoverable_count": sum(1 for e in self._error_history if e.recoverable),
        }


# ================== 进度事件发射器 ==================


class ProgressEventType(str, Enum):
    """进度事件类型"""

    PHASE_START = "phase_start"
    PHASE_PROGRESS = "phase_progress"
    PHASE_COMPLETE = "phase_complete"
    PHASE_ERROR = "phase_error"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"


@dataclass
class ProgressEvent:
    """进度事件"""

    event_type: ProgressEventType
    phase: str
    progress: int  # 0-100
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "phase": self.phase,
            "progress": self.progress,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ProgressEventEmitter:
    """
    进度事件发射器

    统一进度事件格式和发送
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._listeners: List[Callable[[ProgressEvent], None]] = []
        self._current_phase: str = "init"
        self._phase_progress: Dict[str, int] = {}

    def add_listener(self, listener: Callable[[ProgressEvent], None]) -> None:
        """添加事件监听器"""
        self._listeners.append(listener)

    async def emit(self, event: ProgressEvent) -> None:
        """发射事件"""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.warning("事件监听器执行失败: %s", e)

    async def start_phase(self, phase: str, message: str = "") -> None:
        """开始新阶段"""
        self._current_phase = phase
        self._phase_progress[phase] = 0

        await self.emit(
            ProgressEvent(
                event_type=ProgressEventType.PHASE_START,
                phase=phase,
                progress=0,
                message=message or f"开始 {phase}",
            )
        )

    async def update_progress(self, progress: int, message: str = "") -> None:
        """更新当前阶段进度"""
        self._phase_progress[self._current_phase] = progress

        await self.emit(
            ProgressEvent(
                event_type=ProgressEventType.PHASE_PROGRESS,
                phase=self._current_phase,
                progress=progress,
                message=message,
            )
        )

    async def complete_phase(self, message: str = "") -> None:
        """完成当前阶段"""
        self._phase_progress[self._current_phase] = 100

        await self.emit(
            ProgressEvent(
                event_type=ProgressEventType.PHASE_COMPLETE,
                phase=self._current_phase,
                progress=100,
                message=message or f"{self._current_phase} 完成",
            )
        )

    async def report_error(self, error_info: ErrorInfo, message: str = "") -> None:
        """报告错误"""
        await self.emit(
            ProgressEvent(
                event_type=ProgressEventType.PHASE_ERROR,
                phase=self._current_phase,
                progress=self._phase_progress.get(self._current_phase, 0),
                message=message or f"错误: {error_info.message}",
                details={
                    "error": error_info.message,
                    "category": error_info.category.value,
                },
            )
        )

    async def complete_task(self, message: str = "任务完成") -> None:
        """任务完成"""
        await self.emit(
            ProgressEvent(
                event_type=ProgressEventType.TASK_COMPLETE,
                phase="complete",
                progress=100,
                message=message,
            )
        )

    async def fail_task(self, error_info: ErrorInfo) -> None:
        """任务失败"""
        await self.emit(
            ProgressEvent(
                event_type=ProgressEventType.TASK_FAILED,
                phase="failed",
                progress=self.get_overall_progress(),
                message=f"任务失败: {error_info.message}",
                details={"error": error_info.message},
            )
        )

    def get_overall_progress(self) -> int:
        """计算总体进度"""
        if not self._phase_progress:
            return 0
        return sum(self._phase_progress.values()) // len(self._phase_progress)


# ================== 便捷函数 ==================


def create_error_recovery() -> ErrorRecoveryManager:
    """创建错误恢复管理器"""
    return ErrorRecoveryManager()


def create_retry_manager(max_retries: int = 3, base_delay: float = 1.0) -> RetryManager:
    """创建重试管理器"""
    return RetryManager(max_retries=max_retries, base_delay=base_delay)


def create_progress_emitter(task_id: str) -> ProgressEventEmitter:
    """创建进度事件发射器"""
    return ProgressEventEmitter(task_id)
