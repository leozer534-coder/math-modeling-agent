import os
import re
import subprocess

from fastapi import APIRouter, HTTPException

from app.config.setting import settings
from app.utils.common_utils import get_current_files, get_work_dir
from app.utils.log_util import logger

router = APIRouter()

# task_id 合法字符正则：只允许字母、数字、下划线和横线
_TASK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_task_id(task_id: str) -> None:
    """验证 task_id 格式，防止路径遍历和命令注入。

    Raises:
        HTTPException: task_id 包含非法字符
    """
    if not task_id or not _TASK_ID_PATTERN.match(task_id):
        logger.warning("task_id 格式非法: %s", task_id)
        raise HTTPException(
            status_code=400,
            detail="task_id 格式非法，只允许字母、数字、下划线和横线",
        )


@router.get("/download_url")
async def get_download_url(task_id: str, filename: str):
    """获取文件下载链接。"""
    _validate_task_id(task_id)

    # 清理文件名，防止路径遍历
    safe_filename = os.path.basename(filename)
    if not safe_filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    base_url = settings.SERVER_HOST.rstrip("/")
    return {"download_url": f"{base_url}/static/{task_id}/{safe_filename}"}


@router.get("/download_all_url")
async def get_download_all_url(task_id: str):
    """获取全部文件打包下载链接。"""
    _validate_task_id(task_id)

    base_url = settings.SERVER_HOST.rstrip("/")
    return {"download_url": f"{base_url}/static/{task_id}/all.zip"}


@router.get("/files")
async def get_files(task_id: str):
    """获取任务工作目录下的文件列表。"""
    _validate_task_id(task_id)

    work_dir = get_work_dir(task_id)
    files = get_current_files(work_dir, "all")
    file_all = []

    for i in files:
        file_type = i.split(".")[-1]
        file_all.append({"filename": i, "file_type": file_type})

    return file_all


@router.get("/open_folder")
async def open_folder(task_id: str):
    """打开任务工作目录（仅限开发环境）。

    生产环境下禁止调用此端点，防止命令注入风险。
    """
    # 环境检查：仅 DEV 环境允许打开文件夹
    if settings.is_production():
        logger.warning("生产环境下尝试调用 open_folder 端点，已拒绝")
        raise HTTPException(
            status_code=403,
            detail="生产环境不允许打开本地文件夹",
        )

    _validate_task_id(task_id)
    logger.info("请求打开工作目录, task_id: %s", task_id)

    # 打开工作目录
    work_dir = get_work_dir(task_id)

    # 验证工作目录确实存在
    if not os.path.isdir(work_dir):
        raise HTTPException(status_code=404, detail="工作目录不存在")

    if os.name == "nt":
        subprocess.run(["explorer", work_dir])
    elif os.name == "posix":
        subprocess.run(["open", work_dir])
    else:
        raise HTTPException(
            status_code=500, detail="不支持的操作系统"
        )

    return {"message": "打开工作目录成功", "work_dir": work_dir}
