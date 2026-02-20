"""
请求追踪和日志中间件
提供请求 ID、日志记录、响应时间追踪等功能
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.log_util import logger


# 导入可观测性模块（如果存在）
try:
    from app.observability.tracing import (  # noqa: F401
        TraceMiddleware,
        get_trace_id,
        set_trace_id,
    )
    HAS_OBSERVABILITY = True
except ImportError:
    HAS_OBSERVABILITY = False

# 导入 Prometheus 指标中间件（如果存在）
try:
    from app.observability.metrics import PrometheusMiddleware
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求 ID 中间件

    为每个请求生成唯一 ID，便于日志追踪和问题排查
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从请求头获取或生成新的请求 ID
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"

        # 存储到 request.state 供后续使用
        request.state.request_id = request_id

        # 执行请求
        response = await call_next(request)

        # 在响应头中返回请求 ID
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录请求和响应的详细信息
    """

    # 不记录日志的路径
    SKIP_PATHS = {"/health", "/favicon.ico", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过不需要记录的路径
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # 获取请求 ID
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录请求开始
        start_time = time.perf_counter()

        # 请求信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:100]

        logger.info(
            f"[{request_id}] --> {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )

        # 执行请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录异常
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] <-- {request.method} {request.url.path} "
                f"500 {duration:.2f}ms ERROR: {str(e)}",
                extra={
                    "request_id": request_id,
                    "duration_ms": duration,
                    "status_code": 500,
                    "error": str(e),
                }
            )
            raise

        # 计算响应时间
        duration = (time.perf_counter() - start_time) * 1000

        # 记录响应
        log_level = "info" if response.status_code < 400 else "warning"
        log_func = getattr(logger, log_level)

        log_func(
            f"[{request_id}] <-- {request.method} {request.url.path} "
            f"{response.status_code} {duration:.2f}ms",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration,
            }
        )

        # 添加响应时间头
        response.headers["X-Response-Time"] = f"{duration:.2f}ms"

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 优先从代理头获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 直接连接的 IP
        if request.client:
            return request.client.host

        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头中间件

    添加安全相关的 HTTP 响应头
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )

        # Permissions-Policy: 禁用不需要的浏览器特性
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # 生产环境启用 HSTS
        from app.config.setting import settings
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """
    响应时间追踪中间件

    追踪慢请求并记录告警
    """

    # 慢请求阈值（毫秒）
    SLOW_REQUEST_THRESHOLD = 3000

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = (time.perf_counter() - start_time) * 1000

        # 记录慢请求
        if duration > self.SLOW_REQUEST_THRESHOLD:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                f"[{request_id}] 慢请求告警: {request.method} {request.url.path} "
                f"耗时 {duration:.2f}ms (阈值: {self.SLOW_REQUEST_THRESHOLD}ms)",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "duration_ms": duration,
                    "threshold_ms": self.SLOW_REQUEST_THRESHOLD,
                    "alert_type": "slow_request",
                }
            )

        return response


def register_middlewares(app):
    """
    注册所有中间件到 FastAPI 应用

    注意：中间件按照添加顺序的逆序执行
    即最后添加的中间件最先执行
    """
    from app.config.setting import settings

    # 0. 分布式追踪（最外层，如果可用）
    if HAS_OBSERVABILITY:
        app.add_middleware(TraceMiddleware)
        logger.info("分布式追踪中间件已启用")

    # 0.5 Prometheus 指标采集（在追踪之后、安全头之前）
    if HAS_PROMETHEUS:
        app.add_middleware(PrometheusMiddleware)
        logger.info("Prometheus 指标采集中间件已启用")

    # 1. 安全头
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. 速率限制（仅在生产/预发布环境启用）
    if settings.is_production() or settings.ENV == "staging":
        from app.utils.rate_limiter import RateLimitMiddleware, create_rate_limiter

        limiter = create_rate_limiter()
        app.add_middleware(RateLimitMiddleware, limiter=limiter)
        logger.info("速率限制中间件已启用（生产/预发布环境）")

    # 3. 响应时间追踪
    app.add_middleware(ResponseTimeMiddleware)

    # 4. 请求日志
    app.add_middleware(RequestLoggingMiddleware)

    # 5. 请求 ID（最内层，最先执行）
    app.add_middleware(RequestIDMiddleware)

    logger.info("请求追踪中间件已启用")

