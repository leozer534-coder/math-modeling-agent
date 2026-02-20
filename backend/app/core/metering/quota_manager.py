"""
配额管理器模块 - Quota Manager

提供用户/任务级别的资源配额管理

功能：
1. 用户配额管理（按月/按日）
2. 任务配额管理
3. 配额检查与扣减
4. 配额恢复
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from app.utils.log_util import logger


# ============= 枚举定义 =============

class QuotaType(str, Enum):
    """配额类型"""
    TOKEN = "token"  # Token数量
    COST = "cost"  # 成本（USD）
    TASK = "task"  # 任务数量
    API_CALL = "api_call"  # API调用次数


class QuotaPeriod(str, Enum):
    """配额周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    UNLIMITED = "unlimited"


# ============= 配额配置 =============

@dataclass
class QuotaConfig:
    """配额配置"""
    quota_type: QuotaType
    period: QuotaPeriod
    limit: float  # 配额限制值
    soft_limit: Optional[float] = None  # 软限制（警告阈值）
    
    def __post_init__(self):
        if self.soft_limit is None:
            self.soft_limit = self.limit * 0.8  # 默认80%警告


@dataclass
class QuotaUsage:
    """配额使用情况"""
    used: float = 0.0
    limit: float = 0.0
    remaining: float = 0.0
    percent_used: float = 0.0
    period_start: str = ""
    period_end: str = ""
    is_exceeded: bool = False
    is_warning: bool = False


# ============= 用户配额计划 =============

# 预设配额计划
QUOTA_PLANS: Dict[str, Dict[str, QuotaConfig]] = {
    "free": {
        "task": QuotaConfig(QuotaType.TASK, QuotaPeriod.MONTHLY, 5),
        "token": QuotaConfig(QuotaType.TOKEN, QuotaPeriod.MONTHLY, 100_000),
        "cost": QuotaConfig(QuotaType.COST, QuotaPeriod.MONTHLY, 1.0),
    },
    "pro": {
        "task": QuotaConfig(QuotaType.TASK, QuotaPeriod.MONTHLY, 50),
        "token": QuotaConfig(QuotaType.TOKEN, QuotaPeriod.MONTHLY, 2_000_000),
        "cost": QuotaConfig(QuotaType.COST, QuotaPeriod.MONTHLY, 20.0),
    },
    "team": {
        "task": QuotaConfig(QuotaType.TASK, QuotaPeriod.MONTHLY, 500),
        "token": QuotaConfig(QuotaType.TOKEN, QuotaPeriod.MONTHLY, 20_000_000),
        "cost": QuotaConfig(QuotaType.COST, QuotaPeriod.MONTHLY, 200.0),
    },
    "enterprise": {
        "task": QuotaConfig(QuotaType.TASK, QuotaPeriod.UNLIMITED, float("inf")),
        "token": QuotaConfig(QuotaType.TOKEN, QuotaPeriod.UNLIMITED, float("inf")),
        "cost": QuotaConfig(QuotaType.COST, QuotaPeriod.UNLIMITED, float("inf")),
    },
}


# ============= 异常定义 =============

class QuotaExceededError(Exception):
    """配额超出异常"""
    
    def __init__(self, message: str, quota_type: QuotaType, usage: QuotaUsage):
        super().__init__(message)
        self.quota_type = quota_type
        self.usage = usage


class QuotaWarning(Exception):
    """配额警告（软限制）"""
    pass


# ============= 配额管理器 =============

class QuotaManager:
    """
    配额管理器
    
    管理用户和任务的资源配额
    
    使用示例：
        >>> manager = QuotaManager("user-123", plan="pro")
        >>> manager.check_and_deduct("token", 1000)
        >>> usage = manager.get_usage("token")
    """
    
    def __init__(
        self,
        user_id: str,
        plan: str = "free",
        custom_quotas: Optional[Dict[str, QuotaConfig]] = None,
    ):
        """
        初始化配额管理器
        
        Args:
            user_id: 用户ID
            plan: 配额计划名称（free/pro/team/enterprise）
            custom_quotas: 自定义配额配置
        """
        self.user_id = user_id
        self.plan = plan
        
        # 加载配额配置
        self._quotas = QUOTA_PLANS.get(plan, QUOTA_PLANS["free"]).copy()
        if custom_quotas:
            self._quotas.update(custom_quotas)
        
        # 使用量记录
        self._usage: Dict[str, float] = {qt: 0.0 for qt in self._quotas.keys()}
        self._period_start = self._calculate_period_start()
        
        logger.debug("QuotaManager 初始化: user=%s, plan=%s", user_id, plan)
    
    def _calculate_period_start(self) -> datetime:
        """计算当前周期开始时间"""
        now = datetime.now()
        # 默认按月计算
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    def _calculate_period_end(self, period: QuotaPeriod) -> datetime:
        """计算周期结束时间"""
        start = self._period_start
        if period == QuotaPeriod.DAILY:
            return start + timedelta(days=1)
        elif period == QuotaPeriod.WEEKLY:
            return start + timedelta(weeks=1)
        elif period == QuotaPeriod.MONTHLY:
            # 下个月第一天
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1)
            return start.replace(month=start.month + 1)
        else:
            return datetime.max
    
    def check_quota(self, quota_name: str, amount: float = 0) -> QuotaUsage:
        """
        检查配额使用情况
        
        Args:
            quota_name: 配额名称（token/cost/task）
            amount: 要检查的增量（可选）
            
        Returns:
            QuotaUsage: 配额使用情况
        """
        if quota_name not in self._quotas:
            raise ValueError(f"未知配额类型: {quota_name}")
        
        config = self._quotas[quota_name]
        current_used = self._usage.get(quota_name, 0.0)
        projected_used = current_used + amount
        
        remaining = max(0, config.limit - projected_used)
        percent = (projected_used / config.limit * 100) if config.limit > 0 else 0
        
        return QuotaUsage(
            used=current_used,
            limit=config.limit,
            remaining=remaining,
            percent_used=min(percent, 100),
            period_start=self._period_start.isoformat(),
            period_end=self._calculate_period_end(config.period).isoformat(),
            is_exceeded=projected_used > config.limit,
            is_warning=projected_used > config.soft_limit if config.soft_limit else False,
        )
    
    def check_and_deduct(
        self,
        quota_name: str,
        amount: float,
        raise_on_exceed: bool = True,
    ) -> QuotaUsage:
        """
        检查配额并扣减
        
        Args:
            quota_name: 配额名称
            amount: 扣减数量
            raise_on_exceed: 超出时是否抛出异常
            
        Returns:
            QuotaUsage: 扣减后的使用情况
            
        Raises:
            QuotaExceededError: 配额超出
        """
        usage = self.check_quota(quota_name, amount)
        
        if usage.is_exceeded:
            if raise_on_exceed:
                config = self._quotas[quota_name]
                raise QuotaExceededError(
                    f"用户 {self.user_id} 的 {quota_name} 配额已超出 "
                    f"(已用: {usage.used + amount:.2f}, 限额: {config.limit:.2f})",
                    quota_type=config.quota_type,
                    usage=usage,
                )
            logger.warning("配额超出但未阻止: %s", quota_name)
        
        if usage.is_warning:
            logger.warning(
                "⚠️ 用户 %s 的 %s 配额即将用尽 (%.1f%%)",
                self.user_id, quota_name, usage.percent_used,
            )
        
        # 执行扣减
        self._usage[quota_name] = self._usage.get(quota_name, 0.0) + amount
        
        return self.check_quota(quota_name)
    
    def get_usage(self, quota_name: str) -> QuotaUsage:
        """获取指定配额的使用情况"""
        return self.check_quota(quota_name)
    
    def get_all_usage(self) -> Dict[str, QuotaUsage]:
        """获取所有配额的使用情况"""
        return {name: self.check_quota(name) for name in self._quotas.keys()}
    
    def reset_usage(self, quota_name: Optional[str] = None) -> None:
        """
        重置使用量
        
        Args:
            quota_name: 指定配额名称，None则重置全部
        """
        if quota_name:
            self._usage[quota_name] = 0.0
        else:
            self._usage = {qt: 0.0 for qt in self._quotas.keys()}
        
        self._period_start = self._calculate_period_start()
        logger.info("配额使用量已重置: user=%s, quota=%s", self.user_id, quota_name or 'all')
    
    def add_quota(self, quota_name: str, amount: float) -> None:
        """
        添加配额（充值/奖励）
        
        Args:
            quota_name: 配额名称
            amount: 增加的额度
        """
        if quota_name not in self._quotas:
            raise ValueError(f"未知配额类型: {quota_name}")
        
        config = self._quotas[quota_name]
        new_limit = config.limit + amount
        self._quotas[quota_name] = QuotaConfig(
            quota_type=config.quota_type,
            period=config.period,
            limit=new_limit,
            soft_limit=new_limit * 0.8,
        )
        
        logger.info("配额已增加: user=%s, %s +%s", self.user_id, quota_name, amount)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取配额摘要"""
        all_usage = self.get_all_usage()
        return {
            "user_id": self.user_id,
            "plan": self.plan,
            "quotas": {
                name: {
                    "used": usage.used,
                    "limit": usage.limit,
                    "remaining": usage.remaining,
                    "percent_used": round(usage.percent_used, 1),
                    "is_warning": usage.is_warning,
                    "is_exceeded": usage.is_exceeded,
                }
                for name, usage in all_usage.items()
            },
        }


# ============= 全局管理 =============

_user_quotas: Dict[str, QuotaManager] = {}


def get_user_quota_manager(
    user_id: str,
    plan: str = "free",
) -> QuotaManager:
    """获取用户配额管理器（单例）"""
    if user_id not in _user_quotas:
        _user_quotas[user_id] = QuotaManager(user_id, plan)
    return _user_quotas[user_id]
