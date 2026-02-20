"""
请求追踪模块 - Request Tracing

提供分布式追踪功能

功能：
1. Trace ID生成和传播
2. FastAPI中间件注入
3. 协程上下文管理
4. 调用链跟踪
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.log_util import logger


# ============= 上下文变量 =============

# 当前trace_id（协程安全）
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

# span堆栈
_span_stack: ContextVar[List["Span"]] = ContextVar("span_stack", default=[])


# ============= Trace ID管理 =============

def generate_trace_id() -> str:
    """生成新的Trace ID"""
    return uuid.uuid4().hex[:16]


def get_trace_id() -> Optional[str]:
    """获取当前Trace ID"""
    return _trace_id.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前Trace ID"""
    _trace_id.set(trace_id)


def clear_trace_id() -> None:
    """清除当前Trace ID"""
    _trace_id.set(None)


# ============= Span =============

@dataclass
class Span:
    """追踪Span"""
    span_id: str
    trace_id: str
    name: str
    parent_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "ok"
    tags: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0
        return (self.end_time - self.start_time).total_seconds() * 1000
    
    def finish(self, status: str = "ok") -> None:
        self.end_time = datetime.now()
        self.status = status
    
    def set_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
        }


# ============= Trace上下文管理器 =============

class TraceContext:
    """
    追踪上下文管理器
    
    使用示例：
        async with TraceContext("process_task") as span:
            span.set_tag("task_id", "123")
            await do_work()
    """
    
    def __init__(self, name: str, **tags):
        self.name = name
        self.tags = tags
        self.span: Optional[Span] = None
    
    async def __aenter__(self) -> Span:
        trace_id = get_trace_id() or generate_trace_id()
        set_trace_id(trace_id)
        
        # 获取父span
        stack = _span_stack.get()
        parent_id = stack[-1].span_id if stack else None
        
        # 创建新span
        self.span = Span(
            span_id=uuid.uuid4().hex[:8],
            trace_id=trace_id,
            name=self.name,
            parent_id=parent_id,
            tags=self.tags,
        )
        
        # 入栈
        new_stack = stack.copy()
        new_stack.append(self.span)
        _span_stack.set(new_stack)
        
        return self.span
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span:
            status = "error" if exc_type else "ok"
            self.span.finish(status)
            
            if exc_type:
                self.span.set_tag("error", str(exc_val))
        
        # 出栈
        stack = _span_stack.get()
        if stack:
            new_stack = stack[:-1]
            _span_stack.set(new_stack)
    
    def __enter__(self) -> Span:
        """同步版本"""
        trace_id = get_trace_id() or generate_trace_id()
        set_trace_id(trace_id)
        
        stack = _span_stack.get()
        parent_id = stack[-1].span_id if stack else None
        
        self.span = Span(
            span_id=uuid.uuid4().hex[:8],
            trace_id=trace_id,
            name=self.name,
            parent_id=parent_id,
            tags=self.tags,
        )
        
        new_stack = stack.copy()
        new_stack.append(self.span)
        _span_stack.set(new_stack)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span:
            status = "error" if exc_type else "ok"
            self.span.finish(status)
            
            if exc_type:
                self.span.set_tag("error", str(exc_val))
        
        stack = _span_stack.get()
        if stack:
            new_stack = stack[:-1]
            _span_stack.set(new_stack)


# ============= FastAPI中间件 =============

class TraceMiddleware(BaseHTTPMiddleware):
    """
    FastAPI追踪中间件
    
    自动为每个请求生成/传播trace_id
    
    使用方法：
        app.add_middleware(TraceMiddleware)
    """
    
    TRACE_HEADER = "X-Trace-ID"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从请求头获取或生成trace_id
        trace_id = request.headers.get(self.TRACE_HEADER) or generate_trace_id()
        set_trace_id(trace_id)
        
        # 记录请求信息
        start_time = datetime.now()
        
        try:
            response = await call_next(request)
            
            # 计算耗时
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # 在响应头中返回trace_id
            response.headers[self.TRACE_HEADER] = trace_id
            
            # 日志记录（仅记录非健康检查请求）
            if not request.url.path.startswith("/health"):
                logger.info(
                    f"HTTP {request.method} {request.url.path} "
                    f"→ {response.status_code} ({duration_ms:.1f}ms) "
                    f"[trace:{trace_id[:8]}]"
                )
            
            return response
            
        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"HTTP {request.method} {request.url.path} "
                f"→ ERROR ({duration_ms:.1f}ms) [trace:{trace_id[:8]}]: {e}"
            )
            raise
        
        finally:
            clear_trace_id()


# ============= 装饰器 =============

def trace(name: Optional[str] = None, **default_tags):
    """
    追踪装饰器
    
    使用示例：
        @trace("process_data")
        async def process_data(task_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__
        
        async def async_wrapper(*args, **kwargs):
            async with TraceContext(span_name, **default_tags):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with TraceContext(span_name, **default_tags):
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
