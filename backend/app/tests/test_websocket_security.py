"""
WebSocket 安全模块单元测试 - WebSocket Security Tests

测试内容：
1. JWT 认证验证
2. 未认证用户无法连接
3. 过期 token 自动拒绝
4. token 格式错误处理
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt

from app.utils.auth import SECRET_KEY, ALGORITHM, create_access_token, decode_token


class TestWebSocketAuthentication:
    """WebSocket 认证测试"""
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """测试解码有效令牌"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_decode_expired_token(self):
        """测试解码过期令牌"""
        # 手动创建过期令牌
        expire = datetime.now(timezone.utc) - timedelta(minutes=5)
        to_encode = {
            "sub": "user123",
            "exp": expire,
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        }
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        payload = decode_token(token)
        
        # 过期令牌应该返回 None
        assert payload is None
    
    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        payload = decode_token("invalid.token.here")
        assert payload is None
    
    def test_decode_tampered_token(self):
        """测试解码被篡改的令牌"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        # 篡改令牌
        tampered = token[:-5] + "XXXXX"
        
        payload = decode_token(tampered)
        assert payload is None


@pytest.mark.websocket
class TestWebSocketSecurityIntegration:
    """WebSocket 安全集成测试"""
    
    @pytest.mark.asyncio
    async def test_unauthenticated_connection_rejected(self):
        """测试未认证连接被拒绝"""
        from app.routers.ws_router import _authenticate_websocket
        
        # 模拟 WebSocket 连接
        mock_websocket = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        
        # 认证应该失败（超时）
        result = await _authenticate_websocket(mock_websocket)
        
        assert result is False
        mock_websocket.close.assert_called()
    
    @pytest.mark.asyncio
    async def test_invalid_token_format_rejected(self):
        """测试无效 token 格式被拒绝"""
        from app.routers.ws_router import _authenticate_websocket
        
        mock_websocket = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({"type": "auth", "token": "invalid"})
        )
        
        result = await _authenticate_websocket(mock_websocket)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        """测试过期 token 被拒绝"""
        from app.routers.ws_router import _authenticate_websocket
        
        # 创建过期令牌
        expire = datetime.now(timezone.utc) - timedelta(minutes=5)
        to_encode = {
            "sub": "user123",
            "exp": expire,
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        }
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        mock_websocket = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({"type": "auth", "token": token})
        )
        
        result = await _authenticate_websocket(mock_websocket)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_valid_token_accepted(self):
        """测试有效 token 被接受"""
        from app.routers.ws_router import _authenticate_websocket
        
        # 创建有效令牌
        token = create_access_token({"sub": "user123", "email": "test@example.com"})
        
        mock_websocket = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({"type": "auth", "token": token})
        )
        
        result = await _authenticate_websocket(mock_websocket)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_missing_token_field_rejected(self):
        """测试缺少 token 字段被拒绝"""
        from app.routers.ws_router import _authenticate_websocket
        
        mock_websocket = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({"type": "auth"})
        )
        
        result = await _authenticate_websocket(mock_websocket)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_wrong_message_type_rejected(self):
        """测试错误消息类型被拒绝"""
        from app.routers.ws_router import _authenticate_websocket
        
        token = create_access_token({"sub": "user123"})
        
        mock_websocket = AsyncMock()
        mock_websocket.receive_text = AsyncMock(
            return_value=json.dumps({"type": "message", "token": token})
        )
        
        result = await _authenticate_websocket(mock_websocket)
        
        assert result is False


class TestTokenExpiration:
    """Token 过期时间测试"""
    
    def test_token_has_expiration_claim(self):
        """测试令牌包含过期声明"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert "exp" in payload
        assert "iat" in payload
        
        # exp 应该晚于 iat
        assert payload["exp"] > payload["iat"]
    
    def test_token_expiration_time_configurable(self):
        """测试令牌过期时间可配置"""
        import os
        from datetime import timedelta
        
        # 保存原值
        original = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
        
        try:
            # 设置为 5 分钟
            os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "5"
            
            # 需要重新导入以使用新配置
            from importlib import reload
            import app.utils.auth as auth_module
            reload(auth_module)
            
            token = auth_module.create_access_token({"sub": "user123"})
            payload = auth_module.decode_token(token)
            
            # exp - iat 应该约为 5 分钟
            diff = payload["exp"] - payload["iat"]
            assert diff <= timedelta(minutes=6)  # 允许少量误差
            
        finally:
            # 恢复原值
            if original:
                os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = original
            else:
                os.environ.pop("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", None)
            
            # 重新加载回默认配置
            from importlib import reload
            import app.utils.auth as auth_module
            reload(auth_module)
