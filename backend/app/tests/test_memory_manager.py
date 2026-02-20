"""
记忆管理器单元测试
测试短期记忆、长期记忆、情景记忆的核心功能
"""
import shutil
import tempfile

import pytest

from app.core.memory.memory_manager import (
    EpisodicMemory,
    FileBasedStore,
    InMemoryStore,
    LongTermMemory,
    MemoryItem,
    MemoryManager,
    ShortTermMemory,
    create_memory_manager,
)


class TestMemoryItem:
    """测试记忆项"""

    def test_create_memory_item(self):
        """测试创建记忆项"""
        item = MemoryItem(
            memory_id="test_001",
            content="测试内容",
            memory_type="short_term",
            importance=0.8,
        )
        assert item.memory_id == "test_001"
        assert item.content == "测试内容"
        assert item.memory_type == "short_term"
        assert item.importance == 0.8
        assert item.access_count == 0

    def test_memory_item_to_dict(self):
        """测试记忆项转字典"""
        item = MemoryItem(
            memory_id="test_002",
            content="测试内容",
            memory_type="long_term",
        )
        data = item.to_dict()
        assert data["memory_id"] == "test_002"
        assert data["content"] == "测试内容"
        assert "created_at" in data

    def test_memory_item_from_dict(self):
        """测试从字典创建记忆项"""
        data = {
            "memory_id": "test_003",
            "content": "测试内容",
            "memory_type": "episodic",
            "importance": 0.9,
            "created_at": "2026-01-01T00:00:00",
            "last_accessed": "2026-01-01T00:00:00",
            "access_count": 5,
            "metadata": {"key": "value"},
        }
        item = MemoryItem.from_dict(data)
        assert item.memory_id == "test_003"
        assert item.access_count == 5


class TestInMemoryStore:
    """测试内存存储"""

    @pytest.fixture
    def store(self):
        return InMemoryStore(max_size=10)

    @pytest.mark.asyncio
    async def test_add_and_get(self, store):
        """测试添加和获取记忆"""
        item = MemoryItem(
            memory_id="mem_001",
            content="记忆内容",
            memory_type="short_term",
        )
        await store.add(item)
        
        retrieved = await store.get("mem_001")
        assert retrieved is not None
        assert retrieved.content == "记忆内容"
        assert retrieved.access_count == 1  # 访问计数增加

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        """测试获取不存在的记忆"""
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self, store):
        """测试搜索功能"""
        items = [
            MemoryItem(memory_id=f"mem_{i}", content=f"数学建模问题{i}", memory_type="short_term")
            for i in range(5)
        ]
        for item in items:
            await store.add(item)
        
        results = await store.search("数学建模", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_delete(self, store):
        """测试删除记忆"""
        item = MemoryItem(
            memory_id="mem_del",
            content="待删除",
            memory_type="short_term",
        )
        await store.add(item)
        
        success = await store.delete("mem_del")
        assert success is True
        
        result = await store.get("mem_del")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self, store):
        """测试清空存储"""
        for i in range(5):
            item = MemoryItem(
                memory_id=f"clear_{i}",
                content=f"内容{i}",
                memory_type="short_term",
            )
            await store.add(item)
        
        count = await store.clear()
        assert count == 5
        assert len(store.get_all()) == 0

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        """测试超过最大容量时的驱逐策略"""
        store = InMemoryStore(max_size=3)
        
        for i in range(5):
            item = MemoryItem(
                memory_id=f"evict_{i}",
                content=f"内容{i}",
                memory_type="short_term",
            )
            await store.add(item)
        
        # 应该只保留3个
        assert len(store.get_all()) == 3


class TestFileBasedStore:
    """测试文件存储"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def store(self, temp_dir):
        return FileBasedStore(temp_dir)

    @pytest.mark.asyncio
    async def test_add_and_get(self, store):
        """测试文件存储的添加和获取"""
        item = MemoryItem(
            memory_id="file_001",
            content="持久化测试内容",
            memory_type="long_term",
        )
        await store.add(item)
        
        retrieved = await store.get("file_001")
        assert retrieved is not None
        assert retrieved.content == "持久化测试内容"

    @pytest.mark.asyncio
    async def test_persistence(self, temp_dir):
        """测试持久化"""
        # 第一个存储实例
        store1 = FileBasedStore(temp_dir)
        item = MemoryItem(
            memory_id="persist_001",
            content="持久化数据",
            memory_type="long_term",
        )
        await store1.add(item)
        
        # 新建存储实例，数据应该还在
        store2 = FileBasedStore(temp_dir)
        retrieved = await store2.get("persist_001")
        assert retrieved is not None
        assert retrieved.content == "持久化数据"


class TestShortTermMemory:
    """测试短期记忆管理器"""

    @pytest.fixture
    def stm(self):
        return ShortTermMemory(max_items=50)

    @pytest.mark.asyncio
    async def test_add_message(self, stm):
        """测试添加对话消息"""
        await stm.add_message("user", "你好")
        await stm.add_message("assistant", "您好！有什么可以帮您？")
        
        messages = stm.get_recent_messages(10)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_add_context(self, stm):
        """测试添加上下文"""
        await stm.add_context("problem_type", "optimization", importance=0.9)
        
        value = stm.get_context("problem_type")
        assert value == "optimization"

    def test_get_summary(self, stm):
        """测试获取会话摘要"""
        summary = stm.get_summary()
        assert "当前上下文" in summary

    @pytest.mark.asyncio
    async def test_clear(self, stm):
        """测试清空短期记忆"""
        await stm.add_message("user", "测试消息")
        await stm.add_context("key", "value")
        
        await stm.clear()
        
        messages = stm.get_recent_messages()
        assert len(messages) == 0


class TestLongTermMemory:
    """测试长期记忆管理器"""

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def ltm(self, temp_dir):
        return LongTermMemory(storage_path=temp_dir)

    @pytest.mark.asyncio
    async def test_remember_and_recall(self, ltm):
        """测试记忆和回忆"""
        memory_id = await ltm.remember(
            "线性规划是解决优化问题的重要方法",
            category="model_knowledge",
            importance=0.8,
        )
        assert memory_id is not None
        
        results = await ltm.recall("线性规划", limit=5)
        assert len(results) >= 1
        assert "线性规划" in results[0].content

    @pytest.mark.asyncio
    async def test_forget(self, ltm):
        """测试遗忘"""
        memory_id = await ltm.remember("临时知识", category="temp")
        
        success = await ltm.forget(memory_id)
        assert success is True
        
        results = await ltm.recall("临时知识")
        assert len(results) == 0


class TestEpisodicMemory:
    """测试情景记忆管理器"""

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def episodic(self, temp_dir):
        return EpisodicMemory(storage_path=temp_dir)

    @pytest.mark.asyncio
    async def test_save_and_find_episode(self, episodic):
        """测试保存和查找情景"""
        episode_id = await episodic.save_episode(
            problem_type="optimization",
            problem_description="某工厂生产调度问题",
            solution_approach="使用整数规划模型",
            models_used=["整数规划", "动态规划"],
            outcome="success",
            lessons_learned=["需要考虑约束条件的完整性"],
        )
        assert episode_id is not None

        # FileBasedStore.search 基于索引（content 前 100 字符）进行子串匹配，
        # 搜索词必须是索引内容的连续子串才能命中
        similar = await episodic.find_similar_episodes("工厂", limit=3)
        assert len(similar) >= 1

    @pytest.mark.asyncio
    async def test_get_lessons(self, episodic):
        """测试获取经验教训"""
        await episodic.save_episode(
            problem_type="prediction",
            problem_description="销量预测",
            solution_approach="时间序列分析",
            models_used=["ARIMA"],
            outcome="success",
            lessons_learned=["数据平稳性很重要", "季节性因素需要考虑"],
        )
        
        lessons = await episodic.get_lessons_for_problem_type("prediction")
        assert len(lessons) >= 1


class TestMemoryManager:
    """测试记忆管理器"""

    @pytest.fixture
    def temp_dir(self):
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        return MemoryManager(task_id="test_task", storage_base_path=temp_dir)

    @pytest.mark.asyncio
    async def test_remember_context(self, manager):
        """测试记忆上下文"""
        await manager.remember_context("problem", "优化问题", persist=False)
        
        summary = manager.get_session_summary()
        assert "problem" in summary

    @pytest.mark.asyncio
    async def test_recall_relevant(self, manager):
        """测试回忆相关信息"""
        await manager.short_term.add_context("model", "线性规划")
        
        results = await manager.recall_relevant("规划", include_episodes=True)
        assert "short_term" in results
        assert "long_term" in results
        assert "episodes" in results

    @pytest.mark.asyncio
    async def test_save_modeling_experience(self, manager):
        """测试保存建模经验"""
        episode_id = await manager.save_modeling_experience(
            problem_type="evaluation",
            problem_description="多指标评价问题",
            solution_approach="TOPSIS综合评价",
            models_used=["TOPSIS", "熵权法"],
            outcome="success",
            lessons=["指标归一化方法很关键"],
        )
        assert episode_id is not None

    @pytest.mark.asyncio
    async def test_get_experience_for_problem(self, manager):
        """测试获取问题相关经验"""
        # 先保存一些经验
        await manager.save_modeling_experience(
            problem_type="optimization",
            problem_description="车辆路径规划",
            solution_approach="遗传算法",
            models_used=["遗传算法", "模拟退火"],
            outcome="success",
            lessons=["种群大小影响收敛速度"],
        )
        
        experience = await manager.get_experience_for_problem(
            "optimization", "路径优化问题"
        )
        assert "similar_cases" in experience
        assert "lessons_learned" in experience
        assert "suggested_models" in experience

    @pytest.mark.asyncio
    async def test_clear_session(self, manager):
        """测试清空会话"""
        await manager.short_term.add_message("user", "测试")
        await manager.clear_session()
        
        messages = manager.short_term.get_recent_messages()
        assert len(messages) == 0


class TestCreateMemoryManager:
    """测试创建记忆管理器工厂函数"""

    def test_create_memory_manager(self):
        """测试工厂函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = create_memory_manager("task_123", storage_path=temp_dir)
            assert manager is not None
            assert manager.task_id == "task_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
