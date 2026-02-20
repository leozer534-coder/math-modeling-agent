# interpreter_factory.py
from typing import Literal

from app.tools.e2b_interpreter import E2BCodeInterpreter
from app.tools.local_interpreter import LocalCodeInterpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.config.setting import settings
from app.utils.log_util import logger


async def create_interpreter(
    kind: Literal["remote", "local", "docker", "auto"] | None = None,
    *,
    task_id: str,
    work_dir: str,
    notebook_serializer: NotebookSerializer,
    timeout: int = 3000,
):
    """创建代码解释器实例。

    Args:
        kind: 解释器类型，支持 "remote"、"local"、"docker"、"auto"。
              为 None 或 "auto" 时根据环境自动选择：有 E2B_API_KEY 则用 remote，否则 local。
              显式传入 "local"/"remote"/"docker" 时严格遵循调用者意图，不做自动切换。
        task_id: 任务 ID
        work_dir: 工作目录
        notebook_serializer: Notebook 序列化器
        timeout: 执行超时时间（毫秒）

    Returns:
        BaseCodeInterpreter: 代码解释器实例
    """
    # 仅在调用者未明确指定 kind 时，才根据环境自动检测
    if kind is None or kind == "auto":
        if settings.E2B_API_KEY:
            logger.info("检测到 E2B_API_KEY，自动切换为远程解释器")
            kind = "remote"
        else:
            kind = "local"

    if kind == "remote":
        logger.info("使用远程解释器 (E2B)")
        interp = await E2BCodeInterpreter.create(
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
        )
        await interp.initialize(timeout=timeout)
        return interp
    elif kind == "docker":
        logger.info("使用 Docker 沙箱解释器")
        # 延迟导入，避免在未安装 docker 依赖时报错
        from app.tools.docker_interpreter import DockerCodeInterpreter

        interp = DockerCodeInterpreter(
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
            timeout=timeout,
        )
        await interp.initialize()
        return interp
    elif kind == "local":
        logger.info("使用本地解释器")
        interp = LocalCodeInterpreter(
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
        )
        await interp.initialize()
        return interp
    else:
        raise ValueError(f"未知 interpreter 类型：{kind}")
