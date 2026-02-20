from pydantic import BeforeValidator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Annotated, Optional, Self

from app.utils.log_util import logger


def parse_cors(value: str) -> list[str]:
    """
    Parses the CORS settings from a string to a list of URLs.
    """
    if value == "*":
        return ["*"]
    if "," in value:
        return [url.strip() for url in value.split(",")]
    return [value]


class Settings(BaseSettings):
    ENV: str

    COORDINATOR_API_KEY: Optional[str] = None
    COORDINATOR_MODEL: Optional[str] = None
    COORDINATOR_BASE_URL: Optional[str] = None

    MODELER_API_KEY: Optional[str] = None
    MODELER_MODEL: Optional[str] = None
    MODELER_BASE_URL: Optional[str] = None

    CODER_API_KEY: Optional[str] = None
    CODER_MODEL: Optional[str] = None
    CODER_BASE_URL: Optional[str] = None

    WRITER_API_KEY: Optional[str] = None
    WRITER_MODEL: Optional[str] = None
    WRITER_BASE_URL: Optional[str] = None

    MAX_CHAT_TURNS: int = 60
    MAX_RETRIES: int = 5
    CODE_EXECUTION_TIMEOUT: int = 3000
    E2B_API_KEY: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10
    CORS_ALLOW_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors)] = "*"
    SERVER_HOST: str = "http://localhost:8000"
    OPENALEX_EMAIL: Optional[str] = None

    # 质量评审配置
    ENABLE_REVIEW: bool = True  # 是否启用质量评审阶段
    REVIEW_MIN_SCORE: int = 3   # 评审最低通过分（1-5），低于此分触发警告

    # HIL (Human-in-Loop) 配置
    HIL_RESPONSE_TIMEOUT: int = 300
    HIL_MAX_HISTORY: int = 100

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./mathmodel.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @model_validator(mode="after")
    def _validate_agent_configs(self) -> Self:
        """启动时验证各 Agent 的关键配置项。

        生产环境：缺失 API_KEY 或 MODEL 则抛出 ValueError 阻止启动。
        开发/测试环境：缺失时仅输出 warning，不阻断启动。
        """
        _AGENTS = ("COORDINATOR", "MODELER", "CODER", "WRITER")
        _REQUIRED_SUFFIXES = ("API_KEY", "MODEL")

        is_dev_or_test = self.ENV.lower() in ("dev", "development", "test", "testing")

        missing: list[str] = []
        for agent in _AGENTS:
            for suffix in _REQUIRED_SUFFIXES:
                field_name = f"{agent}_{suffix}"
                value = getattr(self, field_name, None)
                if not value:
                    missing.append(field_name)

        if missing:
            detail = ", ".join(missing)
            if is_dev_or_test:
                logger.warning(
                    "以下配置项未设置（开发/测试环境允许跳过）: %s",
                    detail,
                )
            else:
                raise ValueError(
                    f"生产环境启动失败: 以下必需配置项未设置: {detail}。"
                    "请在环境变量或 .env 文件中配置后重试。"
                )

        return self

    def is_production(self) -> bool:
        """判断当前是否为生产环境。"""
        return self.ENV.lower() in ("production", "prod")

    def get_cors_origins(self) -> list[str]:
        """获取安全的 CORS 来源列表。

        生产环境下禁止使用通配符 '*'，必须显式配置允许的域名。
        开发环境允许通配符以方便调试。
        """
        origins = self.CORS_ALLOW_ORIGINS
        if isinstance(origins, str):
            origins = parse_cors(origins)

        if self.is_production() and "*" in origins:
            logger.warning(
                "生产环境检测到 CORS_ALLOW_ORIGINS='*'，已回退为仅允许同源访问。"
                "请在环境变量中配置具体的允许域名，例如: "
                "CORS_ALLOW_ORIGINS=https://example.com,https://app.example.com"
            )
            # 生产环境回退为仅允许 SERVER_HOST
            return [self.SERVER_HOST]

        return origins

    @classmethod
    def from_env(cls, env: str = None):
        env = env or os.getenv("ENV", "dev")
        env_file = f".env.{env.lower()}"
        return cls(_env_file=env_file, _env_file_encoding="utf-8")


settings = Settings()
