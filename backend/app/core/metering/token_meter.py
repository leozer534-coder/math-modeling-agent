"""
Token计量器模块 - Token Meter

提供LLM调用的Token消耗实时计量功能

功能：
1. 实时Token消耗记录
2. 成本累计统计
3. Redis持久化（跨进程共享）
4. 使用历史查询
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.metering.cost_calculator import CostCalculator
from app.utils.log_util import logger


# ============= 使用记录 =============

@dataclass
class UsageRecord:
    """单次调用使用记录"""
    record_id: str
    task_id: str
    agent_type: str  # coordinator, modeler, coder, writer
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageRecord":
        return cls(
            record_id=data.get("record_id", ""),
            task_id=data.get("task_id", ""),
            agent_type=data.get("agent_type", ""),
            model=data.get("model", ""),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost_usd=data.get("cost_usd", 0.0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )


# ============= 使用统计 =============

@dataclass
class UsageStats:
    """使用统计"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    call_count: int = 0
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ============= Token计量器 =============

class TokenMeter:
    """
    Token计量器
    
    跟踪单个任务的Token消耗和成本
    
    使用示例：
        >>> meter = TokenMeter("task-123")
        >>> await meter.record("coder", "deepseek-chat", 1000, 500)
        >>> stats = meter.get_stats()
        >>> print(f"总成本: ${stats.total_cost_usd:.4f}")
    """
    
    def __init__(
        self,
        task_id: str,
        max_cost_usd: float = 10.0,
        max_tokens: int = 1_000_000,
        persist_to_redis: bool = True,
    ):
        """
        初始化计量器
        
        Args:
            task_id: 任务ID
            max_cost_usd: 最大成本限额（USD）
            max_tokens: 最大Token限额
            persist_to_redis: 是否持久化到Redis
        """
        self.task_id = task_id
        self.max_cost_usd = max_cost_usd
        self.max_tokens = max_tokens
        self._persist = persist_to_redis
        
        self._calculator = CostCalculator()
        self._records: List[UsageRecord] = []
        self._stats = UsageStats()
        
        logger.debug("TokenMeter 已初始化: task=%s, max_cost=$%s", task_id, max_cost_usd)
    
    async def record(
        self,
        agent_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """
        记录一次LLM调用
        
        Args:
            agent_type: Agent类型
            model: 模型名称
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            metadata: 额外元数据
            
        Returns:
            UsageRecord: 使用记录
            
        Raises:
            CostLimitExceededError: 超过成本限额
            TokenLimitExceededError: 超过Token限额
        """
        # 计算成本
        cost_result = self._calculator.calculate(model, input_tokens, output_tokens)
        
        # 创建记录
        record = UsageRecord(
            record_id=f"{self.task_id}_{len(self._records)}",
            task_id=self.task_id,
            agent_type=agent_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=cost_result.total_tokens,
            cost_usd=cost_result.total_cost_usd,
            metadata=metadata or {},
        )
        
        # 更新统计
        self._update_stats(record)
        
        # 检查限额
        self._check_limits()
        
        # 保存记录
        self._records.append(record)
        
        # 持久化到Redis
        if self._persist:
            await self._save_to_redis()
        
        logger.info(
            f"📊 Token消耗: {agent_type}/{model} - "
            f"输入:{input_tokens} 输出:{output_tokens} "
            f"成本:${cost_result.total_cost_usd:.4f} "
            f"累计:${self._stats.total_cost_usd:.4f}"
        )
        
        return record
    
    def _update_stats(self, record: UsageRecord) -> None:
        """更新统计数据"""
        self._stats.total_input_tokens += record.input_tokens
        self._stats.total_output_tokens += record.output_tokens
        self._stats.total_tokens += record.total_tokens
        self._stats.total_cost_usd += record.cost_usd
        self._stats.call_count += 1
        
        # 按Agent统计
        if record.agent_type not in self._stats.by_agent:
            self._stats.by_agent[record.agent_type] = {
                "tokens": 0,
                "cost_usd": 0.0,
                "calls": 0,
            }
        self._stats.by_agent[record.agent_type]["tokens"] += record.total_tokens
        self._stats.by_agent[record.agent_type]["cost_usd"] += record.cost_usd
        self._stats.by_agent[record.agent_type]["calls"] += 1
        
        # 按模型统计
        if record.model not in self._stats.by_model:
            self._stats.by_model[record.model] = {
                "tokens": 0,
                "cost_usd": 0.0,
                "calls": 0,
            }
        self._stats.by_model[record.model]["tokens"] += record.total_tokens
        self._stats.by_model[record.model]["cost_usd"] += record.cost_usd
        self._stats.by_model[record.model]["calls"] += 1
    
    def _check_limits(self) -> None:
        """检查限额"""
        if self._stats.total_cost_usd >= self.max_cost_usd:
            raise CostLimitExceededError(
                f"任务 {self.task_id} 成本已达上限 ${self.max_cost_usd:.2f}"
            )
        
        if self._stats.total_tokens >= self.max_tokens:
            raise TokenLimitExceededError(
                f"任务 {self.task_id} Token数已达上限 {self.max_tokens:,}"
            )
    
    async def _save_to_redis(self) -> None:
        """保存到Redis"""
        try:
            from app.services.redis_manager import redis_manager
            
            data = {
                "task_id": self.task_id,
                "stats": {
                    "total_input_tokens": self._stats.total_input_tokens,
                    "total_output_tokens": self._stats.total_output_tokens,
                    "total_tokens": self._stats.total_tokens,
                    "total_cost_usd": self._stats.total_cost_usd,
                    "call_count": self._stats.call_count,
                    "by_agent": self._stats.by_agent,
                    "by_model": self._stats.by_model,
                },
                "updated_at": datetime.now().isoformat(),
            }
            
            await redis_manager.set_json(
                f"metering:{self.task_id}",
                data,
                expire=86400 * 7,  # 7天过期
            )
        except Exception as e:
            logger.warning("保存计量数据到Redis失败: %s", e)
    
    def get_stats(self) -> UsageStats:
        """获取使用统计"""
        return self._stats
    
    def get_records(self) -> List[UsageRecord]:
        """获取所有记录"""
        return self._records.copy()
    
    def get_cost(self) -> float:
        """获取当前总成本（USD）"""
        return self._stats.total_cost_usd
    
    def get_remaining_budget(self) -> float:
        """获取剩余预算（USD）"""
        return max(0, self.max_cost_usd - self._stats.total_cost_usd)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要信息"""
        return {
            "task_id": self.task_id,
            "total_tokens": self._stats.total_tokens,
            "total_cost_usd": round(self._stats.total_cost_usd, 4),
            "total_cost_cny": round(self._stats.total_cost_usd * 7.2, 2),
            "call_count": self._stats.call_count,
            "remaining_budget_usd": round(self.get_remaining_budget(), 4),
            "by_agent": self._stats.by_agent,
        }


# ============= 异常定义 =============

class CostLimitExceededError(Exception):
    """成本限额超出异常"""
    pass


class TokenLimitExceededError(Exception):
    """Token限额超出异常"""
    pass


# ============= 任务计量器管理 =============

_task_meters: Dict[str, TokenMeter] = {}


def get_task_meter(
    task_id: str,
    max_cost_usd: float = 10.0,
    max_tokens: int = 1_000_000,
) -> TokenMeter:
    """
    获取任务的计量器（单例模式）
    
    Args:
        task_id: 任务ID
        max_cost_usd: 最大成本限额
        max_tokens: 最大Token限额
        
    Returns:
        TokenMeter: 计量器实例
    """
    if task_id not in _task_meters:
        _task_meters[task_id] = TokenMeter(
            task_id=task_id,
            max_cost_usd=max_cost_usd,
            max_tokens=max_tokens,
        )
    return _task_meters[task_id]


def remove_task_meter(task_id: str) -> None:
    """移除任务计量器"""
    if task_id in _task_meters:
        del _task_meters[task_id]
