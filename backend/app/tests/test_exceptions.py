"""
异常处理模块测试
测试统一异常处理、错误响应格式等
"""
from fastapi import status


class TestErrorCode:
    """测试错误代码枚举"""

    def test_error_codes_exist(self):
        """测试错误代码存在"""
        from app.utils.exceptions import ErrorCode

        assert ErrorCode.INTERNAL_ERROR.value == "E1000"
        assert ErrorCode.VALIDATION_ERROR.value == "E1001"
        assert ErrorCode.AUTH_FAILED.value == "E2000"
        assert ErrorCode.TASK_NOT_FOUND.value == "E3000"
        assert ErrorCode.LLM_API_ERROR.value == "E4001"
        assert ErrorCode.FILE_NOT_FOUND.value == "E5000"

    def test_error_code_categories(self):
        """测试错误代码分类"""
        from app.utils.exceptions import ErrorCode

        # 通用错误 1000-1999
        assert ErrorCode.INTERNAL_ERROR.value.startswith("E1")

        # 认证错误 2000-2999
        assert ErrorCode.AUTH_FAILED.value.startswith("E2")

        # 业务错误 3000-3999
        assert ErrorCode.TASK_NOT_FOUND.value.startswith("E3")

        # Agent 错误 4000-4999
        assert ErrorCode.AGENT_ERROR.value.startswith("E4")

        # 文件错误 5000-5999
        assert ErrorCode.FILE_NOT_FOUND.value.startswith("E5")


class TestAppException:
    """测试应用基础异常"""

    def test_app_exception_creation(self):
        """测试异常创建"""
        from app.utils.exceptions import AppException, ErrorCode

        exc = AppException(
            code=ErrorCode.INTERNAL_ERROR,
            message="测试错误",
            detail="详细信息",
            status_code=500
        )

        assert exc.code == ErrorCode.INTERNAL_ERROR
        assert exc.message == "测试错误"
        assert exc.detail == "详细信息"
        assert exc.status_code == 500

    def test_to_response(self):
        """测试转换为响应格式"""
        from app.utils.exceptions import AppException, ErrorCode

        exc = AppException(
            code=ErrorCode.VALIDATION_ERROR,
            message="验证失败",
            detail="字段无效"
        )

        response = exc.to_response(request_id="req_123")

        assert response["success"] is False
        assert response["error"]["code"] == "E1001"
        assert response["error"]["message"] == "验证失败"
        assert response["error"]["detail"] == "字段无效"
        assert response["error"]["request_id"] == "req_123"


class TestValidationException:
    """测试验证异常"""

    def test_validation_exception(self):
        """测试验证异常"""
        from app.utils.exceptions import ValidationException

        exc = ValidationException("参数无效", "email 格式错误")

        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert "参数无效" in exc.message


class TestNotFoundException:
    """测试资源未找到异常"""

    def test_not_found_exception(self):
        """测试未找到异常"""
        from app.utils.exceptions import NotFoundException

        exc = NotFoundException("用户", "user_123")

        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "用户" in exc.message
        assert "user_123" in exc.detail


class TestAuthenticationException:
    """测试认证异常"""

    def test_auth_exception(self):
        """测试认证异常"""
        from app.utils.exceptions import AuthenticationException

        exc = AuthenticationException("用户名或密码错误")

        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_token_expired_exception(self):
        """测试 Token 过期异常"""
        from app.utils.exceptions import TokenExpiredException

        exc = TokenExpiredException()

        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert "过期" in exc.message


class TestRateLimitedException:
    """测试限流异常"""

    def test_rate_limited_exception(self):
        """测试限流异常"""
        from app.utils.exceptions import RateLimitedException

        exc = RateLimitedException(retry_after=120)

        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc.headers["Retry-After"] == "120"


class TestTaskException:
    """测试任务异常"""

    def test_task_not_found_exception(self):
        """测试任务未找到异常"""
        from app.utils.exceptions import TaskNotFoundException

        exc = TaskNotFoundException("task_abc")

        assert "task_abc" in exc.detail

    def test_task_exception_with_id(self):
        """测试带任务 ID 的异常"""
        from app.utils.exceptions import ErrorCode, TaskException

        exc = TaskException(
            code=ErrorCode.TASK_FAILED,
            message="任务执行失败",
            task_id="task_123"
        )

        assert "task_123" in exc.detail


class TestAgentException:
    """测试 Agent 异常"""

    def test_agent_exception(self):
        """测试 Agent 异常"""
        from app.utils.exceptions import AgentException

        exc = AgentException(
            message="模型调用失败",
            agent_name="CoderAgent"
        )

        assert "CoderAgent" in exc.message

    def test_llm_exception(self):
        """测试 LLM 异常"""
        from app.utils.exceptions import LLMException

        exc = LLMException(
            message="API 调用超时",
            model="gpt-4",
            detail="连接超时"
        )

        assert "gpt-4" in exc.message

    def test_code_execution_exception(self):
        """测试代码执行异常"""
        from app.utils.exceptions import CodeExecutionException

        exc = CodeExecutionException(
            message="除零错误",
            traceback="ZeroDivisionError: division by zero"
        )

        assert "除零错误" in exc.message
        assert "ZeroDivisionError" in exc.detail

    def test_code_timeout_exception(self):
        """测试代码超时异常"""
        from app.utils.exceptions import CodeTimeoutException

        exc = CodeTimeoutException(timeout=300)

        assert "300" in exc.message


class TestFileException:
    """测试文件异常"""

    def test_file_not_found_exception(self):
        """测试文件未找到异常"""
        from app.utils.exceptions import FileNotFoundException

        exc = FileNotFoundException("data.csv")

        assert "data.csv" in exc.detail

    def test_file_too_large_exception(self):
        """测试文件过大异常"""
        from app.utils.exceptions import FileTooLargeException

        exc = FileTooLargeException("large.zip", max_size_mb=100)

        assert "100MB" in exc.message

    def test_file_type_not_allowed_exception(self):
        """测试文件类型不允许异常"""
        from app.utils.exceptions import FileTypeNotAllowedException

        exc = FileTypeNotAllowedException("script.exe", [".csv", ".xlsx"])

        assert ".csv" in exc.message
        assert ".xlsx" in exc.message


class TestExternalServiceException:
    """测试外部服务异常"""

    def test_external_service_exception(self):
        """测试外部服务异常"""
        from app.utils.exceptions import ExternalServiceException

        exc = ExternalServiceException(
            service_name="OpenAI",
            message="服务暂时不可用"
        )

        assert "OpenAI" in exc.message
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY

    def test_redis_exception(self):
        """测试 Redis 异常"""
        from app.utils.exceptions import RedisException

        exc = RedisException()

        assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
