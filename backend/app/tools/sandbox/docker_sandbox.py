"""
Docker沙箱执行器 - Docker Sandbox Executor

提供安全隔离的代码执行环境

功能：
1. Docker容器隔离执行
2. 资源限制（CPU、内存、执行时间）
3. 网络隔离
4. 文件系统隔离
5. 执行结果捕获
"""

import asyncio
import json
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.code_sanitizer import CodeSanitizer
from app.utils.log_util import logger


# ============= 枚举定义 =============

class SandboxMode(str, Enum):
    """沙箱模式"""
    DOCKER = "docker"  # Docker容器执行
    E2B = "e2b"  # E2B云端沙箱
    LOCAL_UNSAFE = "local_unsafe"  # 本地不安全执行（仅开发）


class ExecutionStatus(str, Enum):
    """执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RESOURCE_EXCEEDED = "resource_exceeded"


# ============= 配置类 =============

@dataclass
class SandboxConfig:
    """沙箱配置"""
    # 容器配置
    image: str = "mathmodel-sandbox:latest"
    container_name_prefix: str = "sandbox"
    
    # 资源限制
    memory_limit: str = "2g"  # 内存限制
    cpu_quota: int = 50000  # CPU配额（微秒/100000微秒）
    cpu_period: int = 100000
    timeout_seconds: int = 300  # 执行超时
    
    # 网络配置
    network_mode: str = "none"  # 禁止网络
    
    # 挂载配置
    work_dir: str = "/workspace"
    read_only_root: bool = True
    
    # 安全配置
    drop_capabilities: List[str] = field(default_factory=lambda: ["ALL"])
    security_opt: List[str] = field(default_factory=lambda: ["no-new-privileges:true"])


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    container_id: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    @property
    def output(self) -> str:
        """合并的输出"""
        return self.stdout + ("\n" + self.stderr if self.stderr else "")


# ============= Docker沙箱 =============

class DockerSandbox:
    """
    Docker沙箱执行器
    
    在Docker容器中安全执行Python代码
    
    使用示例：
        >>> sandbox = DockerSandbox()
        >>> result = await sandbox.execute("print('Hello World')")
        >>> print(result.stdout)
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        初始化沙箱
        
        Args:
            config: 沙箱配置
        """
        self.config = config or SandboxConfig()
        self._docker_available = None
        
        logger.debug("DockerSandbox 初始化: image=%s", self.config.image)
    
    async def check_docker_available(self) -> bool:
        """
        检查Docker是否可用
        
        Returns:
            True如果Docker可用
        """
        if self._docker_available is not None:
            return self._docker_available
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            self._docker_available = proc.returncode == 0
            
            if self._docker_available:
                logger.info("✅ Docker 可用")
            else:
                logger.warning("⚠️ Docker 不可用")
                
        except Exception as e:
            logger.warning("Docker 检查失败: %s", e)
            self._docker_available = False
        
        return self._docker_available
    
    async def check_image_exists(self) -> bool:
        """检查沙箱镜像是否存在"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "image", "inspect", self.config.image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception as e:
            logger.warning("检查 Docker 镜像是否存在时失败: %s", e)
            return False
    
    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        input_files: Optional[Dict[str, bytes]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        在沙箱中执行代码
        
        Args:
            code: Python代码
            timeout: 执行超时（秒）
            input_files: 输入文件 {filename: content}
            env_vars: 环境变量
            
        Returns:
            ExecutionResult: 执行结果
        """
        timeout = timeout or self.config.timeout_seconds
        start_time = datetime.now()
        
        # 检查Docker可用性
        if not await self.check_docker_available():
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stdout="",
                stderr="Docker 未安装或未运行",
                exit_code=-1,
                execution_time_ms=0,
            )
        
        # 代码安全审查: 写入文件前先进行静态分析，拦截危险操作
        is_safe, reason = CodeSanitizer.sanitize(code)
        if not is_safe:
            logger.warning("代码安全审查未通过，拒绝执行: %s", reason)
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stdout="",
                stderr=reason,
                exit_code=-1,
                execution_time_ms=0,
            )

        # 创建临时目录
        with tempfile.TemporaryDirectory(prefix="sandbox_") as temp_dir:
            temp_path = Path(temp_dir)

            # 审查通过后写入代码文件
            code_file = temp_path / "main.py"
            code_file.write_text(code, encoding="utf-8")
            
            # 写入输入文件
            if input_files:
                for filename, content in input_files.items():
                    file_path = temp_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)
            
            # 构建Docker命令
            container_name = f"{self.config.container_name_prefix}_{uuid.uuid4().hex[:8]}"
            
            cmd = self._build_docker_command(
                container_name=container_name,
                host_dir=str(temp_path),
                env_vars=env_vars,
            )
            
            logger.debug("执行Docker命令: %s", ' '.join(cmd))
            
            try:
                # 执行容器
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout,
                    )
                    
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # 确定执行状态
                    if proc.returncode == 0:
                        status = ExecutionStatus.SUCCESS
                    elif proc.returncode == 137:  # OOM killed
                        status = ExecutionStatus.RESOURCE_EXCEEDED
                    else:
                        status = ExecutionStatus.ERROR
                    
                    # 收集创建的文件
                    files_created = self._collect_output_files(temp_path)
                    
                    return ExecutionResult(
                        status=status,
                        stdout=stdout.decode("utf-8", errors="replace"),
                        stderr=stderr.decode("utf-8", errors="replace"),
                        exit_code=proc.returncode,
                        execution_time_ms=execution_time,
                        container_id=container_name,
                        files_created=files_created,
                    )
                    
                except asyncio.TimeoutError:
                    # 超时处理
                    await self._kill_container(container_name)
                    
                    return ExecutionResult(
                        status=ExecutionStatus.TIMEOUT,
                        stdout="",
                        stderr=f"执行超时 ({timeout}秒)",
                        exit_code=-1,
                        execution_time_ms=timeout * 1000,
                        container_id=container_name,
                    )
                    
            except Exception as e:
                logger.error("Docker执行失败: %s", e)
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    stdout="",
                    stderr=str(e),
                    exit_code=-1,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                )
    
    def _build_docker_command(
        self,
        container_name: str,
        host_dir: str,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        构建Docker运行命令

        安全策略:
        - 宿主机临时目录以只读方式挂载到容器，防止容器反向写入宿主机
        - 容器内 /tmp 使用 tmpfs（限制100MB），供代码运行时写入临时文件
        - 使用条件式列表扩展代替三元表达式，避免产生空字符串
        """
        cmd = [
            "docker", "run",
            "--rm",  # 自动删除容器
            "--name", container_name,

            # 资源限制
            "--memory", self.config.memory_limit,
            f"--cpu-period={self.config.cpu_period}",
            f"--cpu-quota={self.config.cpu_quota}",

            # 网络隔离
            f"--network={self.config.network_mode}",

            # 安全设置: 使用条件式列表扩展，避免空字符串
            *(["--read-only"] if self.config.read_only_root else []),

            # 挂载工作目录: 只读挂载宿主机临时目录，防止容器反向写入宿主机文件系统
            "-v", f"{host_dir}:{self.config.work_dir}:ro",

            # tmpfs 挂载: 容器内 /tmp 使用内存文件系统，限制大小为100MB
            "--tmpfs", "/tmp:size=100m,noexec",

            # 输出目录: 为代码生成的输出文件提供可写的 tmpfs
            "--tmpfs", f"{self.config.work_dir}/output:size=50m",

            "-w", self.config.work_dir,

            # 用户权限
            "--user", "nobody",
        ]

        # 添加安全选项
        for cap in self.config.drop_capabilities:
            cmd.extend(["--cap-drop", cap])

        for opt in self.config.security_opt:
            cmd.extend(["--security-opt", opt])

        # 添加环境变量
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        # 添加镜像和命令
        cmd.extend([
            self.config.image,
            "python", "main.py",
        ])

        return cmd
    
    async def _kill_container(self, container_name: str) -> None:
        """强制终止容器"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5)
        except Exception as e:
            logger.warning("终止容器失败: %s", e)
    
    def _collect_output_files(self, temp_path: Path) -> List[str]:
        """收集输出文件列表"""
        files = []
        for item in temp_path.rglob("*"):
            if item.is_file() and item.name != "main.py":
                files.append(str(item.relative_to(temp_path)))
        return files
    
    async def execute_notebook(
        self,
        notebook_content: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        执行Jupyter Notebook

        安全策略:
        - notebook 内容写入独立的 JSON 文件，而非通过字符串拼接嵌入代码
        - 避免三引号逃逸导致的代码注入风险
        - 先验证 notebook_content 是合法 JSON，防止畸形输入

        Args:
            notebook_content: Notebook JSON内容
            timeout: 超时时间

        Returns:
            ExecutionResult: 执行结果
        """
        # 验证 notebook_content 是合法的 JSON，防止畸形输入
        try:
            json.loads(notebook_content)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Notebook 内容不是合法 JSON: %s", e)
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stdout="",
                stderr=f"Notebook 内容不是合法的 JSON 格式: {e}",
                exit_code=-1,
                execution_time_ms=0,
            )

        effective_timeout = timeout or self.config.timeout_seconds

        # 安全方式: notebook 内容通过独立文件传递，不嵌入代码字符串
        # wrapper 代码从文件读取 notebook，彻底避免字符串拼接注入
        wrapper_code = f'''\
import json
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# 从独立文件读取 notebook 内容，避免代码注入风险
with open("notebook_input.json", "r", encoding="utf-8") as f:
    nb_content = f.read()

notebook = nbformat.reads(nb_content, as_version=4)
ep = ExecutePreprocessor(timeout={effective_timeout})
ep.preprocess(notebook)
print(json.dumps({{"cells": len(notebook.cells), "status": "executed"}}))
'''
        # 将 notebook 内容作为输入文件传递，而非拼接进代码
        input_files = {
            "notebook_input.json": notebook_content.encode("utf-8"),
        }

        return await self.execute(
            wrapper_code,
            timeout=timeout,
            input_files=input_files,
        )


# ============= 沙箱工厂 =============

class SandboxFactory:
    """
    沙箱工厂
    
    根据配置创建合适的沙箱执行器
    """
    
    @staticmethod
    def create(mode: SandboxMode = SandboxMode.DOCKER) -> DockerSandbox:
        """
        创建沙箱执行器
        
        Args:
            mode: 沙箱模式
            
        Returns:
            沙箱执行器实例
        """
        if mode == SandboxMode.DOCKER:
            return DockerSandbox()
        elif mode == SandboxMode.E2B:
            # E2B模式使用现有的E2B执行器
            raise NotImplementedError("请使用现有的 E2B 执行器")
        elif mode == SandboxMode.LOCAL_UNSAFE:
            logger.warning("⚠️ 使用本地不安全模式，仅限开发环境！")
            # 返回一个配置为本地执行的沙箱（需要进一步实现）
            return DockerSandbox()
        else:
            raise ValueError(f"未知的沙箱模式: {mode}")


# ============= 全局函数 =============

async def execute_code_safely(
    code: str,
    timeout: int = 300,
    mode: SandboxMode = SandboxMode.DOCKER,
) -> ExecutionResult:
    """
    安全执行代码的便捷函数
    
    Args:
        code: Python代码
        timeout: 超时时间
        mode: 沙箱模式
        
    Returns:
        ExecutionResult: 执行结果
    """
    sandbox = SandboxFactory.create(mode)
    return await sandbox.execute(code, timeout)
