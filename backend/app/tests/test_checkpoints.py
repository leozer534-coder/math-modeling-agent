"""
检查点模块单元测试 - Checkpoint Tests

测试内容：
1. Checkpoint数据类
2. CheckpointManager存储和恢复
3. 检查点装饰器
"""

import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.workflow.checkpoints import (
    Checkpoint,
    CheckpointManager,
    CheckpointStatus,
    TaskCheckpointSummary,
    checkpoint_stage,
)


# ============= Checkpoint Tests =============

class TestCheckpoint:
    """检查点数据类测试"""
    
    def test_create_checkpoint(self):
        """测试创建检查点"""
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="代码实现",
            stage_index=3,
            total_stages=7,
            status=CheckpointStatus.CREATED,
        )
        
        assert cp.checkpoint_id == "cp_001"
        assert cp.task_id == "task_123"
        assert cp.stage_name == "代码实现"
        assert cp.stage_index == 3
        assert cp.total_stages == 7
    
    def test_to_dict(self):
        """测试序列化"""
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="测试阶段",
            stage_index=1,
            total_stages=5,
            status=CheckpointStatus.IN_PROGRESS,
            context_snapshot={"key": "value"},
        )
        
        data = cp.to_dict()
        
        assert data["checkpoint_id"] == "cp_001"
        assert data["status"] == "in_progress"
        assert data["context_snapshot"] == {"key": "value"}
    
    def test_from_dict(self):
        """测试反序列化"""
        data = {
            "checkpoint_id": "cp_002",
            "task_id": "task_456",
            "stage_name": "论文写作",
            "stage_index": 5,
            "total_stages": 7,
            "status": "completed",
            "stage_input": {},
            "stage_output": {"result": "done"},
            "context_snapshot": {},
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T11:00:00",
            "expires_at": None,
            "metadata": {},
        }
        
        cp = Checkpoint.from_dict(data)
        
        assert cp.checkpoint_id == "cp_002"
        assert cp.status == CheckpointStatus.COMPLETED
        assert cp.stage_output == {"result": "done"}
    
    def test_is_resumable_created(self):
        """测试可恢复状态 - 已创建"""
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="测试",
            stage_index=0,
            total_stages=1,
            status=CheckpointStatus.CREATED,
        )
        
        assert cp.is_resumable is True
    
    def test_is_resumable_completed(self):
        """测试可恢复状态 - 已完成"""
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="测试",
            stage_index=0,
            total_stages=1,
            status=CheckpointStatus.COMPLETED,
        )
        
        assert cp.is_resumable is False
    
    def test_is_resumable_expired(self):
        """测试可恢复状态 - 已过期"""
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="测试",
            stage_index=0,
            total_stages=1,
            status=CheckpointStatus.IN_PROGRESS,
            expires_at=yesterday,
        )
        
        assert cp.is_resumable is False
    
    def test_progress_percent(self):
        """测试进度百分比"""
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="测试",
            stage_index=3,
            total_stages=10,
            status=CheckpointStatus.IN_PROGRESS,
        )
        
        assert cp.progress_percent == 30.0
    
    def test_progress_percent_zero_stages(self):
        """测试进度百分比 - 零阶段"""
        cp = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_123",
            stage_name="测试",
            stage_index=0,
            total_stages=0,
            status=CheckpointStatus.CREATED,
        )
        
        assert cp.progress_percent == 0


# ============= CheckpointManager Tests =============

class TestCheckpointManager:
    """检查点管理器测试"""
    
    def test_create_checkpoint(self):
        """测试创建检查点"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            cp = manager.create_checkpoint(
                task_id="task_001",
                stage_name="问题分析",
                stage_index=0,
                total_stages=7,
                context_snapshot={"data": "test"},
            )
            
            assert cp.task_id == "task_001"
            assert cp.stage_name == "问题分析"
            assert cp.stage_index == 0
            assert cp.status == CheckpointStatus.CREATED
            assert cp.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_save_and_load_file(self):
        """测试文件存储和加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            cp = manager.create_checkpoint(
                task_id="task_002",
                stage_name="模型选择",
                stage_index=1,
                total_stages=7,
                context_snapshot={"model": "xgboost"},
            )
            
            # 保存
            result = await manager.save(cp)
            assert result is True
            
            # 加载
            loaded = await manager.load("task_002")
            assert loaded is not None
            assert loaded.task_id == "task_002"
            assert loaded.stage_name == "模型选择"
    
    @pytest.mark.asyncio
    async def test_load_nonexistent(self):
        """测试加载不存在的检查点"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            loaded = await manager.load("nonexistent_task")
            
            assert loaded is None
    
    @pytest.mark.asyncio
    async def test_update_status(self):
        """测试更新状态"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            cp = manager.create_checkpoint(
                task_id="task_003",
                stage_name="代码实现",
                stage_index=2,
                total_stages=7,
                context_snapshot={},
            )
            await manager.save(cp)
            
            # 更新状态
            result = await manager.update_status(
                "task_003",
                CheckpointStatus.COMPLETED,
                {"result": "success"},
            )
            
            assert result is True
            
            # 验证更新
            await manager.load("task_003")
            # 注意：已完成的检查点不可恢复，所以load返回None
            # 这里需要直接读取文件验证
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除检查点"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            cp = manager.create_checkpoint(
                task_id="task_004",
                stage_name="测试",
                stage_index=0,
                total_stages=1,
                context_snapshot={},
            )
            await manager.save(cp)
            
            # 删除
            result = await manager.delete("task_004")
            assert result is True
            
            # 验证删除
            loaded = await manager.load("task_004")
            assert loaded is None
    
    @pytest.mark.asyncio
    async def test_list_resumable_tasks(self):
        """测试列出可恢复任务"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            # 创建多个检查点
            for i in range(3):
                cp = manager.create_checkpoint(
                    task_id=f"task_{i:03d}",
                    stage_name=f"阶段{i}",
                    stage_index=i,
                    total_stages=5,
                    context_snapshot={},
                )
                await manager.save(cp)
            
            # 列出
            resumable = await manager.list_resumable_tasks()
            
            assert len(resumable) == 3
            assert all(isinstance(s, TaskCheckpointSummary) for s in resumable)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """测试清理过期检查点"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False, expire_hours=0)
            
            # 创建已过期的检查点
            cp = manager.create_checkpoint(
                task_id="expired_task",
                stage_name="测试",
                stage_index=0,
                total_stages=1,
                context_snapshot={},
            )
            # 手动设置过期时间为过去
            cp.expires_at = (datetime.now() - timedelta(hours=1)).isoformat()
            manager._save_to_file(cp)
            
            # 清理
            cleaned = await manager.cleanup_expired()
            
            assert cleaned == 1
    
    def test_serialize_context_with_complex_objects(self):
        """测试序列化复杂对象"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CheckpointManager(storage_dir=temp_dir, use_redis=False)
            
            context = {
                "string": "hello",
                "number": 42,
                "list": [1, 2, 3],
                "complex": object(),  # 不可序列化
            }
            
            serialized = manager._serialize_context(context)
            
            assert serialized["string"] == "hello"
            assert serialized["number"] == 42
            assert serialized["list"] == [1, 2, 3]
            assert "_type" in serialized["complex"]


# ============= Decorator Tests =============

class TestCheckpointDecorator:
    """检查点装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_checkpoint_stage_success(self):
        """测试装饰器 - 成功执行"""
        @checkpoint_stage("测试阶段", 0, 1)
        async def test_stage(context):
            return "success"
        
        # 创建mock上下文
        context = MagicMock()
        context.task_id = "decorator_test_001"
        
        with patch("app.core.workflow.checkpoints.get_checkpoint_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.create_checkpoint = MagicMock(return_value=Checkpoint(
                checkpoint_id="cp",
                task_id="decorator_test_001",
                stage_name="测试阶段",
                stage_index=0,
                total_stages=1,
                status=CheckpointStatus.CREATED,
            ))
            mock_manager.save = AsyncMock(return_value=True)
            mock_manager.update_status = AsyncMock(return_value=True)
            mock_get.return_value = mock_manager
            
            result = await test_stage(context)
            
            assert result == "success"
            assert mock_manager.save.called
            assert mock_manager.update_status.called
    
    @pytest.mark.asyncio
    async def test_checkpoint_stage_failure(self):
        """测试装饰器 - 执行失败"""
        @checkpoint_stage("失败阶段", 0, 1)
        async def failing_stage(context):
            raise ValueError("Test error")
        
        context = MagicMock()
        context.task_id = "decorator_test_002"
        
        with patch("app.core.workflow.checkpoints.get_checkpoint_manager") as mock_get:
            mock_manager = MagicMock()
            mock_manager.create_checkpoint = MagicMock(return_value=Checkpoint(
                checkpoint_id="cp",
                task_id="decorator_test_002",
                stage_name="失败阶段",
                stage_index=0,
                total_stages=1,
                status=CheckpointStatus.CREATED,
            ))
            mock_manager.save = AsyncMock(return_value=True)
            mock_manager.update_status = AsyncMock(return_value=True)
            mock_get.return_value = mock_manager
            
            with pytest.raises(ValueError):
                await failing_stage(context)
            
            # 验证失败状态被保存
            mock_manager.update_status.assert_called()
            call_args = mock_manager.update_status.call_args
            assert call_args[0][1] == CheckpointStatus.FAILED
