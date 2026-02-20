"""
错误恢复模块单元测试
测试错误分类器、重试管理器、错误恢复管理器
"""

import pytest

from app.core.error_recovery import (
    ErrorCategory,
    ErrorClassifier,
    ErrorInfo,
    ErrorRecoveryManager,
    ErrorSeverity,
    RecoveryAction,
    RecoveryResult,
    RetryManager,
)


class TestErrorSeverity:
    """测试错误严重程度枚举"""

    def test_severity_values(self):
        """测试严重程度值"""
        assert ErrorSeverity.LOW == "low"
        assert ErrorSeverity.MEDIUM == "medium"
        assert ErrorSeverity.HIGH == "high"
        assert ErrorSeverity.FATAL == "fatal"


class TestErrorCategory:
    """测试错误类别枚举"""

    def test_category_values(self):
        """测试类别值"""
        assert ErrorCategory.NETWORK == "network"
        assert ErrorCategory.API == "api"
        assert ErrorCategory.CODE_EXECUTION == "code"
        assert ErrorCategory.TIMEOUT == "timeout"


class TestRecoveryAction:
    """测试恢复操作枚举"""

    def test_action_values(self):
        """测试操作值"""
        assert RecoveryAction.RETRY == "retry"
        assert RecoveryAction.RETRY_WITH_BACKOFF == "retry_with_backoff"
        assert RecoveryAction.SKIP == "skip"
        assert RecoveryAction.ABORT == "abort"


class TestErrorInfo:
    """测试错误信息数据类"""

    def test_create_error_info(self):
        """测试创建错误信息"""
        error_info = ErrorInfo(
            error_id="err_001",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Connection refused",
            details="无法连接到服务器",
        )
        assert error_info.error_id == "err_001"
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.recoverable is True

    def test_error_info_non_recoverable(self):
        """测试不可恢复错误"""
        error_info = ErrorInfo(
            error_id="err_002",
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.FATAL,
            message="Out of memory",
            recoverable=False,
        )
        assert error_info.recoverable is False


class TestRecoveryResult:
    """测试恢复结果数据类"""

    def test_create_recovery_result(self):
        """测试创建恢复结果"""
        result = RecoveryResult(
            success=True,
            action_taken=RecoveryAction.RETRY,
            attempts=3,
            result_data={"output": "success"},
        )
        assert result.success is True
        assert result.attempts == 3


class TestErrorClassifier:
    """测试错误分类器"""

    def test_classify_network_error(self):
        """测试分类网络错误"""
        error = ConnectionError("connection refused")
        error_info = ErrorClassifier.classify(error)
        
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.LOW
        assert error_info.recoverable is True

    def test_classify_timeout_error(self):
        """测试分类超时错误"""
        error = TimeoutError("request timeout")
        error_info = ErrorClassifier.classify(error)
        
        assert error_info.category == ErrorCategory.TIMEOUT
        assert error_info.recoverable is True

    def test_classify_memory_error(self):
        """测试分类内存错误"""
        error = MemoryError("out of memory")
        error_info = ErrorClassifier.classify(error)
        
        assert error_info.category == ErrorCategory.RESOURCE
        assert error_info.severity == ErrorSeverity.FATAL
        assert error_info.recoverable is False

    def test_classify_value_error(self):
        """测试分类验证错误"""
        error = ValueError("invalid value")
        error_info = ErrorClassifier.classify(error)
        
        assert error_info.category == ErrorCategory.VALIDATION

    def test_classify_unknown_error(self):
        """测试分类未知错误"""
        error = Exception("unknown error type")
        error_info = ErrorClassifier.classify(error)
        
        assert error_info.category == ErrorCategory.UNKNOWN

    def test_classify_api_error(self):
        """测试分类API错误"""
        error = Exception("rate limit exceeded")
        error_info = ErrorClassifier.classify(error)
        
        assert error_info.category == ErrorCategory.API


class TestRetryManager:
    """测试重试管理器"""

    @pytest.fixture
    def retry_manager(self):
        return RetryManager(
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0,
        )

    @pytest.mark.asyncio
    async def test_successful_execution(self, retry_manager):
        """测试成功执行"""
        async def success_func():
            return "success"
        
        result = await retry_manager.execute_with_retry(success_func)
        
        assert result.success is True
        assert result.attempts == 1
        assert result.result_data == "success"

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, retry_manager):
        """测试失败后重试"""
        call_count = 0
        
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary failure")
            return "success after retries"
        
        result = await retry_manager.execute_with_retry(fail_then_succeed)
        
        assert result.success is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, retry_manager):
        """测试超过最大重试次数"""
        async def always_fail():
            raise ConnectionError("always fails")
        
        result = await retry_manager.execute_with_retry(always_fail)
        
        assert result.success is False
        assert result.attempts == retry_manager.max_retries

    @pytest.mark.asyncio
    async def test_retry_callback(self, retry_manager):
        """测试重试回调"""
        retry_log = []
        call_count = 0
        
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temp failure")
            return "done"
        
        def on_retry(attempt, error):
            retry_log.append((attempt, str(error)))
        
        await retry_manager.execute_with_retry(fail_twice, on_retry=on_retry)
        
        assert len(retry_log) == 2

    def test_calculate_delay(self, retry_manager):
        """测试延迟计算"""
        delay1 = retry_manager._calculate_delay(1)
        delay2 = retry_manager._calculate_delay(2)
        
        # 指数退避
        assert delay2 > delay1


class TestErrorRecoveryManager:
    """测试错误恢复管理器"""

    @pytest.fixture
    def recovery_manager(self):
        return ErrorRecoveryManager()

    @pytest.mark.asyncio
    async def test_handle_recoverable_error(self, recovery_manager):
        """测试处理可恢复错误"""
        error = ConnectionError("temporary network issue")
        
        result = await recovery_manager.handle_error(error)
        
        assert result.error_info.recoverable is True

    @pytest.mark.asyncio
    async def test_handle_fatal_error(self, recovery_manager):
        """测试处理致命错误"""
        error = MemoryError("out of memory")
        
        result = await recovery_manager.handle_error(error)
        
        assert result.error_info.severity == ErrorSeverity.FATAL
        assert result.action_taken == RecoveryAction.ABORT

    def test_register_fallback(self, recovery_manager):
        """测试注册备选处理器"""
        def network_fallback(error_info):
            return {"fallback": "network_handler"}
        
        recovery_manager.register_fallback(ErrorCategory.NETWORK, network_fallback)
        
        assert ErrorCategory.NETWORK in recovery_manager._fallback_handlers

    def test_get_error_summary(self, recovery_manager):
        """测试获取错误统计"""
        # 添加一些模拟错误历史
        recovery_manager._error_history.append(
            ErrorInfo(
                error_id="test1",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.LOW,
                message="test error 1",
            )
        )
        recovery_manager._error_history.append(
            ErrorInfo(
                error_id="test2",
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                message="test error 2",
            )
        )
        
        summary = recovery_manager.get_error_summary()
        
        assert summary["total_errors"] == 2
        assert ErrorCategory.NETWORK in summary["by_category"]
        assert ErrorCategory.API in summary["by_category"]


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_recovery_flow(self):
        """测试完整恢复流程"""
        manager = ErrorRecoveryManager()
        
        # 模拟一系列错误处理
        errors = [
            ConnectionError("network issue"),
            TimeoutError("request timeout"),
            ValueError("invalid input"),
        ]
        
        results = []
        for error in errors:
            result = await manager.handle_error(error)
            results.append(result)
        
        summary = manager.get_error_summary()
        assert summary["total_errors"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
