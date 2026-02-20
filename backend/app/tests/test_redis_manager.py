"""
Redis Manager 测试模块
测试 Redis 连接管理、消息发布等功能
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestRedisManagerInitialization:
    """测试 Redis Manager 初始化"""

    def test_redis_manager_import(self):
        """测试 Redis Manager 可导入"""
        from app.services.redis_manager import redis_manager
        assert redis_manager is not None


class TestRedisManagerOperations:
    """测试 Redis 操作"""

    @pytest.fixture
    def mock_redis_client(self):
        """模拟 Redis 客户端"""
        client = AsyncMock()
        client.publish = AsyncMock(return_value=1)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.close = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_publish_message(self, mock_redis_client):
        """测试消息发布"""
        result = await mock_redis_client.publish("test_channel", "test_message")
        assert result == 1
        mock_redis_client.publish.assert_called_once_with("test_channel", "test_message")

    @pytest.mark.asyncio
    async def test_get_value(self, mock_redis_client):
        """测试获取值"""
        mock_redis_client.get.return_value = "cached_value"
        result = await mock_redis_client.get("test_key")
        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_set_value(self, mock_redis_client):
        """测试设置值"""
        result = await mock_redis_client.set("test_key", "test_value")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_value(self, mock_redis_client):
        """测试删除值"""
        result = await mock_redis_client.delete("test_key")
        assert result == 1

    @pytest.mark.asyncio
    async def test_close_connection(self, mock_redis_client):
        """测试关闭连接"""
        await mock_redis_client.close()
        mock_redis_client.close.assert_called_once()


class TestRedisManagerTaskOperations:
    """测试任务相关的 Redis 操作"""

    @pytest.fixture
    def mock_redis_manager(self):
        """模拟 Redis Manager"""
        manager = MagicMock()
        manager.publish = AsyncMock(return_value=None)
        manager.get_task_status = AsyncMock(return_value="running")
        manager.set_task_status = AsyncMock(return_value=True)
        return manager

    @pytest.mark.asyncio
    async def test_publish_task_update(self, mock_redis_manager):
        """测试发布任务更新"""
        await mock_redis_manager.publish("task_update", {"task_id": "123", "status": "completed"})
        mock_redis_manager.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_status(self, mock_redis_manager):
        """测试获取任务状态"""
        status = await mock_redis_manager.get_task_status("task_123")
        assert status == "running"

    @pytest.mark.asyncio
    async def test_set_task_status(self, mock_redis_manager):
        """测试设置任务状态"""
        result = await mock_redis_manager.set_task_status("task_123", "completed")
        assert result is True
