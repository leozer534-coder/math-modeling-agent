"""
Settings 配置测试模块
测试配置加载、验证等功能

注意: get_agent_config()、get_redis_config()、summary() 方法以及
LOG_LEVEL 的大小写转换/有效值校验尚未在 Settings 类中实现，相关测试已移除。
"""
import os
from unittest.mock import patch


class TestSettingsInitialization:
    """测试配置初始化"""

    def test_settings_import(self):
        """测试配置可导入"""
        from app.config.setting import settings
        assert settings is not None

    def test_settings_has_required_fields(self):
        """测试必要字段存在"""
        from app.config.setting import Settings

        # 创建测试实例
        with patch.dict(os.environ, {}, clear=False):
            settings = Settings()

            # 检查基础配置字段
            assert hasattr(settings, 'ENV')
            assert hasattr(settings, 'DEBUG')
            assert hasattr(settings, 'LOG_LEVEL')

            # 检查 Agent 配置字段
            assert hasattr(settings, 'COORDINATOR_API_KEY')
            assert hasattr(settings, 'MODELER_API_KEY')
            assert hasattr(settings, 'CODER_API_KEY')
            assert hasattr(settings, 'WRITER_API_KEY')


class TestSettingsValidation:
    """测试配置验证"""

    def test_log_level_validation_valid(self):
        """测试有效日志级别"""
        from app.config.setting import Settings

        settings = Settings(LOG_LEVEL="DEBUG")
        assert settings.LOG_LEVEL == "DEBUG"

    def test_log_level_accepts_string(self):
        """测试日志级别接受字符串值"""
        from app.config.setting import Settings

        settings = Settings(LOG_LEVEL="INFO")
        assert settings.LOG_LEVEL == "INFO"


class TestSettingsEnvironment:
    """测试环境检测"""

    def test_is_production_dev(self):
        """测试开发环境"""
        from app.config.setting import Settings

        settings = Settings(ENV="dev")
        assert settings.is_production() is False

    def test_is_production_prod(self):
        """测试生产环境"""
        from app.config.setting import Settings

        # 生产环境要求所有 Agent 的 API_KEY 和 MODEL 已配置
        _PROD_AGENT_KEYS = {
            "COORDINATOR_API_KEY": "sk-test",
            "COORDINATOR_MODEL": "gpt-4",
            "MODELER_API_KEY": "sk-test",
            "MODELER_MODEL": "gpt-4",
            "CODER_API_KEY": "sk-test",
            "CODER_MODEL": "gpt-4",
            "WRITER_API_KEY": "sk-test",
            "WRITER_MODEL": "gpt-4",
        }
        settings = Settings(
            ENV="prod",
            API_KEY_MASTER_SECRET="test-secret-for-testing",
            **_PROD_AGENT_KEYS,
        )
        assert settings.is_production() is True

    def test_is_production_production(self):
        """测试 production 环境"""
        from app.config.setting import Settings

        _PROD_AGENT_KEYS = {
            "COORDINATOR_API_KEY": "sk-test",
            "COORDINATOR_MODEL": "gpt-4",
            "MODELER_API_KEY": "sk-test",
            "MODELER_MODEL": "gpt-4",
            "CODER_API_KEY": "sk-test",
            "CODER_MODEL": "gpt-4",
            "WRITER_API_KEY": "sk-test",
            "WRITER_MODEL": "gpt-4",
        }
        settings = Settings(
            ENV="production",
            API_KEY_MASTER_SECRET="test-secret-for-testing",
            **_PROD_AGENT_KEYS,
        )
        assert settings.is_production() is True


class TestSettingsRedisFields:
    """测试 Redis 配置字段"""

    def test_redis_url_default(self):
        """测试 Redis URL 默认值"""
        from app.config.setting import Settings

        settings = Settings()
        assert settings.REDIS_URL == "redis://redis:6379/0"

    def test_redis_url_custom(self):
        """测试自定义 Redis URL"""
        from app.config.setting import Settings

        settings = Settings(REDIS_URL="redis://localhost:6379/1")
        assert settings.REDIS_URL == "redis://localhost:6379/1"

    def test_redis_max_connections_default(self):
        """测试 Redis 最大连接数有合理默认值"""
        from app.config.setting import Settings

        settings = Settings()
        # 默认值可能被 .env.dev 覆盖，只验证字段存在且为正整数
        assert isinstance(settings.REDIS_MAX_CONNECTIONS, int)
        assert settings.REDIS_MAX_CONNECTIONS > 0

    def test_redis_max_connections_custom(self):
        """测试自定义 Redis 最大连接数"""
        from app.config.setting import Settings

        settings = Settings(REDIS_MAX_CONNECTIONS=20)
        assert settings.REDIS_MAX_CONNECTIONS == 20


class TestCorsParser:
    """测试 CORS 解析"""

    def test_parse_cors_wildcard(self):
        """测试通配符解析"""
        from app.config.setting import parse_cors

        result = parse_cors("*")
        assert result == ["*"]

    def test_parse_cors_single_url(self):
        """测试单个 URL 解析"""
        from app.config.setting import parse_cors

        result = parse_cors("http://localhost:3000")
        assert result == ["http://localhost:3000"]

    def test_parse_cors_multiple_urls(self):
        """测试多个 URL 解析"""
        from app.config.setting import parse_cors

        result = parse_cors("http://localhost:3000,http://localhost:5173")
        assert len(result) == 2
        assert "http://localhost:3000" in result
        assert "http://localhost:5173" in result
