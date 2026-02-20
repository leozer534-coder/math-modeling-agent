import asyncio
import json
import os
from collections import OrderedDict
from typing import Optional

import httpx
import litellm
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Header, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.setting import settings
from app.core.workflow import MathModelWorkFlow
from app.schemas.enums import CompTemplate, FormatOutPut
from app.schemas.request import ExampleRequest, Problem
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.services.user_service import UserService
from app.utils.auth import decode_token
from app.utils.common_utils import (
    create_task_id,
    create_work_dir,
    get_current_files,
    md_2_docx,
)
from app.utils.file_validator import validate_upload_file
from app.utils.log_util import logger

router = APIRouter()


def _extract_user_id(authorization: Optional[str]) -> Optional[str]:
    """从可选的 Authorization header 中提取 user_id"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization[7:]
        payload = decode_token(token)
        return payload.get("sub") if payload else None
    except Exception:
        return None

# ============================================================
# 任务级 API 配置存储（替代直接修改全局 settings 单例）
# 使用 Redis 存储每次请求提交的配置，按 config_id 隔离
# ============================================================


class _LRUConfigCache(OrderedDict):
    """LRU 配置缓存，超出容量时自动淘汰最旧条目。

    基于 OrderedDict 实现，写入时将 key 移至末尾，
    当条目数超过 maxsize 时从头部淘汰最久未更新的条目，
    防止长期运行的服务因配置缓存无限增长导致内存泄漏。
    """

    def __init__(self, maxsize: int = 1000) -> None:
        super().__init__()
        self._maxsize = maxsize

    def __setitem__(self, key: str, value: dict) -> None:
        # 如果 key 已存在，先删除再插入（移到末尾）
        if key in self:
            del self[key]
        super().__setitem__(key, value)
        # 超出容量时淘汰最旧条目
        while len(self) > self._maxsize:
            evicted_key, _ = self.popitem(last=False)
            logger.debug("LRU 配置缓存淘汰条目: %s", evicted_key)


_task_api_configs: _LRUConfigCache = _LRUConfigCache(maxsize=1000)
"""内存中的任务级 API 配置 LRU 缓存（上限 1000 条）。

键为 config_id（由 save_api_config 返回），值为完整配置字典。
超出容量时自动淘汰最旧条目。在生产环境中应迁移到 Redis 或数据库持久化存储。
"""


# ============================================================
# 请求/响应模型
# ============================================================


class ValidateApiKeyRequest(BaseModel):
    """API Key 验证请求。"""

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_id: str
    api_format: str = "openai"  # openai / anthropic / gemini


class ValidateOpenalexEmailRequest(BaseModel):
    """OpenAlex 邮箱验证请求。"""

    email: str


class ValidateOpenalexEmailResponse(BaseModel):
    """OpenAlex 邮箱验证响应。"""

    valid: bool
    message: str


class ValidateApiKeyResponse(BaseModel):
    """API Key 验证响应。"""

    valid: bool
    message: str


class SaveApiConfigRequest(BaseModel):
    """保存 API 配置请求。"""

    coordinator: dict
    modeler: dict
    coder: dict
    writer: dict
    openalex_email: str


# ============================================================
# API 端点
# ============================================================


@router.post("/save-api-config")
async def save_api_config(request: SaveApiConfigRequest):
    """保存验证成功的 API 配置。

    不再直接修改全局 settings 单例，而是将配置保存到
    任务级别的配置存储中，并同步到 Redis 以支持多实例部署。
    生产环境下此端点被禁用（应通过环境变量管理配置）。
    """
    # 生产环境下禁止通过 API 修改配置
    if settings.is_production():
        logger.warning("生产环境下尝试调用 save-api-config 端点")
        raise HTTPException(
            status_code=403,
            detail="生产环境不允许通过 API 修改配置，请使用环境变量",
        )

    try:
        # 生成唯一配置 ID
        config_id = create_task_id()

        # 构建配置字典（不直接修改全局 settings）
        config_data: dict = {}

        if request.coordinator:
            config_data["coordinator"] = {
                "api_key": request.coordinator.get("apiKey", ""),
                "model": request.coordinator.get("modelId", ""),
                "base_url": request.coordinator.get("baseUrl", ""),
            }

        if request.modeler:
            config_data["modeler"] = {
                "api_key": request.modeler.get("apiKey", ""),
                "model": request.modeler.get("modelId", ""),
                "base_url": request.modeler.get("baseUrl", ""),
            }

        if request.coder:
            config_data["coder"] = {
                "api_key": request.coder.get("apiKey", ""),
                "model": request.coder.get("modelId", ""),
                "base_url": request.coder.get("baseUrl", ""),
            }

        if request.writer:
            config_data["writer"] = {
                "api_key": request.writer.get("apiKey", ""),
                "model": request.writer.get("modelId", ""),
                "base_url": request.writer.get("baseUrl", ""),
            }

        if request.openalex_email:
            config_data["openalex_email"] = request.openalex_email

        # 存储到任务级配置缓存
        _task_api_configs[config_id] = config_data

        # 同步到 Redis，便于多实例共享（TTL 24 小时）
        try:
            config_json = json.dumps(config_data)
            await redis_manager.set(
                f"api_config:{config_id}",
                config_json,
            )
            # 同时保存到固定 key，用于重启后恢复
            # 仅当至少有一个 agent 的 api_key 非空时才更新 latest
            has_valid_key = any(
                config_data.get(agent, {}).get("api_key")
                for agent in ("coordinator", "modeler", "coder", "writer")
            )
            if has_valid_key:
                await redis_manager.set("api_config:latest", config_json)
                logger.info("API 配置已保存到 Redis (latest), config_id: %s", config_id)
            else:
                logger.info("API 配置已保存到 Redis (无有效 key，跳过 latest), config_id: %s", config_id)
        except Exception as e:
            logger.warning("保存配置到 Redis 失败（仅内存缓存可用）: %s", e)

        # 开发环境向后兼容：同步更新全局 settings
        # 注意：这是为了兼容现有 workflow 读取 settings 的逻辑
        _apply_config_to_settings(config_data)

        logger.info(
            "配置保存成功, config_id: %s, agents: %s",
            config_id,
            list(config_data.keys()),
        )

        return {
            "success": True,
            "message": "配置保存成功",
            "config_id": config_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("保存配置失败: %s", e)
        raise HTTPException(
            status_code=500, detail="保存配置失败，请重试"
        )


def _apply_config_to_settings(config_data: dict) -> None:
    """将配置应用到全局 settings（仅开发环境向后兼容使用）。

    警告：此函数修改全局状态，仅在开发环境单实例模式下安全。
    生产环境应通过环境变量配置，不应调用此函数。
    """
    agent_field_map = {
        "coordinator": (
            "COORDINATOR_API_KEY",
            "COORDINATOR_MODEL",
            "COORDINATOR_BASE_URL",
        ),
        "modeler": (
            "MODELER_API_KEY",
            "MODELER_MODEL",
            "MODELER_BASE_URL",
        ),
        "coder": (
            "CODER_API_KEY",
            "CODER_MODEL",
            "CODER_BASE_URL",
        ),
        "writer": (
            "WRITER_API_KEY",
            "WRITER_MODEL",
            "WRITER_BASE_URL",
        ),
    }

    for agent_name, (key_field, model_field, url_field) in agent_field_map.items():
        agent_config = config_data.get(agent_name)
        if agent_config:
            api_key = agent_config.get("api_key", "")
            model = agent_config.get("model", "")
            base_url = agent_config.get("base_url", "")

            # 仅当新值非空时才覆盖，防止刷新页面后空值覆盖已有配置
            if api_key:
                setattr(settings, key_field, api_key)
            if model:
                setattr(settings, model_field, model)
            if base_url:
                setattr(settings, url_field, base_url)

            # 调试日志（脱敏）
            actual_key = getattr(settings, key_field, "")
            masked_key = f"{actual_key[:8]}...{actual_key[-4:]}" if len(actual_key) > 12 else ("***" if actual_key else "(empty)")
            actual_model = getattr(settings, model_field, "")
            actual_url = getattr(settings, url_field, "")
            logger.info(
                "配置状态: agent=%s, key=%s, model=%s, base_url=%s",
                agent_name, masked_key, actual_model, actual_url
            )

    openalex_email = config_data.get("openalex_email")
    if openalex_email:
        settings.OPENALEX_EMAIL = openalex_email


async def restore_config_from_redis() -> bool:
    """从 Redis 恢复最近一次保存的 API 配置到 settings。

    用于后端重启后自动恢复配置，避免用户需要重新输入 API Key。
    Returns:
        bool: 是否成功恢复了配置
    """
    try:
        client = await redis_manager.get_client()
        raw = await client.get("api_config:latest")
        if not raw:
            logger.info("Redis 中未找到已保存的 API 配置")
            return False

        config_data = json.loads(raw)
        _apply_config_to_settings(config_data)
        logger.info("已从 Redis 恢复 API 配置, agents: %s", list(config_data.keys()))
        return True
    except Exception as e:
        logger.warning("从 Redis 恢复配置失败: %s", e)
        return False


async def _validate_anthropic(api_key: str, base_url: str, model_id: str) -> ValidateApiKeyResponse:
    """使用 Anthropic 协议验证 API 连接。"""
    url = f"{base_url.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model_id,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "Hi"}],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            return ValidateApiKeyResponse(valid=True, message="API 验证成功")
        error_data = resp.text
        logger.error(
            "Anthropic API 验证失败, status: %s, response: %s",
            resp.status_code, error_data[:500],
        )
        if resp.status_code == 401:
            return ValidateApiKeyResponse(valid=False, message="API Key 无效或已过期")
        elif resp.status_code == 404:
            return ValidateApiKeyResponse(valid=False, message="模型 ID 不存在或 Base URL 错误")
        elif resp.status_code == 429:
            return ValidateApiKeyResponse(valid=False, message="请求过于频繁，请稍后再试")
        elif resp.status_code == 403:
            return ValidateApiKeyResponse(valid=False, message="API 权限不足或账户余额不足")
        else:
            return ValidateApiKeyResponse(valid=False, message=f"验证失败 (HTTP {resp.status_code})，请检查配置")


async def _validate_gemini(api_key: str, base_url: str, model_id: str) -> ValidateApiKeyResponse:
    """使用 Gemini 协议验证 API 连接。"""
    url = f"{base_url.rstrip('/')}/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {"content-type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": "Hi"}]}],
        "generationConfig": {"maxOutputTokens": 1},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            return ValidateApiKeyResponse(valid=True, message="API 验证成功")
        logger.error(
            "Gemini API 验证失败, status: %s, response: %s",
            resp.status_code, resp.text[:500],
        )
        if resp.status_code in (401, 403):
            return ValidateApiKeyResponse(valid=False, message="API Key 无效或权限不足")
        elif resp.status_code == 404:
            return ValidateApiKeyResponse(valid=False, message="模型 ID 不存在或 Base URL 错误")
        else:
            return ValidateApiKeyResponse(valid=False, message=f"验证失败 (HTTP {resp.status_code})，请检查配置")


async def _validate_openai(api_key: str, base_url: str, model_id: str) -> ValidateApiKeyResponse:
    """使用 OpenAI 兼容协议验证 API 连接。"""
    try:
        await litellm.acompletion(
            model=model_id,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            api_key=api_key,
            base_url=base_url
            if base_url != "https://api.openai.com/v1"
            else None,
        )
        return ValidateApiKeyResponse(valid=True, message="API 验证成功")
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return ValidateApiKeyResponse(valid=False, message="API Key 无效或已过期")
        elif "404" in error_msg or "Not Found" in error_msg:
            return ValidateApiKeyResponse(valid=False, message="模型 ID 不存在或 Base URL 错误")
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return ValidateApiKeyResponse(valid=False, message="请求过于频繁，请稍后再试")
        elif "403" in error_msg or "Forbidden" in error_msg:
            return ValidateApiKeyResponse(valid=False, message="API 权限不足或账户余额不足")
        else:
            logger.error(
                "OpenAI API 验证失败, model: %s, error: %s",
                model_id, error_msg,
            )
            return ValidateApiKeyResponse(valid=False, message="验证失败，请检查配置后重试")


@router.post("/validate-api-key", response_model=ValidateApiKeyResponse)
async def validate_api_key(request: ValidateApiKeyRequest):
    """验证 API Key 的有效性，支持 OpenAI / Anthropic / Gemini 三种协议。"""
    try:
        logger.info(
            "验证 API Key, format: %s, model: %s, base_url: %s",
            request.api_format, request.model_id, request.base_url,
        )

        if request.api_format == "anthropic":
            return await _validate_anthropic(request.api_key, request.base_url, request.model_id)
        elif request.api_format == "gemini":
            return await _validate_gemini(request.api_key, request.base_url, request.model_id)
        else:
            return await _validate_openai(request.api_key, request.base_url, request.model_id)

    except httpx.ConnectError:
        return ValidateApiKeyResponse(valid=False, message="无法连接到 API 服务器，请检查 Base URL")
    except httpx.TimeoutException:
        return ValidateApiKeyResponse(valid=False, message="连接超时，请检查网络或 Base URL")
    except Exception as e:
        logger.error(
            "API Key 验证异常, model: %s, error: %s",
            request.model_id, str(e),
        )
        return ValidateApiKeyResponse(valid=False, message="验证失败，请检查配置后重试")


@router.post(
    "/validate-openalex-email", response_model=ValidateOpenalexEmailResponse
)
async def validate_openalex_email(request: ValidateOpenalexEmailRequest):
    """验证 OpenAlex Email 的有效性。"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.openalex.org/works?mailto={request.email}"
            )
        logger.debug("OpenAlex Email 验证响应: %s", response)
        response.raise_for_status()
        return ValidateOpenalexEmailResponse(
            valid=True, message="OpenAlex Email 验证成功"
        )
    except Exception as e:
        logger.warning("OpenAlex Email 验证失败: %s", e)
        return ValidateOpenalexEmailResponse(
            valid=False, message="OpenAlex Email 验证失败，请检查邮箱地址"
        )


@router.post("/example")
async def exampleModeling(
    example_request: ExampleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """使用内置示例运行建模任务。"""
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)
    example_dir = os.path.join("app", "example", "example", example_request.source)
    logger.debug("示例目录: %s", example_dir)

    with open(
        os.path.join(example_dir, "questions.txt"), "r", encoding="utf-8"
    ) as f:
        ques_all = f.read()

    current_files = get_current_files(example_dir, "data")
    for file in current_files:
        src_file = os.path.join(example_dir, file)
        dst_file = os.path.join(work_dir, file)
        with open(src_file, "rb") as src, open(dst_file, "wb") as dst:
            dst.write(src.read())
    # 存储任务ID
    await redis_manager.set(f"task_id:{task_id}", task_id)

    # 保存任务到数据库
    user_id = _extract_user_id(authorization)
    if user_id:
        try:
            user_service = UserService(db)
            title = f"示例任务: {example_request.source}"
            await user_service.create_task(user_id, task_id, title, ques_all)
        except Exception as e:
            logger.warning("保存任务记录失败: %s", e)

    logger.info("Adding background task for task_id: %s", task_id)
    # 将任务添加到后台执行
    background_tasks.add_task(
        run_modeling_task_async,
        task_id,
        ques_all,
        CompTemplate.CHINA,
        FormatOutPut.Markdown,
    )
    return {"task_id": task_id, "status": "processing"}


# 文件上传安全白名单（允许的扩展名）
_UPLOAD_ALLOWED_EXTENSIONS = {
    ".csv",
    ".xlsx",
    ".xls",
    ".txt",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".json",
    ".zip",
}
# 单文件大小限制: 50MB
_UPLOAD_MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/modeling")
async def modeling(
    background_tasks: BackgroundTasks,
    ques_all: str = Form(...),
    comp_template: CompTemplate = Form(...),
    format_output: FormatOutPut = Form(...),
    files: list[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """创建建模任务。"""
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)

    # 如果有上传文件，保存文件
    if files:
        logger.info("开始处理上传的文件，工作目录: %s", work_dir)
        for file in files:
            try:
                clean_filename, content = await validate_upload_file(
                    file,
                    max_size=_UPLOAD_MAX_FILE_SIZE,
                    allowed_extensions=_UPLOAD_ALLOWED_EXTENSIONS,
                )

                data_file_path = os.path.join(work_dir, clean_filename)
                logger.info(
                    "保存文件: %s -> %s", clean_filename, data_file_path
                )

                with open(data_file_path, "wb") as f:
                    f.write(content)
                logger.info("成功保存文件: %s", data_file_path)

            except HTTPException:
                raise
            except Exception as e:
                logger.error("保存文件失败: %s", e)
                raise HTTPException(
                    status_code=500, detail="保存文件失败，请重试"
                )
    else:
        logger.warning("没有上传文件")

    # 存储任务ID
    await redis_manager.set(f"task_id:{task_id}", task_id)

    # 保存任务到数据库
    user_id = _extract_user_id(authorization)
    if user_id:
        try:
            user_service = UserService(db)
            title = ques_all[:100].strip().replace("\n", " ") if ques_all else "未命名任务"
            await user_service.create_task(user_id, task_id, title, ques_all)
        except Exception as e:
            logger.warning("保存任务记录失败: %s", e)

    logger.info("Adding background task for task_id: %s", task_id)
    # 将任务添加到后台执行
    background_tasks.add_task(
        run_modeling_task_async, task_id, ques_all, comp_template, format_output
    )
    return {"task_id": task_id, "status": "processing"}


@router.post("/modeling/retry")
async def retry_modeling(
    background_tasks: BackgroundTasks,
    task_id: str = Form(...),
    ques_all: str = Form(...),
    comp_template: CompTemplate = Form(...),
    format_output: FormatOutPut = Form(...),
):
    """使用已有 task_id 重试建模任务（断点续跑）。

    如果 work_dir 中存在 checkpoint.json，将自动跳过已完成的
    Coordinator/Modeler 阶段，从断点处继续执行。
    """
    from app.utils.common_utils import get_work_dir

    # 验证 work_dir 存在
    try:
        get_work_dir(task_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"任务 {task_id} 的工作目录不存在，无法重试",
        )

    logger.info("重试建模任务 (断点续跑): task_id=%s", task_id)

    background_tasks.add_task(
        run_modeling_task_async, task_id, ques_all, comp_template, format_output
    )
    return {"task_id": task_id, "status": "retrying"}


async def run_modeling_task_async(
    task_id: str,
    ques_all: str,
    comp_template: CompTemplate,
    format_output: FormatOutPut,
):
    """后台异步执行建模任务。"""
    logger.info("run modeling task for task_id: %s", task_id)

    problem = Problem(
        task_id=task_id,
        ques_all=ques_all,
        comp_template=comp_template,
        format_output=format_output,
    )

    # 发送任务开始状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务开始处理"),
    )

    # 给一个短暂的延迟，确保 WebSocket 有机会连接
    await asyncio.sleep(1)

    try:
        # 创建任务并等待它完成
        task = asyncio.create_task(MathModelWorkFlow().execute(problem))
        # 设置超时时间（比如 300 分钟）
        await asyncio.wait_for(task, timeout=3600 * 5)

        # 发送任务完成状态
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="任务处理完成", type="success"),
        )
        # 转换md为docx
        md_2_docx(task_id)
    except asyncio.TimeoutError:
        logger.error("任务执行超时, task_id: %s", task_id)
        await redis_manager.publish_message(
            task_id,
            SystemMessage(
                content="任务执行超时，请缩短问题描述或减少子问题数量后重试",
                type="error",
            ),
        )
    except Exception as e:
        logger.error(
            "后台任务执行失败, task_id: %s, error: %s",
            task_id,
            e,
            exc_info=True,
        )
        await redis_manager.publish_message(
            task_id,
            SystemMessage(
                content=f"任务执行失败: {str(e)[:200]}",
                type="error",
            ),
        )
    finally:
        # 确保清理任务锁，防止内存泄漏
        redis_manager.cleanup_task_lock(task_id)
