from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """模型配置"""

    model_name: str
    litellm_params: Dict[str, Any]
    tpm: int = 100000  # tokens per minute
    rpm: int = 100  # requests per minute


@dataclass
class RouterConfig:
    """Router配置"""

    model_list: List[ModelConfig]
    routing_strategy: str = "simple-shuffle"  # or "least-busy", "latency-based"
    num_retries: int = 3
    retry_after: int = 5  # seconds
    cooldown_time: int = 60  # seconds

    # 回退策略
    fallbacks: Optional[List[str]] = field(default_factory=list)
    context_window_fallbacks: Optional[List[Dict[str, str]]] = field(
        default_factory=list
    )
    content_policy_fallbacks: Optional[List[Dict[str, str]]] = field(
        default_factory=list
    )

    # 缓存配置
    cache_enabled: bool = True
    cache_type: str = "redis"
    cache_ttl: int = 3600

    # 预算控制
    max_budget: float = 100.0  # USD
    budget_duration: str = "monthly"


# 默认配置
DEFAULT_ROUTER_CONFIG = RouterConfig(
    model_list=[
        ModelConfig(
            model_name="gpt-4o",
            litellm_params={"model": "gpt-4o", "api_key": "env:OPENAI_API_KEY"},
        ),
        ModelConfig(
            model_name="claude-3-sonnet",
            litellm_params={
                "model": "claude-3-sonnet-20240229",
                "api_key": "env:ANTHROPIC_API_KEY",
            },
        ),
        ModelConfig(
            model_name="deepseek-chat",
            litellm_params={
                "model": "deepseek/deepseek-chat",
                "api_key": "env:DEEPSEEK_API_KEY",
            },
        ),
    ],
    fallbacks=["claude-3-sonnet", "deepseek-chat"],
    context_window_fallbacks=[
        {"gpt-4o": "gpt-4o-mini"},
        {"claude-3-sonnet": "claude-3-haiku-20240307"},
    ],
)
