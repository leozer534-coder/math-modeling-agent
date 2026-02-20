"""
交互式建模API路由
提供用户参与建模过程的接口

安全：所有端点均需 JWT 认证（Bearer Token）
"""
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from pydantic import BaseModel

from app.schemas.enums import CompTemplate, FormatOutPut
from app.services.workflow_service import WorkflowService
from app.utils.auth import get_current_user


router = APIRouter(prefix="/interactive", tags=["interactive_modeling"])


class UserActionRequest(BaseModel):
    """用户操作请求"""
    task_id: str
    action: str  # confirm, modify, cancel, rollback, retry
    feedback: dict = {}
    message: str = ""


class InteractiveModelingRequest(BaseModel):
    """交互式建模请求"""
    task_id: str
    message: str
    action: str = "submit"  # submit, confirm, modify, cancel


@router.post("/start-modeling")
async def start_interactive_modeling(
    background_tasks: BackgroundTasks,
    ques_all: str = Form(...),
    comp_template: CompTemplate = Form(...),
    format_output: FormatOutPut = Form(...),
    files: list[UploadFile] = File(default=None),
    _user: dict = Depends(get_current_user),
):
    """启动交互式建模任务"""
    return await WorkflowService.start_interactive_modeling(
        background_tasks, ques_all, comp_template, format_output, files
    )


@router.post("/user-action")
async def handle_user_action(
    request: UserActionRequest,
    _user: dict = Depends(get_current_user),
):
    """处理用户操作"""
    return await WorkflowService.handle_user_action(
        request.task_id, request.action, request.message, request.feedback
    )


@router.get("/task-status/{task_id}")
async def get_interactive_task_status(
    task_id: str,
    _user: dict = Depends(get_current_user),
):
    """获取交互式任务状态"""
    return await WorkflowService.get_task_status(task_id)


@router.get("/task-history/{task_id}")
async def get_task_history(
    task_id: str,
    _user: dict = Depends(get_current_user),
):
    """获取任务历史记录"""
    return await WorkflowService.get_task_history(task_id)


@router.post("/pause-task/{task_id}")
async def pause_task(
    task_id: str,
    _user: dict = Depends(get_current_user),
):
    """暂停任务执行"""
    return await WorkflowService.pause_task(task_id)


@router.post("/resume-task/{task_id}")
async def resume_task(
    task_id: str,
    _user: dict = Depends(get_current_user),
):
    """恢复任务执行"""
    return await WorkflowService.resume_task(task_id)


@router.delete("/cancel-task/{task_id}")
async def cancel_task(
    task_id: str,
    _user: dict = Depends(get_current_user),
):
    """取消任务执行"""
    return await WorkflowService.cancel_task(task_id)
