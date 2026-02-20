"""
Celery 任务定义模块

将建模工作流执行逻辑封装为 Celery Task，支持:
- 任务状态持久化与查询
- 通过 Redis Pub/Sub 向 WebSocket 推送状态变更
- 任务取消（revoke）
- 服务重启后任务不丢失
"""

import asyncio
import json
import logging
from typing import Optional

import redis

from app.config.setting import settings
from app.core.task_queue.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_redis_client() -> redis.Redis:
    """
    获取同步 Redis 客户端（Celery Worker 运行在同步上下文中）

    Returns:
        同步 Redis 客户端实例
    """
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


def _publish_task_status(
    task_id: str,
    content: str,
    msg_type: str = "info",
) -> None:
    """
    通过 Redis Pub/Sub 发布任务状态消息（同步版本）

    在 Celery Worker 中无法使用 async redis，因此使用同步客户端
    将消息发布到与 WebSocket 订阅相同的频道。

    Args:
        task_id: 任务ID
        content: 消息内容
        msg_type: 消息类型 (info/warning/success/error)
    """
    try:
        client = _get_sync_redis_client()
        channel = f"task:{task_id}:messages"
        message = {
            "id": f"celery-{task_id}",
            "msg_type": "system",
            "content": content,
            "type": msg_type,
        }
        client.publish(channel, json.dumps(message, ensure_ascii=False))
        client.close()
    except Exception as e:
        # 状态推送失败不应影响任务执行
        logger.debug("Redis 状态推送失败: %s", e)


def _run_async_workflow(
    task_id: str,
    ques_all: str,
    comp_template_value: str,
    format_output_value: str,
    workflow_mode_value: str,
    agent_configs: Optional[dict] = None,
) -> None:
    """
    在同步 Celery Worker 中运行异步工作流

    创建新的事件循环执行异步建模任务。

    Args:
        task_id: 任务ID
        ques_all: 问题描述
        comp_template_value: 竞赛模板枚举值
        format_output_value: 输出格式枚举值
        workflow_mode_value: 工作流模式枚举值
        agent_configs: 用户级 Agent API 配置
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _execute_modeling_workflow(
                task_id=task_id,
                ques_all=ques_all,
                comp_template_value=comp_template_value,
                format_output_value=format_output_value,
                workflow_mode_value=workflow_mode_value,
                agent_configs=agent_configs,
            )
        )
    finally:
        loop.close()


async def _execute_modeling_workflow(
    task_id: str,
    ques_all: str,
    comp_template_value: str,
    format_output_value: str,
    workflow_mode_value: str,
    agent_configs: Optional[dict] = None,
) -> None:
    """
    执行建模工作流核心逻辑（异步）

    根据 workflow_mode 选择对应工作流并执行，复用原有 modeling_router 中的逻辑。

    Args:
        task_id: 任务ID
        ques_all: 问题描述
        comp_template_value: 竞赛模板枚举值
        format_output_value: 输出格式枚举值
        workflow_mode_value: 工作流模式枚举值
        agent_configs: 用户级 Agent API 配置
    """
    from app.core.award_winning_workflow import AwardWinningWorkflow
    from app.core.math_model_workflow import MathModelWorkFlow
    from app.schemas.enums import CompTemplate, FormatOutPut, WorkflowMode
    from app.schemas.request import Problem
    from app.schemas.response import SystemMessage
    from app.services.redis_manager import redis_manager
    from app.utils.common_utils import md_2_docx
    from app.utils.log_util import logger

    comp_template = CompTemplate(comp_template_value)
    format_output = FormatOutPut(format_output_value)
    workflow_mode = WorkflowMode(workflow_mode_value)

    problem = Problem(
        task_id=task_id,
        ques_all=ques_all,
        comp_template=comp_template,
        format_output=format_output,
        workflow_mode=workflow_mode.value,
    )

    # 发送任务开始状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务开始处理"),
    )

    # 短暂延迟，确保 WebSocket 有机会连接
    await asyncio.sleep(1)

    logger.info(
        f"Celery Worker 开始执行建模任务: task_id={task_id}, mode={workflow_mode.value}"
    )

    # 根据 workflow_mode 选择工作流
    if workflow_mode == WorkflowMode.AWARD:
        paper_language = "en" if comp_template == CompTemplate.AMERICAN else "zh"
        enable_latex = format_output == FormatOutPut.LaTeX
        workflow = AwardWinningWorkflow(
            enable_research=True,
            enable_assumptions=True,
            enable_model_strategy=True,
            enable_sensitivity=True,
            enable_validation=True,
            enable_quality_check=True,
            enable_abstract=True,
            enable_latex=enable_latex,
            paper_language=paper_language,
            agent_configs=agent_configs,
        )
        await workflow.execute(problem)

    elif workflow_mode in (
        WorkflowMode.ENHANCED,
        WorkflowMode.AUTO,
        WorkflowMode.STANDARD,
    ):
        from app.core.workflow.workflow_selector import (
            WorkflowSelector,
            WorkflowType,
        )

        workflow_type = WorkflowSelector.select(workflow_mode, problem)

        if workflow_type == WorkflowType.ENHANCED:
            from app.core.enhanced_workflow import EnhancedMathModelWorkFlow
            workflow = EnhancedMathModelWorkFlow(agent_configs=agent_configs)
        else:
            workflow = MathModelWorkFlow(agent_configs=agent_configs)

        await workflow.execute(problem)

    else:
        # 未知模式降级为 STANDARD
        logger.warning("未知工作流模式 %s，降级为 STANDARD", workflow_mode)
        workflow = MathModelWorkFlow(agent_configs=agent_configs)
        await workflow.execute(problem)

    # 发送任务完成状态
    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务处理完成", type="success"),
    )

    # 转换 md 为 docx
    md_2_docx(task_id)

    logger.info("Celery 建模任务执行完成: task_id=%s", task_id)


@celery_app.task(
    name="app.core.task_queue.tasks.run_modeling_task",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=1,
    default_retry_delay=60,
)
def run_modeling_task(
    self,
    task_id: str,
    ques_all: str,
    comp_template_value: str,
    format_output_value: str,
    workflow_mode_value: str = "auto",
    agent_configs: Optional[dict] = None,
) -> dict:
    """
    Celery 建模任务入口

    将建模工作流封装为 Celery Task，支持持久化、超时、取消、重试。

    Args:
        self: Celery Task 实例（bind=True）
        task_id: 业务任务ID（由 create_task_id 生成）
        ques_all: 问题描述
        comp_template_value: 竞赛模板枚举值（字符串）
        format_output_value: 输出格式枚举值（字符串）
        workflow_mode_value: 工作流模式枚举值（字符串）
        agent_configs: 用户级 Agent API 配置字典

    Returns:
        包含任务执行结果的字典
    """
    # 将业务 task_id 与 Celery task_id 的映射关系存入 Redis
    try:
        sync_client = _get_sync_redis_client()
        # 存储双向映射: 业务ID -> Celery ID, Celery ID -> 业务ID
        sync_client.set(
            f"celery_task_map:{task_id}",
            self.request.id,
            ex=86400,  # 24 小时过期
        )
        sync_client.set(
            f"celery_task_reverse:{self.request.id}",
            task_id,
            ex=86400,
        )
        sync_client.close()
    except Exception as e:
        logger.warning("存储 Celery 任务映射失败: %s", e)

    # 更新任务状态为 STARTED 并附带元信息
    self.update_state(
        state="STARTED",
        meta={
            "task_id": task_id,
            "workflow_mode": workflow_mode_value,
            "progress": 0,
        },
    )

    # 通过 Redis Pub/Sub 通知 WebSocket 客户端
    _publish_task_status(task_id, "建模任务已进入 Celery 队列，开始执行...")

    try:
        _run_async_workflow(
            task_id=task_id,
            ques_all=ques_all,
            comp_template_value=comp_template_value,
            format_output_value=format_output_value,
            workflow_mode_value=workflow_mode_value,
            agent_configs=agent_configs,
        )

        # 任务成功完成
        _publish_task_status(task_id, "建模任务执行完成", msg_type="success")

        return {
            "task_id": task_id,
            "status": "completed",
            "message": "建模任务执行完成",
        }

    except Exception as exc:
        # 任务执行失败
        error_msg = f"建模任务执行失败: {type(exc).__name__}: {str(exc)}"
        _publish_task_status(task_id, error_msg, msg_type="error")

        # 更新 Celery 任务状态为 FAILURE
        self.update_state(
            state="FAILURE",
            meta={
                "task_id": task_id,
                "error": error_msg,
            },
        )

        # 不再重试，直接抛出（建模任务重试意义不大）
        raise


def get_celery_task_id(task_id: str) -> Optional[str]:
    """
    根据业务 task_id 查询对应的 Celery task_id

    Args:
        task_id: 业务任务ID

    Returns:
        Celery task_id，不存在返回 None
    """
    try:
        client = _get_sync_redis_client()
        celery_id = client.get(f"celery_task_map:{task_id}")
        client.close()
        return celery_id
    except Exception as e:
        logger.warning("查询 Celery 任务映射失败: %s", e)
        return None


def cancel_celery_task(task_id: str) -> bool:
    """
    取消 Celery 任务

    通过 revoke 发送取消信号，终止正在执行的 Worker。

    Args:
        task_id: 业务任务ID

    Returns:
        是否成功发送取消信号
    """
    celery_id = get_celery_task_id(task_id)
    if not celery_id:
        return False

    try:
        celery_app.control.revoke(celery_id, terminate=True, signal="SIGTERM")
        _publish_task_status(task_id, "任务已被取消", msg_type="warning")
        return True
    except Exception as e:
        logger.warning("取消 Celery 任务失败: %s", e)
        return False
