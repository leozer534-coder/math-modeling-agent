import asyncio

import pytest

from app.core.hil.hil_manager import (
    HILDecision,
    HILEvent,
    HILEventType,
    HILManager,
    HILOption,
    HILResponse,
)


class TestHILManager:
    
    @pytest.fixture
    def hil_manager(self):
        return HILManager(
            task_id="test_task_123",
            auto_approve=False,
            default_timeout=60,
        )
    
    @pytest.fixture
    def auto_approve_manager(self):
        return HILManager(
            task_id="test_task_456",
            auto_approve=True,
            default_timeout=60,
        )
    
    def test_hil_event_to_dict(self):
        event = HILEvent(
            event_id="evt_001",
            event_type=HILEventType.MODEL_SELECTION,
            title="选择模型",
            description="请选择一个模型",
            phase="modeling",
            options=[
                HILOption(id="opt1", label="模型A", description="描述A", is_default=True),
                HILOption(id="opt2", label="模型B", description="描述B"),
            ],
            timeout_seconds=120,
        )
        
        result = event.to_dict()
        
        assert result["event_id"] == "evt_001"
        assert result["event_type"] == "model_selection"
        assert result["title"] == "选择模型"
        assert len(result["options"]) == 2
        assert result["options"][0]["is_default"] is True
    
    def test_hil_response_from_dict(self):
        data = {
            "event_id": "evt_002",
            "decision": "approve",
            "selected_option_id": "opt1",
            "user_comment": "看起来不错",
        }
        
        response = HILResponse.from_dict(data)
        
        assert response.event_id == "evt_002"
        assert response.decision == HILDecision.APPROVE
        assert response.selected_option_id == "opt1"
        assert response.user_comment == "看起来不错"
    
    def test_hil_response_timeout(self):
        response = HILResponse.timeout_response("evt_003")
        
        assert response.event_id == "evt_003"
        assert response.decision == HILDecision.TIMEOUT
    
    def test_hil_response_default_approve(self):
        response = HILResponse.default_approve("evt_004")
        
        assert response.event_id == "evt_004"
        assert response.decision == HILDecision.APPROVE
    
    @pytest.mark.asyncio
    async def test_auto_approve_mode(self, auto_approve_manager):
        response = await auto_approve_manager.request_decision(
            event_type=HILEventType.PLAN_REVIEW,
            title="方案审核",
            description="请审核方案",
            phase="planning",
        )
        
        assert response.decision == HILDecision.APPROVE
    
    @pytest.mark.asyncio
    async def test_submit_response(self, hil_manager):
        event_id = "evt_005"
        
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        hil_manager._response_futures[event_id] = future
        
        response = HILResponse(
            event_id=event_id,
            decision=HILDecision.APPROVE,
            selected_option_id="opt1",
        )
        
        await hil_manager.submit_response(event_id, response)
        
        assert event_id in hil_manager._responses
        assert hil_manager._responses[event_id].decision == HILDecision.APPROVE
    
    def test_get_event_history_empty(self, hil_manager):
        history = hil_manager.get_event_history()
        assert history == []
    
    def test_get_pending_events_empty(self, hil_manager):
        events = hil_manager.get_pending_events()
        assert events == []


class TestHILEventType:
    
    def test_all_event_types_defined(self):
        expected_types = [
            "model_selection",
            "plan_review",
            "parameter_adjustment",
            "quality_checkpoint",
            "error_recovery",
            "agent_handoff",
            "result_approval",
            "custom",
        ]
        
        for event_type in expected_types:
            assert event_type in [e.value for e in HILEventType]


class TestHILDecision:
    
    def test_all_decisions_defined(self):
        expected_decisions = [
            "approve",
            "reject",
            "modify",
            "skip",
            "retry",
            "escalate",
            "timeout",
        ]
        
        for decision in expected_decisions:
            assert decision in [d.value for d in HILDecision]


class TestHILOption:
    
    def test_option_creation(self):
        option = HILOption(
            id="opt_001",
            label="选项一",
            description="这是第一个选项",
            is_default=True,
            metadata={"priority": "high"},
        )
        
        assert option.id == "opt_001"
        assert option.label == "选项一"
        assert option.is_default is True
        assert option.metadata["priority"] == "high"
    
    def test_option_defaults(self):
        option = HILOption(id="opt_002", label="选项二")
        
        assert option.description == ""
        assert option.is_default is False
        assert option.metadata == {}
