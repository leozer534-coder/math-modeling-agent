"""
统一异常处理模块
提供标准化的异常类和错误响应格式，用于商业化运行
"""
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """标准错误代码"""
    # 通用错误 (1000-1999)
    INTERNAL_ERROR = "E1000"
    VALIDATION_ERROR = "E1001"
    NOT_FOUND = "E1002"
    PERMISSION_DENIED = "E1003"
    RATE_LIMITED = "E1004"

    # 认证错误 (2000-2999)
    AUTH_FAILED = "E2000"
    TOKEN_EXPIRED = "E2001"
    TOKEN_INVALID = "E2002"
    CREDENTIALS_INVALID = "E2003"

    # 业务错误 (3000-3999)
    TASK_NOT_FOUND = "E3000"
    TASK_ALREADY_RUNNING = "E3001"
    TASK_FAILED = "E3002"
    TASK_CANCELLED = "E3003"

    # Agent 错误 (4000-4999)
    AGENT_ERROR = "E4000"
    LLM_API_ERROR = "E4001"
    LLM_RATE_LIMITED = "E4002"
    LLM_CONTEXT_TOO_LONG = "E4003"
    CODE_EXECUTION_ERROR = "E4004"
    CODE_TIMEOUT = "E4005"

    # 文件错误 (5000-5999)
    FILE_NOT_FOUND = "E5000"
    FILE_TOO_LARGE = "E5001"
    FILE_TYPE_NOT_ALLOWED = "E5002"
    FILE_UPLOAD_FAILED = "E5003"

    # 外部服务错误 (6000-6999)
    REDIS_ERROR = "E6000"
    EXTERNAL_API_ERROR = "E6001"

    # 租户资源限制错误 (7000-7999)
    CONCURRENT_LIMIT_EXCEEDED = "E7000"
    STORAGE_QUOTA_EXCEEDED = "E7001"
    WORKSPACE_ERROR = "E7002"


class ErrorResponse(BaseModel):
    """标准错误响应格式"""
    success: bool = False
    error: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "E1000",
                    "message": "服务器内部错误",
                    "detail": "详细错误信息",
                    "request_id": "req_abc123"
                }
            }
        }


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[Dict[str, str]] = None
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        self.headers = headers
        super().__init__(message)

    def to_response(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """转换为标准响应格式"""
        error_data = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.detail:
            error_data["detail"] = self.detail
        if request_id:
            error_data["request_id"] = request_id

        return {
            "success": False,
            "error": error_data
        }


# ============= 具体异常类 =============

class ValidationException(AppException):
    """验证错误"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class NotFoundException(AppException):
    """资源未找到"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} 未找到",
            detail=f"ID: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class AuthenticationException(AppException):
    """认证失败"""
    def __init__(self, message: str = "认证失败", detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.AUTH_FAILED,
            message=message,
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenExpiredException(AppException):
    """Token 过期"""
    def __init__(self):
        super().__init__(
            code=ErrorCode.TOKEN_EXPIRED,
            message="Token 已过期，请重新登录",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionDeniedException(AppException):
    """权限不足"""
    def __init__(self, action: str = "操作"):
        super().__init__(
            code=ErrorCode.PERMISSION_DENIED,
            message=f"没有权限执行此{action}",
            status_code=status.HTTP_403_FORBIDDEN
        )


class RateLimitedException(AppException):
    """请求过于频繁"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message="请求过于频繁，请稍后重试",
            detail=f"请在 {retry_after} 秒后重试",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)}
        )


class TaskException(AppException):
    """任务相关异常"""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        task_id: Optional[str] = None
    ):
        super().__init__(
            code=code,
            message=message,
            detail=f"Task ID: {task_id}" if task_id else None,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class TaskNotFoundException(TaskException):
    """任务未找到"""
    def __init__(self, task_id: str):
        super().__init__(
            code=ErrorCode.TASK_NOT_FOUND,
            message="任务未找到",
            task_id=task_id
        )


class AgentException(AppException):
    """Agent 相关异常"""
    def __init__(
        self,
        code: ErrorCode = ErrorCode.AGENT_ERROR,
        message: str = "Agent 执行错误",
        agent_name: Optional[str] = None,
        detail: Optional[str] = None
    ):
        full_message = f"[{agent_name}] {message}" if agent_name else message
        super().__init__(
            code=code,
            message=full_message,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class LLMException(AgentException):
    """LLM API 调用异常"""
    def __init__(
        self,
        message: str = "LLM API 调用失败",
        model: Optional[str] = None,
        detail: Optional[str] = None
    ):
        super().__init__(
            code=ErrorCode.LLM_API_ERROR,
            message=message,
            agent_name=model,
            detail=detail
        )


class CodeExecutionException(AgentException):
    """代码执行异常"""
    def __init__(self, message: str, traceback: Optional[str] = None):
        super().__init__(
            code=ErrorCode.CODE_EXECUTION_ERROR,
            message=message,
            detail=traceback
        )


class CodeTimeoutException(AgentException):
    """代码执行超时"""
    def __init__(self, timeout: int):
        super().__init__(
            code=ErrorCode.CODE_TIMEOUT,
            message=f"代码执行超时（{timeout}秒）",
            detail="请检查代码是否存在无限循环或长时间运行的操作"
        )


class AgentExecutionError(AgentException):
    """Agent run() 执行过程中的异常，用于区分正常输出和错误"""
    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        detail: Optional[str] = None
    ):
        super().__init__(
            code=ErrorCode.AGENT_ERROR,
            message=message,
            agent_name=agent_name,
            detail=detail
        )


class FileException(AppException):
    """文件相关异常"""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        filename: Optional[str] = None
    ):
        super().__init__(
            code=code,
            message=message,
            detail=f"文件: {filename}" if filename else None,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class FileNotFoundException(FileException):
    """文件未找到"""
    def __init__(self, filename: str):
        super().__init__(
            code=ErrorCode.FILE_NOT_FOUND,
            message="文件未找到",
            filename=filename
        )


class FileTooLargeException(FileException):
    """文件过大"""
    def __init__(self, filename: str, max_size_mb: int):
        super().__init__(
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"文件大小超过限制（最大 {max_size_mb}MB）",
            filename=filename
        )


class FileTypeNotAllowedException(FileException):
    """文件类型不允许"""
    def __init__(self, filename: str, allowed_types: list):
        super().__init__(
            code=ErrorCode.FILE_TYPE_NOT_ALLOWED,
            message=f"不支持的文件类型，允许: {', '.join(allowed_types)}",
            filename=filename
        )


class ExternalServiceException(AppException):
    """外部服务异常"""
    def __init__(
        self,
        service_name: str,
        message: str,
        detail: Optional[str] = None
    ):
        super().__init__(
            code=ErrorCode.EXTERNAL_API_ERROR,
            message=f"[{service_name}] {message}",
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY
        )


class RedisException(AppException):
    """Redis 服务异常"""
    def __init__(self, message: str = "Redis 服务不可用"):
        super().__init__(
            code=ErrorCode.REDIS_ERROR,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# ============= 租户资源限制异常 =============

class ConcurrentLimitExceededException(AppException):
    """并发任务数超限"""
    def __init__(self, user_id: str, max_tasks: int, current_tasks: int):
        super().__init__(
            code=ErrorCode.CONCURRENT_LIMIT_EXCEEDED,
            message=f"并发任务数已达上限（{current_tasks}/{max_tasks}），请等待现有任务完成后再提交",
            detail=f"用户: {user_id}, 当前活跃任务数: {current_tasks}, 上限: {max_tasks}",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class StorageQuotaExceededException(AppException):
    """存储配额超限"""
    def __init__(self, user_id: str, used_mb: float, max_mb: int):
        super().__init__(
            code=ErrorCode.STORAGE_QUOTA_EXCEEDED,
            message=f"存储空间已满（已用 {used_mb:.1f}MB / 上限 {max_mb}MB），请清理历史任务后重试",
            detail=f"用户: {user_id}, 已使用: {used_mb:.1f}MB, 上限: {max_mb}MB",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class WorkspaceException(AppException):
    """工作目录操作异常"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            code=ErrorCode.WORKSPACE_ERROR,
            message=message,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============= 异常处理器 =============

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """应用异常处理器"""
    from app.utils.log_util import logger

    # 生成请求 ID
    request_id = getattr(request.state, "request_id", None)

    # 记录日志
    logger.error(
        f"AppException: {exc.code.value} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.code.value,
            "detail": exc.detail
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response(request_id),
        headers=exc.headers
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 异常处理器"""
    from app.utils.log_util import logger

    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "request_id": request_id
            }
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未处理异常处理器"""
    from app.utils.log_util import logger

    request_id = getattr(request.state, "request_id", None)

    logger.exception(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )

    # 生产环境不暴露详细错误信息
    from app.config.setting import settings
    detail = str(exc) if settings.DEBUG else None

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "服务器内部错误",
                "detail": detail,
                "request_id": request_id
            }
        }
    )


def register_exception_handlers(app):
    """注册异常处理器到 FastAPI 应用"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
