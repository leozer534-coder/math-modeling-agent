"""
后台任务注册表

统一管理 asyncio 后台任务的生命周期：
- 注册：创建任务时注册到注册表
- 异常捕获：任务完成后自动检查异常并记录日志
- 取消：支持按 task_id 或全量取消
- 清理：自动清理已完成的任务引用
"""
import asyncio
from typing import Coroutine, Optional

from app.utils.log_util import logger


class TaskRegistry:
    """后台任务注册表（进程内单例）"""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def create_task(
        self,
        coro: Coroutine,
        *,
        task_id: str,
        name: Optional[str] = None,
    ) -> asyncio.Task:
        """
        创建并注册一个后台任务

        Args:
            coro: 要执行的协程
            task_id: 任务唯一标识（用于查找和取消）
            name: 可选的任务名称（用于日志）

        Returns:
            创建的 asyncio.Task
        """
        # 清理同 ID 的旧任务
        self._cleanup_task(task_id)

        task = asyncio.create_task(coro, name=name or f"bg-{task_id}")
        self._tasks[task_id] = task

        # 添加完成回调：异常捕获 + 自动清理
        task.add_done_callback(lambda t: self._on_task_done(task_id, t))

        logger.info("后台任务已注册: %s (%s)", task_id, name or 'unnamed')
        return task

    def _on_task_done(self, task_id: str, task: asyncio.Task) -> None:
        """任务完成回调"""
        try:
            exc = task.exception()
            if exc:
                logger.error(
                    f"后台任务异常: {task_id} - {type(exc).__name__}: {exc}",
                    exc_info=exc,
                )
        except asyncio.CancelledError:
            logger.info("后台任务已取消: %s", task_id)
        except asyncio.InvalidStateError:
            pass
        finally:
            self._tasks.pop(task_id, None)

    def cancel(self, task_id: str) -> bool:
        """取消指定任务"""
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info("已请求取消任务: %s", task_id)
            return True
        return False

    def cancel_all(self) -> int:
        """取消所有活跃任务"""
        cancelled = 0
        for task_id in list(self._tasks.keys()):
            if self.cancel(task_id):
                cancelled += 1
        return cancelled

    def get_active_tasks(self) -> dict[str, str]:
        """获取所有活跃任务的状态"""
        self._cleanup_done()
        return {
            tid: task.get_name()
            for tid, task in self._tasks.items()
            if not task.done()
        }

    def _cleanup_task(self, task_id: str) -> None:
        """清理指定 ID 的旧任务"""
        old = self._tasks.pop(task_id, None)
        if old and not old.done():
            old.cancel()
            logger.warning("覆盖未完成的旧任务: %s", task_id)

    def _cleanup_done(self) -> None:
        """清理已完成的任务引用"""
        done_ids = [tid for tid, t in self._tasks.items() if t.done()]
        for tid in done_ids:
            self._tasks.pop(tid, None)


# 全局单例
task_registry = TaskRegistry()
