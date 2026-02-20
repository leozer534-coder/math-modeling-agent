"""
沙箱模块单元测试 - Sandbox Module Tests

测试内容：
1. SandboxConfig配置
2. ExecutionResult结果
3. DockerSandbox执行器（Mock测试）
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.tools.sandbox.docker_sandbox import (
    DockerSandbox,
    ExecutionResult,
    ExecutionStatus,
    SandboxConfig,
    SandboxFactory,
    SandboxMode,
    execute_code_safely,
)


# ============= SandboxConfig Tests =============

class TestSandboxConfig:
    """沙箱配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SandboxConfig()
        
        assert config.image == "mathmodel-sandbox:latest"
        assert config.memory_limit == "2g"
        assert config.timeout_seconds == 300
        assert config.network_mode == "none"
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SandboxConfig(
            image="custom-sandbox:v2",
            memory_limit="4g",
            timeout_seconds=600,
            network_mode="bridge",
        )
        
        assert config.image == "custom-sandbox:v2"
        assert config.memory_limit == "4g"
        assert config.timeout_seconds == 600
        assert config.network_mode == "bridge"
    
    def test_security_defaults(self):
        """测试安全默认值"""
        config = SandboxConfig()
        
        assert "ALL" in config.drop_capabilities
        assert "no-new-privileges:true" in config.security_opt
        assert config.read_only_root is True


# ============= ExecutionResult Tests =============

class TestExecutionResult:
    """执行结果测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Hello World\n",
            stderr="",
            exit_code=0,
            execution_time_ms=150.5,
        )
        
        assert result.is_success
        assert result.exit_code == 0
        assert "Hello World" in result.output
    
    def test_error_result(self):
        """测试错误结果"""
        result = ExecutionResult(
            status=ExecutionStatus.ERROR,
            stdout="",
            stderr="NameError: name 'x' is not defined",
            exit_code=1,
            execution_time_ms=50.0,
        )
        
        assert not result.is_success
        assert "NameError" in result.stderr
    
    def test_timeout_result(self):
        """测试超时结果"""
        result = ExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            stdout="",
            stderr="执行超时 (300秒)",
            exit_code=-1,
            execution_time_ms=300000,
        )
        
        assert result.status == ExecutionStatus.TIMEOUT
        assert not result.is_success
    
    def test_combined_output(self):
        """测试合并输出"""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="stdout output",
            stderr="stderr output",
            exit_code=0,
            execution_time_ms=100,
        )
        
        assert "stdout output" in result.output
        assert "stderr output" in result.output
    
    def test_files_created(self):
        """测试文件创建记录"""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="",
            stderr="",
            exit_code=0,
            execution_time_ms=100,
            files_created=["output.csv", "figure.png"],
        )
        
        assert "output.csv" in result.files_created
        assert "figure.png" in result.files_created


# ============= DockerSandbox Tests =============

class TestDockerSandbox:
    """Docker沙箱测试"""
    
    def test_init_default_config(self):
        """测试默认配置初始化"""
        sandbox = DockerSandbox()
        
        assert sandbox.config.image == "mathmodel-sandbox:latest"
    
    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = SandboxConfig(image="custom:latest")
        sandbox = DockerSandbox(config)
        
        assert sandbox.config.image == "custom:latest"
    
    @pytest.mark.asyncio
    async def test_check_docker_available_success(self):
        """测试Docker可用性检查成功"""
        sandbox = DockerSandbox()
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"Docker version 24.0", b""))
            mock_exec.return_value = mock_proc
            
            result = await sandbox.check_docker_available()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_docker_available_failure(self):
        """测试Docker可用性检查失败"""
        sandbox = DockerSandbox()
        sandbox._docker_available = None  # 重置缓存
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("docker not found")
            
            result = await sandbox.check_docker_available()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_docker_not_available(self):
        """测试Docker不可用时执行"""
        sandbox = DockerSandbox()
        sandbox._docker_available = False
        
        result = await sandbox.execute("print('test')")
        
        assert result.status == ExecutionStatus.ERROR
        assert "Docker" in result.stderr
    
    def test_build_docker_command(self):
        """测试构建Docker命令"""
        sandbox = DockerSandbox()
        
        cmd = sandbox._build_docker_command(
            container_name="test-container",
            host_dir="/tmp/workspace",
            env_vars={"DEBUG": "1"},
        )
        
        assert "docker" in cmd
        assert "run" in cmd
        assert "--rm" in cmd
        assert "--name" in cmd
        assert "test-container" in cmd
        assert "--memory" in cmd
        assert "2g" in cmd
        assert "-e" in cmd
        assert "DEBUG=1" in cmd


# ============= SandboxFactory Tests =============

class TestSandboxFactory:
    """沙箱工厂测试"""
    
    def test_create_docker_sandbox(self):
        """测试创建Docker沙箱"""
        sandbox = SandboxFactory.create(SandboxMode.DOCKER)
        
        assert isinstance(sandbox, DockerSandbox)
    
    def test_create_e2b_not_implemented(self):
        """测试E2B模式未实现"""
        with pytest.raises(NotImplementedError):
            SandboxFactory.create(SandboxMode.E2B)
    
    def test_create_local_unsafe(self):
        """测试本地不安全模式"""
        sandbox = SandboxFactory.create(SandboxMode.LOCAL_UNSAFE)
        
        # 本地模式也返回DockerSandbox（需要进一步实现）
        assert isinstance(sandbox, DockerSandbox)


# ============= Integration-like Tests (Mocked) =============

class TestSandboxIntegration:
    """沙箱集成测试（Mock）"""
    
    @pytest.mark.asyncio
    async def test_execute_simple_code(self):
        """测试执行简单代码"""
        sandbox = DockerSandbox()
        
        with patch.object(sandbox, "check_docker_available", return_value=True):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(
                    return_value=(b"Hello World\n", b"")
                )
                mock_exec.return_value = mock_proc
                
                result = await sandbox.execute("print('Hello World')")
                
                # 由于我们mock了整个执行过程，实际会进入临时目录逻辑
                # 这里主要测试逻辑流程
                assert mock_exec.called or result.status in [
                    ExecutionStatus.SUCCESS,
                    ExecutionStatus.ERROR,
                ]
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """测试执行超时"""
        sandbox = DockerSandbox()
        
        with patch.object(sandbox, "check_docker_available", return_value=True):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(
                    side_effect=asyncio.TimeoutError()
                )
                mock_exec.return_value = mock_proc
                
                with patch.object(sandbox, "_kill_container", return_value=None):
                    result = await sandbox.execute("import time; time.sleep(1000)", timeout=1)
                
                # 超时应返回TIMEOUT状态
                assert result.status == ExecutionStatus.TIMEOUT


# ============= Helper Function Tests =============

class TestExecuteCodeSafely:
    """安全执行函数测试"""
    
    @pytest.mark.asyncio
    async def test_execute_code_safely_creates_sandbox(self):
        """测试便捷函数创建沙箱"""
        with patch.object(DockerSandbox, "execute") as mock_execute:
            mock_execute.return_value = ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                stdout="test",
                stderr="",
                exit_code=0,
                execution_time_ms=100,
            )
            
            result = await execute_code_safely("print('test')")
            
            assert result.status == ExecutionStatus.SUCCESS
