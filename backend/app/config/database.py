"""
数据库配置模块
支持 SQLite（开发环境）和 PostgreSQL（生产环境）

根据 settings.DATABASE_URL 自动检测数据库类型并应用对应的连接参数：
- SQLite: 使用 aiosqlite 驱动，无连接池（单文件数据库）
- PostgreSQL: 使用 asyncpg 驱动，启用连接池 + 健康检查
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config.setting import settings
from app.utils.log_util import logger


def _build_engine():
    """根据 DATABASE_URL 构建异步引擎。

    Returns:
        AsyncEngine: SQLAlchemy 异步引擎实例
    """
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")

    # 生产环境使用 SQLite 时发出警告
    if is_sqlite and settings.is_production():
        logger.warning(
            "生产环境正在使用 SQLite，存在并发限制和数据丢失风险。"
            "请设置 DATABASE_URL 环境变量切换到 PostgreSQL。"
            "示例: DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname"
        )

    if is_sqlite:
        # SQLite - 开发/测试环境
        return create_async_engine(
            url,
            echo=settings.DEBUG and settings.ENV.lower() == "dev",
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL - 生产级配置，启用连接池
    return create_async_engine(
        url,
        echo=False,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=30,  # 从连接池获取连接的超时时间（秒）
        pool_recycle=settings.DATABASE_POOL_RECYCLE,  # 连接回收周期
        pool_pre_ping=True,  # 每次取连接前发送 ping，自动剔除失效连接
    )


# 全局引擎实例
engine = _build_engine()

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ORM 基类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入函数。

    使用方式::

        @router.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: 数据库异步会话，事务在正常退出时自动提交，异常时自动回滚
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库表。

    在应用启动时调用，根据 ORM 模型自动创建缺失的表。
    注意：生产环境建议使用 Alembic 进行数据库迁移，而非 create_all。
    """
    db_type = "SQLite" if settings.DATABASE_URL.startswith("sqlite") else "PostgreSQL"
    logger.info(f"正在初始化数据库（{db_type}）...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info(f"数据库初始化完成（{db_type}）")


async def close_db() -> None:
    """关闭数据库连接池。

    在应用关闭时调用，释放所有数据库连接资源。
    """
    await engine.dispose()
    logger.info("数据库连接已关闭")
