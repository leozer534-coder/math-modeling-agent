"""
LLM 调用层共享工具函数

为 llm.py (LLM) 和 llm_gateway.py (LLMGateway) 提供统一的规范化逻辑，
避免两处维护相同代码导致的不一致风险。
"""

from typing import Optional


def normalize_model_name(model: str) -> str:
    """规范化模型名称，确保包含 provider 前缀。

    LiteLLM 要求模型名包含 provider 前缀（如 openai/gpt-4）。
    如果用户提供的模型名不包含 '/'，默认添加 'openai/' 前缀。

    Args:
        model: 原始模型名称

    Returns:
        带有 provider 前缀的模型名称
    """
    if not model:
        return model
    if "/" not in model:
        return f"openai/{model}"
    return model


def normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    """规范化 base_url，确保以 /v1 结尾。

    部分 API 提供商要求 base_url 以 /v1 结尾，
    本函数自动补齐缺失的后缀。

    Args:
        base_url: 原始 API 基础地址

    Returns:
        规范化后的地址，None 保持不变
    """
    if not base_url:
        return base_url
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        return base_url + "/v1"
    return base_url
