"""
A2A (Agent-to-Agent) 智能移交配置模块

提供模型分层配置的集中管理，支持环境变量覆盖和运行时修改。
"""
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelTierSettings(BaseModel):
    """单个模型层级的配置"""
    models: List[str] = Field(description="该层级可用的模型列表，按优先级排序")
    max_errors_before_escalate: int = Field(ge=1, le=10, description="升级前允许的最大错误次数")
    cost_multiplier: float = Field(ge=0.1, le=100.0, description="相对成本倍数")
    capabilities: List[str] = Field(description="该层级的能力标签")
    description: str = Field(default="", description="层级描述")


class A2AConfig(BaseSettings):
    """
    A2A 智能移交配置类

    支持从环境变量加载配置，也可在运行时动态修改。
    """

    # ============= 全局设置 =============
    A2A_ENABLED: bool = Field(default=True, description="是否启用A2A功能")
    A2A_AUTO_ESCALATE: bool = Field(default=True, description="是否自动升级")
    A2A_MAX_ESCALATIONS: int = Field(default=2, ge=0, le=5, description="最大升级次数")
    A2A_DEFAULT_TIER: str = Field(default="tier_2_standard", description="默认起始层级")

    # ============= 层级配置 =============
    # Tier 1: 快速模型 - 用于简单任务
    TIER_1_MODELS: List[str] = Field(
        default=["gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash"],
        description="Tier 1 可用模型"
    )
    TIER_1_MAX_ERRORS: int = Field(default=2, ge=1, le=10)
    TIER_1_COST_MULTIPLIER: float = Field(default=1.0)
    TIER_1_CAPABILITIES: List[str] = Field(
        default=["simple_code", "basic_math"]
    )

    # Tier 2: 标准模型 - 用于常规任务
    TIER_2_MODELS: List[str] = Field(
        default=["gpt-4o", "claude-3.5-sonnet", "gemini-1.5-pro"],
        description="Tier 2 可用模型"
    )
    TIER_2_MAX_ERRORS: int = Field(default=3, ge=1, le=10)
    TIER_2_COST_MULTIPLIER: float = Field(default=5.0)
    TIER_2_CAPABILITIES: List[str] = Field(
        default=["complex_code", "advanced_math", "debugging"]
    )

    # Tier 3: 高级模型 - 用于复杂任务
    TIER_3_MODELS: List[str] = Field(
        default=["claude-sonnet-4-20250514", "gpt-4.1"],
        description="Tier 3 可用模型"
    )
    TIER_3_MAX_ERRORS: int = Field(default=4, ge=1, le=10)
    TIER_3_COST_MULTIPLIER: float = Field(default=10.0)
    TIER_3_CAPABILITIES: List[str] = Field(
        default=["expert_code", "research", "optimization"]
    )

    # Tier 4: 顶级模型 - 用于最复杂的任务
    TIER_4_MODELS: List[str] = Field(
        default=["claude-opus-4-20250514", "o1", "o3-mini"],
        description="Tier 4 可用模型"
    )
    TIER_4_MAX_ERRORS: int = Field(default=5, ge=1, le=10)
    TIER_4_COST_MULTIPLIER: float = Field(default=20.0)
    TIER_4_CAPABILITIES: List[str] = Field(
        default=["cutting_edge", "complex_reasoning", "novel_solutions"]
    )

    # ============= 错误处理配置 =============
    A2A_LOOP_DETECTION_THRESHOLD: int = Field(
        default=3, ge=2, le=10,
        description="相同错误连续出现多少次视为死循环"
    )
    A2A_CONSECUTIVE_ERROR_THRESHOLD: int = Field(
        default=5, ge=2, le=20,
        description="连续错误多少次触发升级"
    )

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="allow",
    )

    def get_tier_config(self, tier: str) -> Dict[str, Any]:
        """
        获取指定层级的配置

        Args:
            tier: 层级名称 (tier_1_fast, tier_2_standard, tier_3_advanced, tier_4_premium)

        Returns:
            包含 models, max_errors_before_escalate, cost_multiplier, capabilities 的字典
        """
        tier_map = {
            "tier_1_fast": {
                "models": self.TIER_1_MODELS,
                "max_errors_before_escalate": self.TIER_1_MAX_ERRORS,
                "cost_multiplier": self.TIER_1_COST_MULTIPLIER,
                "capabilities": self.TIER_1_CAPABILITIES,
            },
            "tier_2_standard": {
                "models": self.TIER_2_MODELS,
                "max_errors_before_escalate": self.TIER_2_MAX_ERRORS,
                "cost_multiplier": self.TIER_2_COST_MULTIPLIER,
                "capabilities": self.TIER_2_CAPABILITIES,
            },
            "tier_3_advanced": {
                "models": self.TIER_3_MODELS,
                "max_errors_before_escalate": self.TIER_3_MAX_ERRORS,
                "cost_multiplier": self.TIER_3_COST_MULTIPLIER,
                "capabilities": self.TIER_3_CAPABILITIES,
            },
            "tier_4_premium": {
                "models": self.TIER_4_MODELS,
                "max_errors_before_escalate": self.TIER_4_MAX_ERRORS,
                "cost_multiplier": self.TIER_4_COST_MULTIPLIER,
                "capabilities": self.TIER_4_CAPABILITIES,
            },
        }
        return tier_map.get(tier, tier_map["tier_2_standard"])

    def get_all_tier_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有层级的配置

        Returns:
            包含所有层级配置的字典，格式与 MODEL_TIER_CONFIG 兼容
        """
        return {
            "tier_1_fast": self.get_tier_config("tier_1_fast"),
            "tier_2_standard": self.get_tier_config("tier_2_standard"),
            "tier_3_advanced": self.get_tier_config("tier_3_advanced"),
            "tier_4_premium": self.get_tier_config("tier_4_premium"),
        }

    def summary(self) -> str:
        """生成配置摘要（用于日志）"""
        lines = [
            "=" * 50,
            "A2A 智能移交配置摘要",
            "=" * 50,
            f"启用状态: {'启用' if self.A2A_ENABLED else '禁用'}",
            f"自动升级: {'是' if self.A2A_AUTO_ESCALATE else '否'}",
            f"最大升级次数: {self.A2A_MAX_ESCALATIONS}",
            f"默认层级: {self.A2A_DEFAULT_TIER}",
            "",
            "层级配置:",
            f"  Tier 1 (快速): {self.TIER_1_MODELS[0] if self.TIER_1_MODELS else 'N/A'}",
            f"  Tier 2 (标准): {self.TIER_2_MODELS[0] if self.TIER_2_MODELS else 'N/A'}",
            f"  Tier 3 (高级): {self.TIER_3_MODELS[0] if self.TIER_3_MODELS else 'N/A'}",
            f"  Tier 4 (顶级): {self.TIER_4_MODELS[0] if self.TIER_4_MODELS else 'N/A'}",
            "=" * 50,
        ]
        return "\n".join(lines)


# 全局配置实例
a2a_config = A2AConfig()


def get_model_tier_config() -> Dict[str, Dict[str, Any]]:
    """
    获取 MODEL_TIER_CONFIG 兼容格式的配置

    供 handoff_manager.py 使用，返回与原硬编码格式完全兼容的配置字典。

    Returns:
        Dict 格式的模型层级配置
    """
    return a2a_config.get_all_tier_configs()
