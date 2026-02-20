"""
API Key 安全存储模块 - API Key Vault

提供API Key的加密存储、读取和管理功能

功能：
1. API Key加密存储
2. 按Agent类型管理密钥
3. 自动加密未加密的密钥
4. 密钥轮换支持
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.security.encryption import (
    EncryptionService,
    mask_api_key,
)
from app.utils.log_util import logger


# ============= 常量定义 =============

# 主密钥环境变量名
MASTER_KEY_ENV = "API_KEY_MASTER_SECRET"

# 默认开发环境主密钥（仅开发使用，生产必须设置环境变量）
DEV_MASTER_KEY = "mathmodel-dev-key-do-not-use-in-prod"


# ============= 数据类 =============

@dataclass
class StoredAPIKey:
    """存储的API Key信息"""
    agent_type: str  # coordinator, modeler, coder, writer
    encrypted_key: str  # 加密后的密钥
    model_name: str = ""  # 模型名称
    base_url: str = ""  # API基础URL
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None
    use_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "encrypted_key": self.encrypted_key,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredAPIKey":
        return cls(
            agent_type=data.get("agent_type", ""),
            encrypted_key=data.get("encrypted_key", ""),
            model_name=data.get("model_name", ""),
            base_url=data.get("base_url", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_used=data.get("last_used"),
            use_count=data.get("use_count", 0),
        )


# ============= API Key Vault =============

class APIKeyVault:
    """
    API Key 安全保险库
    
    集中管理所有Agent的API Key，提供：
    - 加密存储
    - 按需解密
    - 使用统计
    
    使用示例：
        >>> vault = APIKeyVault()
        >>> vault.store("coordinator", "sk-xxx", "gpt-4", "https://api.openai.com")
        >>> api_key = vault.get("coordinator")
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化Vault
        
        Args:
            master_key: 主密钥，如果不提供则从环境变量读取
        """
        # 获取主密钥
        self._master_key = master_key or os.environ.get(MASTER_KEY_ENV)
        
        if not self._master_key:
            # 开发环境使用默认密钥并警告
            self._master_key = DEV_MASTER_KEY
            logger.warning(
                "⚠️ 未设置 %s 环境变量，使用开发环境默认密钥。"
                "生产环境请务必设置此变量！",
                MASTER_KEY_ENV,
            )
        
        self._encryption = EncryptionService(self._master_key)
        self._keys: Dict[str, StoredAPIKey] = {}
        
        logger.debug("API Key Vault 已初始化")
    
    def store(
        self,
        agent_type: str,
        api_key: str,
        model_name: str = "",
        base_url: str = "",
    ) -> None:
        """
        存储API Key（自动加密）
        
        Args:
            agent_type: Agent类型 (coordinator, modeler, coder, writer)
            api_key: API Key明文
            model_name: 模型名称
            base_url: API基础URL
        """
        if not api_key:
            logger.warning("尝试存储空的 %s API Key", agent_type)
            return
        
        # 加密API Key
        encrypted_key = self._encryption.encrypt(api_key)
        
        # 存储
        self._keys[agent_type] = StoredAPIKey(
            agent_type=agent_type,
            encrypted_key=encrypted_key,
            model_name=model_name,
            base_url=base_url,
        )
        
        logger.info("✅ %s API Key 已安全存储 [%s]", agent_type, mask_api_key(api_key))
    
    def get(self, agent_type: str) -> Optional[str]:
        """
        获取解密后的API Key
        
        Args:
            agent_type: Agent类型
            
        Returns:
            解密后的API Key，不存在返回None
        """
        stored = self._keys.get(agent_type)
        if not stored:
            return None
        
        # 更新使用统计
        stored.use_count += 1
        stored.last_used = datetime.now().isoformat()
        
        # 解密并返回
        return self._encryption.decrypt(stored.encrypted_key)
    
    def get_config(self, agent_type: str) -> Dict[str, Any]:
        """
        获取完整的Agent配置（含解密的API Key）
        
        Args:
            agent_type: Agent类型
            
        Returns:
            配置字典，包含api_key, model, base_url
        """
        stored = self._keys.get(agent_type)
        if not stored:
            return {
                "api_key": None,
                "model": None,
                "base_url": None,
            }
        
        return {
            "api_key": self.get(agent_type),
            "model": stored.model_name,
            "base_url": stored.base_url,
        }
    
    def import_from_settings(
        self,
        coordinator_key: Optional[str] = None,
        coordinator_model: Optional[str] = None,
        coordinator_url: Optional[str] = None,
        modeler_key: Optional[str] = None,
        modeler_model: Optional[str] = None,
        modeler_url: Optional[str] = None,
        coder_key: Optional[str] = None,
        coder_model: Optional[str] = None,
        coder_url: Optional[str] = None,
        writer_key: Optional[str] = None,
        writer_model: Optional[str] = None,
        writer_url: Optional[str] = None,
    ) -> None:
        """
        从配置导入API Keys（兼容旧配置格式）
        
        将明文配置加密存储
        """
        agents = [
            ("coordinator", coordinator_key, coordinator_model, coordinator_url),
            ("modeler", modeler_key, modeler_model, modeler_url),
            ("coder", coder_key, coder_model, coder_url),
            ("writer", writer_key, writer_model, writer_url),
        ]
        
        for agent_type, key, model, url in agents:
            if key and key != "your_api_key_here":
                self.store(
                    agent_type=agent_type,
                    api_key=key,
                    model_name=model or "deepseek-chat",
                    base_url=url or "",
                )
    
    def has_key(self, agent_type: str) -> bool:
        """检查是否存在指定Agent的API Key"""
        return agent_type in self._keys
    
    def list_agents(self) -> list:
        """列出所有已配置的Agent"""
        return list(self._keys.keys())
    
    def get_summary(self) -> Dict[str, str]:
        """
        获取配置摘要（安全显示）
        
        Returns:
            Agent -> 遮蔽后的Key显示
        """
        summary = {}
        for agent_type, stored in self._keys.items():
            try:
                decrypted = self._encryption.decrypt(stored.encrypted_key)
                summary[agent_type] = mask_api_key(decrypted)
            except Exception:
                summary[agent_type] = "❌ 解密失败"
        return summary
    
    def rotate_master_key(self, new_master_key: str) -> None:
        """
        轮换主密钥
        
        Args:
            new_master_key: 新的主密钥
        """
        if not new_master_key or len(new_master_key) < 16:
            raise ValueError("新主密钥长度不足")
        
        new_encryption = EncryptionService(new_master_key)
        
        # 重新加密所有密钥
        for agent_type, stored in self._keys.items():
            # 用旧密钥解密
            plaintext = self._encryption.decrypt(stored.encrypted_key)
            # 用新密钥加密
            stored.encrypted_key = new_encryption.encrypt(plaintext)
        
        # 更新加密服务
        self._master_key = new_master_key
        self._encryption = new_encryption
        
        logger.info("✅ 主密钥轮换完成，所有API Key已重新加密")
    
    def clear(self) -> None:
        """清空所有存储的密钥"""
        self._keys.clear()
        logger.info("✅ API Key Vault 已清空")


# ============= 全局实例 =============

# 延迟初始化的全局Vault实例
_vault_instance: Optional[APIKeyVault] = None


def get_api_key_vault() -> APIKeyVault:
    """
    获取全局API Key Vault实例
    
    Returns:
        APIKeyVault单例
    """
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = APIKeyVault()
    return _vault_instance


# 便捷别名
api_key_vault = get_api_key_vault
