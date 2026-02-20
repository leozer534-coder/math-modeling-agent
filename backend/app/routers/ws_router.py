import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from app.config.setting import settings
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage
from app.services.ws_manager import ws_manager
from app.utils.log_util import logger
from app.utils.auth import decode_token

router = APIRouter()

# WebSocket 认证超时时间（秒）
_AUTH_TIMEOUT_SECONDS = 10


async def _authenticate_websocket(websocket: WebSocket) -> bool:
    """WebSocket 连接后首条消息认证。

    客户端需在连接建立后 _AUTH_TIMEOUT_SECONDS 秒内发送:
        {"type": "auth", "token": "<token>"}

    开发环境下跳过认证以方便调试。

    Returns:
        bool: 认证是否成功
    """
    # 开发环境跳过认证
    if not settings.is_production():
        logger.debug("非生产环境，跳过 WebSocket 认证")
        return True

    try:
        # 等待客户端发送认证消息，设置超时
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=_AUTH_TIMEOUT_SECONDS,
        )
        auth_msg = json.loads(raw)

        if auth_msg.get("type") != "auth" or not auth_msg.get("token"):
            logger.warning("WebSocket 认证消息格式无效")
            await ws_manager.send_personal_message_json(
                {"type": "auth_fail", "message": "认证消息格式无效，需要 {type: 'auth', token: '...'}"},
                websocket,
            )
            return False

        # 验证 JWT token 有效性
        token = auth_msg.get("token")
        if not token:
            logger.warning("WebSocket 认证 token 为空")
            await ws_manager.send_personal_message_json(
                {"type": "auth_fail", "message": "认证失败，token 为空"},
                websocket,
            )
            return False

        # 使用 decode_token 验证 JWT 有效性（包括过期时间检查）
        payload = decode_token(token)
        if not payload:
            logger.warning("WebSocket 认证 token 无效或已过期")
            await ws_manager.send_personal_message_json(
                {"type": "auth_fail", "message": "认证失败，token 无效或已过期"},
                websocket,
            )
            return False

        # 提取 user_id 用于任务权限校验
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("WebSocket 认证 token 缺少 user_id")
            await ws_manager.send_personal_message_json(
                {"type": "auth_fail", "message": "认证失败，token 格式错误"},
                websocket,
            )
            return False

        logger.info("WebSocket 认证成功, user_id: %s", user_id)
        await ws_manager.send_personal_message_json(
            {"type": "auth_ok", "message": "认证成功"},
            websocket,
        )
        return True

    except asyncio.TimeoutError:
        logger.warning("WebSocket 认证超时（%ss 内未收到认证消息）", _AUTH_TIMEOUT_SECONDS)
        await ws_manager.send_personal_message_json(
            {"type": "auth_fail", "message": "认证超时"},
            websocket,
        )
        return False
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("WebSocket 认证消息解析失败: %s", e)
        await ws_manager.send_personal_message_json(
            {"type": "auth_fail", "message": "认证消息解析失败"},
            websocket,
        )
        return False


@router.websocket("/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket 端点：双向通信（推送任务进度 + 接收用户操作）。"""
    logger.info("WebSocket 尝试连接 task_id: %s", task_id)

    redis_async_client = await redis_manager.get_client()
    if not await redis_async_client.exists(f"task_id:{task_id}"):
        logger.warning("Task not found: %s", task_id)
        await websocket.close(code=1008, reason="Task not found")
        return
    logger.info("WebSocket connected for task: %s", task_id)

    # 建立 WebSocket 连接
    await ws_manager.connect(websocket)
    websocket.timeout = 500
    logger.debug("WebSocket connection status: %s", websocket.client)

    # 执行认证流程（生产环境强制认证）
    if not await _authenticate_websocket(websocket):
        logger.warning("WebSocket 认证失败，关闭连接, task_id: %s", task_id)
        ws_manager.disconnect(websocket)
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # 订阅 Redis 频道
    pubsub = await redis_manager.subscribe_to_task(task_id)
    logger.info("Subscribed to Redis channel: task:%s:messages", task_id)

    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务开始处理"),
    )

    # 标记连接是否活跃
    connection_alive = True

    async def _push_redis_to_ws():
        """从 Redis pubsub 推送消息到 WebSocket 客户端"""
        nonlocal connection_alive
        try:
            while connection_alive:
                try:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True)
                    if msg:
                        logger.debug("Received message: %s", msg)
                        try:
                            msg_dict = json.loads(msg["data"])
                            await ws_manager.send_personal_message_json(msg_dict, websocket)
                            logger.debug("Sent message to WebSocket: %s", msg_dict)
                        except Exception as e:
                            logger.error("Error parsing message: %s", e)
                            await ws_manager.send_personal_message_json(
                                {"error": str(e)}, websocket
                            )
                    await asyncio.sleep(0.1)
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected (push), task_id: %s", task_id)
                    connection_alive = False
                    break
                except Exception as e:
                    logger.error("Error in push loop: %s", e)
                    await asyncio.sleep(1)
        except Exception as e:
            logger.error("Push task error: %s", e)
            connection_alive = False

    async def _receive_ws_messages():
        """接收 WebSocket 客户端消息并存入 Redis"""
        nonlocal connection_alive
        try:
            while connection_alive:
                try:
                    raw = await websocket.receive_text()
                    data = json.loads(raw)
                    msg_type = data.get("type", "")
                    logger.info("收到客户端消息: task=%s, type=%s", task_id, msg_type)

                    if msg_type == "user_action":
                        # 用户操作：确认/取消/回退/修改/跳过/重试
                        action_data = {
                            "action": data.get("action", "confirm"),
                            "feedback": data.get("feedback", {}),
                            "message": data.get("message", ""),
                            "modifications": data.get("modifications", {}),
                        }
                        action_key = f"user_action:{task_id}"
                        await redis_manager.set_json(action_key, action_data, expire=300)
                        logger.info("用户操作已存入 Redis: %s -> %s", action_key, action_data.get("action"))

                    elif msg_type == "user_message":
                        # 用户自由输入消息
                        user_content = data.get("content", "")
                        if user_content:
                            # 将用户消息广播给前端（回显）
                            from app.schemas.response import UserMessage as UserMsg
                            await redis_manager.publish_message(
                                task_id,
                                UserMsg(content=user_content),
                            )
                            # 同时存入 Redis，供工作流消费
                            action_data = {
                                "action": "message",
                                "message": user_content,
                                "feedback": {},
                            }
                            action_key = f"user_action:{task_id}"
                            await redis_manager.set_json(action_key, action_data, expire=300)
                            logger.info("用户消息已处理: task=%s", task_id)

                    elif msg_type == "cancel":
                        # 快捷取消
                        cancel_key = f"task_cancel:{task_id}"
                        await redis_manager.setex(cancel_key, 3600, "cancelled")
                        action_data = {"action": "cancel"}
                        await redis_manager.set_json(f"user_action:{task_id}", action_data, expire=300)
                        await redis_manager.publish_message(
                            task_id,
                            SystemMessage(content="🛑 用户发起取消", type="warning"),
                        )
                        logger.info("用户取消任务: task=%s", task_id)

                    else:
                        logger.debug("未知消息类型: %s", msg_type)

                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected (receive), task_id: %s", task_id)
                    connection_alive = False
                    break
                except json.JSONDecodeError as e:
                    logger.warning("客户端消息 JSON 解析失败: %s", e)
                except Exception as e:
                    logger.error("Error receiving WS message: %s", e)
                    await asyncio.sleep(0.5)
        except Exception as e:
            logger.error("Receive task error: %s", e)
            connection_alive = False

    try:
        # 并发运行双向通信
        push_task = asyncio.create_task(_push_redis_to_ws())
        recv_task = asyncio.create_task(_receive_ws_messages())

        # 等待任意一个任务完成（通常是断连触发）
        done, pending = await asyncio.wait(
            [push_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # 取消未完成的任务
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        await pubsub.unsubscribe(f"task:{task_id}:messages")
        ws_manager.disconnect(websocket)
        logger.info("WebSocket connection closed for task: %s", task_id)
