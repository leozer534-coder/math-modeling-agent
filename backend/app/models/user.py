"""用户数据模型"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.config.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Google 用户无密码
    nickname = Column(String(100))
    avatar_url = Column(String(500))
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    auth_provider = Column(String(50), default="google")  # 认证来源: google
    credits = Column(Integer, default=50)
    vip_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "credits": self.credits,
            "vip_level": self.vip_level,
            "is_active": self.is_active,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(String(500))
    order_id = Column(String(36), nullable=True)
    task_id = Column(String(36), nullable=True)
    balance_after = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255))
    problem_description = Column(String(10000))
    language = Column(String(10), default="zh")
    model_tier = Column(String(20), default="standard")
    status = Column(String(50), default="pending")
    credits_consumed = Column(Integer, default=0)
    result_summary = Column(String(5000))
    result_file_url = Column(String(500))
    error_message = Column(String(2000))
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
