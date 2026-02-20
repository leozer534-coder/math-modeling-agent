"""用户服务层"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import CreditTransaction, Task, User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """根据 Google ID 查找用户"""
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_google_user(
        self,
        google_id: str,
        email: str,
        nickname: Optional[str] = None,
        avatar_url: Optional[str] = None,
        initial_credits: int = 50
    ) -> User:
        """根据 Google 用户信息查找或创建用户
        
        优先通过 google_id 查找，其次通过 email 查找（处理已有用户关联 Google 的情况）。
        如果都不存在则创建新用户。
        """
        # 优先用 google_id 查找
        user = await self.get_by_google_id(google_id)
        if user:
            # 更新头像和昵称（Google 信息可能变化）
            user.avatar_url = avatar_url or user.avatar_url
            user.nickname = nickname or user.nickname
            user.last_login_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(user)
            return user
        
        # 用 email 查找（已有用户首次用 Google 登录）
        user = await self.get_by_email(email)
        if user:
            user.google_id = google_id
            user.auth_provider = "google"
            user.avatar_url = avatar_url or user.avatar_url
            user.nickname = nickname or user.nickname
            user.last_login_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(user)
            return user
        
        # 创建新用户
        user = User(
            email=email,
            google_id=google_id,
            auth_provider="google",
            nickname=nickname or email.split("@")[0],
            avatar_url=avatar_url,
            credits=initial_credits
        )
        self.db.add(user)
        await self.db.flush()
        
        if initial_credits > 0:
            transaction = CreditTransaction(
                user_id=user.id,
                amount=initial_credits,
                type="gift",
                description="新用户注册赠送",
                balance_after=initial_credits
            )
            self.db.add(transaction)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_last_login(self, user_id: str):
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.db.commit()
    
    async def get_credits(self, user_id: str) -> int:
        result = await self.db.execute(
            select(User.credits).where(User.id == user_id)
        )
        return result.scalar_one_or_none() or 0
    
    async def add_credits(
        self,
        user_id: str,
        amount: int,
        type: str,
        description: str = None,
        order_id: str = None
    ) -> CreditTransaction:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(credits=User.credits + amount)
        )
        
        new_balance = await self.get_credits(user_id)
        
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            type=type,
            description=description,
            order_id=order_id,
            balance_after=new_balance
        )
        self.db.add(transaction)
        await self.db.commit()
        
        return transaction
    
    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        task_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[CreditTransaction]:
        """扣减用户积分。

        使用 WHERE credits >= amount 条件更新，避免先查后改的竞态条件。
        如果余额不足，返回 None。
        """
        # 原子操作：仅当余额充足时才扣减，防止并发请求导致超扣
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id, User.credits >= amount)
            .values(credits=User.credits - amount)
        )

        # 如果没有行被更新，说明余额不足或用户不存在
        if result.rowcount == 0:
            return None

        # 扣减成功后查询最新余额，用于记录交易
        new_balance = await self.get_credits(user_id)

        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            type="consume",
            description=description,
            task_id=task_id,
            balance_after=new_balance
        )
        self.db.add(transaction)
        await self.db.commit()

        return transaction

    async def create_task(
        self,
        user_id: str,
        task_id: str,
        title: str,
        problem_description: str = "",
        language: str = "zh",
    ) -> Task:
        """创建任务记录"""
        task = Task(
            id=task_id,
            user_id=user_id,
            title=title[:255] if title else "未命名任务",
            problem_description=problem_description[:10000] if problem_description else "",
            language=language,
            status="processing",
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_user_tasks(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Task]:
        """获取用户的历史任务列表（按创建时间倒序）"""
        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result_summary: str = None,
        error_message: str = None,
    ):
        """更新任务状态"""
        values = {"status": status}
        if status == "completed":
            values["completed_at"] = datetime.utcnow()
        if status == "processing":
            values["started_at"] = datetime.utcnow()
        if result_summary:
            values["result_summary"] = result_summary
        if error_message:
            values["error_message"] = error_message
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(**values)
        )
        await self.db.commit()
