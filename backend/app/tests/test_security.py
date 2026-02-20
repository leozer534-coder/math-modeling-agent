"""
安全模块单元测试 - Security Module Tests

测试内容：
1. 加密/解密功能
2. API Key Vault存储和读取
3. 密钥轮换
"""


import pytest

from app.core.security.api_key_vault import (
    APIKeyVault,
    StoredAPIKey,
)
from app.core.security.encryption import (
    NONCE_LENGTH,
    SALT_LENGTH,
    EncryptedData,
    EncryptionService,
    generate_encryption_key,
    hash_api_key,
    mask_api_key,
)


# ============= Encryption Tests =============

class TestEncryptionService:
    """加密服务测试"""
    
    def test_generate_encryption_key(self):
        """测试生成加密密钥"""
        key = generate_encryption_key()
        assert key is not None
        assert len(key) >= 32  # Base64编码的32字节
        
        # 确保每次生成的密钥不同
        key2 = generate_encryption_key()
        assert key != key2
    
    def test_encrypt_decrypt_roundtrip(self):
        """测试加密解密往返"""
        service = EncryptionService("test-master-key-12345")
        
        plaintext = "sk-1234567890abcdef"
        encrypted = service.encrypt(plaintext)
        
        # 加密后应该不同于明文
        assert encrypted != plaintext
        
        # 解密后应该与原文相同
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        service = EncryptionService("test-master-key-12345")
        
        encrypted = service.encrypt("")
        assert encrypted == ""
        
        decrypted = service.decrypt("")
        assert decrypted == ""
    
    def test_encrypt_unicode(self):
        """测试加密Unicode字符"""
        service = EncryptionService("test-master-key-12345")
        
        plaintext = "中文API密钥🔐"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_different_keys_different_results(self):
        """测试不同密钥产生不同结果"""
        service1 = EncryptionService("master-key-1-12345")
        service2 = EncryptionService("master-key-2-12345")
        
        plaintext = "same-api-key"
        encrypted1 = service1.encrypt(plaintext)
        service2.encrypt(plaintext)
        
        # 不同密钥加密结果不同
        # 注意：由于随机盐值和nonce，即使同一密钥加密结果也不同
        # 但我们确认用错误密钥无法解密
        with pytest.raises(ValueError):
            service2.decrypt(encrypted1)
    
    def test_same_plaintext_different_ciphertext(self):
        """测试相同明文每次加密结果不同（因为随机nonce）"""
        service = EncryptionService("test-master-key-12345")
        
        plaintext = "test-api-key"
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)
        
        # 每次加密结果不同
        assert encrypted1 != encrypted2
        
        # 但都能解密为相同明文
        assert service.decrypt(encrypted1) == plaintext
        assert service.decrypt(encrypted2) == plaintext
    
    def test_decrypt_invalid_data(self):
        """测试解密无效数据"""
        service = EncryptionService("test-master-key-12345")
        
        with pytest.raises(ValueError):
            service.decrypt("not-valid-encrypted-data")
    
    def test_is_encrypted(self):
        """测试检测是否为加密格式"""
        service = EncryptionService("test-master-key-12345")
        
        plaintext = "sk-plain-api-key"
        encrypted = service.encrypt(plaintext)
        
        assert not service.is_encrypted(plaintext)
        assert service.is_encrypted(encrypted)
        assert not service.is_encrypted("")
        assert not service.is_encrypted("random-string")
    
    def test_encrypt_if_needed(self):
        """测试按需加密"""
        service = EncryptionService("test-master-key-12345")
        
        plaintext = "sk-api-key"
        encrypted = service.encrypt(plaintext)
        
        # 明文会被加密
        result1 = service.encrypt_if_needed(plaintext)
        assert result1 != plaintext
        assert service.decrypt(result1) == plaintext
        
        # 已加密的不会再次加密
        result2 = service.encrypt_if_needed(encrypted)
        assert result2 == encrypted
    
    def test_weak_master_key_rejected(self):
        """测试弱主密钥被拒绝"""
        with pytest.raises(ValueError):
            EncryptionService("")
        
        with pytest.raises(ValueError):
            EncryptionService("short")


class TestEncryptedData:
    """加密数据序列化测试"""
    
    def test_serialization_roundtrip(self):
        """测试序列化往返"""
        original = EncryptedData(
            ciphertext=b"test-ciphertext",
            salt=b"0" * SALT_LENGTH,
            nonce=b"1" * NONCE_LENGTH,
        )
        
        serialized = original.to_string()
        restored = EncryptedData.from_string(serialized)
        
        assert restored.ciphertext == original.ciphertext
        assert restored.salt == original.salt
        assert restored.nonce == original.nonce
    
    def test_invalid_string_rejected(self):
        """测试无效字符串被拒绝"""
        with pytest.raises(ValueError):
            EncryptedData.from_string("invalid")
        
        with pytest.raises(ValueError):
            EncryptedData.from_string("YWJj")  # 太短


class TestHashAndMask:
    """哈希和遮蔽测试"""
    
    def test_hash_api_key(self):
        """测试API Key哈希"""
        result = hash_api_key("sk-1234567890")
        assert "..." in result
        assert len(result) < 20
        
        # 相同输入相同输出
        assert hash_api_key("sk-1234567890") == result
        
        # 不同输入不同输出
        assert hash_api_key("sk-different") != result
    
    def test_hash_empty_key(self):
        """测试哈希空密钥"""
        assert hash_api_key("") == "未设置"
        assert hash_api_key(None) == "未设置"
    
    def test_mask_api_key(self):
        """测试遮蔽API Key"""
        assert mask_api_key("sk-1234567890abcdef") == "✅ sk-123...cdef"
        assert mask_api_key("short") == "✅ sh***"
        assert mask_api_key("") == "❌ 未配置"
        assert mask_api_key(None) == "❌ 未配置"
        assert mask_api_key("your_api_key_here") == "❌ 未配置"


# ============= API Key Vault Tests =============

class TestAPIKeyVault:
    """API Key Vault测试"""
    
    def test_store_and_get(self):
        """测试存储和获取"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.store("coordinator", "sk-test-key", "gpt-4", "https://api.openai.com")
        
        retrieved = vault.get("coordinator")
        assert retrieved == "sk-test-key"
    
    def test_get_nonexistent(self):
        """测试获取不存在的密钥"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        assert vault.get("nonexistent") is None
    
    def test_get_config(self):
        """测试获取完整配置"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.store("modeler", "sk-modeler-key", "deepseek-chat", "https://api.deepseek.com")
        
        config = vault.get_config("modeler")
        assert config["api_key"] == "sk-modeler-key"
        assert config["model"] == "deepseek-chat"
        assert config["base_url"] == "https://api.deepseek.com"
    
    def test_has_key(self):
        """测试检查密钥存在"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        assert not vault.has_key("coder")
        
        vault.store("coder", "sk-coder-key", "claude-3", "")
        
        assert vault.has_key("coder")
    
    def test_list_agents(self):
        """测试列出所有Agent"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.store("coordinator", "key1", "", "")
        vault.store("modeler", "key2", "", "")
        
        agents = vault.list_agents()
        assert "coordinator" in agents
        assert "modeler" in agents
        assert len(agents) == 2
    
    def test_get_summary(self):
        """测试获取摘要"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.store("writer", "sk-1234567890abcdef", "gpt-4", "")
        
        summary = vault.get_summary()
        assert "writer" in summary
        assert "✅" in summary["writer"]
        assert "sk-123" in summary["writer"]  # 开头部分可见

    
    def test_import_from_settings(self):
        """测试从配置导入"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.import_from_settings(
            coordinator_key="coord-key",
            coordinator_model="gpt-4",
            modeler_key="mod-key",
            modeler_model="deepseek-chat",
        )
        
        assert vault.get("coordinator") == "coord-key"
        assert vault.get("modeler") == "mod-key"
    
    def test_ignore_placeholder_keys(self):
        """测试忽略占位符密钥"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.import_from_settings(
            coordinator_key="your_api_key_here",
        )
        
        assert not vault.has_key("coordinator")
    
    def test_use_count_tracking(self):
        """测试使用次数跟踪"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.store("coordinator", "sk-key", "", "")
        
        # 获取3次
        vault.get("coordinator")
        vault.get("coordinator")
        vault.get("coordinator")
        
        stored = vault._keys["coordinator"]
        assert stored.use_count == 3
        assert stored.last_used is not None
    
    def test_rotate_master_key(self):
        """测试密钥轮换"""
        vault = APIKeyVault(master_key="old-master-key-123")
        
        vault.store("coordinator", "sk-secret-key", "gpt-4", "")
        
        # 轮换密钥
        vault.rotate_master_key("new-master-key-456")
        
        # 仍能正确解密
        assert vault.get("coordinator") == "sk-secret-key"
    
    def test_clear(self):
        """测试清空Vault"""
        vault = APIKeyVault(master_key="test-vault-key-123")
        
        vault.store("coordinator", "key1", "", "")
        vault.store("modeler", "key2", "", "")
        
        vault.clear()
        
        assert vault.list_agents() == []


class TestStoredAPIKey:
    """存储的API Key数据类测试"""
    
    def test_to_dict(self):
        """测试转字典"""
        stored = StoredAPIKey(
            agent_type="coordinator",
            encrypted_key="encrypted",
            model_name="gpt-4",
            base_url="https://api.openai.com",
        )
        
        data = stored.to_dict()
        assert data["agent_type"] == "coordinator"
        assert data["encrypted_key"] == "encrypted"
        assert data["model_name"] == "gpt-4"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "agent_type": "modeler",
            "encrypted_key": "encrypted",
            "model_name": "deepseek",
            "base_url": "",
        }
        
        stored = StoredAPIKey.from_dict(data)
        assert stored.agent_type == "modeler"
        assert stored.encrypted_key == "encrypted"
