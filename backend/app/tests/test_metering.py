"""
计量模块单元测试 - Metering Module Tests

测试内容：
1. 成本计算器
2. Token计量器
3. 配额管理器
"""


import pytest

from app.core.metering.cost_calculator import (
    MODEL_PRICING,
    CostCalculator,
    CostResult,
)
from app.core.metering.quota_manager import (
    QuotaConfig,
    QuotaExceededError,
    QuotaManager,
    QuotaPeriod,
    QuotaType,
)
from app.core.metering.token_meter import (
    CostLimitExceededError,
    TokenLimitExceededError,
    TokenMeter,
    get_task_meter,
    remove_task_meter,
)


# ============= CostCalculator Tests =============

class TestCostCalculator:
    """成本计算器测试"""
    
    def test_calculate_known_model(self):
        """测试已知模型成本计算"""
        calc = CostCalculator()
        
        result = calc.calculate("deepseek-chat", 1000, 500)
        
        assert isinstance(result, CostResult)
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.total_tokens == 1500
        
        # deepseek-chat: input 0.14, output 0.28 per 1M
        expected_input_cost = (1000 / 1_000_000) * 0.14
        expected_output_cost = (500 / 1_000_000) * 0.28
        
        assert abs(result.input_cost_usd - expected_input_cost) < 0.0001
        assert abs(result.output_cost_usd - expected_output_cost) < 0.0001
    
    def test_calculate_unknown_model(self):
        """测试未知模型使用默认定价"""
        calc = CostCalculator()
        
        result = calc.calculate("unknown-model-xyz", 1000, 1000)
        
        # 默认定价: input 1.0, output 2.0
        expected_cost = (1000 / 1_000_000) * 1.0 + (1000 / 1_000_000) * 2.0
        
        assert abs(result.total_cost_usd - expected_cost) < 0.0001
    
    def test_calculate_gpt4o(self):
        """测试GPT-4o成本计算"""
        calc = CostCalculator()
        
        result = calc.calculate("gpt-4o", 10000, 5000)
        
        # gpt-4o: input 2.5, output 10.0 per 1M
        expected = (10000 / 1_000_000) * 2.5 + (5000 / 1_000_000) * 10.0
        
        assert abs(result.total_cost_usd - expected) < 0.0001
    
    def test_cost_to_cny(self):
        """测试美元转人民币"""
        calc = CostCalculator()
        
        result = calc.calculate("gpt-4o", 1_000_000, 0)  # $2.5
        
        assert abs(result.total_cost_cny - 2.5 * 7.2) < 0.01
    
    def test_estimate_cost(self):
        """测试成本预估"""
        calc = CostCalculator()
        
        result = calc.estimate_cost(
            "deepseek-chat",
            prompt_chars=3500,  # ~1000 tokens
            expected_output_chars=1750,  # ~500 tokens
            chars_per_token=3.5,
        )
        
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
    
    def test_add_model_pricing(self):
        """测试添加自定义模型定价"""
        calc = CostCalculator()
        
        calc.add_model_pricing("custom-model", 0.5, 1.0)
        
        result = calc.calculate("custom-model", 1_000_000, 1_000_000)
        expected = 0.5 + 1.0
        
        assert abs(result.total_cost_usd - expected) < 0.0001
    
    def test_list_models(self):
        """测试列出所有模型"""
        calc = CostCalculator()
        
        models = calc.list_models()
        
        assert "deepseek-chat" in models
        assert "gpt-4o" in models
        assert "claude-3-5-sonnet" in models
    
    def test_prefix_matching(self):
        """测试前缀匹配"""
        calc = CostCalculator()
        
        # gpt-4o-2024-01-01 应该匹配 gpt-4o
        pricing = calc.get_pricing("gpt-4o-2024-01-01")
        
        assert pricing == MODEL_PRICING["gpt-4o"]


# ============= TokenMeter Tests =============

class TestTokenMeter:
    """Token计量器测试"""
    
    @pytest.mark.asyncio
    async def test_record_usage(self):
        """测试记录使用量"""
        meter = TokenMeter("test-task-1", persist_to_redis=False)
        
        record = await meter.record("coder", "deepseek-chat", 1000, 500)
        
        assert record.task_id == "test-task-1"
        assert record.agent_type == "coder"
        assert record.model == "deepseek-chat"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.cost_usd > 0
    
    @pytest.mark.asyncio
    async def test_stats_accumulation(self):
        """测试统计累计"""
        meter = TokenMeter("test-task-2", persist_to_redis=False)
        
        await meter.record("coordinator", "deepseek-chat", 1000, 500)
        await meter.record("modeler", "deepseek-chat", 2000, 1000)
        
        stats = meter.get_stats()
        
        assert stats.total_input_tokens == 3000
        assert stats.total_output_tokens == 1500
        assert stats.total_tokens == 4500
        assert stats.call_count == 2
    
    @pytest.mark.asyncio
    async def test_by_agent_stats(self):
        """测试按Agent统计"""
        meter = TokenMeter("test-task-3", persist_to_redis=False)
        
        await meter.record("coder", "deepseek-chat", 1000, 500)
        await meter.record("coder", "deepseek-chat", 1000, 500)
        await meter.record("writer", "gpt-4o", 500, 200)
        
        stats = meter.get_stats()
        
        assert "coder" in stats.by_agent
        assert stats.by_agent["coder"]["calls"] == 2
        assert "writer" in stats.by_agent
        assert stats.by_agent["writer"]["calls"] == 1
    
    @pytest.mark.asyncio
    async def test_cost_limit_exceeded(self):
        """测试成本限额超出"""
        meter = TokenMeter("test-task-4", max_cost_usd=0.001, persist_to_redis=False)
        
        with pytest.raises(CostLimitExceededError):
            # 使用高价模型产生足够成本
            await meter.record("coder", "gpt-4o", 10000, 10000)
    
    @pytest.mark.asyncio
    async def test_token_limit_exceeded(self):
        """测试Token限额超出"""
        meter = TokenMeter("test-task-5", max_tokens=1000, persist_to_redis=False)
        
        with pytest.raises(TokenLimitExceededError):
            await meter.record("coder", "deepseek-chat", 600, 500)
    
    @pytest.mark.asyncio
    async def test_get_remaining_budget(self):
        """测试剩余预算计算"""
        meter = TokenMeter("test-task-6", max_cost_usd=1.0, persist_to_redis=False)
        
        # 记录一些使用
        await meter.record("coder", "deepseek-chat", 100000, 50000)
        
        remaining = meter.get_remaining_budget()
        
        assert remaining < 1.0
        assert remaining > 0
    
    @pytest.mark.asyncio
    async def test_get_summary(self):
        """测试获取摘要"""
        meter = TokenMeter("test-task-7", persist_to_redis=False)
        
        await meter.record("coordinator", "deepseek-chat", 1000, 500)
        
        summary = meter.get_summary()
        
        assert summary["task_id"] == "test-task-7"
        assert summary["total_tokens"] == 1500
        assert "total_cost_usd" in summary
        assert "total_cost_cny" in summary
        assert "by_agent" in summary


class TestTokenMeterFactory:
    """Token计量器工厂测试"""
    
    def test_get_task_meter_singleton(self):
        """测试单例获取"""
        meter1 = get_task_meter("singleton-task")
        meter2 = get_task_meter("singleton-task")
        
        assert meter1 is meter2
        
        # 清理
        remove_task_meter("singleton-task")
    
    def test_remove_task_meter(self):
        """测试移除计量器"""
        meter1 = get_task_meter("removable-task")
        remove_task_meter("removable-task")
        meter2 = get_task_meter("removable-task")
        
        assert meter1 is not meter2


# ============= QuotaManager Tests =============

class TestQuotaManager:
    """配额管理器测试"""
    
    def test_free_plan_limits(self):
        """测试免费计划限制"""
        manager = QuotaManager("user-1", plan="free")
        
        usage = manager.check_quota("task")
        
        assert usage.limit == 5  # 免费计划5次/月
    
    def test_pro_plan_limits(self):
        """测试Pro计划限制"""
        manager = QuotaManager("user-2", plan="pro")
        
        usage = manager.check_quota("task")
        
        assert usage.limit == 50
    
    def test_check_and_deduct(self):
        """测试检查并扣减"""
        manager = QuotaManager("user-3", plan="pro")
        
        usage = manager.check_and_deduct("token", 1000)
        
        assert usage.used == 1000
    
    def test_quota_exceeded(self):
        """测试配额超出"""
        manager = QuotaManager("user-4", plan="free")
        
        # 免费计划Token限制 100,000
        with pytest.raises(QuotaExceededError):
            manager.check_and_deduct("token", 150_000)
    
    def test_quota_warning(self):
        """测试配额警告"""
        manager = QuotaManager("user-5", plan="free")
        
        # 使用85%，应该触发警告
        usage = manager.check_and_deduct("token", 85_000)
        
        assert usage.is_warning
    
    def test_add_quota(self):
        """测试添加配额"""
        manager = QuotaManager("user-6", plan="free")
        
        original_limit = manager.check_quota("task").limit
        manager.add_quota("task", 10)
        new_limit = manager.check_quota("task").limit
        
        assert new_limit == original_limit + 10
    
    def test_reset_usage(self):
        """测试重置使用量"""
        manager = QuotaManager("user-7", plan="pro")
        
        manager.check_and_deduct("token", 10000)
        assert manager.check_quota("token").used == 10000
        
        manager.reset_usage("token")
        assert manager.check_quota("token").used == 0
    
    def test_get_all_usage(self):
        """测试获取所有配额使用情况"""
        manager = QuotaManager("user-8", plan="pro")
        
        all_usage = manager.get_all_usage()
        
        assert "task" in all_usage
        assert "token" in all_usage
        assert "cost" in all_usage
    
    def test_get_summary(self):
        """测试获取摘要"""
        manager = QuotaManager("user-9", plan="team")
        
        summary = manager.get_summary()
        
        assert summary["user_id"] == "user-9"
        assert summary["plan"] == "team"
        assert "quotas" in summary
    
    def test_enterprise_unlimited(self):
        """测试企业版无限制"""
        manager = QuotaManager("user-10", plan="enterprise")
        
        # 企业版应该不会超限
        usage = manager.check_and_deduct("token", 1_000_000_000)
        
        assert not usage.is_exceeded
    
    def test_custom_quotas(self):
        """测试自定义配额"""
        custom = {
            "special": QuotaConfig(QuotaType.API_CALL, QuotaPeriod.DAILY, 100)
        }
        manager = QuotaManager("user-11", plan="free", custom_quotas=custom)
        
        usage = manager.check_quota("special")
        
        assert usage.limit == 100
