import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.config.a2a_config import get_model_tier_config
from app.config.setting import settings
from app.core.llm.llm import LLM
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


class ModelTier(str, Enum):
    TIER_1_FAST = "tier_1_fast"
    TIER_2_STANDARD = "tier_2_standard"
    TIER_3_ADVANCED = "tier_3_advanced"
    TIER_4_PREMIUM = "tier_4_premium"


class HandoffTrigger(str, Enum):
    REPEATED_ERRORS = "repeated_errors"
    COMPLEXITY_DETECTED = "complexity_detected"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    USER_REQUESTED = "user_requested"
    QUALITY_THRESHOLD = "quality_threshold"
    STUCK_IN_LOOP = "stuck_in_loop"


class HandoffDecision(str, Enum):
    ESCALATE = "escalate"
    RETRY_CURRENT = "retry_current"
    SIMPLIFY_TASK = "simplify_task"
    ABORT = "abort"
    WAIT_FOR_USER = "wait_for_user"


@dataclass
class ErrorPattern:
    error_hash: str
    error_type: str
    occurrence_count: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    sample_message: str = ""


@dataclass
class HandoffResult:
    decision: HandoffDecision
    from_tier: ModelTier
    to_tier: Optional[ModelTier]
    reason: str
    new_model: Optional[LLM] = None
    context_preserved: bool = True
    retry_count_reset: bool = False


def _build_model_tier_config() -> Dict[ModelTier, Dict[str, Any]]:
    config_dict = get_model_tier_config()
    return {
        ModelTier.TIER_1_FAST: config_dict["tier_1_fast"],
        ModelTier.TIER_2_STANDARD: config_dict["tier_2_standard"],
        ModelTier.TIER_3_ADVANCED: config_dict["tier_3_advanced"],
        ModelTier.TIER_4_PREMIUM: config_dict["tier_4_premium"],
    }


MODEL_TIER_CONFIG: Dict[ModelTier, Dict[str, Any]] = _build_model_tier_config()


class A2AHandoffManager:

    def __init__(
        self,
        task_id: str,
        initial_tier: ModelTier = ModelTier.TIER_2_STANDARD,
        auto_escalate: bool = True,
        max_escalations: int = 2,
        hil_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[Any]]] = None,
        agent_configs: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.current_tier = initial_tier
        self.auto_escalate = auto_escalate
        self.max_escalations = max_escalations
        self.hil_callback = hil_callback
        # 用户级 API 配置（多租户隔离）
        self.agent_configs = agent_configs
        
        self._error_patterns: Dict[str, ErrorPattern] = {}
        self._escalation_count = 0
        self._handoff_history: List[HandoffResult] = []
        
        self._consecutive_errors = 0
        self._same_error_streak = 0
        self._last_error_hash: Optional[str] = None
    
    def _hash_error(self, error_message: str) -> str:
        core_error = error_message.split('\n')[0] if '\n' in error_message else error_message
        import re
        core_error = re.sub(r'\d+', 'N', core_error)
        core_error = re.sub(r'0x[a-fA-F0-9]+', 'ADDR', core_error)
        return hashlib.md5(core_error.encode()).hexdigest()[:12]
    
    def _classify_error(self, error_message: str) -> str:
        error_lower = error_message.lower()
        
        if "syntax" in error_lower or "invalid syntax" in error_lower:
            return "syntax_error"
        elif "nameerror" in error_lower or "undefined" in error_lower:
            return "name_error"
        elif "typeerror" in error_lower:
            return "type_error"
        elif "keyerror" in error_lower or "indexerror" in error_lower:
            return "access_error"
        elif "memory" in error_lower or "oom" in error_lower:
            return "memory_error"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "timeout_error"
        elif "import" in error_lower or "module" in error_lower:
            return "import_error"
        elif "file" in error_lower or "path" in error_lower:
            return "file_error"
        elif "connection" in error_lower or "network" in error_lower:
            return "network_error"
        else:
            return "unknown_error"
    
    def record_error(self, error_message: str) -> ErrorPattern:
        error_hash = self._hash_error(error_message)
        error_type = self._classify_error(error_message)
        
        if error_hash in self._error_patterns:
            pattern = self._error_patterns[error_hash]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.now()
        else:
            pattern = ErrorPattern(
                error_hash=error_hash,
                error_type=error_type,
                sample_message=error_message[:500],
            )
            self._error_patterns[error_hash] = pattern
        
        self._consecutive_errors += 1
        
        if self._last_error_hash == error_hash:
            self._same_error_streak += 1
        else:
            self._same_error_streak = 1
            self._last_error_hash = error_hash
        
        return pattern
    
    def record_success(self):
        self._consecutive_errors = 0
        self._same_error_streak = 0
        self._last_error_hash = None
    
    async def evaluate_handoff(
        self,
        error_message: str,
        current_retry_count: int,
        task_complexity: str = "medium",
    ) -> HandoffResult:
        pattern = self.record_error(error_message)
        
        trigger = self._determine_trigger(pattern, current_retry_count)
        
        if trigger is None:
            return HandoffResult(
                decision=HandoffDecision.RETRY_CURRENT,
                from_tier=self.current_tier,
                to_tier=None,
                reason="继续重试当前模型",
            )
        
        decision, next_tier = self._make_decision(trigger, pattern, task_complexity)
        
        if decision == HandoffDecision.ESCALATE and next_tier:
            if self.hil_callback:
                should_escalate = await self._request_user_confirmation(
                    from_tier=self.current_tier,
                    to_tier=next_tier,
                    reason=f"触发条件: {trigger.value}, 错误类型: {pattern.error_type}",
                )
                if not should_escalate:
                    decision = HandoffDecision.RETRY_CURRENT
                    next_tier = None
        
        result = await self._execute_handoff(decision, next_tier, pattern, trigger)
        
        self._handoff_history.append(result)
        
        return result
    
    def _determine_trigger(
        self,
        pattern: ErrorPattern,
        retry_count: int,
    ) -> Optional[HandoffTrigger]:
        tier_config = MODEL_TIER_CONFIG[self.current_tier]
        max_errors = tier_config["max_errors_before_escalate"]
        
        if self._same_error_streak >= 3:
            return HandoffTrigger.STUCK_IN_LOOP
        
        if pattern.occurrence_count >= max_errors:
            return HandoffTrigger.REPEATED_ERRORS
        
        if self._consecutive_errors >= max_errors + 1:
            return HandoffTrigger.COMPLEXITY_DETECTED
        
        return None
    
    def _make_decision(
        self,
        trigger: HandoffTrigger,
        pattern: ErrorPattern,
        task_complexity: str,
    ) -> tuple[HandoffDecision, Optional[ModelTier]]:
        
        if self._escalation_count >= self.max_escalations:
            if pattern.error_type in ["memory_error", "timeout_error"]:
                return HandoffDecision.SIMPLIFY_TASK, None
            return HandoffDecision.ABORT, None
        
        if not self.auto_escalate:
            return HandoffDecision.WAIT_FOR_USER, None
        
        next_tier = self._get_next_tier()
        
        if next_tier is None:
            return HandoffDecision.SIMPLIFY_TASK, None
        
        if trigger == HandoffTrigger.STUCK_IN_LOOP:
            return HandoffDecision.ESCALATE, next_tier
        
        if trigger == HandoffTrigger.REPEATED_ERRORS:
            if pattern.error_type in ["syntax_error", "name_error"]:
                if self._same_error_streak < 2:
                    return HandoffDecision.RETRY_CURRENT, None
            return HandoffDecision.ESCALATE, next_tier
        
        if trigger == HandoffTrigger.COMPLEXITY_DETECTED:
            return HandoffDecision.ESCALATE, next_tier
        
        return HandoffDecision.RETRY_CURRENT, None
    
    def _get_next_tier(self) -> Optional[ModelTier]:
        tier_order = [
            ModelTier.TIER_1_FAST,
            ModelTier.TIER_2_STANDARD,
            ModelTier.TIER_3_ADVANCED,
            ModelTier.TIER_4_PREMIUM,
        ]
        
        try:
            current_index = tier_order.index(self.current_tier)
            if current_index < len(tier_order) - 1:
                return tier_order[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    async def _execute_handoff(
        self,
        decision: HandoffDecision,
        next_tier: Optional[ModelTier],
        pattern: ErrorPattern,
        trigger: HandoffTrigger,
    ) -> HandoffResult:
        
        if decision != HandoffDecision.ESCALATE or next_tier is None:
            return HandoffResult(
                decision=decision,
                from_tier=self.current_tier,
                to_tier=None,
                reason=f"决策: {decision.value}, 触发: {trigger.value}",
            )
        
        previous_tier = self.current_tier
        self.current_tier = next_tier
        self._escalation_count += 1
        
        self._consecutive_errors = 0
        self._same_error_streak = 0
        
        new_model = await self._create_upgraded_model(next_tier)
        
        await self._notify_handoff(previous_tier, next_tier, trigger, pattern)
        
        return HandoffResult(
            decision=decision,
            from_tier=previous_tier,
            to_tier=next_tier,
            reason=f"从 {previous_tier.value} 升级到 {next_tier.value}",
            new_model=new_model,
            context_preserved=True,
            retry_count_reset=True,
        )
    
    async def _create_upgraded_model(self, tier: ModelTier) -> Optional[LLM]:
        """
        创建升级后的模型实例

        使用 A2A 配置中的模型名称，但使用 CODER 的 API 配置
        （因为 A2A 主要用于代码执行错误升级场景）

        优先从 agent_configs 获取 CODER 配置，回退到全局 settings
        """
        try:
            tier_config = MODEL_TIER_CONFIG[tier]
            preferred_model = tier_config["models"][0]

            # 优先从用户级配置获取 CODER 的 API 凭证
            coder_api_key = None
            coder_base_url = None
            if self.agent_configs and "coder" in self.agent_configs:
                coder_cfg = self.agent_configs["coder"]
                coder_api_key = coder_cfg.get("api_key")
                coder_base_url = coder_cfg.get("base_url")

            # 回退到全局 settings
            if not coder_api_key:
                coder_api_key = settings.CODER_API_KEY
            if not coder_base_url:
                coder_base_url = settings.CODER_BASE_URL

            upgraded_llm = LLM(
                api_key=coder_api_key,
                model=preferred_model,
                base_url=coder_base_url,
                task_id=self.task_id,
            )

            logger.info("A2A: 创建升级模型 %s (Tier: %s)", preferred_model, tier.value)

            return upgraded_llm

        except Exception as e:
            logger.error("A2A: 创建升级模型失败: %s", e)
            return None
    
    async def _notify_handoff(
        self,
        from_tier: ModelTier,
        to_tier: ModelTier,
        trigger: HandoffTrigger,
        pattern: ErrorPattern,
    ):
        message = (
            f"🔄 智能移交: {from_tier.value} → {to_tier.value}\n"
            f"触发原因: {trigger.value}\n"
            f"错误类型: {pattern.error_type}"
        )
        
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content=message, type="info"),
        )
        
        logger.info("A2A Handoff: %s", message)
    
    async def _request_user_confirmation(
        self,
        from_tier: ModelTier,
        to_tier: ModelTier,
        reason: str,
    ) -> bool:
        if not self.hil_callback:
            return True
        
        try:
            response = await self.hil_callback(
                "agent_handoff",
                {
                    "from_model": from_tier.value,
                    "to_model": to_tier.value,
                    "reason": reason,
                },
            )
            return response.get("approved", True) if isinstance(response, dict) else True
        except Exception as e:
            logger.warning("A2A: HIL 回调失败，默认继续升级: %s", e)
            return True
    
    def get_current_tier(self) -> ModelTier:
        return self.current_tier
    
    def get_escalation_count(self) -> int:
        return self._escalation_count
    
    def get_error_summary(self) -> Dict[str, Any]:
        return {
            "current_tier": self.current_tier.value,
            "escalation_count": self._escalation_count,
            "consecutive_errors": self._consecutive_errors,
            "same_error_streak": self._same_error_streak,
            "unique_error_patterns": len(self._error_patterns),
            "error_types": {
                p.error_type: p.occurrence_count
                for p in self._error_patterns.values()
            },
        }
    
    def get_handoff_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "decision": h.decision.value,
                "from_tier": h.from_tier.value,
                "to_tier": h.to_tier.value if h.to_tier else None,
                "reason": h.reason,
            }
            for h in self._handoff_history
        ]
