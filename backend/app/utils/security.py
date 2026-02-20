"""
输入验证和安全工具
提供统一的输入验证、数据脱敏、安全检查功能
"""
import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator


# ============= 安全配置 =============

class SecurityConfig:
    """安全配置"""
    # 允许的文件扩展名
    ALLOWED_FILE_EXTENSIONS: Set[str] = {
        ".csv", ".xlsx", ".xls", ".json", ".txt", ".md",
        ".png", ".jpg", ".jpeg", ".gif", ".pdf"
    }

    # 最大文件大小 (MB)
    MAX_FILE_SIZE_MB: int = 100

    # 敏感字段名（用于日志脱敏）
    SENSITIVE_FIELDS: Set[str] = {
        "password", "api_key", "token", "secret", "credential",
        "authorization", "access_token", "refresh_token"
    }

    # 禁止的文件名模式
    FORBIDDEN_FILENAME_PATTERNS: List[str] = [
        r"\.\.\/",  # 路径遍历
        r"\.\.\\",  # Windows 路径遍历
        r"^\/",     # 绝对路径
        r"^[a-zA-Z]:\\",  # Windows 绝对路径
    ]

    # SQL 注入检测模式
    SQL_INJECTION_PATTERNS: List[str] = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--|\#|\/\*)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"(\'.*\bOR\b.*\')",
    ]

    # XSS 检测模式
    XSS_PATTERNS: List[str] = [
        r"<script\b[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe\b",
    ]


# ============= 输入验证器 =============

class InputValidator:
    """输入验证器"""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 10000) -> str:
        """
        清理字符串输入

        - 移除控制字符
        - 限制长度
        - HTML 转义
        """
        if not value:
            return ""

        # 移除控制字符（保留换行和制表符）
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

        # 限制长度
        if len(value) > max_length:
            value = value[:max_length]

        return value

    @staticmethod
    def sanitize_html(value: str) -> str:
        """HTML 转义"""
        return html.escape(value)

    @staticmethod
    def validate_filename(filename: str) -> tuple[bool, str]:
        """
        验证文件名安全性

        Returns:
            (is_valid, error_message)
        """
        if not filename:
            return False, "文件名不能为空"

        # 检查路径遍历
        for pattern in SecurityConfig.FORBIDDEN_FILENAME_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return False, "文件名包含非法字符"

        # 检查扩展名
        ext = Path(filename).suffix.lower()
        if ext and ext not in SecurityConfig.ALLOWED_FILE_EXTENSIONS:
            return False, f"不支持的文件类型: {ext}"

        # 检查文件名长度
        if len(filename) > 255:
            return False, "文件名过长"

        # 检查特殊字符
        if re.search(r'[<>:"|?*]', filename):
            return False, "文件名包含非法字符"

        return True, ""

    @staticmethod
    def validate_path(path: str, base_dir: str) -> tuple[bool, str]:
        """
        验证路径安全性，防止路径遍历攻击

        Args:
            path: 待验证的路径
            base_dir: 允许的基础目录

        Returns:
            (is_valid, error_message)
        """
        try:
            # 解析为绝对路径
            base_path = Path(base_dir).resolve()
            target_path = (base_path / path).resolve()

            # 检查是否在基础目录内
            if not str(target_path).startswith(str(base_path)):
                return False, "路径访问被拒绝"

            return True, ""

        except Exception as e:
            return False, f"路径验证失败: {str(e)}"

    @staticmethod
    def check_sql_injection(value: str) -> bool:
        """
        检查 SQL 注入风险

        Returns:
            True if suspicious, False if safe
        """
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def check_xss(value: str) -> bool:
        """
        检查 XSS 风险

        Returns:
            True if suspicious, False if safe
        """
        for pattern in SecurityConfig.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_task_id(task_id: str) -> bool:
        """验证任务 ID 格式"""
        # 格式: YYYYMMDD-HHMMSS-xxxxxxxx
        pattern = r'^\d{8}-\d{6}-[a-f0-9]{8}$'
        return bool(re.match(pattern, task_id))


# ============= 数据脱敏 =============

class DataMasker:
    """数据脱敏工具"""

    @staticmethod
    def mask_api_key(key: str) -> str:
        """脱敏 API Key"""
        if not key or len(key) < 10:
            return "***"
        return f"{key[:6]}...{key[-4:]}"

    @staticmethod
    def mask_email(email: str) -> str:
        """脱敏邮箱"""
        if not email or "@" not in email:
            return "***@***.***"
        local, domain = email.rsplit("@", 1)
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """脱敏手机号"""
        if not phone or len(phone) < 7:
            return "***"
        return f"{phone[:3]}****{phone[-4:]}"

    @staticmethod
    def mask_ip(ip: str) -> str:
        """脱敏 IP 地址"""
        if not ip:
            return "***"
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.***"
        return "***"

    @staticmethod
    def mask_dict(data: Dict[str, Any], sensitive_fields: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        脱敏字典中的敏感字段

        Args:
            data: 待脱敏的字典
            sensitive_fields: 敏感字段名集合

        Returns:
            脱敏后的字典
        """
        if sensitive_fields is None:
            sensitive_fields = SecurityConfig.SENSITIVE_FIELDS

        result = {}
        for key, value in data.items():
            key_lower = key.lower()

            if any(field in key_lower for field in sensitive_fields):
                if isinstance(value, str):
                    result[key] = DataMasker.mask_api_key(value)
                else:
                    result[key] = "***"
            elif isinstance(value, dict):
                result[key] = DataMasker.mask_dict(value, sensitive_fields)
            elif isinstance(value, list):
                result[key] = [
                    DataMasker.mask_dict(item, sensitive_fields) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result


# ============= 安全验证模型 =============

class SecureTaskInput(BaseModel):
    """安全的任务输入模型"""
    problem: str = Field(..., min_length=10, max_length=50000, description="问题描述")
    questions: Dict[str, str] = Field(default_factory=dict, description="问题列表")

    @field_validator('problem')
    @classmethod
    def validate_problem(cls, v: str) -> str:
        v = InputValidator.sanitize_string(v)

        if InputValidator.check_sql_injection(v):
            raise ValueError("输入包含可疑内容")

        if InputValidator.check_xss(v):
            raise ValueError("输入包含非法字符")

        return v


class SecureFileUpload(BaseModel):
    """安全的文件上传验证"""
    filename: str = Field(..., max_length=255)
    size: int = Field(..., gt=0)

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        is_valid, error = InputValidator.validate_filename(v)
        if not is_valid:
            raise ValueError(error)
        return v

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: int) -> int:
        max_size = SecurityConfig.MAX_FILE_SIZE_MB * 1024 * 1024
        if v > max_size:
            raise ValueError(f"文件大小超过限制 ({SecurityConfig.MAX_FILE_SIZE_MB}MB)")
        return v


# ============= 安全检查函数 =============

def check_request_safety(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    检查请求数据安全性

    Returns:
        (is_safe, error_message)
    """
    def check_value(value: Any, path: str = "") -> tuple[bool, str]:
        if isinstance(value, str):
            if InputValidator.check_sql_injection(value):
                return False, f"检测到可疑输入 (位置: {path})"
            if InputValidator.check_xss(value):
                return False, f"检测到非法字符 (位置: {path})"
        elif isinstance(value, dict):
            for k, v in value.items():
                is_safe, error = check_value(v, f"{path}.{k}" if path else k)
                if not is_safe:
                    return False, error
        elif isinstance(value, list):
            for i, item in enumerate(value):
                is_safe, error = check_value(item, f"{path}[{i}]")
                if not is_safe:
                    return False, error
        return True, ""

    return check_value(data)
