import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.core.interactive_workflow import InteractiveMathModelWorkflow
from app.schemas.enums import CompTemplate, FormatOutPut
from app.schemas.request import Problem
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.common_utils import (
    create_task_id,
    create_work_dir,
    md_2_docx,
)
from app.utils.file_validator import validate_multiple_files
from app.utils.log_util import logger


class WorkflowService:
    @staticmethod
    async def start_interactive_modeling(
        background_tasks: BackgroundTasks,
        ques_all: str,
        comp_template: CompTemplate,
        format_output: FormatOutPut,
        files: Optional[List[UploadFile]] = None
    ) -> Dict[str, Any]:
        """
        Start a new interactive modeling task.
        """
        task_id = create_task_id()
        work_dir = create_work_dir(task_id)

        logger.info("🚀 Starting interactive modeling task: task_id=%s", task_id)

        # Handle file uploads
        if files:
            try:
                validated_files = await validate_multiple_files(files)
                for clean_filename, content in validated_files:
                    data_file_path = os.path.join(work_dir, clean_filename)
                    with open(data_file_path, "wb") as f:
                        f.write(content)
                    logger.info("Saved file: %s (%s bytes)", clean_filename, len(content))
            except Exception as e:
                logger.error("File processing failed: %s", e)
                if os.path.exists(work_dir):
                    import shutil
                    shutil.rmtree(work_dir)
                raise HTTPException(status_code=400, detail=f"File processing failed: {str(e)}")

        # Store task ID in Redis
        await redis_manager.set(f"task_id:{task_id}", task_id)

        # Send start message
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="🎯 Interactive modeling task started", type="info")
        )

        # Add background task
        background_tasks.add_task(
            WorkflowService._run_interactive_modeling_task,
            task_id,
            ques_all,
            comp_template,
            format_output,
        )

        return {
            "task_id": task_id,
            "status": "started",
            "message": "Interactive modeling task started, please check real-time progress"
        }

    @staticmethod
    async def handle_user_action(
        task_id: str,
        action: str,
        message: str = "",
        feedback: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """
        Handle user action for a task.
        """
        # Check if task exists
        stored_task_id = await redis_manager.get(f"task_id:{task_id}")
        if not stored_task_id:
            raise HTTPException(status_code=404, detail="Task not found")

        # Store user action in Redis
        action_key = f"user_action:{task_id}"
        action_data = {
            "action": action,
            "feedback": feedback,
            "message": message,
            "timestamp": datetime.now().timestamp()
        }

        await redis_manager.setex(action_key, 3600, json.dumps(action_data))

        # 发布操作已接收的系统消息（使用正确的 Message 类型）
        await redis_manager.publish_message(
            task_id,
            SystemMessage(
                content=f"Received action: {action}",
                type="info"
            )
        )

        logger.info("📝 Received user action %s: %s", task_id, action)

        return {
            "success": True,
            "message": "Action received, processing...",
            "action": action
        }

    @staticmethod
    async def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Get task status.
        """
        stored_task_id = await redis_manager.get(f"task_id:{task_id}")
        if not stored_task_id:
            raise HTTPException(status_code=404, detail="Task not found")

        status_key = f"task_status:{task_id}"
        status_data = await redis_manager.get(status_key)

        if status_data:
            status_info = json.loads(status_data)
            return {
                "task_id": task_id,
                "current_stage": status_info.get("stage", "unknown"),
                "progress": status_info.get("progress", 0),
                "pending_user_input": status_info.get("pending_user_input", False),
                "last_update": status_info.get("last_update"),
                "can_rollback": status_info.get("can_rollback", False),
                "available_actions": status_info.get("available_actions", [])
            }
        else:
            return {
                "task_id": task_id,
                "current_stage": "initializing",
                "progress": 0,
                "pending_user_input": False,
                "can_rollback": False,
                "available_actions": []
            }

    @staticmethod
    async def get_task_history(task_id: str) -> Dict[str, Any]:
        """
        Get task history.
        """
        stored_task_id = await redis_manager.get(f"task_id:{task_id}")
        if not stored_task_id:
            raise HTTPException(status_code=404, detail="Task not found")

        history_key = f"task_history:{task_id}"
        history_messages = await redis_manager.lrange(history_key, 0, -1)

        history = []
        for message_data in history_messages:
            try:
                message = json.loads(message_data)
                history.append({
                    "timestamp": message.get("timestamp"),
                    "type": message.get("type"),
                    "content": message.get("content"),
                    "data": message.get("data", {}),
                    "stage": message.get("stage")
                })
            except json.JSONDecodeError:
                continue

        return {
            "task_id": task_id,
            "history": history,
            "total_messages": len(history)
        }

    @staticmethod
    async def pause_task(task_id: str) -> Dict[str, Any]:
        stored_task_id = await redis_manager.get(f"task_id:{task_id}")
        if not stored_task_id:
            raise HTTPException(status_code=404, detail="Task not found")

        pause_key = f"task_pause:{task_id}"
        await redis_manager.setex(pause_key, 3600, "paused")

        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="⏸️ Task paused", type="warning")
        )

        return {"success": True, "message": "Task paused"}

    @staticmethod
    async def resume_task(task_id: str) -> Dict[str, Any]:
        stored_task_id = await redis_manager.get(f"task_id:{task_id}")
        if not stored_task_id:
            raise HTTPException(status_code=404, detail="Task not found")

        pause_key = f"task_pause:{task_id}"
        await redis_manager.delete(pause_key)

        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="▶️ Task resumed", type="info")
        )

        return {"success": True, "message": "Task resumed"}

    @staticmethod
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        stored_task_id = await redis_manager.get(f"task_id:{task_id}")
        if not stored_task_id:
            raise HTTPException(status_code=404, detail="Task not found")

        cancel_key = f"task_cancel:{task_id}"
        await redis_manager.setex(cancel_key, 3600, "cancelled")

        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="🛑 Task cancelled", type="error")
        )

        return {"success": True, "message": "Task cancelled"}

    @staticmethod
    async def _run_interactive_modeling_task(
        task_id: str,
        ques_all: str,
        comp_template: CompTemplate,
        format_output: FormatOutPut,
    ):
        """
        Internal method to run the task logic.
        """
        logger.info("🎯 Starting interactive modeling: task_id=%s", task_id)

        try:
            # Check for cancellation
            cancel_key = f"task_cancel:{task_id}"
            if await redis_manager.get(cancel_key):
                logger.info("Task %s cancelled", task_id)
                return

            # Update status
            await WorkflowService._update_task_status(task_id, {
                "stage": "analysis",
                "progress": 5,
                "pending_user_input": False,
                "can_rollback": False,
                "available_actions": ["cancel"]
            })

            problem = Problem(
                task_id=task_id,
                ques_all=ques_all,
                comp_template=comp_template,
                format_output=format_output,
            )

            workflow = InteractiveMathModelWorkflow()

            await redis_manager.publish_message(
                task_id,
                SystemMessage(content="🚀 Interactive modeling started", type="success")
            )

            await workflow.execute(problem)

            await WorkflowService._update_task_status(task_id, {
                "stage": "completed",
                "progress": 100,
                "pending_user_input": False,
                "can_rollback": False,
                "available_actions": ["restart", "download"]
            })

            md_2_docx(task_id)

            await redis_manager.publish_message(
                task_id,
                SystemMessage(content="🎉 Interactive modeling task completed!", type="success")
            )

        except asyncio.TimeoutError:
            logger.error("Task %s timed out", task_id)
            await redis_manager.publish_message(
                task_id,
                SystemMessage(content="⏰ Task timed out", type="error")
            )
        except Exception as e:
            logger.error("Task %s failed: %s", task_id, e)
            await redis_manager.publish_message(
                task_id,
                SystemMessage(content=f"❌ Task failed: {str(e)}", type="error")
            )
            await WorkflowService._update_task_status(task_id, {
                "stage": "failed",
                "progress": 0,
                "pending_user_input": False,
                "can_rollback": False,
                "available_actions": [],
                "error": str(e)
            })

    @staticmethod
    async def _update_task_status(task_id: str, status_info: dict):
        """
        Internal method to update task status.
        """
        status_key = f"task_status:{task_id}"
        status_info["last_update"] = datetime.now().isoformat()
        await redis_manager.setex(status_key, 86400, json.dumps(status_info))

        history_key = f"task_history:{task_id}"
        history_message = {
            "timestamp": datetime.now().isoformat(),
            "type": "status_update",
            "content": f"Status update: {status_info.get('stage', 'unknown')}",
            "data": status_info,
            "stage": status_info.get("stage")
        }

        await redis_manager.lpush(history_key, json.dumps(history_message))
        await redis_manager.expire(history_key, 86400)
