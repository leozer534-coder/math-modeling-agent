"""
检查点管理模块 - Checkpoint Manager

提供工作流断点续传功能

功能：
1. 检查点创建与保存
2. 检查点恢复
3. 任务状态持久化（Redis/文件）
4. 过期清理
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar

from app.utils.log_util import logger


# ============= 类型定义 =============

T = TypeVar('T')


class CheckpointStatus(str, Enum):
    """检查点状态"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


# ============= 检查点数据 =============

@dataclass
class Checkpoint:
    """工作流检查点"""
    checkpoint_id: str
    task_id: str
    stage_name: str
    stage_index: int
    total_stages: int
    status: CheckpointStatus
    
    # 阶段数据
    stage_input: Dict[str, Any] = field(default_factory=dict)
    stage_output: Dict[str, Any] = field(default_factory=dict)
    
    # 上下文状态
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # 时间信息
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        data["status"] = CheckpointStatus(data.get("status", "created"))
        return cls(**data)
    
    @property
    def is_resumable(self) -> bool:
        """是否可恢复"""
        if self.status in [CheckpointStatus.EXPIRED, CheckpointStatus.COMPLETED]:
            return False
        if self.expires_at:
            expires = datetime.fromisoformat(self.expires_at)
            if datetime.now() > expires:
                return False
        return True
    
    @property
    def progress_percent(self) -> float:
        """进度百分比"""
        if self.total_stages == 0:
            return 0
        return (self.stage_index / self.total_stages) * 100


@dataclass
class TaskCheckpointSummary:
    """任务检查点摘要"""
    task_id: str
    current_stage: str
    stage_index: int
    total_stages: int
    status: str
    created_at: str
    updated_at: str
    is_resumable: bool
    progress_percent: float


# ============= 检查点管理器 =============

class CheckpointManager:
    """
    检查点管理器
    
    管理工作流的断点保存和恢复
    
    使用示例：
        >>> manager = CheckpointManager()
        >>> cp = manager.create_checkpoint("task-123", "代码实现", 3, 7, {...})
        >>> await manager.save(cp)
        >>> restored = await manager.load("task-123")
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        use_redis: bool = True,
        expire_hours: int = 168,  # 7天
    ):
        """
        初始化检查点管理器
        
        Args:
            storage_dir: 文件存储目录（Redis不可用时的备份）
            use_redis: 是否使用Redis存储
            expire_hours: 检查点过期时间（小时）
        """
        self.storage_dir = Path(storage_dir or "data/checkpoints")
        self.use_redis = use_redis
        self.expire_hours = expire_hours
        
        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("CheckpointManager 初始化: redis=%s, expire=%sh", use_redis, expire_hours)
    
    def create_checkpoint(
        self,
        task_id: str,
        stage_name: str,
        stage_index: int,
        total_stages: int,
        context_snapshot: Dict[str, Any],
        stage_input: Optional[Dict[str, Any]] = None,
        stage_output: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """
        创建新检查点
        
        Args:
            task_id: 任务ID
            stage_name: 阶段名称
            stage_index: 阶段索引（从0开始）
            total_stages: 总阶段数
            context_snapshot: 上下文快照
            stage_input: 阶段输入
            stage_output: 阶段输出
            metadata: 元数据
            
        Returns:
            Checkpoint: 新检查点
        """
        checkpoint_id = f"{task_id}_{stage_index}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        expires_at = (datetime.now() + timedelta(hours=self.expire_hours)).isoformat()
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            stage_name=stage_name,
            stage_index=stage_index,
            total_stages=total_stages,
            status=CheckpointStatus.CREATED,
            stage_input=stage_input or {},
            stage_output=stage_output or {},
            context_snapshot=self._serialize_context(context_snapshot),
            expires_at=expires_at,
            metadata=metadata or {},
        )
        
        logger.info("创建检查点: %s (%s/%s)", stage_name, stage_index + 1, total_stages)
        return checkpoint
    
    def _serialize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """序列化上下文（处理不可序列化对象）"""
        serialized = {}
        
        for key, value in context.items():
            try:
                # 尝试JSON序列化测试
                json.dumps(value)
                serialized[key] = value
            except (TypeError, ValueError):
                # 不可序列化的对象，存储类型信息
                serialized[key] = {
                    "_type": type(value).__name__,
                    "_repr": str(value)[:500],  # 截断长字符串
                }
        
        return serialized
    
    async def save(self, checkpoint: Checkpoint) -> bool:
        """
        保存检查点
        
        Args:
            checkpoint: 检查点对象
            
        Returns:
            bool: 是否保存成功
        """
        checkpoint.updated_at = datetime.now().isoformat()
        
        # 优先使用Redis
        if self.use_redis:
            try:
                from app.services.redis_manager import redis_manager
                
                await redis_manager.set_json(
                    f"checkpoint:{checkpoint.task_id}",
                    checkpoint.to_dict(),
                    expire=self.expire_hours * 3600,
                )
                
                # 同时保存到历史记录
                await redis_manager.push_to_list(
                    f"checkpoint_history:{checkpoint.task_id}",
                    json.dumps(checkpoint.to_dict()),
                    max_length=50,  # 最多保留50条历史
                )
                
                logger.debug("检查点已保存到Redis: %s", checkpoint.checkpoint_id)
                return True
                
            except Exception as e:
                logger.warning("Redis保存失败，回退到文件: %s", e)
        
        # 文件存储备份
        return self._save_to_file(checkpoint)
    
    def _save_to_file(self, checkpoint: Checkpoint) -> bool:
        """保存到文件"""
        try:
            file_path = self.storage_dir / f"{checkpoint.task_id}.json"
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.debug("检查点已保存到文件: %s", file_path)
            return True
            
        except Exception as e:
            logger.error("文件保存失败: %s", e)
            return False
    
    async def load(self, task_id: str) -> Optional[Checkpoint]:
        """
        加载最新检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            Checkpoint 或 None
        """
        # 优先从Redis加载
        if self.use_redis:
            try:
                from app.services.redis_manager import redis_manager
                
                data = await redis_manager.get_json(f"checkpoint:{task_id}")
                if data:
                    checkpoint = Checkpoint.from_dict(data)
                    if checkpoint.is_resumable:
                        logger.info("从Redis恢复检查点: %s", checkpoint.stage_name)
                        return checkpoint
                    else:
                        logger.warning("检查点已过期或不可恢复: %s", task_id)
                        
            except Exception as e:
                logger.warning("Redis加载失败: %s", e)
        
        # 从文件加载
        return self._load_from_file(task_id)
    
    def _load_from_file(self, task_id: str) -> Optional[Checkpoint]:
        """从文件加载"""
        try:
            file_path = self.storage_dir / f"{task_id}.json"
            
            if not file_path.exists():
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            checkpoint = Checkpoint.from_dict(data)
            
            if checkpoint.is_resumable:
                logger.info("从文件恢复检查点: %s", checkpoint.stage_name)
                return checkpoint
            else:
                logger.warning("检查点已过期: %s", task_id)
                return None
                
        except Exception as e:
            logger.error("文件加载失败: %s", e)
            return None
    
    async def update_status(
        self,
        task_id: str,
        status: CheckpointStatus,
        stage_output: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新检查点状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            stage_output: 阶段输出
            
        Returns:
            bool: 是否更新成功
        """
        checkpoint = await self.load(task_id)
        if not checkpoint:
            return False
        
        checkpoint.status = status
        if stage_output:
            checkpoint.stage_output = stage_output
        
        return await self.save(checkpoint)
    
    async def delete(self, task_id: str) -> bool:
        """删除检查点"""
        try:
            # 删除Redis中的检查点
            if self.use_redis:
                from app.services.redis_manager import redis_manager
                await redis_manager.delete(f"checkpoint:{task_id}")
            
            # 删除文件
            file_path = self.storage_dir / f"{task_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            logger.info("检查点已删除: %s", task_id)
            return True
            
        except Exception as e:
            logger.error("删除检查点失败: %s", e)
            return False
    
    async def list_resumable_tasks(self) -> List[TaskCheckpointSummary]:
        """列出所有可恢复的任务"""
        summaries = []
        
        # 从文件系统扫描
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                checkpoint = Checkpoint.from_dict(data)
                
                if checkpoint.is_resumable:
                    summaries.append(TaskCheckpointSummary(
                        task_id=checkpoint.task_id,
                        current_stage=checkpoint.stage_name,
                        stage_index=checkpoint.stage_index,
                        total_stages=checkpoint.total_stages,
                        status=checkpoint.status.value,
                        created_at=checkpoint.created_at,
                        updated_at=checkpoint.updated_at,
                        is_resumable=True,
                        progress_percent=checkpoint.progress_percent,
                    ))
            except Exception as e:
                logger.warning("读取检查点文件失败 %s: %s", file_path, e)
        
        return summaries
    
    async def cleanup_expired(self) -> int:
        """清理过期检查点"""
        cleaned = 0
        now = datetime.now()
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                expires_at = data.get("expires_at")
                if expires_at and datetime.fromisoformat(expires_at) < now:
                    file_path.unlink()
                    cleaned += 1
                    
            except Exception as e:
                logger.warning("清理检查点失败 %s: %s", file_path, e)
        
        if cleaned > 0:
            logger.info("已清理 %s 个过期检查点", cleaned)
        
        return cleaned


# ============= 全局实例 =============

_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """获取全局检查点管理器"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


# ============= 装饰器 =============

def checkpoint_stage(stage_name: str, stage_index: int, total_stages: int):
    """
    阶段检查点装饰器
    
    自动在阶段执行前后保存检查点
    
    使用示例:
        @checkpoint_stage("代码实现", 3, 7)
        async def execute_code_stage(context):
            ...
    """
    def decorator(func):
        async def wrapper(context, *args, **kwargs):
            manager = get_checkpoint_manager()
            task_id = getattr(context, "task_id", "unknown")
            
            # 阶段开始前保存检查点
            checkpoint = manager.create_checkpoint(
                task_id=task_id,
                stage_name=stage_name,
                stage_index=stage_index,
                total_stages=total_stages,
                context_snapshot=_extract_context(context),
            )
            checkpoint.status = CheckpointStatus.IN_PROGRESS
            await manager.save(checkpoint)
            
            try:
                # 执行阶段
                result = await func(context, *args, **kwargs)
                
                # 成功后更新检查点
                await manager.update_status(
                    task_id,
                    CheckpointStatus.COMPLETED,
                    {"result": str(result)[:1000] if result else None},
                )
                
                return result
                
            except Exception as e:
                # 失败后保存错误状态
                await manager.update_status(
                    task_id,
                    CheckpointStatus.FAILED,
                    {"error": str(e)},
                )
                raise
        
        return wrapper
    return decorator


def _extract_context(context) -> Dict[str, Any]:
    """从上下文对象提取可序列化数据"""
    if hasattr(context, "__dict__"):
        return {k: v for k, v in context.__dict__.items() 
                if not k.startswith("_") and not callable(v)}
    return {}
