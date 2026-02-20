from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routers import modeling_router, ws_router, common_router, files_router
from app.routers import auth_router, interactive_modeling_router
from app.routers.secure_files_router import router as secure_files_router
from app.utils.log_util import logger
from app.config.database import init_db, close_db
from app.utils.cli import get_ascii_banner, center_cli_str
from app.config.setting import settings
from app.routers.modeling_router import restore_config_from_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(get_ascii_banner())
    logger.info(center_cli_str("GitHub:https://github.com/jihe520/MathModelAgent"))
    logger.info("Starting MathModelAgent")

    PROJECT_FOLDER = "./project"
    os.makedirs(PROJECT_FOLDER, exist_ok=True)

    # 初始化数据库表
    await init_db()

    # 从 Redis 恢复之前保存的 API 配置（后端重启恢复）
    await restore_config_from_redis()

    yield

    # 关闭数据库连接
    await close_db()
    logger.info("Stopping MathModelAgent")


app = FastAPI(
    title="MathModelAgent",
    description="Agents for MathModel",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router.router)
app.include_router(modeling_router.router)
app.include_router(ws_router.router)
app.include_router(common_router.router)
app.include_router(files_router.router)
app.include_router(interactive_modeling_router.router)
app.include_router(secure_files_router)


# 跨域 CORS：从 settings 读取允许的来源，生产环境禁止通配符
cors_origins = settings.get_cors_origins()
logger.info("CORS 允许的来源: %s", cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
