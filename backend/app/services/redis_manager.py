import asyncio
import json
import time
from pathlib import Path
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config.setting import settings
from app.schemas.response import Message
from app.utils.log_util import logger


class RedisManager:
    """Redis 管理器，提供连接管理、消息发布/订阅、键值操作等功能。"""

    def __init__(self) -> None:
        self.redis_url = settings.REDIS_URL
        self._client: Optional[aioredis.Redis] = None
        # 上次 ping 时间戳，避免每次 get_client 都执行 ping
        self._last_ping_time: float = 0.0
        # ping 检查间隔（秒）
        self._ping_interval: float = 30.0
        # 创建消息存储目录
        self.messages_dir = Path("logs/messages")
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        # 文件写入锁，防止并发写入导致数据损坏
        self._file_locks: dict[str, asyncio.Lock] = {}

    def _get_file_lock(self, task_id: str) -> asyncio.Lock:
        """获取指定任务的文件写入锁。

        当锁数量超过阈值时自动触发清理，防止内存泄漏。
        """
        if task_id not in self._file_locks:
            self._file_locks[task_id] = asyncio.Lock()
            # 每次新增锁时检查是否需要清理
            self.cleanup_stale_locks()
        return self._file_locks[task_id]

    def cleanup_task_lock(self, task_id: str) -> None:
        """清理指定任务的文件写入锁，在任务完成后调用以防止内存泄漏。

        Args:
            task_id: 要清理的任务ID。
        """
        self._file_locks.pop(task_id, None)
        logger.debug("已清理任务文件锁: %s, 当前锁数量: %d", task_id, len(self._file_locks))

    def cleanup_stale_locks(self, max_locks: int = 500) -> int:
        """当锁数量超过阈值时，清理所有未被持有的锁，防止长期运行导致内存泄漏。

        Args:
            max_locks: 锁数量上限，超过此值时触发清理。

        Returns:
            本次清理的锁数量。
        """
        if len(self._file_locks) <= max_locks:
            return 0

        stale_keys = [
            task_id
            for task_id, lock in self._file_locks.items()
            if not lock.locked()
        ]
        for task_id in stale_keys:
            del self._file_locks[task_id]

        if stale_keys:
            logger.info(
                "清理了 %d 个过期文件锁, 剩余 %d 个",
                len(stale_keys),
                len(self._file_locks),
            )
        return len(stale_keys)

    async def get_client(self) -> aioredis.Redis:
        """获取 Redis 客户端连接。

        仅在首次连接或距上次 ping 超过 30 秒时执行 ping 检查，
        避免频繁 ping 带来的性能开销。
        """
        if self._client is None:
            self._client = aioredis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # 首次连接，强制 ping 验证
            self._last_ping_time = 0.0

        now = time.monotonic()
        if now - self._last_ping_time > self._ping_interval:
            try:
                await self._client.ping()
                self._last_ping_time = now
                logger.debug("Redis 连接正常: %s", self.redis_url)
            except Exception as e:
                logger.error("无法连接到 Redis: %s", e)
                # 重置客户端，下次调用时重新创建
                self._client = None
                raise

        return self._client

    # ========== 基础键值操作 ==========

    async def get(self, key: str) -> Optional[str]:
        """获取 Redis 键对应的值。"""
        client = await self.get_client()
        result = await client.get(key)
        return result

    async def set(self, key: str, value: str) -> None:
        """设置 Redis 键值对，默认过期时间 36000 秒。"""
        client = await self.get_client()
        await client.set(key, value)
        await client.expire(key, 36000)

    async def setex(self, key: str, seconds: int, value: str) -> None:
        """设置带过期时间的 Redis 键值对。"""
        client = await self.get_client()
        await client.setex(key, seconds, value)

    async def delete(self, *keys: str) -> int:
        """删除一个或多个 Redis 键，返回成功删除的数量。"""
        if not keys:
            return 0
        client = await self.get_client()
        result = await client.delete(*keys)
        return result

    async def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间（秒）。"""
        client = await self.get_client()
        result = await client.expire(key, seconds)
        return result

    # ========== JSON 序列化操作 ==========

    async def set_json(self, key: str, value: Any, expire: int = 3600) -> None:
        """将 Python 对象序列化为 JSON 并存储到 Redis。

        Args:
            key: Redis 键。
            value: 要序列化的对象。
            expire: 过期时间（秒），默认 3600。
        """
        client = await self.get_client()
        await client.setex(
            key, expire, json.dumps(value, ensure_ascii=False, default=str)
        )

    async def get_json(self, key: str) -> Optional[Any]:
        """从 Redis 读取 JSON 字符串并反序列化为 Python 对象。

        Args:
            key: Redis 键。

        Returns:
            反序列化后的对象，键不存在时返回 None。
        """
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Redis 键 %s 的值无法解析为 JSON", key)
            return None

    # ========== 列表操作 ==========

    async def lpush(self, key: str, *values: str) -> int:
        """向列表左端推入一个或多个值，返回列表长度。"""
        if not values:
            return 0
        client = await self.get_client()
        result = await client.lpush(key, *values)
        return result

    async def lrange(self, key: str, start: int, end: int) -> list:
        """获取列表指定范围内的元素。"""
        client = await self.get_client()
        result = await client.lrange(key, start, end)
        return result

    # ========== 消息发布/订阅 ==========

    @staticmethod
    def _sync_write_message(file_path: str, line: str) -> None:
        """同步写入消息到文件（在线程池中执行，避免阻塞事件循环）。"""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)

    async def _save_message_to_file(self, task_id: str, message: Message) -> None:
        """将消息保存到文件中，同一任务的消息保存在同一个文件中。

        使用 asyncio.Lock 防止并发写入导致数据损坏，
        采用 JSON Lines 格式追加写入，文件 I/O 通过 run_in_executor
        卸载到线程池以避免阻塞事件循环。
        """
        lock = self._get_file_lock(task_id)
        async with lock:
            try:
                # 确保目录存在
                self.messages_dir.mkdir(exist_ok=True)

                # 使用任务 ID 作为文件名，采用 JSON Lines 格式追加写入
                file_path = self.messages_dir / f"{task_id}.jsonl"

                message_data = message.model_dump()
                line = json.dumps(message_data, ensure_ascii=False) + "\n"

                # 将同步文件写入卸载到线程池，避免阻塞事件循环
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, self._sync_write_message, str(file_path), line
                )

                logger.debug("消息已追加到文件: %s", file_path)
            except Exception as e:
                logger.error("保存消息到文件失败: %s", e)
                # 不抛出异常，确保主流程不受影响

    async def publish_message(self, task_id: str, message: Message) -> None:
        """发布消息到特定任务的频道并保存到文件。"""
        client = await self.get_client()
        channel = f"task:{task_id}:messages"
        try:
            message_json = message.model_dump_json()
            await client.publish(channel, message_json)
            logger.debug(
                "消息已发布到频道 %s:msg_type:%s:msg_content:%s",
                channel, message.msg_type, message.content
            )
            # 保存消息到文件
            await self._save_message_to_file(task_id, message)
        except Exception as e:
            logger.error("发布消息失败: %s", e)
            raise

    async def subscribe_to_task(self, task_id: str):
        """订阅特定任务的消息。"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"task:{task_id}:messages")
        return pubsub

    async def close(self) -> None:
        """关闭 Redis 连接。"""
        if self._client:
            await self._client.close()
            self._client = None
            self._last_ping_time = 0.0
        # 清理文件锁
        self._file_locks.clear()


redis_manager = RedisManager()

# 依赖注入支持: 供 FastAPI Depends 使用
_redis_manager: Optional[RedisManager] = redis_manager


def get_redis_manager() -> RedisManager:
    """获取 RedisManager 实例的依赖注入函数。

    用于 FastAPI 路由中通过 Depends(get_redis_manager) 注入，
    便于测试时通过 app.dependency_overrides 替换为 Mock。
    """
    if _redis_manager is None:
        raise RuntimeError("RedisManager 尚未初始化")
    return _redis_manager
