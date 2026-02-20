"""
API速率限制中间件
提供基于IP和用户的请求频率限制
"""
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.log_util import logger


@dataclass
class RateLimitRule:
    """速率限制规则"""
    requests: int  # 允许的请求数
    window: int  # 时间窗口（秒）
    burst: int = 0  # 突发请求数（可选）


@dataclass
class RateLimitState:
    """速率限制状态"""
    requests: list[float] = field(default_factory=list)
    blocked_until: float = 0


class RateLimiter:
    """
    速率限制器

    使用滑动窗口算法实现请求频率限制
    """

    def __init__(
        self,
        default_rule: RateLimitRule = None,
        cleanup_interval: int = 60
    ):
        """
        初始化速率限制器

        Args:
            default_rule: 默认限制规则
            cleanup_interval: 清理间隔（秒）
        """
        self.default_rule = default_rule or RateLimitRule(
            requests=60,  # 每分钟60次
            window=60,
            burst=10
        )
        self.cleanup_interval = cleanup_interval

        # 存储每个客户端的状态
        self._states: dict[str, RateLimitState] = defaultdict(RateLimitState)

        # 路由特定规则
        self._route_rules: dict[str, RateLimitRule] = {}

        # 白名单（不受限制）
        self._whitelist: set[str] = set()

        # 黑名单（完全阻止）
        self._blacklist: set[str] = set()

        # 上次清理时间
        self._last_cleanup = time.time()

        # 锁
        self._lock = asyncio.Lock()

    def add_route_rule(self, path_pattern: str, rule: RateLimitRule):
        """添加路由特定规则"""
        self._route_rules[path_pattern] = rule

    def add_to_whitelist(self, client_id: str):
        """添加到白名单"""
        self._whitelist.add(client_id)

    def add_to_blacklist(self, client_id: str):
        """添加到黑名单"""
        self._blacklist.add(client_id)

    def remove_from_blacklist(self, client_id: str):
        """从黑名单移除"""
        self._blacklist.discard(client_id)

    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用X-Forwarded-For（代理后面）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # 取第一个IP（原始客户端）
            return forwarded.split(",")[0].strip()

        # 使用X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用直接连接IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rule_for_path(self, path: str) -> RateLimitRule:
        """获取路径对应的规则"""
        for pattern, rule in self._route_rules.items():
            if path.startswith(pattern):
                return rule
        return self.default_rule

    async def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """
        检查请求是否超过速率限制

        Args:
            request: FastAPI请求对象

        Returns:
            tuple[bool, dict]: (是否允许, 限制信息)
        """
        client_id = self._get_client_id(request)
        now = time.time()

        # 检查黑名单
        if client_id in self._blacklist:
            return False, {
                "error": "blocked",
                "message": "您的IP已被封禁",
                "retry_after": -1
            }

        # 检查白名单
        if client_id in self._whitelist:
            return True, {}

        # 获取规则
        rule = self._get_rule_for_path(request.url.path)

        async with self._lock:
            state = self._states[client_id]

            # 检查是否在封禁期
            if state.blocked_until > now:
                retry_after = int(state.blocked_until - now)
                return False, {
                    "error": "rate_limited",
                    "message": "请求过于频繁，请稍后重试",
                    "retry_after": retry_after
                }

            # 清理过期请求记录
            cutoff = now - rule.window
            state.requests = [t for t in state.requests if t > cutoff]

            # 检查是否超过限制
            if len(state.requests) >= rule.requests + rule.burst:
                # 超过限制，封禁一段时间
                state.blocked_until = now + rule.window
                logger.warning(
                    f"速率限制触发: client={client_id}, "
                    f"requests={len(state.requests)}, limit={rule.requests}"
                )
                return False, {
                    "error": "rate_limited",
                    "message": "请求过于频繁，请稍后重试",
                    "retry_after": rule.window
                }

            # 记录请求
            state.requests.append(now)

            # 定期清理
            if now - self._last_cleanup > self.cleanup_interval:
                await self._cleanup()

        # 计算剩余配额
        remaining = rule.requests - len(state.requests)
        reset_at = int(now + rule.window)

        return True, {
            "limit": rule.requests,
            "remaining": max(0, remaining),
            "reset": reset_at
        }

    async def _cleanup(self):
        """清理过期状态"""
        now = time.time()
        expired_clients = []

        for client_id, state in self._states.items():
            # 如果最后一次请求超过2倍窗口时间，清理
            if state.requests:
                last_request = max(state.requests)
                if now - last_request > self.default_rule.window * 2:
                    expired_clients.append(client_id)
            elif state.blocked_until < now:
                expired_clients.append(client_id)

        for client_id in expired_clients:
            del self._states[client_id]

        self._last_cleanup = now

        if expired_clients:
            logger.debug("清理过期速率限制状态: %s 个客户端", len(expired_clients))

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "active_clients": len(self._states),
            "blacklisted": len(self._blacklist),
            "whitelisted": len(self._whitelist),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件

    在FastAPI应用中使用：
    ```python
    from app.utils.rate_limiter import RateLimitMiddleware, RateLimiter, RateLimitRule

    limiter = RateLimiter(
        default_rule=RateLimitRule(requests=100, window=60)
    )

    # 对特定路由设置更严格的限制
    limiter.add_route_rule("/api/modeling", RateLimitRule(requests=10, window=60))

    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    ```
    """

    def __init__(self, app, limiter: RateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查等端点
        skip_paths = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
        if request.url.path in skip_paths:
            return await call_next(request)

        # 检查速率限制
        allowed, info = await self.limiter.check_rate_limit(request)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": info.get("message", "请求过于频繁"),
                    "retry_after": info.get("retry_after", 60)
                },
                headers={
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-RateLimit-Reset": str(info.get("retry_after", 60))
                }
            )

        # 执行请求
        response = await call_next(request)

        # 添加速率限制头
        if info:
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))

        return response


# 便捷函数
def create_rate_limiter(
    requests_per_minute: int = 60,
    burst: int = 10,
    modeling_requests_per_minute: int = 5
) -> RateLimiter:
    """
    创建配置好的速率限制器

    Args:
        requests_per_minute: 每分钟默认请求数
        burst: 突发请求数
        modeling_requests_per_minute: 建模API每分钟请求数

    Returns:
        RateLimiter: 配置好的速率限制器
    """
    limiter = RateLimiter(
        default_rule=RateLimitRule(
            requests=requests_per_minute,
            window=60,
            burst=burst
        )
    )

    # 建模相关API使用更严格的限制
    limiter.add_route_rule(
        "/api/modeling",
        RateLimitRule(requests=modeling_requests_per_minute, window=60, burst=2)
    )

    # 文件上传使用更严格的限制
    limiter.add_route_rule(
        "/api/upload",
        RateLimitRule(requests=20, window=60, burst=5)
    )

    return limiter
