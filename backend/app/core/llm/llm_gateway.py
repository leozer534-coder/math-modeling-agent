"""
LLM Gateway - 统一LLM调用入口
=============================

功能：
1. 统一所有LLM调用，提供一致的接口
2. 自动重试与错误恢复
3. 模型回退策略
4. Redis缓存支持
5. 成本与Token追踪
6. 请求限流与冷却
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from litellm import acompletion
from litellm.exceptions import (
    APIConnectionError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    RateLimitError,
    Timeout,
)
from app.config.setting import settings
from app.core.llm.router_config import RouterConfig, DEFAULT_ROUTER_CONFIG, ModelConfig
from app.core.llm.llm_utils import normalize_base_url, normalize_model_name
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger


# 路由策略类型
RoutingStrategy = Literal[
    "simple-shuffle",
    "least-busy",
    "usage-based-routing",
    "latency-based-routing",
    "cost-based-routing",
    "usage-based-routing-v2",
]


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    cost: float
    latency_ms: float
    cached: bool = False
    retries: int = 0


@dataclass
class GatewayConfig:
    """LLM Gateway 配置。"""

    primary_models: List[ModelConfig] = field(default_factory=list)
    fallback_models: List[ModelConfig] = field(default_factory=list)
    num_retries: int = 3
    retry_delay: float = 1.0
    cache_enabled: bool = True
    cache_namespace: str = "llm_cache"
    cache_ttl: int = 3600
    cooldown_time: int = 60
    max_budget_usd: float = 0.0
    request_timeout: int = 120
    context_window_fallbacks: Dict[str, str] = field(default_factory=dict)
    content_policy_fallbacks: Dict[str, str] = field(default_factory=dict)


class CostTracker:
    """LLM 调用成本追踪器。

    # DEPRECATED: 请使用 app.core.metering.TokenMeter 替代。此类将在后续版本移除。
    # TokenMeter 提供更完善的计量能力（按 agent 维度统计、成本限额熔断等）。
    """

    COST_PER_1K_TOKENS: Dict[str, Dict[str, float]] = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "deepseek-chat": {"input": 0.00014, "output": 0.00028},
        "deepseek-coder": {"input": 0.00014, "output": 0.00028},
    }

    def __init__(self) -> None:
        self._total_cost: float = 0.0
        self._session_start: datetime = datetime.now()
        self._usage_log: List[Dict[str, Any]] = []

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        model_key: Optional[str] = None
        for key in self.COST_PER_1K_TOKENS:
            if key in model.lower():
                model_key = key
                break

        if not model_key:
            return 0.0

        costs = self.COST_PER_1K_TOKENS[model_key]
        cost = (input_tokens / 1000 * costs["input"]) + (
            output_tokens / 1000 * costs["output"]
        )
        return round(cost, 6)

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> float:
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self._total_cost += cost

        self._usage_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "run_id": run_id,
                "agent_id": agent_id,
            }
        )

        return cost

    @property
    def total_cost(self) -> float:
        return self._total_cost

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_cost_usd": self._total_cost,
            "session_start": self._session_start.isoformat(),
            "total_requests": len(self._usage_log),
            "by_model": self._aggregate_by_model(),
        }

    def _aggregate_by_model(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for entry in self._usage_log:
            model = entry["model"]
            if model not in result:
                result[model] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0,
                }
            result[model]["requests"] += 1
            result[model]["input_tokens"] += entry["input_tokens"]
            result[model]["output_tokens"] += entry["output_tokens"]
            result[model]["cost"] += entry["cost"]
        return result


class CooldownManager:
    def __init__(self, cooldown_time: int = 60) -> None:
        self._cooldowns: Dict[str, datetime] = {}
        self._cooldown_time = cooldown_time

    def set_cooldown(self, model: str) -> None:
        self._cooldowns[model] = datetime.now() + timedelta(seconds=self._cooldown_time)
        logger.warning("Model %s in cooldown until %s", model, self._cooldowns[model])

    def is_available(self, model: str) -> bool:
        if model not in self._cooldowns:
            return True
        return datetime.now() > self._cooldowns[model]

    def get_available_models(self, models: List[str]) -> List[str]:
        return [m for m in models if self.is_available(m)]


class LLMGateway:
    def __init__(self, config: Optional[GatewayConfig] = None) -> None:
        self.config: GatewayConfig = config or self._default_config()
        self.cost_tracker = CostTracker()
        self.cooldown_manager = CooldownManager(self.config.cooldown_time)

    def _default_config(self) -> GatewayConfig:
        models: List[ModelConfig] = []

        if settings.COORDINATOR_API_KEY:
            models.append(
                ModelConfig(
                    model_name="coordinator",
                    litellm_params={
                        "model": normalize_model_name(settings.COORDINATOR_MODEL),
                        "api_key": settings.COORDINATOR_API_KEY,
                        "api_base": normalize_base_url(settings.COORDINATOR_BASE_URL),
                    },
                )
            )

        return GatewayConfig(primary_models=models, num_retries=3, cache_enabled=True)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.time()

        if use_cache and self.config.cache_enabled:
            cached = await self._get_cached_response(messages, model, temperature)
            if cached:
                return cached

        if (
            self.config.max_budget_usd > 0
            and self.cost_tracker.total_cost >= self.config.max_budget_usd
        ):
            raise Exception(
                f"Budget exceeded: ${self.cost_tracker.total_cost:.2f} >= ${self.config.max_budget_usd}"
            )

        last_error: Optional[Exception] = None
        retries = 0

        for attempt in range(self.config.num_retries + 1):
            try:
                current_model = model or self._get_available_model()

                response = await acompletion(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                    timeout=self.config.request_timeout,
                    **kwargs,
                )

                latency_ms = (time.time() - start_time) * 1000
                usage = response.usage  # type: ignore[union-attr]
                cost = self.cost_tracker.record(
                    model=current_model,
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                    run_id=run_id,
                    agent_id=agent_id,
                )

                result = LLMResponse(
                    content=response.choices[0].message.content or "",  # type: ignore[union-attr]
                    model=current_model,
                    usage={
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    },
                    cost=cost,
                    latency_ms=latency_ms,
                    cached=False,
                    retries=retries,
                )

                if use_cache and self.config.cache_enabled:
                    await self._cache_response(messages, model, temperature, result)

                await self._publish_metrics(result, run_id, agent_id)

                return result

            except RateLimitError as e:
                last_error = e
                retries += 1
                self.cooldown_manager.set_cooldown(model or "default")
                if attempt < self.config.num_retries:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

            except ContextWindowExceededError as e:
                last_error = e
                if model:
                    fallback = self.config.context_window_fallbacks.get(model)
                    if fallback:
                        model = fallback
                        logger.info(
                            f"Context window exceeded, falling back to {fallback}"
                        )
                    else:
                        raise
                else:
                    raise

            except ContentPolicyViolationError as e:
                last_error = e
                if model:
                    fallback = self.config.content_policy_fallbacks.get(model)
                    if fallback:
                        model = fallback
                        logger.info(
                            f"Content policy violation, falling back to {fallback}"
                        )
                    else:
                        raise
                else:
                    raise

            except (APIConnectionError, Timeout) as e:
                last_error = e
                retries += 1
                if attempt < self.config.num_retries:
                    await asyncio.sleep(self.config.retry_delay)

            except Exception as e:
                logger.error("LLM Gateway error: %s", e)
                raise

        raise last_error or Exception("Max retries exceeded")

    def _get_available_model(self) -> str:
        for mc in self.config.primary_models:
            if self.cooldown_manager.is_available(mc.model_name):
                return mc.litellm_params.get("model") or mc.model_name

        if self.config.fallback_models:
            for mc in self.config.fallback_models:
                model_name = mc.litellm_params.get("model", "") if hasattr(mc, "litellm_params") else str(mc)
                if self.cooldown_manager.is_available(model_name):
                    return model_name

        if self.config.primary_models:
            return (
                self.config.primary_models[0].litellm_params.get("model")
                or self.config.primary_models[0].model_name
            )

        raise Exception("No available models")

    def _cache_key(
        self, messages: List[Dict[str, Any]], model: Optional[str], temperature: float
    ) -> str:
        content = json.dumps(
            {"messages": messages, "model": model, "temperature": temperature},
            sort_keys=True,
        )
        return f"{self.config.cache_namespace}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"

    async def _get_cached_response(
        self, messages: List[Dict[str, Any]], model: Optional[str], temperature: float
    ) -> Optional[LLMResponse]:
        try:
            key = self._cache_key(messages, model, temperature)
            cached = await redis_manager.get(key)
            if cached:
                data = json.loads(cached)
                return LLMResponse(
                    content=data["content"],
                    model=data["model"],
                    usage=data["usage"],
                    cost=0,
                    latency_ms=0,
                    cached=True,
                    retries=0,
                )
        except Exception as e:
            logger.debug("Cache read error: %s", e)
        return None

    async def _cache_response(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str],
        temperature: float,
        response: LLMResponse,
    ) -> None:
        try:
            key = self._cache_key(messages, model, temperature)
            data = {
                "content": response.content,
                "model": response.model,
                "usage": response.usage,
            }
            await redis_manager.set(key, json.dumps(data), expire=self.config.cache_ttl)
        except Exception as e:
            logger.debug("Cache write error: %s", e)

    async def _publish_metrics(
        self,
        response: LLMResponse,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        """发布LLM使用指标到Redis"""
        try:
            client = await redis_manager.get_client()
            metrics_data = {
                "type": "llm_usage",
                "run_id": run_id,
                "agent_id": agent_id,
                "model": response.model,
                "tokens": response.usage["total_tokens"],
                "cost": response.cost,
                "latency_ms": response.latency_ms,
                "cached": response.cached,
                "retries": response.retries,
                "timestamp": datetime.now().isoformat(),
            }
            await client.publish("llm_metrics", json.dumps(metrics_data))
        except Exception as e:
            logger.debug("Metrics publish error: %s", e)

    def get_cost_summary(self) -> Dict[str, Any]:
        return self.cost_tracker.get_summary()


llm_gateway = LLMGateway()


async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    **kwargs: Any,
) -> LLMResponse:
    return await llm_gateway.chat(
        messages=messages, model=model, run_id=run_id, agent_id=agent_id, **kwargs
    )
