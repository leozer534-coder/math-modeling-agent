"""
Celery 应用实例配置

使用 Redis 作为 Broker 和 Result Backend，复用项目现有的 REDIS_URL 配置。
提供统一的 Celery 实例供任务模块使用。
"""

from celery import Celery

from app.config.setting import settings


# 创建 Celery 应用实例
celery_app = Celery(
    "mathmodel_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.core.task_queue.tasks"],
)

# ============= Celery 配置 =============
celery_app.conf.update(
    # --- 序列化配置 ---
    # 使用 JSON 序列化，保证跨语言兼容性和可读性
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # --- 时区配置 ---
    timezone="Asia/Shanghai",
    enable_utc=True,

    # --- 结果存储配置 ---
    # 结果过期时间: 24 小时（秒）
    result_expires=86400,
    # 忽略无返回值的任务结果，减少 Redis 存储压力
    task_ignore_result=False,
    # 任务状态追踪（允许查询 PENDING/STARTED/SUCCESS/FAILURE 等状态）
    task_track_started=True,

    # --- 超时与限制 ---
    # 单任务软超时: CELERY_TASK_TIMEOUT（默认 6 小时），超时后抛出 SoftTimeLimitExceeded
    task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
    # 单任务硬超时: 比软超时多 10 分钟，强制终止 Worker
    task_time_limit=settings.CELERY_TASK_TIMEOUT + 600,

    # --- Worker 配置 ---
    # 每个 Worker 并发数（建模任务属于 CPU/IO 密集型，限制并发避免资源争抢）
    worker_concurrency=2,
    # Worker 预取数量（设为 1 保证公平调度，避免长任务阻塞短任务）
    worker_prefetch_multiplier=1,
    # Worker 执行一定数量任务后重启，防止内存泄漏
    worker_max_tasks_per_child=10,

    # --- 重试配置 ---
    # Broker 连接断开后的重试间隔（秒）
    broker_connection_retry_on_startup=True,

    # --- 任务路由 ---
    # 建模任务路由到专用队列，便于后续按队列分配 Worker 资源
    task_routes={
        "app.core.task_queue.tasks.run_modeling_task": {
            "queue": "modeling",
        },
    },

    # --- 默认队列 ---
    task_default_queue="default",
)
