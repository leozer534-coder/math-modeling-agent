"""
成本计算器模块 - Cost Calculator

提供LLM调用成本计算功能

功能：
1. 模型定价表管理
2. Token消耗成本计算
3. 成本预估
"""

from dataclasses import dataclass
from typing import Dict, Optional

from app.utils.log_util import logger


# ============= 模型定价表 =============
# 价格单位：USD per 1M tokens

MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # DeepSeek 系列
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    
    # OpenAI 系列
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    
    # Anthropic Claude 系列
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    
    # Google Gemini 系列
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    
    # 国产模型
    "qwen-max": {"input": 0.20, "output": 0.60},
    "qwen-plus": {"input": 0.08, "output": 0.20},
    "glm-4": {"input": 0.10, "output": 0.10},
    "moonshot-v1": {"input": 0.12, "output": 0.12},
}

# 默认定价（未知模型使用）
DEFAULT_PRICING = {"input": 1.00, "output": 2.00}


# ============= 成本计算结果 =============

@dataclass
class CostResult:
    """成本计算结果"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    model: str
    
    @property
    def total_cost_cny(self) -> float:
        """转换为人民币（汇率7.2）"""
        return self.total_cost_usd * 7.2


# ============= 成本计算器 =============

class CostCalculator:
    """
    LLM成本计算器
    
    根据模型和Token数量计算API调用成本
    
    使用示例：
        >>> calc = CostCalculator()
        >>> result = calc.calculate("gpt-4o", 1000, 500)
        >>> print(f"总成本: ${result.total_cost_usd:.4f}")
    """
    
    def __init__(self, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None):
        """
        初始化计算器
        
        Args:
            custom_pricing: 自定义定价表（会覆盖默认定价）
        """
        self._pricing = MODEL_PRICING.copy()
        if custom_pricing:
            self._pricing.update(custom_pricing)
    
    def get_pricing(self, model: str) -> Dict[str, float]:
        """
        获取模型定价
        
        Args:
            model: 模型名称
            
        Returns:
            定价字典 {"input": x, "output": y}
        """
        # 尝试精确匹配
        if model in self._pricing:
            return self._pricing[model]
        
        # 尝试前缀匹配（处理版本号等）
        model_lower = model.lower()
        for key in self._pricing:
            if model_lower.startswith(key.lower()) or key.lower() in model_lower:
                return self._pricing[key]
        
        # 返回默认定价
        logger.warning("未知模型 %s，使用默认定价", model)
        return DEFAULT_PRICING
    
    def calculate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostResult:
        """
        计算调用成本
        
        Args:
            model: 模型名称
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            
        Returns:
            CostResult: 成本计算结果
        """
        pricing = self.get_pricing(model)
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return CostResult(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=input_cost + output_cost,
            model=model,
        )
    
    def estimate_cost(
        self,
        model: str,
        prompt_chars: int,
        expected_output_chars: int = 2000,
        chars_per_token: float = 3.5,
    ) -> CostResult:
        """
        预估成本（根据字符数估算Token）
        
        Args:
            model: 模型名称
            prompt_chars: 提示词字符数
            expected_output_chars: 预期输出字符数
            chars_per_token: 平均每Token字符数（中文约2-3，英文约4-5）
            
        Returns:
            CostResult: 预估成本
        """
        input_tokens = int(prompt_chars / chars_per_token)
        output_tokens = int(expected_output_chars / chars_per_token)
        
        return self.calculate(model, input_tokens, output_tokens)
    
    def list_models(self) -> list:
        """列出所有已配置定价的模型"""
        return list(self._pricing.keys())
    
    def add_model_pricing(self, model: str, input_price: float, output_price: float) -> None:
        """
        添加或更新模型定价
        
        Args:
            model: 模型名称
            input_price: 输入Token价格 (USD/1M tokens)
            output_price: 输出Token价格 (USD/1M tokens)
        """
        self._pricing[model] = {"input": input_price, "output": output_price}
        logger.info("模型 %s 定价已更新: 输入$%s/1M, 输出$%s/1M", model, input_price, output_price)


# ============= 全局实例 =============

_calculator_instance: Optional[CostCalculator] = None


def get_cost_calculator() -> CostCalculator:
    """获取全局成本计算器实例"""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = CostCalculator()
    return _calculator_instance
