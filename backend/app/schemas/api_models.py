"""
API 响应模型和文档增强
提供标准化的 API 响应格式和 OpenAPI 文档增强
"""
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar('T')


# ============= 通用响应模型 =============

class SuccessResponse(BaseModel, Generic[T]):
    """成功响应基类"""
    success: bool = True
    data: T
    message: str = "操作成功"
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "message": "操作成功",
                "timestamp": "2024-01-01T00:00:00"
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    success: bool = True
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    message: str = "获取成功"

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "message": "获取成功"
            }
        }


class ErrorResponseModel(BaseModel):
    """错误响应"""
    success: bool = False
    error: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "E1000",
                    "message": "服务器内部错误",
                    "detail": "详细错误信息",
                    "request_id": "req_abc123"
                }
            }
        }


# ============= 健康检查响应 =============

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态", example="healthy")
    version: str = Field(..., description="API 版本", example="0.1.0")
    env: str = Field(..., description="运行环境", example="dev")
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Optional[Dict[str, str]] = Field(
        None,
        description="依赖服务状态",
        example={"redis": "connected", "database": "connected"}
    )


# ============= 任务相关响应 =============

class TaskCreateResponse(BaseModel):
    """创建任务响应"""
    task_id: str = Field(..., description="任务 ID", example="20240101-120000-abc123")
    status: str = Field(..., description="任务状态", example="pending")
    message: str = Field(default="任务创建成功", description="提示信息")
    created_at: datetime = Field(default_factory=datetime.now)


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="任务状态", example="running")
    progress: float = Field(0.0, description="进度百分比 (0-100)", ge=0, le=100)
    current_phase: str = Field("", description="当前阶段")
    message: str = Field("", description="状态描述")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskStatusResponse]
    total: int


# ============= 文件相关响应 =============

class FileInfo(BaseModel):
    """文件信息"""
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="文件路径")
    size: int = Field(..., description="文件大小（字节）")
    type: str = Field(..., description="文件类型")
    created_at: datetime = Field(..., description="创建时间")
    modified_at: datetime = Field(..., description="修改时间")


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    success: bool = True
    files: List[FileInfo]
    message: str = "上传成功"


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[FileInfo]
    total: int
    path: str = Field(..., description="当前目录路径")


# ============= 建模相关响应 =============

class ModelingStartResponse(BaseModel):
    """开始建模响应"""
    task_id: str = Field(..., description="任务 ID")
    status: str = "started"
    message: str = "建模任务已启动"
    websocket_url: str = Field(..., description="WebSocket 连接地址")


class ModelingResultResponse(BaseModel):
    """建模结果响应"""
    task_id: str
    status: str = "completed"
    result: Dict[str, Any] = Field(..., description="建模结果")
    files: List[FileInfo] = Field(default_factory=list, description="生成的文件")
    execution_time: float = Field(..., description="执行时间（秒）")
    tokens_used: int = Field(0, description="消耗的 Token 数")


# ============= 用户认证响应 =============

class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    id: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    created_at: datetime
    last_login: Optional[datetime] = None


# ============= API Key 验证响应 =============

class ApiKeyValidationResponse(BaseModel):
    """API Key 验证响应"""
    valid: bool = Field(..., description="是否有效")
    message: str = Field(..., description="验证结果描述")
    model_id: Optional[str] = Field(None, description="模型 ID")
    provider: Optional[str] = Field(None, description="服务商")


# ============= OpenAPI 文档增强 =============

API_TAGS_METADATA = [
    {
        "name": "健康检查",
        "description": "服务健康状态检查接口",
    },
    {
        "name": "认证",
        "description": "用户认证和授权相关接口",
    },
    {
        "name": "建模",
        "description": "数学建模任务管理接口，包括创建、查询、取消任务",
    },
    {
        "name": "文件",
        "description": "文件上传、下载和管理接口",
    },
    {
        "name": "WebSocket",
        "description": "实时通信接口，用于任务进度推送",
    },
    {
        "name": "配置",
        "description": "系统配置和 API Key 管理接口",
    },
]


API_DESCRIPTION = """
# MathModelAgent API

专为数学建模竞赛设计的智能体系统 API。

## 功能特性

- 🔍 **自动分析问题** - 智能理解建模题目
- 🧮 **数学建模** - 自动选择和构建数学模型
- 💻 **代码执行** - 自动编写和运行代码
- 📝 **论文生成** - 自动撰写格式化论文

## 认证方式

API 使用 Bearer Token 认证：

```
Authorization: Bearer <your_token>
```

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| E1xxx | 通用错误 |
| E2xxx | 认证错误 |
| E3xxx | 业务错误 |
| E4xxx | Agent 错误 |
| E5xxx | 文件错误 |
| E6xxx | 外部服务错误 |

## WebSocket 连接

实时任务进度通过 WebSocket 推送：

```
ws://localhost:8000/ws/{task_id}
```

## 速率限制

- 普通接口: 100 请求/分钟
- 建模接口: 10 请求/分钟

超过限制返回 429 状态码。
"""
