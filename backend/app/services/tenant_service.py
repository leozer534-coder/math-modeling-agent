"""
多租户资源隔离服务

提供用户级工作目录隔离、并发任务限制、存储配额检查等功能，
确保不同用户之间的资源互不干扰。
"""
import os
from pathlib import Path
from typing import Optional

from app.config.setting import settings
from app.services.redis_manager import redis_manager
from app.utils.exceptions import (
    ConcurrentLimitExceededException,
    StorageQuotaExceededException,
    WorkspaceException,
)
from app.utils.log_util import logger


# Redis 键前缀常量
_ACTIVE_TASKS_KEY_PREFIX = "tenant:active_tasks:"
_TASK_OWNER_KEY_PREFIX = "tenant:task_owner:"


class TenantService:
    """
    多租户资源隔离服务

    职责:
    - 为每个用户创建隔离的工作目录 (work_dir/{user_id}/{task_id}/)
    - 通过 Redis 计数器跟踪用户活跃任务数，实施并发限制
    - 检查用户工作目录总大小，实施存储配额限制
    """

    # ==================== 工作目录隔离 ====================

    @staticmethod
    def get_user_workspace(user_id: str) -> Path:
        """
        获取用户专属的工作空间根目录

        目录结构: {WORKSPACE_BASE_DIR}/{user_id}/
        如果目录不存在则自动创建。

        Args:
            user_id: 用户唯一标识

        Returns:
            Path: 用户工作空间根目录的绝对路径

        Raises:
            WorkspaceException: 目录创建失败时抛出
        """
        if not user_id or not user_id.strip():
            raise WorkspaceException(
                message="无法创建工作目录: 用户ID无效",
                detail=f"收到的 user_id 为空或无效: '{user_id}'",
            )

        # 对 user_id 做基本的路径安全校验，防止路径穿越攻击
        sanitized_id = _sanitize_path_component(user_id)

        workspace = Path(settings.WORKSPACE_BASE_DIR) / sanitized_id
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("用户工作空间就绪: %s", workspace)
            return workspace
        except OSError as e:
            logger.error("创建用户工作空间失败: user_id=%s, error=%s", user_id, e)
            raise WorkspaceException(
                message="创建用户工作目录失败",
                detail=str(e),
            )

    @staticmethod
    def get_task_workspace(user_id: str, task_id: str) -> Path:
        """
        获取用户某个任务的隔离工作目录

        目录结构: {WORKSPACE_BASE_DIR}/{user_id}/{task_id}/
        如果目录不存在则自动创建。

        Args:
            user_id: 用户唯一标识
            task_id: 任务唯一标识

        Returns:
            Path: 任务工作目录的绝对路径

        Raises:
            WorkspaceException: 目录创建失败时抛出
        """
        if not task_id or not task_id.strip():
            raise WorkspaceException(
                message="无法创建任务工作目录: 任务ID无效",
                detail=f"收到的 task_id 为空或无效: '{task_id}'",
            )

        sanitized_task_id = _sanitize_path_component(task_id)
        user_workspace = TenantService.get_user_workspace(user_id)
        task_workspace = user_workspace / sanitized_task_id

        try:
            task_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug(
                "任务工作目录就绪: user_id=%s, task_id=%s, path=%s",
                user_id, task_id, task_workspace
            )
            return task_workspace
        except OSError as e:
            logger.error(
                "创建任务工作目录失败: user_id=%s, task_id=%s, error=%s",
                user_id, task_id, e
            )
            raise WorkspaceException(
                message="创建任务工作目录失败",
                detail=str(e),
            )

    # ==================== 并发任务限制 ====================

    @staticmethod
    async def check_concurrent_limit(
        user_id: str,
        max_tasks: Optional[int] = None,
    ) -> bool:
        """
        检查用户是否超出并发任务限制

        使用 Redis 计数器（Set 结构）跟踪每个用户当前活跃的任务数。
        如果未超限返回 True，超限则返回 False。

        Args:
            user_id: 用户唯一标识
            max_tasks: 最大并发任务数，默认使用配置值

        Returns:
            bool: True 表示未超限可以继续，False 表示已超限
        """
        if max_tasks is None:
            max_tasks = settings.MAX_CONCURRENT_TASKS_PER_USER

        try:
            key = f"{_ACTIVE_TASKS_KEY_PREFIX}{user_id}"
            client = await redis_manager.get_client()
            current_count = await client.scard(key)

            if current_count >= max_tasks:
                logger.warning(
                    "用户并发任务超限: user_id=%s, 当前=%s, 上限=%s",
                    user_id, current_count, max_tasks
                )
                return False

            logger.debug(
                "并发任务检查通过: user_id=%s, 当前=%s, 上限=%s",
                user_id, current_count, max_tasks
            )
            return True
        except ConnectionError as e:
            # Redis 不可用时，出于安全考虑默认放行，避免阻塞业务
            logger.error("Redis 连接失败，跳过并发检查: %s", e)
            return True
        except Exception as e:
            logger.error("检查并发任务限制时出错: user_id=%s, error=%s", user_id, e)
            return True

    @staticmethod
    async def register_active_task(user_id: str, task_id: str) -> None:
        """
        注册一个活跃任务（任务开始时调用）

        将 task_id 添加到用户的活跃任务集合中，并记录任务归属关系。

        Args:
            user_id: 用户唯一标识
            task_id: 任务唯一标识
        """
        try:
            client = await redis_manager.get_client()
            tasks_key = f"{_ACTIVE_TASKS_KEY_PREFIX}{user_id}"
            owner_key = f"{_TASK_OWNER_KEY_PREFIX}{task_id}"

            # 将 task_id 加入用户活跃任务集合
            await client.sadd(tasks_key, task_id)
            # 设置集合的过期时间（10小时），防止异常情况下未清理
            await client.expire(tasks_key, 36000)

            # 记录任务与用户的归属关系（用于任务完成时查找所属用户）
            await client.set(owner_key, user_id)
            await client.expire(owner_key, 36000)

            current_count = await client.scard(tasks_key)
            logger.info(
                "注册活跃任务: user_id=%s, task_id=%s, 当前活跃任务数=%s",
                user_id, task_id, current_count
            )
        except Exception as e:
            # 注册失败不应阻塞任务执行
            logger.error(
                "注册活跃任务失败: user_id=%s, task_id=%s, error=%s",
                user_id, task_id, e
            )

    @staticmethod
    async def unregister_active_task(task_id: str, user_id: Optional[str] = None) -> None:
        """
        注销一个活跃任务（任务完成或失败时调用）

        从用户的活跃任务集合中移除 task_id。

        Args:
            task_id: 任务唯一标识
            user_id: 用户唯一标识（可选，如不提供会从 Redis 查找）
        """
        try:
            client = await redis_manager.get_client()

            # 如果未提供 user_id，从 Redis 中查找归属关系
            if not user_id:
                owner_key = f"{_TASK_OWNER_KEY_PREFIX}{task_id}"
                user_id = await client.get(owner_key)
                if not user_id:
                    logger.warning("找不到任务归属用户: task_id=%s", task_id)
                    return
                # 清理归属记录
                await client.delete(owner_key)

            tasks_key = f"{_ACTIVE_TASKS_KEY_PREFIX}{user_id}"
            removed = await client.srem(tasks_key, task_id)

            if removed:
                remaining = await client.scard(tasks_key)
                logger.info(
                    "注销活跃任务: user_id=%s, task_id=%s, 剩余活跃任务数=%s",
                    user_id, task_id, remaining
                )
            else:
                logger.debug(
                    "任务已不在活跃列表中: user_id=%s, task_id=%s", user_id, task_id
                )
        except Exception as e:
            # 注销失败不应影响业务，集合有过期时间保底
            logger.error(
                "注销活跃任务失败: task_id=%s, user_id=%s, error=%s",
                task_id, user_id, e
            )

    @staticmethod
    async def get_active_task_count(user_id: str) -> int:
        """
        获取用户当前活跃任务数

        Args:
            user_id: 用户唯一标识

        Returns:
            int: 活跃任务数量
        """
        try:
            client = await redis_manager.get_client()
            key = f"{_ACTIVE_TASKS_KEY_PREFIX}{user_id}"
            count = await client.scard(key)
            return int(count)
        except Exception as e:
            logger.error("获取活跃任务数失败: user_id=%s, error=%s", user_id, e)
            return 0

    # ==================== 存储配额检查 ====================

    @staticmethod
    def check_storage_quota(
        user_id: str,
        max_size_mb: Optional[int] = None,
    ) -> bool:
        """
        检查用户存储配额是否超限

        遍历用户工作目录下所有文件，计算总大小。
        如果未超限返回 True，超限则返回 False。

        Args:
            user_id: 用户唯一标识
            max_size_mb: 最大存储空间（MB），默认使用配置值

        Returns:
            bool: True 表示未超限，False 表示已超限
        """
        if max_size_mb is None:
            max_size_mb = settings.MAX_STORAGE_MB_PER_USER

        try:
            used_mb = TenantService.get_storage_usage_mb(user_id)

            if used_mb >= max_size_mb:
                logger.warning(
                    "用户存储配额超限: user_id=%s, 已用=%.1fMB, 上限=%sMB",
                    user_id, used_mb, max_size_mb
                )
                return False

            logger.debug(
                "存储配额检查通过: user_id=%s, 已用=%.1fMB, 上限=%sMB",
                user_id, used_mb, max_size_mb
            )
            return True
        except Exception as e:
            # 检查失败时默认放行，避免阻塞业务
            logger.error("检查存储配额时出错: user_id=%s, error=%s", user_id, e)
            return True

    @staticmethod
    def get_storage_usage_mb(user_id: str) -> float:
        """
        计算用户工作目录的存储使用量

        Args:
            user_id: 用户唯一标识

        Returns:
            float: 已使用的存储空间（MB）
        """
        sanitized_id = _sanitize_path_component(user_id)
        user_workspace = Path(settings.WORKSPACE_BASE_DIR) / sanitized_id

        if not user_workspace.exists():
            return 0.0

        total_bytes = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(user_workspace):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    # 跳过符号链接，防止恶意链接导致统计错误
                    if not os.path.islink(filepath):
                        total_bytes += os.path.getsize(filepath)
        except OSError as e:
            logger.error("计算存储使用量时出错: user_id=%s, error=%s", user_id, e)

        return total_bytes / (1024 * 1024)

    # ==================== 资源检查聚合方法 ====================

    @staticmethod
    async def enforce_resource_limits(user_id: str) -> None:
        """
        统一执行所有资源限制检查

        在任务提交前调用，如果任何一项检查不通过则抛出对应异常。

        Args:
            user_id: 用户唯一标识

        Raises:
            ConcurrentLimitExceededException: 并发任务数超限
            StorageQuotaExceededException: 存储配额超限
        """
        max_tasks = settings.MAX_CONCURRENT_TASKS_PER_USER
        max_storage = settings.MAX_STORAGE_MB_PER_USER

        # 1. 检查并发任务限制
        can_proceed = await TenantService.check_concurrent_limit(
            user_id, max_tasks
        )
        if not can_proceed:
            current_count = await TenantService.get_active_task_count(user_id)
            raise ConcurrentLimitExceededException(
                user_id=user_id,
                max_tasks=max_tasks,
                current_tasks=current_count,
            )

        # 2. 检查存储配额
        within_quota = TenantService.check_storage_quota(user_id, max_storage)
        if not within_quota:
            used_mb = TenantService.get_storage_usage_mb(user_id)
            raise StorageQuotaExceededException(
                user_id=user_id,
                used_mb=used_mb,
                max_mb=max_storage,
            )

        logger.info("用户资源限制检查全部通过: user_id=%s", user_id)


def _sanitize_path_component(component: str) -> str:
    """
    对路径组件进行安全清洗，防止路径穿越攻击

    移除 '..'、'/'、'\\' 等危险字符，仅保留安全字符。

    Args:
        component: 原始路径组件（如 user_id 或 task_id）

    Returns:
        str: 清洗后的安全路径组件

    Raises:
        WorkspaceException: 清洗后结果为空时抛出
    """
    # 移除路径分隔符和上级目录引用
    sanitized = component.replace("..", "").replace("/", "").replace("\\", "")
    # 移除空白字符
    sanitized = sanitized.strip()

    if not sanitized:
        raise WorkspaceException(
            message="路径组件无效",
            detail=f"原始值 '{component}' 经安全清洗后为空，可能包含非法字符",
        )

    return sanitized


# 全局单例
tenant_service = TenantService()
