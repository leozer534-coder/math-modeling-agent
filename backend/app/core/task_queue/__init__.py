"""
Celery 任务队列模块

提供基于 Celery + Redis 的持久化任务队列，替代 FastAPI BackgroundTasks。
支持任务状态持久化、超时控制、取消、以及服务重启后的任务恢复。
"""

from app.core.task_queue.celery_app import celery_app
from app.core.task_queue.tasks import run_modeling_task


__all__ = ["celery_app", "run_modeling_task"]
