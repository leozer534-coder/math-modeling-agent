from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routers import modeling_router, ws_router, common_router, files_router
from app.routers import auth_router, interactive_modeling_router
from app.utils.log_util import logger
from app.config.database import init_db, close_db
from fastapi.staticfiles import StaticFiles
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

# TODO(security): [B18] 此 StaticFiles 挂载直接暴露整个 work_dir，任何人可通过
#   /static/{task_id}/notebook.ipynb 访问任意任务文件，存在未授权访问风险。
#   应替换为带认证的文件下载路由（如 secure_files_router）。
#   当前前端依赖此路径的位置:
#     - frontend/src/utils/markdown.ts (图片渲染)
#     - frontend/src/components/common/InteractiveModeling.vue (下载 notebook/report)
#     - backend/app/routers/files_router.py (下载链接生成)
#   迁移时需同步修改以上位置，改为调用带认证的 API 端点。
app.mount(
    "/static",
    StaticFiles(directory="project/work_dir"),
    name="static",
)
