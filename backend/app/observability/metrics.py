"""
Prometheus 指标收集模块 - Metrics Collection

提供应用核心业务指标的定义、收集和暴露功能。

功能:
1. 建模任务耗时和计数指标
2. Agent 执行耗时指标
3. LLM Token 消耗指标
4. WebSocket 连接数指标
5. HTTP 请求延迟指标
6. FastAPI 中间件自动采集 HTTP 指标
7. /metrics 端点暴露 Prometheus 格式数据
"""

import time
from typing import Callable

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ============= 全局注册表 =============
# 使用默认注册表，兼容多进程部署时可切换为 multiprocess 模式
REGISTRY = CollectorRegistry()

# 尝试合并多进程收集器（gunicorn 多 worker 场景）
try:
    multiprocess.MultiProcessCollector(REGISTRY)
except ValueError:
    # 非多进程模式，使用默认注册表
    from prometheus_client import REGISTRY as DEFAULT_REGISTRY

    REGISTRY = DEFAULT_REGISTRY


# ============= 建模任务指标 =============

# 建模任务耗时直方图
# 桶边界覆盖: 10s, 30s, 1min, 2min, 5min, 10min, 30min, 1h
modeling_task_duration_seconds = Histogram(
    "modeling_task_duration_seconds",
    "建模任务端到端耗时（秒）",
    labelnames=["task_type"],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600),
    registry=REGISTRY,
)

# 建模任务计数器
modeling_task_total = Counter(
    "modeling_task_total",
    "建模任务总数",
    labelnames=["status"],  # success / failed / cancelled
    registry=REGISTRY,
)


# ============= Agent 执行指标 =============

# Agent 执行耗时直方图
agent_execution_seconds = Histogram(
    "agent_execution_seconds",
    "Agent 单次执行耗时（秒）",
    labelnames=["agent_type"],  # coordinator / modeler / coder / writer / reviewer
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
    registry=REGISTRY,
)


# ============= LLM 消耗指标 =============

# LLM Token 消耗计数器
llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM Token 消耗总量",
    labelnames=["model", "direction"],  # direction: input / output
    registry=REGISTRY,
)

# LLM 调用计数器（补充指标，便于计算平均 token/请求）
llm_calls_total = Counter(
    "llm_calls_total",
    "LLM 调用总次数",
    labelnames=["model", "status"],  # status: success / error
    registry=REGISTRY,
)


# ============= WebSocket 指标 =============

# 当前活跃 WebSocket 连接数
active_websocket_connections = Gauge(
    "active_websocket_connections",
    "当前活跃的 WebSocket 连接数",
    registry=REGISTRY,
)


# ============= HTTP 指标 =============

# HTTP 请求延迟直方图
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求处理延迟（秒）",
    labelnames=["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

# HTTP 请求总数计数器
http_requests_total = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    labelnames=["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

# 当前正在处理的请求数
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "当前正在处理的 HTTP 请求数",
    labelnames=["method"],
    registry=REGISTRY,
)


# ============= 辅助函数 =============


def _normalize_path(path: str) -> str:
    """
    归一化 URL 路径，避免高基数标签。

    将包含动态参数的路径（如 /api/v1/tasks/abc123）
    归一化为 /api/v1/tasks/{id}，防止 Prometheus 标签爆炸。
    """
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        # 跳过看起来像 UUID 或纯数字的路径段
        if len(part) >= 8 and part.replace("-", "").isalnum():
            normalized.append("{id}")
        elif part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


# ============= HTTP 指标收集中间件 =============


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus HTTP 指标收集中间件。

    自动为每个 HTTP 请求记录:
    - 请求延迟 (Histogram)
    - 请求计数 (Counter)
    - 进行中请求数 (Gauge)

    跳过 /metrics, /health, /docs 等基础设施端点。
    """

    # 不采集指标的路径前缀
    SKIP_PREFIXES = ("/metrics", "/health", "/docs", "/openapi.json", "/redoc")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过基础设施端点，避免自身请求污染业务指标
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return await call_next(request)

        method = request.method
        endpoint = _normalize_path(path)

        # 记录进行中请求
        http_requests_in_progress.labels(method=method).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        finally:
            # 计算耗时并记录指标
            duration = time.perf_counter() - start_time

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).observe(duration)

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            http_requests_in_progress.labels(method=method).dec()

        return response


# ============= 指标端点 =============


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus 指标暴露端点。

    返回 Prometheus 文本格式的所有指标数据，
    供 Prometheus Server 定期抓取。
    """
    metrics_output = generate_latest(REGISTRY)
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )


# ============= 业务指标辅助记录器 =============


def record_modeling_task(
    duration_seconds: float,
    status: str,
    task_type: str = "default",
) -> None:
    """
    记录一次建模任务的指标。

    Args:
        duration_seconds: 任务总耗时（秒）
        status: 任务状态 (success / failed / cancelled)
        task_type: 任务类型
    """
    modeling_task_duration_seconds.labels(task_type=task_type).observe(
        duration_seconds
    )
    modeling_task_total.labels(status=status).inc()


def record_agent_execution(
    agent_type: str,
    duration_seconds: float,
) -> None:
    """
    记录一次 Agent 执行的耗时。

    Args:
        agent_type: Agent 类型 (coordinator / modeler / coder / writer)
        duration_seconds: 执行耗时（秒）
    """
    agent_execution_seconds.labels(agent_type=agent_type).observe(duration_seconds)


def record_llm_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    success: bool = True,
) -> None:
    """
    记录一次 LLM 调用的 Token 消耗。

    Args:
        model: 模型名称
        input_tokens: 输入 Token 数
        output_tokens: 输出 Token 数
        success: 调用是否成功
    """
    llm_tokens_total.labels(model=model, direction="input").inc(input_tokens)
    llm_tokens_total.labels(model=model, direction="output").inc(output_tokens)
    llm_calls_total.labels(
        model=model, status="success" if success else "error"
    ).inc()


def track_websocket_connection(connected: bool) -> None:
    """
    追踪 WebSocket 连接状态变化。

    Args:
        connected: True 表示新连接建立，False 表示连接断开
    """
    if connected:
        active_websocket_connections.inc()
    else:
        active_websocket_connections.dec()
