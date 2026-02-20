"""用户 API 配置数据模型

存储每个用户针对不同 Agent 的 LLM API 配置，
解决全局 settings 单例在多用户并发时互相覆盖的问题。
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, UniqueConstraint

from app.config.database import Base
from app.models.user import generate_uuid


# 支持的 Agent 类型
VALID_AGENT_TYPES = ("coordinator", "modeler", "coder", "writer")


class UserApiConfig(Base):
    """用户 API 配置模型

    每个用户可以为每种 Agent 类型单独配置 API Key、模型和接口地址。
    通过 (user_id, agent_type) 唯一约束保证同一用户同一 Agent 只有一条配置。
    """

    __tablename__ = "user_api_configs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "agent_type",
            name="uq_user_agent_type",
        ),
    )

    # 主键
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # 关联用户（与 users 表的 id 对应）
    user_id = Column(String(36), nullable=False, index=True)

    # Agent 类型：coordinator / modeler / coder / writer
    agent_type = Column(String(20), nullable=False)

    # LLM API Key（AES-256-GCM 加密存储，由 UserConfigService 负责加解密）
    api_key = Column(String(500), nullable=False)

    # 模型标识，如 deepseek-chat、gpt-4o、claude-sonnet-4-20250514 等
    model_id = Column(String(100), nullable=True, default="deepseek-chat")

    # API 基础地址，如 https://api.deepseek.com
    base_url = Column(String(500), nullable=True)

    # API 兼容格式：openai / anthropic / gemini
    provider = Column(String(50), nullable=True, default="openai")

    # 是否启用该配置
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    @classmethod
    def mask_api_key(cls, key: str) -> str:
        """对 API Key 进行掩码处理，仅保留前6位和后4位

        Args:
            key: 原始 API Key

        Returns:
            掩码后的字符串，如 "sk-abc1***xyz9"
        """
        if not key:
            return ""
        if len(key) <= 10:
            # Key 太短时只显示前2位
            return f"{key[:2]}***"
        return f"{key[:6]}***{key[-4:]}"

    def to_dict(self, decrypted_key: str | None = None) -> dict:
        """转换为安全字典，api_key 仅返回掩码值

        Args:
            decrypted_key: 已解密的 API Key 明文（可选）。
                如果传入则对明文做掩码；否则对数据库原始值做掩码
                （加密后的密文掩码无实际意义，建议传入解密值）。

        Returns:
            不含敏感信息的字典表示
        """
        display_key = decrypted_key if decrypted_key else self.api_key
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "api_key": self.mask_api_key(display_key),
            "model_id": self.model_id,
            "base_url": self.base_url,
            "provider": self.provider,
            "is_active": self.is_active,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


class UserProviderConfig(Base):
    """用户供应商配置模型

    存储前端供应商配置，API Key 使用 AES-256-GCM 加密存储。
    一个供应商可以被分配给多个 Agent 使用。
    与 UserApiConfig（按 Agent 维度）不同，此表按供应商维度存储。
    """

    __tablename__ = "user_provider_configs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider_id",
            name="uq_user_provider_id",
        ),
    )

    # 主键
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # 关联用户
    user_id = Column(String(36), nullable=False, index=True)

    # 前端生成的供应商 ID（如 provider_1234567890）
    provider_id = Column(String(100), nullable=False)

    # 供应商名称（如 DeepSeek、OpenAI）
    name = Column(String(100), nullable=False)

    # API Key（AES-256-GCM 加密存储）
    api_key = Column(String(500), nullable=False)

    # API 基础地址
    base_url = Column(String(500), nullable=True)

    # 模型标识
    model_id = Column(String(100), nullable=True, default="deepseek-chat")

    # API 协议格式：openai / anthropic / gemini
    api_format = Column(String(20), nullable=True, default="openai")

    # 连接状态：valid / invalid / untested
    status = Column(String(20), nullable=True, default="untested")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class UserAgentAssignment(Base):
    """用户 Agent 分配配置

    存储每个 Agent 使用的供应商 provider_id。
    每个用户只有一条分配记录（upsert 语义）。
    """

    __tablename__ = "user_agent_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_assignment"),
    )

    # 主键
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # 关联用户
    user_id = Column(String(36), nullable=False, index=True)

    # 每个 Agent 对应的 provider_id
    coordinator = Column(String(100), nullable=True, default="")
    modeler = Column(String(100), nullable=True, default="")
    coder = Column(String(100), nullable=True, default="")
    writer = Column(String(100), nullable=True, default="")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class UserOpenAlexConfig(Base):
    """用户 OpenAlex 配置模型

    存储用户用于 OpenAlex 学术搜索服务的邮箱配置。
    OpenAlex 的 Polite Pool 需要提供邮箱以获得更高的速率限制。
    """

    __tablename__ = "user_openalex_configs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_user_openalex",
        ),
    )

    # 主键
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # 关联用户
    user_id = Column(String(36), nullable=False, index=True)

    # OpenAlex 邮箱
    email = Column(String(255), nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self) -> dict:
        """转换为字典表示"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }
