"""
记忆系统模块 - Memory System
为数学建模智能体提供短期记忆、长期记忆和情景记忆管理

功能：
1. 短期记忆 - 当前会话的上下文管理
2. 长期记忆 - 跨会话的知识存储和检索
3. 情景记忆 - 建模经验的存储和复用
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.log_util import logger


@dataclass
class MemoryItem:
    """记忆项"""
    memory_id: str
    content: str
    memory_type: str  # short_term, long_term, episodic
    importance: float = 0.5  # 0-1, 重要性评分
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        return cls(**data)


class MemoryStore(ABC):
    """记忆存储抽象基类"""
    
    @abstractmethod
    async def add(self, item: MemoryItem) -> None:
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        pass


class InMemoryStore(MemoryStore):
    """内存存储（用于短期记忆）"""
    
    def __init__(self, max_size: int = 100):
        self._store: Dict[str, MemoryItem] = {}
        self.max_size = max_size
    
    async def add(self, item: MemoryItem) -> None:
        # 如果超过最大容量，删除最久未访问的
        if len(self._store) >= self.max_size:
            oldest = min(
                self._store.values(), 
                key=lambda x: x.last_accessed
            )
            del self._store[oldest.memory_id]
        
        self._store[item.memory_id] = item
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        item = self._store.get(memory_id)
        if item:
            item.last_accessed = datetime.now().isoformat()
            item.access_count += 1
        return item
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        # 简单的关键词匹配
        query_lower = query.lower()
        matches = []
        
        for item in self._store.values():
            if query_lower in item.content.lower():
                matches.append(item)
        
        # 按重要性和访问次数排序
        matches.sort(
            key=lambda x: (x.importance, x.access_count), 
            reverse=True
        )
        return matches[:limit]
    
    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._store:
            del self._store[memory_id]
            return True
        return False
    
    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count
    
    def get_all(self) -> List[MemoryItem]:
        return list(self._store.values())


class FileBasedStore(MemoryStore):
    """文件存储（用于长期记忆和情景记忆）"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._index_file = self.storage_path / "index.json"
        self._index: Dict[str, str] = self._load_index()
    
    def _load_index(self) -> Dict[str, str]:
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("加载记忆索引文件失败，使用空索引: %s", e)
                return {}
        return {}
    
    def _save_index(self) -> None:
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)
    
    def _get_file_path(self, memory_id: str) -> Path:
        return self.storage_path / f"{memory_id}.json"
    
    async def add(self, item: MemoryItem) -> None:
        file_path = self._get_file_path(item.memory_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(item.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新索引
        self._index[item.memory_id] = item.content[:100]
        self._save_index()
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        file_path = self._get_file_path(memory_id)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            item = MemoryItem.from_dict(data)
            
            # 更新访问信息
            item.last_accessed = datetime.now().isoformat()
            item.access_count += 1
            await self.add(item)  # 保存更新
            
            return item
        except Exception as e:
            logger.error("加载记忆失败: %s", e)
            return None
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        query_lower = query.lower()
        matches = []
        
        for memory_id, summary in self._index.items():
            if query_lower in summary.lower():
                item = await self.get(memory_id)
                if item:
                    matches.append(item)
        
        matches.sort(
            key=lambda x: (x.importance, x.access_count),
            reverse=True
        )
        return matches[:limit]
    
    async def delete(self, memory_id: str) -> bool:
        file_path = self._get_file_path(memory_id)
        if file_path.exists():
            file_path.unlink()
            self._index.pop(memory_id, None)
            self._save_index()
            return True
        return False
    
    async def clear(self) -> int:
        count = 0
        for file in self.storage_path.glob("*.json"):
            if file.name != "index.json":
                file.unlink()
                count += 1
        self._index.clear()
        self._save_index()
        return count


class ShortTermMemory:
    """短期记忆管理器 - 管理当前会话的上下文"""
    
    def __init__(self, max_items: int = 50):
        self._store = InMemoryStore(max_size=max_items)
        self._conversation_history: List[Dict[str, str]] = []
        self._current_context: Dict[str, Any] = {}
    
    async def add_message(self, role: str, content: str) -> None:
        """添加对话消息"""
        self._conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保留最近的消息
        if len(self._conversation_history) > 100:
            self._conversation_history = self._conversation_history[-100:]
    
    async def add_context(self, key: str, value: Any, importance: float = 0.5) -> None:
        """添加上下文信息"""
        self._current_context[key] = value
        
        memory_id = hashlib.md5(f"{key}:{str(value)[:50]}".encode()).hexdigest()[:16]
        await self._store.add(MemoryItem(
            memory_id=memory_id,
            content=f"{key}: {str(value)}",
            memory_type="short_term",
            importance=importance,
            metadata={"key": key}
        ))
    
    def get_context(self, key: str) -> Any:
        """获取上下文信息"""
        return self._current_context.get(key)
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取最近的对话消息"""
        return self._conversation_history[-limit:]
    
    def get_summary(self) -> str:
        """获取当前会话摘要"""
        context_summary = "\n".join([
            f"- {k}: {str(v)[:100]}" 
            for k, v in self._current_context.items()
        ])
        return f"当前上下文:\n{context_summary}"
    
    async def clear(self) -> None:
        """清空短期记忆"""
        self._conversation_history.clear()
        self._current_context.clear()
        await self._store.clear()


class LongTermMemory:
    """长期记忆管理器 - 管理跨会话的知识"""
    
    def __init__(self, storage_path: str = "./data/memory/long_term"):
        self._store = FileBasedStore(storage_path)
    
    async def remember(
        self, 
        content: str, 
        category: str = "general",
        importance: float = 0.5,
        metadata: Dict[str, Any] = None
    ) -> str:
        """记住一条信息"""
        memory_id = hashlib.md5(
            f"{content}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        item = MemoryItem(
            memory_id=memory_id,
            content=content,
            memory_type="long_term",
            importance=importance,
            metadata={
                "category": category,
                **(metadata or {})
            }
        )
        
        await self._store.add(item)
        logger.info("长期记忆添加: %s", memory_id)
        return memory_id
    
    async def recall(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """回忆相关信息"""
        return await self._store.search(query, limit)
    
    async def forget(self, memory_id: str) -> bool:
        """遗忘一条记忆"""
        return await self._store.delete(memory_id)


class EpisodicMemory:
    """情景记忆管理器 - 存储建模经验"""
    
    def __init__(self, storage_path: str = "./data/memory/episodic"):
        self._store = FileBasedStore(storage_path)
    
    async def save_episode(
        self,
        problem_type: str,
        problem_description: str,
        solution_approach: str,
        models_used: List[str],
        outcome: str,  # success, partial, failed
        lessons_learned: List[str],
        metadata: Dict[str, Any] = None
    ) -> str:
        """保存一次建模经历"""
        episode_id = hashlib.md5(
            f"{problem_description[:100]}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        content = f"""问题类型: {problem_type}
问题描述: {problem_description}
解决方案: {solution_approach}
使用模型: {', '.join(models_used)}
结果: {outcome}
经验教训: {'; '.join(lessons_learned)}"""
        
        importance = 0.8 if outcome == "success" else 0.5
        
        item = MemoryItem(
            memory_id=episode_id,
            content=content,
            memory_type="episodic",
            importance=importance,
            metadata={
                "problem_type": problem_type,
                "models_used": models_used,
                "outcome": outcome,
                "lessons_learned": lessons_learned,
                **(metadata or {})
            }
        )
        
        await self._store.add(item)
        logger.info("情景记忆保存: %s", episode_id)
        return episode_id
    
    async def find_similar_episodes(
        self, 
        problem_description: str, 
        limit: int = 3
    ) -> List[MemoryItem]:
        """查找类似的建模经历"""
        return await self._store.search(problem_description, limit)
    
    async def get_lessons_for_problem_type(
        self, 
        problem_type: str
    ) -> List[str]:
        """获取特定问题类型的经验教训"""
        episodes = await self._store.search(problem_type, 10)
        
        lessons = []
        for ep in episodes:
            if ep.metadata.get("lessons_learned"):
                lessons.extend(ep.metadata["lessons_learned"])
        
        return list(set(lessons))  # 去重


class MemoryManager:
    """
    记忆管理器 - 统一管理所有类型的记忆
    
    整合短期、长期和情景记忆，提供统一的接口
    """
    
    def __init__(
        self,
        task_id: str,
        storage_base_path: str = "./data/memory"
    ):
        self.task_id = task_id
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(f"{storage_base_path}/long_term")
        self.episodic = EpisodicMemory(f"{storage_base_path}/episodic")
    
    async def remember_context(self, key: str, value: Any, persist: bool = False) -> None:
        """记住上下文信息"""
        await self.short_term.add_context(key, value)
        
        if persist:
            await self.long_term.remember(
                f"{key}: {str(value)}",
                category="context",
                importance=0.6
            )
    
    async def recall_relevant(self, query: str, include_episodes: bool = True) -> Dict[str, List]:
        """回忆所有相关信息"""
        result = {
            "short_term": await self.short_term._store.search(query, 5),
            "long_term": await self.long_term.recall(query, 5)
        }
        
        if include_episodes:
            result["episodes"] = await self.episodic.find_similar_episodes(query, 3)
        
        return result
    
    async def save_modeling_experience(
        self,
        problem_type: str,
        problem_description: str,
        solution_approach: str,
        models_used: List[str],
        outcome: str,
        lessons: List[str]
    ) -> str:
        """保存建模经验"""
        return await self.episodic.save_episode(
            problem_type=problem_type,
            problem_description=problem_description,
            solution_approach=solution_approach,
            models_used=models_used,
            outcome=outcome,
            lessons_learned=lessons
        )
    
    async def get_experience_for_problem(
        self, 
        problem_type: str, 
        problem_description: str
    ) -> Dict[str, Any]:
        """获取针对特定问题的经验"""
        similar_episodes = await self.episodic.find_similar_episodes(
            problem_description, 5
        )
        lessons = await self.episodic.get_lessons_for_problem_type(problem_type)
        
        return {
            "similar_cases": [ep.to_dict() for ep in similar_episodes],
            "lessons_learned": lessons,
            "suggested_models": self._extract_successful_models(similar_episodes)
        }
    
    def _extract_successful_models(self, episodes: List[MemoryItem]) -> List[str]:
        """从成功案例中提取推荐模型"""
        models = []
        for ep in episodes:
            if ep.metadata.get("outcome") == "success":
                models.extend(ep.metadata.get("models_used", []))
        
        # 统计频率
        from collections import Counter
        return [m for m, _ in Counter(models).most_common(5)]
    
    async def clear_session(self) -> None:
        """清空当前会话记忆"""
        await self.short_term.clear()
    
    def get_session_summary(self) -> str:
        """获取会话摘要"""
        return self.short_term.get_summary()


def create_memory_manager(
    task_id: str,
    storage_path: str = "./data/memory"
) -> MemoryManager:
    """
    创建记忆管理器
    
    Args:
        task_id: 任务ID
        storage_path: 存储路径
        
    Returns:
        MemoryManager实例
    """
    return MemoryManager(task_id, storage_path)
