"""
Modeling Router 测试模块
测试建模 API 端点的功能
"""

import pytest
from fastapi.testclient import TestClient


class TestValidateApiKeyEndpoint:
    """测试 API Key 验证端点"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    def test_validate_api_key_request_model(self):
        """测试请求模型"""
        from app.routers.modeling_router import ValidateApiKeyRequest

        request = ValidateApiKeyRequest(
            api_key="test_key",
            base_url="https://api.example.com/v1",
            model_id="gpt-4"
        )

        assert request.api_key == "test_key"
        assert request.model_id == "gpt-4"

    def test_validate_api_key_default_base_url(self):
        """测试默认 base_url"""
        from app.routers.modeling_router import ValidateApiKeyRequest

        request = ValidateApiKeyRequest(
            api_key="test_key",
            model_id="gpt-4"
        )

        assert request.base_url == "https://api.openai.com/v1"


class TestSaveApiConfigEndpoint:
    """测试保存 API 配置端点"""

    def test_save_api_config_request_model(self):
        """测试保存配置请求模型"""
        from app.routers.modeling_router import SaveApiConfigRequest

        request = SaveApiConfigRequest(
            coordinator={"api_key": "key1", "model": "model1"},
            modeler={"api_key": "key2", "model": "model2"},
            coder={"api_key": "key3", "model": "model3"},
            writer={"api_key": "key4", "model": "model4"},
            openalex_email="test@example.com"
        )

        assert request.coordinator["api_key"] == "key1"
        assert request.openalex_email == "test@example.com"


class TestValidateOpenalexEmail:
    """测试 OpenAlex 邮箱验证"""

    def test_validate_email_request_model(self):
        """测试邮箱验证请求模型"""
        from app.routers.modeling_router import ValidateOpenalexEmailRequest

        request = ValidateOpenalexEmailRequest(email="test@example.com")
        assert request.email == "test@example.com"

    def test_validate_email_response_model(self):
        """测试邮箱验证响应模型"""
        from app.routers.modeling_router import ValidateOpenalexEmailResponse

        response = ValidateOpenalexEmailResponse(
            valid=True,
            message="验证成功"
        )

        assert response.valid is True
        assert response.message == "验证成功"


class TestApiKeyValidation:
    """API Key 验证逻辑测试"""

    def test_api_key_response_model(self):
        """测试 API Key 响应模型"""
        from app.routers.modeling_router import ValidateApiKeyResponse

        response = ValidateApiKeyResponse(
            valid=True,
            message="API Key 有效"
        )

        assert response.valid is True

    def test_api_key_invalid_response(self):
        """测试无效 API Key 响应"""
        from app.routers.modeling_router import ValidateApiKeyResponse

        response = ValidateApiKeyResponse(
            valid=False,
            message="API Key 无效"
        )

        assert response.valid is False
        assert "无效" in response.message
