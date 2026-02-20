"""
结构化日志模块 - Structured Logger

提供JSON格式的结构化日志功能

功能：
1. JSON格式输出（便于ELK/Loki解析）
2. 自动注入trace_id、task_id等上下文
3. 日志级别管理
4. 敏感信息脱敏
5. 日志文件持久化（按大小/时间轮转）
"""

import json
import logging
import os
import sys
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from app.observability.tracing import get_trace_id


# ============= 日志目录配置 =============

# 日志文件存放目录，相对于项目根目录
LOG_DIR = os.environ.get("LOG_DIR", "logs")

# 单个日志文件最大大小（字节），默认 100MB
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 100 * 1024 * 1024))

# 日志文件保留数量（按大小轮转时的备份数）
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))

# 是否启用文件日志输出
LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "true").lower() in ("true", "1", "yes")


def _ensure_log_dir() -> str:
    """
    确保日志目录存在，返回绝对路径。

    日志目录位于 backend/logs/，如果不存在则自动创建。
    """
    log_path = Path(LOG_DIR)
    log_path.mkdir(parents=True, exist_ok=True)
    return str(log_path)


# ============= 上下文管理 =============

# 日志上下文（线程/协程安全）
_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


@dataclass
class LogContext:
    """日志上下文数据"""
    trace_id: Optional[str] = None
    task_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_type: Optional[str] = None
    stage: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("extra")
        data.update(self.extra)
        return {k: v for k, v in data.items() if v is not None}


def set_log_context(**kwargs) -> None:
    """设置日志上下文"""
    current = _log_context.get().copy()
    current.update(kwargs)
    _log_context.set(current)


def get_log_context() -> Dict[str, Any]:
    """获取日志上下文"""
    ctx = _log_context.get().copy()
    # 自动注入trace_id
    if "trace_id" not in ctx:
        trace_id = get_trace_id()
        if trace_id:
            ctx["trace_id"] = trace_id
    return ctx


def clear_log_context() -> None:
    """清空日志上下文"""
    _log_context.set({})


# ============= 敏感信息处理 =============

SENSITIVE_KEYS = {
    "password", "api_key", "apikey", "secret", "token",
    "auth", "credential", "private_key", "access_key",
}


def mask_sensitive(data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
    """遮蔽敏感信息"""
    if max_depth <= 0:
        return data

    result = {}
    for key, value in data.items():
        key_lower = key.lower()

        # 检查是否是敏感字段
        is_sensitive = any(s in key_lower for s in SENSITIVE_KEYS)

        if is_sensitive and isinstance(value, str):
            # 遮蔽敏感值
            if len(value) <= 8:
                result[key] = "***"
            else:
                result[key] = f"{value[:4]}...{value[-2:]}"
        elif isinstance(value, dict):
            result[key] = mask_sensitive(value, max_depth - 1)
        elif isinstance(value, list):
            result[key] = [
                mask_sensitive(item, max_depth - 1) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


# ============= JSON格式化 =============

class JsonFormatter(logging.Formatter):
    """JSON日志格式化器"""

    def __init__(self, include_context: bool = True, mask_sensitive_: bool = True):
        super().__init__()
        self.include_context = include_context
        self.mask_sensitive = mask_sensitive_

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加上下文
        if self.include_context:
            ctx = get_log_context()
            if ctx:
                log_data["context"] = ctx

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外数据
        if hasattr(record, "data") and record.data:
            extra_data = record.data
            if self.mask_sensitive:
                extra_data = mask_sensitive(extra_data)
            log_data["data"] = extra_data

        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============= 结构化日志器 =============

class StructuredLogger:
    """
    结构化日志器

    提供JSON格式输出和上下文自动注入，支持同时输出到控制台和文件。

    文件日志支持两种轮转策略（同时启用）:
    - 按大小轮转: 单个文件达到 100MB 后自动轮转，保留最近 10 个备份
    - 按时间轮转: 每天午夜自动轮转，保留最近 30 天的日志

    使用示例：
        >>> logger = get_structured_logger("agent")
        >>> logger.info("任务开始", task_id="123", stage="分析")
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        format_json: bool = True,
        log_to_file: bool = True,
    ):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._format_json = format_json

        # 避免重复添加handler
        if not self._logger.handlers:
            # --- 控制台 Handler ---
            console_handler = logging.StreamHandler(sys.stdout)

            if format_json:
                console_handler.setFormatter(JsonFormatter())
            else:
                console_handler.setFormatter(logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                ))

            self._logger.addHandler(console_handler)

            # --- 文件 Handler（日志持久化） ---
            if log_to_file and LOG_TO_FILE:
                self._setup_file_handlers(name, level, format_json)

    def _setup_file_handlers(
        self,
        name: str,
        level: int,
        format_json: bool,
    ) -> None:
        """
        配置文件日志 Handler。

        同时添加两个文件 Handler:
        1. RotatingFileHandler: 按大小轮转（100MB/文件，保留10个备份）
        2. TimedRotatingFileHandler: 按时间轮转（每天午夜，保留30天）
        """
        try:
            log_dir = _ensure_log_dir()
            formatter = JsonFormatter() if format_json else logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )

            # 按大小轮转的日志文件: logs/{name}.log
            size_handler = RotatingFileHandler(
                filename=os.path.join(log_dir, f"{name}.log"),
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            size_handler.setLevel(level)
            size_handler.setFormatter(formatter)
            self._logger.addHandler(size_handler)

            # 按时间轮转的日志文件: logs/{name}.daily.log
            # 每天午夜轮转，后缀格式 .YYYY-MM-DD，保留 30 天
            time_handler = TimedRotatingFileHandler(
                filename=os.path.join(log_dir, f"{name}.daily.log"),
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
                utc=True,
            )
            time_handler.suffix = "%Y-%m-%d"
            time_handler.setLevel(level)
            time_handler.setFormatter(formatter)
            self._logger.addHandler(time_handler)

        except OSError as e:
            # 文件 Handler 创建失败不应阻塞应用启动，回退到仅控制台输出。
            # 注意: 此处故意使用 print 而非 logger —— 因为此刻 logger 的文件
            # 输出能力本身就处于不可用状态，用 logger 可能导致递归或丢失告警。
            print(
                f"[WARNING] 文件日志 Handler 创建失败 (logger={name}): {e}，"
                "将仅输出到控制台",
                file=sys.stderr,
            )

    def _log(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        **kwargs,
    ) -> None:
        """内部日志方法"""
        record = self._logger.makeRecord(
            name=self._logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=exc_info if exc_info else None,
        )

        if kwargs:
            record.data = kwargs

        self._logger.handle(record)

    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """错误日志"""
        self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """严重错误日志"""
        self._log(logging.CRITICAL, message, exc_info=exc_info, **kwargs)

    def with_context(self, **context) -> "StructuredLogger":
        """设置上下文并返回self（链式调用）"""
        set_log_context(**context)
        return self


# ============= 全局实例 =============

_loggers: Dict[str, StructuredLogger] = {}


def get_structured_logger(name: str = "app") -> StructuredLogger:
    """
    获取结构化日志器（单例模式）。

    同一 name 只会创建一次 Logger 实例，后续调用返回缓存实例。

    Args:
        name: 日志器名称，建议按模块命名（如 "agent", "workflow", "api"）

    Returns:
        StructuredLogger 实例
    """
    if name not in _loggers:
        format_json = os.environ.get("LOG_FORMAT", "json").lower() == "json"
        level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)

        _loggers[name] = StructuredLogger(
            name,
            level=level,
            format_json=format_json,
            log_to_file=LOG_TO_FILE,
        )

    return _loggers[name]
