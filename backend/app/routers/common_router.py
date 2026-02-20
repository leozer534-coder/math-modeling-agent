from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.config.setting import settings
from app.utils.common_utils import get_config_template
from app.schemas.enums import CompTemplate
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger

import json
from pathlib import Path

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/task/{task_id}/messages")
async def get_task_messages(task_id: str):
    """获取指定任务的历史消息列表。

    从 logs/messages/{task_id}.jsonl 文件中读取所有消息并返回。
    """
    file_path = Path("logs/messages") / f"{task_id}.jsonl"
    if not file_path.exists():
        return []

    messages = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error("读取任务消息文件失败: %s", e)
        return []

    return messages


@router.get("/config")
async def config():
    """获取系统配置信息。

    生产环境下隐藏敏感信息（模型名称、Base URL 等），
    仅返回非敏感的运行参数。
    """
    # 基础配置（所有环境均可返回）
    safe_config = {
        "environment": settings.ENV,
        "max_chat_turns": settings.MAX_CHAT_TURNS,
        "max_retries": settings.MAX_RETRIES,
    }

    # 开发环境下额外返回调试信息
    if not settings.is_production():
        safe_config["CORS_ALLOW_ORIGINS"] = settings.CORS_ALLOW_ORIGINS
    else:
        # 生产环境不暴露内部配置细节
        logger.debug("生产环境 /config 端点已隐藏敏感信息")

    return safe_config


@router.get("/writer_seque")
async def get_writer_seque():
    # 返回论文顺序
    config_template: dict = get_config_template(CompTemplate.CHINA)
    return list(config_template.keys())


@router.get("/track")
async def track(task_id: str):
    """获取任务的 Token 使用情况。

    TODO: 尚未实现，当前返回 501 Not Implemented。
    待接入 metering 模块后提供完整的 Token 用量统计。
    """
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Token 用量追踪功能尚未实现",
            "task_id": task_id,
        },
    )


@router.get("/status")
async def get_service_status():
    """获取各个服务的状态"""
    status = {
        "backend": {"status": "running", "message": "Backend service is running"},
        "redis": {"status": "unknown", "message": "Redis connection status unknown"}
    }

    # 检查Redis连接状态
    try:
        redis_client = await redis_manager.get_client()
        await redis_client.ping()
        status["redis"] = {"status": "running", "message": "Redis connection is healthy"}
    except Exception as e:
        logger.error("Redis 连接检查失败: %s", e)
        status["redis"] = {"status": "error", "message": "Redis 连接异常"}

    return status
