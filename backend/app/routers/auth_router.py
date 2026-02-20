import os
import urllib.parse
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 加载 .env.auth 配置文件（包含 Google OAuth 和 JWT 配置）
_env_auth_path = Path(__file__).resolve().parents[2] / ".env.auth"
load_dotenv(_env_auth_path, override=False)

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.services.user_service import UserService
from app.utils.auth import create_access_token, get_current_user
from app.utils.log_util import logger


router = APIRouter(prefix="/auth", tags=["认证"])

# Google OAuth 配置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Google OAuth 端点
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# 回调 URL（后端处理）
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8001/auth/google/callback"
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    credits: int
    vip_level: int


@router.get("/google/login")
async def google_login():
    """生成 Google OAuth 授权 URL 并重定向"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth 未配置")
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db)
):
    """处理 Google OAuth 回调
    
    流程：用授权码换取 access_token → 获取用户信息 → 创建/查找用户 → 签发 JWT → 重定向到前端
    """
    if error:
        logger.error(f"Google OAuth 错误: {error}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error={urllib.parse.quote(error)}"
        )
    
    if not code:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=missing_code"
        )
    
    try:
        # 1. 用授权码换取 access_token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        
        if token_response.status_code != 200:
            logger.error(f"Google token 交换失败: {token_response.text}")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=token_exchange_failed"
            )
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=no_access_token"
            )
        
        # 2. 用 access_token 获取用户信息
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        
        if userinfo_response.status_code != 200:
            logger.error(f"获取 Google 用户信息失败: {userinfo_response.text}")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=userinfo_failed"
            )
        
        userinfo = userinfo_response.json()
        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name")
        picture = userinfo.get("picture")
        
        if not google_id or not email:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=invalid_userinfo"
            )
        
        # 3. 查找或创建用户
        user_service = UserService(db)
        user = await user_service.get_or_create_google_user(
            google_id=google_id,
            email=email,
            nickname=name,
            avatar_url=picture,
        )
        
        if not user.is_active:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=account_disabled"
            )
        
        # 4. 签发 JWT
        jwt_token = create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        
        logger.info(f"Google 用户登录成功: {email}")
        
        # 5. 重定向到前端，携带 JWT
        redirect_url = (
            f"{FRONTEND_URL}/oauth/callback"
            f"?token={urllib.parse.quote(jwt_token)}"
        )
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        import traceback
        logger.error(f"Google OAuth 处理异常: {e}\n{traceback.format_exc()}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=server_error"
        )


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return user.to_dict()


@router.get("/credits")
async def get_credits(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    balance = await user_service.get_credits(current_user["user_id"])
    return {"credits": balance}


@router.post("/refresh")
async def refresh_token(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["user_id"])
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/tasks")
async def get_user_tasks(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的历史任务列表"""
    user_service = UserService(db)
    tasks = await user_service.get_user_tasks(current_user["user_id"])
    return [
        {
            "id": task.id,
            "title": task.title or "未命名任务",
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
        for task in tasks
    ]
