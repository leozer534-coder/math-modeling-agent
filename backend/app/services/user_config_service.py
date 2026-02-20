"""
用户API配置服务层

封装用户级别的 API 配置 CRUD 操作，
当用户未配置时回退到全局 settings 默认值。

安全特性：
- API Key 使用 AES-256-GCM 加密后存储到数据库
- 读取时自动解密，兼容历史明文数据（encrypt_if_needed / decrypt_if_needed）
- 主密钥通过 settings.API_KEY_MASTER_SECRET 配置，未设置时使用开发模式回退
"""

import uuid

from sqlalchemy import delete, select

from app.config.database import AsyncSessionLocal
from app.config.setting import settings
from app.core.security.encryption import EncryptionService
from app.models.user_api_config import (
    UserAgentAssignment,
    UserApiConfig,
    UserOpenAlexConfig,
    UserProviderConfig,
)
from app.utils.log_util import logger


# 支持的 Agent 类型列表
AGENT_TYPES = ("coordinator", "modeler", "coder", "writer")

# 开发环境回退密钥（生产环境必须通过 API_KEY_MASTER_SECRET 设置）
_DEV_MASTER_KEY = "mathmodel-dev-key-do-not-use-in-prod"


def _get_encryption_service() -> EncryptionService:
    """获取加密服务单例

    优先使用 settings.API_KEY_MASTER_SECRET，
    未设置时回退到开发环境密钥并打印警告。

    Returns:
        已初始化的 EncryptionService 实例
    """
    master_key = settings.API_KEY_MASTER_SECRET
    if not master_key:
        if settings.is_production():
            logger.error(
                "⛔ 生产环境未设置 API_KEY_MASTER_SECRET，"
                "API Key 加密将使用不安全的回退密钥！"
            )
        else:
            logger.debug(
                "使用开发环境回退密钥（非生产环境）"
            )
        master_key = _DEV_MASTER_KEY
    return EncryptionService(master_key)


class UserConfigService:
    """用户API配置服务"""

    # ------------------------------------------------------------------
    #  单个 Agent 配置
    # ------------------------------------------------------------------

    @staticmethod
    async def save_agent_config(
        user_id: str,
        agent_type: str,
        api_key: str,
        model_id: str,
        base_url: str | None = None,
        provider: str = "openai",
    ) -> UserApiConfig:
        """
        保存或更新某个 Agent 的 API 配置（upsert 语义）

        API Key 在写入数据库前会使用 AES-256-GCM 加密。

        Args:
            user_id: 用户ID
            agent_type: Agent 类型 (coordinator/modeler/coder/writer)
            api_key: API Key（明文，内部自动加密后存储）
            model_id: 模型ID
            base_url: API 基础URL
            provider: LLM 提供商

        Returns:
            保存后的 UserApiConfig 实例
        """
        agent_type = agent_type.lower()
        try:
            # 加密 API Key（幂等：已加密的不会重复加密）
            encryption = _get_encryption_service()
            encrypted_key = encryption.encrypt_if_needed(api_key)

            async with AsyncSessionLocal() as session:
                # 查询是否已存在
                stmt = select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.agent_type == agent_type,
                )
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()

                if config:
                    # 更新已有记录
                    config.api_key = encrypted_key
                    config.model_id = model_id
                    config.base_url = base_url
                    config.provider = provider
                    config.is_active = True
                    logger.debug(
                        "更新用户 %s 的 %s 配置（已加密）", user_id, agent_type
                    )
                else:
                    # 创建新记录
                    config = UserApiConfig(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        agent_type=agent_type,
                        api_key=encrypted_key,
                        model_id=model_id,
                        base_url=base_url,
                        provider=provider,
                        is_active=True,
                    )
                    session.add(config)
                    logger.debug(
                        "创建用户 %s 的 %s 配置（已加密）", user_id, agent_type
                    )

                await session.commit()
                await session.refresh(config)
                return config

        except Exception as e:
            logger.error(
                "保存用户 %s 的 %s 配置失败: %s", user_id, agent_type, e
            )
            raise

    # ------------------------------------------------------------------
    #  批量保存
    # ------------------------------------------------------------------

    @staticmethod
    async def save_all_configs(
        user_id: str, configs: dict
    ) -> list[UserApiConfig]:
        """
        批量保存所有 Agent 配置

        Args:
            user_id: 用户ID
            configs: 配置字典，格式示例::

                {
                    "coordinator": {
                        "apiKey": "sk-xxx",
                        "modelId": "deepseek-chat",
                        "baseUrl": "https://api.deepseek.com",
                        "provider": "openai",
                    },
                    ...
                }

        Returns:
            保存后的 UserApiConfig 列表
        """
        saved: list[UserApiConfig] = []
        try:
            for agent_type, cfg in configs.items():
                agent_type = agent_type.lower()
                if agent_type not in AGENT_TYPES:
                    logger.warning(
                        "跳过未知的 Agent 类型: %s", agent_type
                    )
                    continue

                api_key = cfg.get("apiKey") or cfg.get("api_key")
                if not api_key:
                    # 没有提供 API Key 则跳过该 Agent
                    continue

                model_id = (
                    cfg.get("modelId")
                    or cfg.get("model_id")
                    or cfg.get("model")
                    or "deepseek-chat"
                )
                base_url = (
                    cfg.get("baseUrl")
                    or cfg.get("base_url")
                )
                provider = cfg.get("provider", "openai")

                result = await UserConfigService.save_agent_config(
                    user_id=user_id,
                    agent_type=agent_type,
                    api_key=api_key,
                    model_id=model_id,
                    base_url=base_url,
                    provider=provider,
                )
                saved.append(result)

            logger.info(
                "批量保存用户 %s 的 %s 个 Agent 配置", user_id, len(saved)
            )
            return saved

        except Exception as e:
            logger.error(
                "批量保存用户 %s 配置失败: %s", user_id, e
            )
            raise

    # ------------------------------------------------------------------
    #  查询单个 Agent 配置
    # ------------------------------------------------------------------

    @staticmethod
    async def get_agent_config(
        user_id: str, agent_type: str
    ) -> dict | None:
        """
        获取某个 Agent 的配置

        数据库中存储的是加密后的 API Key，此方法自动解密后返回明文。

        Args:
            user_id: 用户ID
            agent_type: Agent 类型

        Returns:
            配置字典 {"api_key": ..., "model": ..., "base_url": ...}
            或 None（用户未配置该 Agent）
        """
        agent_type = agent_type.lower()
        try:
            encryption = _get_encryption_service()

            async with AsyncSessionLocal() as session:
                stmt = select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.agent_type == agent_type,
                    UserApiConfig.is_active.is_(True),
                )
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()

                if config is None:
                    return None

                # 解密 API Key（兼容历史明文数据）
                decrypted_key = encryption.decrypt_if_needed(
                    config.api_key
                )

                return {
                    "api_key": decrypted_key,
                    "model": config.model_id,
                    "base_url": config.base_url,
                    "provider": config.provider,
                }

        except Exception as e:
            logger.error(
                "获取用户 %s 的 %s 配置失败: %s", user_id, agent_type, e
            )
            return None

    # ------------------------------------------------------------------
    #  获取全局 settings 的回退值
    # ------------------------------------------------------------------

    @staticmethod
    def _get_fallback(agent_type: str) -> dict:
        """
        从全局 settings 获取指定 Agent 的回退配置

        Args:
            agent_type: Agent 类型（小写）

        Returns:
            回退配置字典
        """
        upper = agent_type.upper()
        return {
            "api_key": getattr(settings, f"{upper}_API_KEY", None),
            "model": getattr(
                settings, f"{upper}_MODEL", "deepseek-chat"
            ),
            "base_url": getattr(settings, f"{upper}_BASE_URL", None),
        }

    # ------------------------------------------------------------------
    #  查询所有 Agent 配置（带回退）
    # ------------------------------------------------------------------

    @staticmethod
    async def get_all_configs(user_id: str) -> dict:
        """
        获取用户所有 Agent 配置

        如果某个 Agent 没有用户级配置，回退到全局 settings 默认值。
        数据库中的 API Key 自动解密后返回明文。

        Args:
            user_id: 用户ID

        Returns:
            格式示例::

                {
                    "coordinator": {"api_key": "...", "model": "...", "base_url": "..."},
                    "modeler":     {...},
                    "coder":       {...},
                    "writer":      {...},
                }
        """
        all_configs: dict = {}
        try:
            encryption = _get_encryption_service()

            async with AsyncSessionLocal() as session:
                stmt = select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.is_active.is_(True),
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                # 将数据库记录按 agent_type 索引
                db_map: dict[str, UserApiConfig] = {
                    row.agent_type: row for row in rows
                }

            for agent_type in AGENT_TYPES:
                if agent_type in db_map:
                    row = db_map[agent_type]
                    # 解密 API Key（兼容历史明文数据）
                    decrypted_key = encryption.decrypt_if_needed(
                        row.api_key
                    )
                    all_configs[agent_type] = {
                        "api_key": decrypted_key,
                        "model": row.model_id,
                        "base_url": row.base_url,
                        "provider": row.provider,
                    }
                else:
                    # 回退到全局 settings（明文，不需要解密）
                    all_configs[agent_type] = (
                        UserConfigService._get_fallback(agent_type)
                    )

            return all_configs

        except Exception as e:
            logger.error(
                "获取用户 %s 所有配置失败: %s", user_id, e
            )
            # 出错时全部使用全局回退
            return {
                at: UserConfigService._get_fallback(at)
                for at in AGENT_TYPES
            }

    # ------------------------------------------------------------------
    #  获取 LLMFactory 专用配置
    # ------------------------------------------------------------------

    @staticmethod
    async def get_llm_factory_config(user_id: str) -> dict:
        """
        获取用于 LLMFactory 的配置字典

        每个 Agent 先查用户配置，没有则回退全局 settings。
        返回格式与 ``get_all_configs`` 一致，但保证每个 Agent 都有值。

        Args:
            user_id: 用户ID

        Returns:
            格式示例::

                {
                    "coordinator": {"api_key": "...", "model": "...", "base_url": "..."},
                    "modeler":     {"api_key": "...", "model": "...", "base_url": "..."},
                    "coder":       {"api_key": "...", "model": "...", "base_url": "..."},
                    "writer":      {"api_key": "...", "model": "...", "base_url": "..."},
                }
        """
        return await UserConfigService.get_all_configs(user_id)

    # ------------------------------------------------------------------
    #  OpenAlex 邮箱
    # ------------------------------------------------------------------

    @staticmethod
    async def save_openalex_email(
        user_id: str, email: str
    ) -> None:
        """
        保存 OpenAlex Email（upsert 语义）

        Args:
            user_id: 用户ID
            email: OpenAlex 邮箱
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserOpenAlexConfig).where(
                    UserOpenAlexConfig.user_id == user_id,
                )
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()

                if config:
                    config.email = email
                    logger.debug(
                        "更新用户 %s 的 OpenAlex 邮箱", user_id
                    )
                else:
                    config = UserOpenAlexConfig(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        email=email,
                    )
                    session.add(config)
                    logger.debug(
                        "创建用户 %s 的 OpenAlex 邮箱", user_id
                    )

                await session.commit()

        except Exception as e:
            logger.error(
                "保存用户 %s OpenAlex 邮箱失败: %s", user_id, e
            )
            raise

    @staticmethod
    async def get_openalex_email(user_id: str) -> str | None:
        """
        获取 OpenAlex Email，未配置则回退到 settings.OPENALEX_EMAIL

        Args:
            user_id: 用户ID

        Returns:
            邮箱字符串或 None
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserOpenAlexConfig).where(
                    UserOpenAlexConfig.user_id == user_id,
                )
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()

                if config and config.email:
                    return config.email

        except Exception as e:
            logger.error(
                "获取用户 %s OpenAlex 邮箱失败: %s", user_id, e
            )

        # 回退到全局设置
        return settings.OPENALEX_EMAIL

    # ------------------------------------------------------------------
    #  前端安全查询（API Key 掩码）
    # ------------------------------------------------------------------

    @staticmethod
    async def get_all_configs_masked(user_id: str) -> dict:
        """获取用户所有 Agent 配置（API Key 掩码处理，供前端展示）

        与 ``get_all_configs`` 不同，此方法不会返回明文 API Key，
        仅返回掩码后的 Key 用于前端展示是否已配置。

        Args:
            user_id: 用户ID

        Returns:
            格式示例::

                {
                    "configs": {
                        "coordinator": {
                            "api_key_masked": "sk-abc1***xyz9",
                            "has_key": true,
                            "model_id": "deepseek-chat",
                            "base_url": "https://api.deepseek.com",
                            "provider": "openai",
                        },
                        ...
                    },
                    "openalex_email": "user@example.com",
                }
        """
        result: dict = {"configs": {}, "openalex_email": None}
        try:
            encryption = _get_encryption_service()

            async with AsyncSessionLocal() as session:
                stmt = select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.is_active.is_(True),
                )
                db_result = await session.execute(stmt)
                rows = db_result.scalars().all()

                db_map: dict[str, UserApiConfig] = {
                    row.agent_type: row for row in rows
                }

            for agent_type in AGENT_TYPES:
                if agent_type in db_map:
                    row = db_map[agent_type]
                    # 解密后做掩码，不返回明文
                    try:
                        decrypted_key = encryption.decrypt_if_needed(
                            row.api_key
                        )
                        masked_key = UserApiConfig.mask_api_key(
                            decrypted_key
                        )
                    except Exception:
                        masked_key = "***解密失败***"

                    result["configs"][agent_type] = {
                        "api_key_masked": masked_key,
                        "has_key": bool(row.api_key),
                        "model_id": row.model_id,
                        "base_url": row.base_url,
                        "provider": row.provider,
                    }
                else:
                    # 检查全局 settings 是否有回退配置
                    fallback = UserConfigService._get_fallback(
                        agent_type
                    )
                    has_fallback = bool(fallback.get("api_key"))
                    result["configs"][agent_type] = {
                        "api_key_masked": (
                            UserApiConfig.mask_api_key(
                                fallback["api_key"]
                            )
                            if has_fallback
                            else ""
                        ),
                        "has_key": has_fallback,
                        "model_id": fallback.get("model", "deepseek-chat"),
                        "base_url": fallback.get("base_url"),
                        "provider": None,
                        "source": "global_fallback",
                    }

            # 获取 OpenAlex 邮箱
            result["openalex_email"] = (
                await UserConfigService.get_openalex_email(user_id)
            )

            return result

        except Exception as e:
            logger.error(
                "获取用户 %s 掩码配置失败: %s", user_id, e
            )
            return result

    @staticmethod
    async def delete_agent_config(
        user_id: str, agent_type: str
    ) -> bool:
        """删除用户指定 Agent 的 API 配置

        Args:
            user_id: 用户ID
            agent_type: Agent 类型

        Returns:
            True 表示删除成功
        """
        agent_type = agent_type.lower()
        try:
            async with AsyncSessionLocal() as session:
                stmt = delete(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.agent_type == agent_type,
                )
                result = await session.execute(stmt)
                await session.commit()

                deleted = result.rowcount > 0
                if deleted:
                    logger.info(
                        "已删除用户 %s 的 %s 配置", user_id, agent_type
                    )
                return deleted

        except Exception as e:
            logger.error(
                "删除用户 %s 的 %s 配置失败: %s", user_id, agent_type, e
            )
            raise

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    async def has_complete_config(user_id: str) -> bool:
        """
        检查用户是否配置了所有 4 个 Agent 的 API Key

        注意：数据库中存储的是加密后的 API Key，
        非空字符串即表示已配置（无需解密验证）。

        Args:
            user_id: 用户ID

        Returns:
            True 表示 4 个 Agent 全部配置完毕
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.is_active.is_(True),
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                # 加密后的 key 不为空即代表已配置
                configured_types = {
                    row.agent_type
                    for row in rows
                    if row.api_key
                }
                return set(AGENT_TYPES).issubset(configured_types)

        except Exception as e:
            logger.error(
                "检查用户 %s 配置完整性失败: %s", user_id, e
            )
            return False

    @staticmethod
    async def delete_all_configs(user_id: str) -> None:
        """
        删除用户所有 API 配置（包括 OpenAlex 邮箱）

        Args:
            user_id: 用户ID
        """
        try:
            async with AsyncSessionLocal() as session:
                # 删除 Agent 配置
                stmt_api = delete(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                )
                await session.execute(stmt_api)

                # 删除 OpenAlex 配置
                stmt_alex = delete(UserOpenAlexConfig).where(
                    UserOpenAlexConfig.user_id == user_id,
                )
                await session.execute(stmt_alex)

                await session.commit()
                logger.info(
                    "已删除用户 %s 的所有 API 配置", user_id
                )

        except Exception as e:
            logger.error(
                "删除用户 %s 配置失败: %s", user_id, e
            )
            raise

    # ==================================================================
    #  供应商维度 CRUD（前端 ProviderConfig 对应）
    # ==================================================================

    @staticmethod
    async def save_provider_configs(
        user_id: str,
        providers: list[dict],
        assignment: dict,
        openalex_email: str = "",
    ) -> dict:
        """批量保存用户的供应商配置、Agent 分配、OpenAlex 邮箱

        同时将供应商 + 分配关系展开为 UserApiConfig（按 Agent 维度），
        以保持与现有 LLMFactory 流程的兼容。

        Args:
            user_id: 用户ID
            providers: 供应商列表，每项包含
                id, name, apiKey, baseUrl, modelId, apiFormat, status
            assignment: Agent 分配映射
                {"coordinator": "provider_id", ...}
            openalex_email: OpenAlex 邮箱（可选）

        Returns:
            {"saved_providers": int, "saved_agents": int}
        """
        encryption = _get_encryption_service()
        saved_provider_count = 0
        saved_agent_count = 0

        try:
            async with AsyncSessionLocal() as session:
                # ---- 1. 保存供应商 ----
                # 先删除该用户的旧供应商记录（全量替换策略）
                await session.execute(
                    delete(UserProviderConfig).where(
                        UserProviderConfig.user_id == user_id
                    )
                )

                for p in providers:
                    api_key = p.get("apiKey") or p.get("api_key", "")
                    if not api_key:
                        continue

                    encrypted_key = encryption.encrypt_if_needed(api_key)
                    provider_row = UserProviderConfig(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        provider_id=p["id"],
                        name=p.get("name", ""),
                        api_key=encrypted_key,
                        base_url=p.get("baseUrl") or p.get("base_url", ""),
                        model_id=p.get("modelId") or p.get("model_id", ""),
                        api_format=p.get("apiFormat") or p.get("api_format", "openai"),
                        status=p.get("status", "untested"),
                    )
                    session.add(provider_row)
                    saved_provider_count += 1

                # ---- 2. 保存 Agent 分配 ----
                stmt = select(UserAgentAssignment).where(
                    UserAgentAssignment.user_id == user_id,
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.coordinator = assignment.get("coordinator", "")
                    existing.modeler = assignment.get("modeler", "")
                    existing.coder = assignment.get("coder", "")
                    existing.writer = assignment.get("writer", "")
                else:
                    new_assignment = UserAgentAssignment(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        coordinator=assignment.get("coordinator", ""),
                        modeler=assignment.get("modeler", ""),
                        coder=assignment.get("coder", ""),
                        writer=assignment.get("writer", ""),
                    )
                    session.add(new_assignment)

                await session.commit()

            # ---- 3. 展开为 Agent 维度配置（兼容 LLMFactory） ----
            provider_map = {p["id"]: p for p in providers if p.get("apiKey") or p.get("api_key")}
            for agent_type in AGENT_TYPES:
                pid = assignment.get(agent_type, "")
                if pid and pid in provider_map:
                    p = provider_map[pid]
                    await UserConfigService.save_agent_config(
                        user_id=user_id,
                        agent_type=agent_type,
                        api_key=p.get("apiKey") or p.get("api_key", ""),
                        model_id=p.get("modelId") or p.get("model_id", "deepseek-chat"),
                        base_url=p.get("baseUrl") or p.get("base_url"),
                        provider=p.get("apiFormat") or p.get("api_format", "openai"),
                    )
                    saved_agent_count += 1

            # ---- 4. OpenAlex 邮箱 ----
            if openalex_email:
                await UserConfigService.save_openalex_email(
                    user_id, openalex_email
                )

            logger.info(
                "保存用户 %s 的供应商配置: %s 个供应商, %s 个 Agent",
                user_id, saved_provider_count, saved_agent_count
            )
            return {
                "saved_providers": saved_provider_count,
                "saved_agents": saved_agent_count,
            }

        except Exception as e:
            logger.error("保存用户 %s 供应商配置失败: %s", user_id, e)
            raise

    @staticmethod
    async def get_provider_configs_masked(user_id: str) -> dict:
        """获取用户供应商配置（API Key 掩码处理，供前端展示）

        前端打开设置对话框时调用此方法，
        返回供应商列表（API Key 已掩码）、Agent 分配、OpenAlex 邮箱。

        Args:
            user_id: 用户ID

        Returns:
            格式示例::

                {
                    "providers": [
                        {
                            "id": "provider_xxx",
                            "name": "DeepSeek",
                            "apiKeyMasked": "sk-abc1***xyz9",
                            "hasKey": true,
                            "baseUrl": "https://api.deepseek.com",
                            "modelId": "deepseek-chat",
                            "apiFormat": "openai",
                            "status": "valid",
                        },
                        ...
                    ],
                    "assignment": {
                        "coordinator": "provider_xxx",
                        "modeler": "provider_xxx",
                        ...
                    },
                    "openalex_email": "user@example.com",
                    "config_saved": true,
                }
        """
        result: dict = {
            "providers": [],
            "assignment": {
                "coordinator": "",
                "modeler": "",
                "coder": "",
                "writer": "",
            },
            "openalex_email": "",
            "config_saved": False,
        }

        try:
            encryption = _get_encryption_service()

            async with AsyncSessionLocal() as session:
                # 查询供应商
                stmt_p = select(UserProviderConfig).where(
                    UserProviderConfig.user_id == user_id,
                )
                p_result = await session.execute(stmt_p)
                provider_rows = p_result.scalars().all()

                # 查询 Agent 分配
                stmt_a = select(UserAgentAssignment).where(
                    UserAgentAssignment.user_id == user_id,
                )
                a_result = await session.execute(stmt_a)
                assignment_row = a_result.scalar_one_or_none()

            for row in provider_rows:
                try:
                    decrypted = encryption.decrypt_if_needed(row.api_key)
                    masked = UserApiConfig.mask_api_key(decrypted)
                except Exception:
                    masked = "***"

                result["providers"].append({
                    "id": row.provider_id,
                    "name": row.name,
                    "apiKeyMasked": masked,
                    "hasKey": bool(row.api_key),
                    "baseUrl": row.base_url or "",
                    "modelId": row.model_id or "",
                    "apiFormat": row.api_format or "openai",
                    "status": row.status or "untested",
                })

            if assignment_row:
                result["assignment"] = {
                    "coordinator": assignment_row.coordinator or "",
                    "modeler": assignment_row.modeler or "",
                    "coder": assignment_row.coder or "",
                    "writer": assignment_row.writer or "",
                }

            result["openalex_email"] = (
                await UserConfigService.get_openalex_email(user_id)
            ) or ""

            result["config_saved"] = len(provider_rows) > 0

            return result

        except Exception as e:
            logger.error(
                "获取用户 %s 供应商掩码配置失败: %s", user_id, e
            )
            return result

    @staticmethod
    async def get_api_config_status(user_id: str) -> dict:
        """检查用户的 API 配置状态（不返回 Key 内容）

        仅返回每个 Agent 是否已配置的布尔值，
        用于前端快速判断是否需要引导用户配置。

        Args:
            user_id: 用户ID

        Returns:
            格式示例::

                {
                    "coordinator": true,
                    "modeler": true,
                    "coder": false,
                    "writer": false,
                }
        """
        status: dict[str, bool] = {at: False for at in AGENT_TYPES}
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.is_active.is_(True),
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                for row in rows:
                    if row.agent_type in status and row.api_key:
                        status[row.agent_type] = True

            # 对于未在数据库配置的 Agent，检查全局回退
            for at in AGENT_TYPES:
                if not status[at]:
                    fallback = UserConfigService._get_fallback(at)
                    if fallback.get("api_key"):
                        status[at] = True

            return status

        except Exception as e:
            logger.error(
                "获取用户 %s 配置状态失败: %s", user_id, e
            )
            return status
