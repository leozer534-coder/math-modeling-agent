
import pytest

from app.core.a2a.handoff_manager import (
    MODEL_TIER_CONFIG,
    A2AHandoffManager,
    ErrorPattern,
    HandoffDecision,
    HandoffResult,
    HandoffTrigger,
    ModelTier,
)


class TestModelTier:
    
    def test_all_tiers_defined(self):
        expected_tiers = [
            "tier_1_fast",
            "tier_2_standard",
            "tier_3_advanced",
            "tier_4_premium",
        ]
        
        for tier in expected_tiers:
            assert tier in [t.value for t in ModelTier]
    
    def test_tier_config_exists_for_all_tiers(self):
        for tier in ModelTier:
            assert tier in MODEL_TIER_CONFIG
            config = MODEL_TIER_CONFIG[tier]
            assert "models" in config
            assert "max_errors_before_escalate" in config
            assert "cost_multiplier" in config


class TestHandoffTrigger:
    
    def test_all_triggers_defined(self):
        expected_triggers = [
            "repeated_errors",
            "complexity_detected",
            "timeout_exceeded",
            "user_requested",
            "quality_threshold",
            "stuck_in_loop",
        ]
        
        for trigger in expected_triggers:
            assert trigger in [t.value for t in HandoffTrigger]


class TestHandoffDecision:
    
    def test_all_decisions_defined(self):
        expected_decisions = [
            "escalate",
            "retry_current",
            "simplify_task",
            "abort",
            "wait_for_user",
        ]
        
        for decision in expected_decisions:
            assert decision in [d.value for d in HandoffDecision]


class TestA2AHandoffManager:
    
    @pytest.fixture
    def handoff_manager(self):
        return A2AHandoffManager(
            task_id="test_task_123",
            initial_tier=ModelTier.TIER_2_STANDARD,
            auto_escalate=True,
            max_escalations=2,
        )
    
    @pytest.fixture
    def non_auto_manager(self):
        return A2AHandoffManager(
            task_id="test_task_456",
            initial_tier=ModelTier.TIER_1_FAST,
            auto_escalate=False,
            max_escalations=2,
        )
    
    def test_initialization(self, handoff_manager):
        assert handoff_manager.current_tier == ModelTier.TIER_2_STANDARD
        assert handoff_manager._escalation_count == 0
        assert handoff_manager._consecutive_errors == 0
    
    def test_hash_error_consistency(self, handoff_manager):
        error1 = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        error2 = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        
        hash1 = handoff_manager._hash_error(error1)
        hash2 = handoff_manager._hash_error(error2)
        
        assert hash1 == hash2
    
    def test_hash_error_ignores_numbers(self, handoff_manager):
        error1 = "IndexError: list index 5 out of range"
        error2 = "IndexError: list index 10 out of range"
        
        hash1 = handoff_manager._hash_error(error1)
        hash2 = handoff_manager._hash_error(error2)
        
        assert hash1 == hash2
    
    def test_classify_error_syntax(self, handoff_manager):
        error = "SyntaxError: invalid syntax"
        assert handoff_manager._classify_error(error) == "syntax_error"
    
    def test_classify_error_type(self, handoff_manager):
        error = "TypeError: expected str, got int"
        assert handoff_manager._classify_error(error) == "type_error"
    
    def test_classify_error_name(self, handoff_manager):
        error = "NameError: name 'x' is not defined"
        assert handoff_manager._classify_error(error) == "name_error"
    
    def test_classify_error_memory(self, handoff_manager):
        error = "MemoryError: unable to allocate array"
        assert handoff_manager._classify_error(error) == "memory_error"
    
    def test_classify_error_timeout(self, handoff_manager):
        error = "TimeoutError: operation timed out"
        assert handoff_manager._classify_error(error) == "timeout_error"
    
    def test_classify_error_unknown(self, handoff_manager):
        error = "SomeUnknownError: something went wrong"
        assert handoff_manager._classify_error(error) == "unknown_error"
    
    def test_record_error_creates_pattern(self, handoff_manager):
        error = "TestError: test message"
        pattern = handoff_manager.record_error(error)
        
        assert isinstance(pattern, ErrorPattern)
        assert pattern.occurrence_count == 1
        assert handoff_manager._consecutive_errors == 1
    
    def test_record_error_increments_count(self, handoff_manager):
        error = "TestError: test message"
        
        handoff_manager.record_error(error)
        pattern = handoff_manager.record_error(error)
        
        assert pattern.occurrence_count == 2
        assert handoff_manager._same_error_streak == 2
    
    def test_record_success_resets_counters(self, handoff_manager):
        handoff_manager.record_error("TestError: test message")
        handoff_manager.record_error("TestError: test message")
        
        assert handoff_manager._consecutive_errors == 2
        
        handoff_manager.record_success()
        
        assert handoff_manager._consecutive_errors == 0
        assert handoff_manager._same_error_streak == 0
    
    def test_get_next_tier_from_standard(self, handoff_manager):
        next_tier = handoff_manager._get_next_tier()
        assert next_tier == ModelTier.TIER_3_ADVANCED
    
    def test_get_next_tier_from_premium_returns_none(self, handoff_manager):
        handoff_manager.current_tier = ModelTier.TIER_4_PREMIUM
        next_tier = handoff_manager._get_next_tier()
        assert next_tier is None
    
    def test_get_current_tier(self, handoff_manager):
        assert handoff_manager.get_current_tier() == ModelTier.TIER_2_STANDARD
    
    def test_get_escalation_count(self, handoff_manager):
        assert handoff_manager.get_escalation_count() == 0
    
    def test_get_error_summary(self, handoff_manager):
        handoff_manager.record_error("TypeError: test")
        handoff_manager.record_error("SyntaxError: test")
        
        summary = handoff_manager.get_error_summary()
        
        assert summary["current_tier"] == "tier_2_standard"
        assert summary["consecutive_errors"] == 2
        assert summary["unique_error_patterns"] == 2
    
    def test_get_handoff_history_empty(self, handoff_manager):
        history = handoff_manager.get_handoff_history()
        assert history == []
    
    @pytest.mark.asyncio
    async def test_evaluate_handoff_retry_current(self, handoff_manager):
        result = await handoff_manager.evaluate_handoff(
            error_message="Minor error",
            current_retry_count=0,
        )
        
        assert result.decision == HandoffDecision.RETRY_CURRENT
    
    @pytest.mark.asyncio
    async def test_non_auto_escalate_waits_for_user(self, non_auto_manager):
        for _ in range(5):
            non_auto_manager.record_error("SameError: repeated")
        
        result = await non_auto_manager.evaluate_handoff(
            error_message="SameError: repeated",
            current_retry_count=5,
        )
        
        assert result.decision == HandoffDecision.WAIT_FOR_USER


class TestHandoffResult:
    
    def test_handoff_result_creation(self):
        result = HandoffResult(
            decision=HandoffDecision.ESCALATE,
            from_tier=ModelTier.TIER_2_STANDARD,
            to_tier=ModelTier.TIER_3_ADVANCED,
            reason="多次重复错误",
            context_preserved=True,
            retry_count_reset=True,
        )
        
        assert result.decision == HandoffDecision.ESCALATE
        assert result.from_tier == ModelTier.TIER_2_STANDARD
        assert result.to_tier == ModelTier.TIER_3_ADVANCED
        assert result.context_preserved is True


class TestErrorPattern:
    
    def test_error_pattern_creation(self):
        pattern = ErrorPattern(
            error_hash="abc123",
            error_type="syntax_error",
            sample_message="SyntaxError: invalid syntax",
        )
        
        assert pattern.error_hash == "abc123"
        assert pattern.error_type == "syntax_error"
        assert pattern.occurrence_count == 1
