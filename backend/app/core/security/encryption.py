"""
加密服务模块 - Encryption Service

提供AES-256-GCM加密功能，用于API Key等敏感数据的安全存储

功能：
1. 对称加密（AES-256-GCM）
2. 密钥派生（PBKDF2）
3. 安全随机数生成
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.utils.log_util import logger


# ============= 常量定义 =============

SALT_LENGTH = 16  # 盐值长度（字节）
NONCE_LENGTH = 12  # GCM nonce长度（字节）
KEY_LENGTH = 32  # AES-256密钥长度（字节）
ITERATIONS = 100_000  # PBKDF2迭代次数


# ============= 工具函数 =============

def generate_encryption_key() -> str:
    """
    生成随机加密主密钥
    
    Returns:
        Base64编码的32字节随机密钥
    """
    random_bytes = secrets.token_bytes(KEY_LENGTH)
    return base64.urlsafe_b64encode(random_bytes).decode()


def _derive_key(master_key: str, salt: bytes) -> bytes:
    """
    使用PBKDF2从主密钥派生加密密钥
    
    Args:
        master_key: 主密钥字符串
        salt: 盐值
        
    Returns:
        派生的32字节密钥
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(master_key.encode("utf-8"))


# ============= 加密结果 =============

@dataclass
class EncryptedData:
    """加密结果数据类"""
    ciphertext: bytes  # 密文
    salt: bytes  # 盐值
    nonce: bytes  # 随机数
    
    def to_string(self) -> str:
        """
        序列化为Base64字符串，格式：base64(salt + nonce + ciphertext)
        """
        combined = self.salt + self.nonce + self.ciphertext
        return base64.urlsafe_b64encode(combined).decode()
    
    @classmethod
    def from_string(cls, encrypted_string: str) -> "EncryptedData":
        """
        从Base64字符串反序列化
        
        Args:
            encrypted_string: Base64编码的加密数据
            
        Returns:
            EncryptedData实例
            
        Raises:
            ValueError: 数据格式不正确
        """
        try:
            combined = base64.urlsafe_b64decode(encrypted_string.encode())
            if len(combined) < SALT_LENGTH + NONCE_LENGTH + 1:
                raise ValueError("加密数据长度不足")
            
            salt = combined[:SALT_LENGTH]
            nonce = combined[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
            ciphertext = combined[SALT_LENGTH + NONCE_LENGTH:]
            
            return cls(ciphertext=ciphertext, salt=salt, nonce=nonce)
        except Exception as e:
            raise ValueError(f"无法解析加密数据: {e}")


# ============= 加密服务 =============

class EncryptionService:
    """
    加密服务类
    
    使用AES-256-GCM提供认证加密，确保：
    - 机密性：数据加密
    - 完整性：GCM认证标签
    - 抗重放：随机nonce
    
    使用示例：
        >>> service = EncryptionService("my-master-key")
        >>> encrypted = service.encrypt("sensitive-api-key")
        >>> decrypted = service.decrypt(encrypted)
    """
    
    def __init__(self, master_key: str):
        """
        初始化加密服务
        
        Args:
            master_key: 主密钥，建议使用generate_encryption_key()生成
            
        Raises:
            ValueError: 主密钥为空
        """
        if not master_key or len(master_key) < 16:
            raise ValueError("主密钥长度不足，建议至少16个字符")
        
        self._master_key = master_key
        logger.debug("加密服务已初始化")
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密明文
        
        Args:
            plaintext: 待加密的明文
            
        Returns:
            Base64编码的加密数据字符串
        """
        if not plaintext:
            return ""
        
        # 生成随机盐值和nonce
        salt = secrets.token_bytes(SALT_LENGTH)
        nonce = secrets.token_bytes(NONCE_LENGTH)
        
        # 派生密钥
        derived_key = _derive_key(self._master_key, salt)
        
        # AES-GCM加密
        aesgcm = AESGCM(derived_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        
        # 封装并返回
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            salt=salt,
            nonce=nonce,
        )
        return encrypted_data.to_string()
    
    def decrypt(self, encrypted_string: str) -> str:
        """
        解密密文
        
        Args:
            encrypted_string: Base64编码的加密数据
            
        Returns:
            解密后的明文
            
        Raises:
            ValueError: 解密失败（数据损坏或密钥错误）
        """
        if not encrypted_string:
            return ""
        
        try:
            # 解析加密数据
            encrypted_data = EncryptedData.from_string(encrypted_string)
            
            # 派生密钥
            derived_key = _derive_key(self._master_key, encrypted_data.salt)
            
            # AES-GCM解密
            aesgcm = AESGCM(derived_key)
            plaintext = aesgcm.decrypt(
                encrypted_data.nonce,
                encrypted_data.ciphertext,
                None,
            )
            
            return plaintext.decode("utf-8")
        
        except Exception as e:
            logger.error("解密失败: %s", e)
            raise ValueError(f"解密失败，请检查主密钥是否正确: {e}")
    
    def is_encrypted(self, data: str) -> bool:
        """
        检查数据是否为加密格式
        
        Args:
            data: 待检查的数据
            
        Returns:
            True如果是加密格式
        """
        if not data:
            return False
        
        try:
            EncryptedData.from_string(data)
            return True
        except (ValueError, Exception):
            return False
    
    def encrypt_if_needed(self, data: str) -> str:
        """
        如果数据未加密则加密，已加密则原样返回
        
        Args:
            data: 待处理的数据
            
        Returns:
            加密后的数据
        """
        if not data:
            return data
        
        if self.is_encrypted(data):
            return data
        
        return self.encrypt(data)
    
    def decrypt_if_needed(self, data: str) -> str:
        """
        如果数据已加密则解密，否则原样返回
        
        Args:
            data: 待处理的数据
            
        Returns:
            解密后的数据
        """
        if not data:
            return data
        
        if not self.is_encrypted(data):
            return data
        
        return self.decrypt(data)


# ============= 哈希工具 =============

def hash_api_key(api_key: str) -> str:
    """
    对API Key进行单向哈希，用于日志记录（不可逆）
    
    Args:
        api_key: API Key明文
        
    Returns:
        SHA256哈希值的前16个字符
    """
    if not api_key:
        return "未设置"
    
    hash_bytes = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return f"{hash_bytes[:8]}...{hash_bytes[-4:]}"


def mask_api_key(api_key: Optional[str]) -> str:
    """
    遮蔽API Key用于安全显示
    
    Args:
        api_key: API Key明文
        
    Returns:
        遮蔽后的显示字符串
    """
    if not api_key or api_key == "your_api_key_here":
        return "❌ 未配置"
    
    if len(api_key) <= 10:
        return f"✅ {api_key[:2]}***"
    
    return f"✅ {api_key[:6]}...{api_key[-4:]}"
