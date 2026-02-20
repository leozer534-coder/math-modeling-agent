"""
安全的文件访问路由
防止路径遍历攻击，只允许访问指定 task_id 的文件
"""
import os
from pathlib import Path as PathLib

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse

from app.utils.auth import get_current_user
from app.utils.log_util import logger


router = APIRouter(prefix="/files", tags=["files"])


def is_safe_path(basedir: str, path: str) -> bool:
    """
    检查路径是否安全，防止路径遍历攻击

    Args:
        basedir: 基础目录
        path: 要检查的路径

    Returns:
        bool: 路径是否安全
    """
    # 将路径规范化并解析绝对路径
    base = PathLib(basedir).resolve()
    target = PathLib(os.path.join(basedir, path)).resolve()

    # 检查目标路径是否在基础目录内
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


@router.get("/tasks/{task_id}/{file_path:path}")
async def get_task_file(
    task_id: str = Path(..., regex="^[a-zA-Z0-9_-]+$"),  # 只允许字母数字下划线横线
    file_path: str = Path(...),
    current_user: dict = Depends(get_current_user),
):
    """
    安全地获取指定任务的文件

    Args:
        task_id: 任务 ID
        file_path: 文件相对路径

    Returns:
        FileResponse: 文件内容
    """
    # 构建基础目录
    work_dir = os.path.join("project", "work_dir", task_id)

    # 检查基础目录是否存在
    if not os.path.exists(work_dir):
        logger.warning("任务目录不存在: %s", task_id)
        raise HTTPException(status_code=404, detail="任务不存在")

    # 安全性检查：防止路径遍历
    if not is_safe_path(work_dir, file_path):
        logger.error("检测到路径遍历攻击: task_id=%s, file_path=%s", task_id, file_path)
        raise HTTPException(status_code=403, detail="非法的文件路径")

    # 构建完整文件路径
    full_path = os.path.join(work_dir, file_path)

    # 检查文件是否存在
    if not os.path.exists(full_path):
        logger.warning("文件不存在: %s", full_path)
        raise HTTPException(status_code=404, detail="文件不存在")

    # 检查是否是文件（不是目录）
    if not os.path.isfile(full_path):
        logger.warning("请求的不是文件: %s", full_path)
        raise HTTPException(status_code=400, detail="请求的不是文件")

    # 返回文件
    logger.info("提供文件访问: task_id=%s, file=%s", task_id, file_path)
    return FileResponse(
        full_path,
        media_type="application/octet-stream",
        filename=os.path.basename(file_path),
    )


@router.get("/tasks/{task_id}/images/{image_name}")
async def get_task_image(
    task_id: str = Path(..., regex="^[a-zA-Z0-9_-]+$"),
    image_name: str = Path(..., regex="^[a-zA-Z0-9_.-]+$"),  # 只允许安全的文件名字符
    current_user: dict = Depends(get_current_user),
):
    """
    获取任务生成的图片文件

    Args:
        task_id: 任务 ID
        image_name: 图片文件名

    Returns:
        FileResponse: 图片文件
    """
    # 只允许特定的图片扩展名
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf'}
    file_ext = PathLib(image_name).suffix.lower()

    if file_ext not in allowed_extensions:
        logger.warning("不允许的文件类型: %s", image_name)
        raise HTTPException(status_code=400, detail="不允许的文件类型")

    # 构建图片路径
    image_path = os.path.join("project", "work_dir", task_id, image_name)

    # 安全性检查
    if not is_safe_path("project/work_dir", os.path.join(task_id, image_name)):
        logger.error("检测到路径遍历攻击: task_id=%s, image=%s", task_id, image_name)
        raise HTTPException(status_code=403, detail="非法的文件路径")

    # 检查文件是否存在
    if not os.path.exists(image_path) or not os.path.isfile(image_path):
        logger.warning("图片不存在: %s", image_path)
        raise HTTPException(status_code=404, detail="图片不存在")

    # 根据文件扩展名确定 MIME 类型
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
    }

    logger.info("提供图片访问: task_id=%s, image=%s", task_id, image_name)
    return FileResponse(
        image_path,
        media_type=mime_types.get(file_ext, 'application/octet-stream'),
        filename=image_name,
    )
