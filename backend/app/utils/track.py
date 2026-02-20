import logging
from typing import Any

from litellm.integrations.custom_logger import CustomLogger

logger = logging.getLogger(__name__)


class AgentMetrics(CustomLogger):
    """LiteLLM 自定义日志回调，用于记录 Agent 调用的 Token 用量、成本和延迟指标。"""

    async def async_log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """记录 LLM 调用成功事件的关键指标。"""
        try:
            # 提取 agent 名称
            litellm_params = kwargs.get("litellm_params", {})
            metadata = litellm_params.get("metadata", {})
            agent_name = metadata.get("agent_name", "unknown")

            # 提取模型名称
            model = kwargs.get("model", "unknown")

            # 提取 Token 用量
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            if hasattr(response_obj, "usage") and response_obj.usage is not None:
                usage = response_obj.usage
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                total_tokens = getattr(usage, "total_tokens", 0) or 0

            # 提取成本
            response_cost = kwargs.get("response_cost", 0) or 0

            # 计算延迟（毫秒）
            latency_ms = 0.0
            if start_time and end_time:
                delta = end_time - start_time
                latency_ms = round(delta.total_seconds() * 1000, 2)

            logger.info(
                "LLM 调用成功 | agent=%s | model=%s | "
                "prompt_tokens=%d | completion_tokens=%d | total_tokens=%d | "
                "cost=%.6f | latency_ms=%.2f",
                agent_name,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                response_cost,
                latency_ms,
            )
        except Exception as e:
            logger.debug("Agent 指标记录失败: %s", e)

    async def async_log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """记录 LLM 调用失败事件。"""
        try:
            litellm_params = kwargs.get("litellm_params", {})
            metadata = litellm_params.get("metadata", {})
            agent_name = metadata.get("agent_name", "unknown")
            model = kwargs.get("model", "unknown")

            # 计算延迟（毫秒）
            latency_ms = 0.0
            if start_time and end_time:
                delta = end_time - start_time
                latency_ms = round(delta.total_seconds() * 1000, 2)

            # 提取异常信息
            exception = kwargs.get("exception", "unknown error")

            logger.warning(
                "LLM 调用失败 | agent=%s | model=%s | latency_ms=%.2f | error=%s",
                agent_name,
                model,
                latency_ms,
                exception,
            )
        except Exception as e:
            logger.debug("Agent 失败指标记录失败: %s", e)


# 全局指标收集器实例
agent_metrics = AgentMetrics()
