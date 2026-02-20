"""
可观测性模块 - Observability Module

提供结构化日志、追踪、指标收集功能
"""

from app.observability.metrics import (
    PrometheusMiddleware,
    active_websocket_connections,
    agent_execution_seconds,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    llm_calls_total,
    llm_tokens_total,
    metrics_endpoint,
    modeling_task_duration_seconds,
    modeling_task_total,
    record_agent_execution,
    record_llm_usage,
    record_modeling_task,
    track_websocket_connection,
)
from app.observability.structured_log import (
    LogContext,
    StructuredLogger,
    get_structured_logger,
)
from app.observability.tracing import (
    TraceContext,
    TraceMiddleware,
    get_trace_id,
    set_trace_id,
)


__all__ = [
    # 结构化日志
    "StructuredLogger",
    "get_structured_logger",
    "LogContext",
    # 分布式追踪
    "TraceContext",
    "TraceMiddleware",
    "get_trace_id",
    "set_trace_id",
    # Prometheus 中间件和端点
    "PrometheusMiddleware",
    "metrics_endpoint",
    # 业务指标记录辅助函数
    "record_modeling_task",
    "record_agent_execution",
    "record_llm_usage",
    "track_websocket_connection",
    # 原始指标对象（高级用法）
    "modeling_task_duration_seconds",
    "modeling_task_total",
    "agent_execution_seconds",
    "llm_tokens_total",
    "llm_calls_total",
    "active_websocket_connections",
    "http_request_duration_seconds",
    "http_requests_total",
    "http_requests_in_progress",
]
