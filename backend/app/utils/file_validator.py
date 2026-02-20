"""
文件上传验证工具
提供文件安全验证，包括扩展名、内容类型、魔术字节检查
"""
import os
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.utils.log_util import logger


# 允许的文件扩展名（数据文件）
ALLOWED_DATA_EXTENSIONS = {
    '.csv', '.xlsx', '.xls', '.txt', '.json',
    '.dat', '.tsv', '.xml', '.parquet'
}

# 允许的图片扩展名
ALLOWED_IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg'
}

# 文件大小限制（字节）
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 总计 500MB

# 危险的文件扩展名（应该被拒绝）
DANGEROUS_EXTENSIONS = {
    '.exe', '.dll', '.so', '.sh', '.bat', '.cmd',
    '.ps1', '.vbs', '.jar', '.app', '.deb', '.rpm',
    '.msi', '.scr', '.pif', '.com', '.hta', '.cpl'
}

# 文件魔术字节（用于验证真实文件类型）
FILE_SIGNATURES = {
    '.xlsx': [b'PK\x03\x04'],  # ZIP-based
    '.xls': [b'\xd0\xcf\x11\xe0'],  # OLE2
    '.zip': [b'PK\x03\x04'],
    '.png': [b'\x89PNG\r\n\x1a\n'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.gif': [b'GIF87a', b'GIF89a'],
    '.pdf': [b'%PDF'],
    '.xml': [b'<?xml', b'\xef\xbb\xbf<?xml'],
    '.json': [b'{', b'['],  # JSON通常以这些字符开头
}


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符

    Args:
        filename: 原始文件名

    Returns:
        str: 清理后的文件名

    Raises:
        HTTPException: 文件名包含非法字符
    """
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 移除路径分隔符，防止路径遍历
    filename = os.path.basename(filename)

    # 检查是否包含非法字符（只允许字母、数字、下划线、横线、点、空格、中文）
    if not re.match(r'^[\w\s.\-\u4e00-\u9fa5]+$', filename):
        logger.warning("文件名包含非法字符: %s", filename)
        raise HTTPException(
            status_code=400,
            detail=f"文件名包含非法字符: {filename}"
        )

    # 检查文件名长度
    if len(filename) > 255:
        raise HTTPException(status_code=400, detail="文件名过长（最多255字符）")

    # 防止双扩展名攻击（如 file.txt.exe）
    parts = filename.split('.')
    if len(parts) > 2:
        logger.warning("文件名包含多个扩展名: %s", filename)
        # 只保留最后一个扩展名
        filename = f"{'.'.join(parts[:-1])}_{parts[-1]}"

    return filename


def validate_file_extension(
    filename: str,
    allowed_extensions: set = None
) -> bool:
    """
    验证文件扩展名

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名集合

    Returns:
        bool: 是否允许

    Raises:
        HTTPException: 扩展名不允许
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_DATA_EXTENSIONS

    ext = Path(filename).suffix.lower()

    # 检查是否是危险文件
    if ext in DANGEROUS_EXTENSIONS:
        logger.error("检测到危险文件类型: %s (%s)", filename, ext)
        raise HTTPException(
            status_code=400,
            detail=f"不允许上传 {ext} 文件（安全风险）"
        )

    # 检查是否在白名单中
    if ext not in allowed_extensions:
        logger.warning("文件类型不允许: %s (%s)", filename, ext)
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {ext}。允许的类型: {', '.join(sorted(allowed_extensions))}"
        )

    return True


def verify_file_signature(content: bytes, extension: str) -> bool:
    """
    通过魔术字节验证文件真实类型

    Args:
        content: 文件内容
        extension: 文件扩展名

    Returns:
        bool: 签名是否匹配
    """
    ext = extension.lower()

    # 如果没有该扩展名的签名定义，跳过验证
    if ext not in FILE_SIGNATURES:
        return True

    signatures = FILE_SIGNATURES[ext]

    for sig in signatures:
        if content[:len(sig)] == sig:
            return True

    logger.warning("文件签名不匹配: 扩展名=%s, 实际签名=%s", ext, content[:8].hex())
    return False


def check_for_malicious_content(content: bytes, filename: str) -> bool:
    """
    检查文件内容是否包含恶意代码

    Args:
        content: 文件内容
        filename: 文件名

    Returns:
        bool: 是否安全

    Raises:
        HTTPException: 检测到恶意内容
    """
    ext = Path(filename).suffix.lower()

    # 对于文本文件，检查危险模式
    text_extensions = {'.csv', '.txt', '.json', '.xml', '.tsv'}

    if ext in text_extensions:
        try:
            # 尝试解码为文本
            text_content = content.decode('utf-8', errors='ignore')

            # 检查常见的恶意模式
            dangerous_patterns = [
                r'<script\s*>',  # JavaScript注入
                r'javascript:',  # JS协议
                r'data:text/html',  # 数据URI攻击
                r'on\w+\s*=',  # 事件处理器
                r'eval\s*\(',  # eval调用
                r'exec\s*\(',  # exec调用
                r'__import__',  # Python导入
                r'subprocess',  # 子进程调用
                r'os\.system',  # 系统命令
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    logger.error("检测到危险内容: %s, 模式: %s", filename, pattern)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件 {filename} 包含不安全内容"
                    )

        except UnicodeDecodeError:
            # 非文本文件，跳过检查
            pass

    return True


async def validate_upload_file(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE,
    allowed_extensions: set = None,
    check_signature: bool = True,
    check_content: bool = True
) -> tuple[str, bytes]:
    """
    验证上传的文件

    Args:
        file: FastAPI UploadFile 对象
        max_size: 最大文件大小（字节）
        allowed_extensions: 允许的扩展名集合
        check_signature: 是否检查文件签名
        check_content: 是否检查恶意内容

    Returns:
        tuple[str, bytes]: (清理后的文件名, 文件内容)

    Raises:
        HTTPException: 验证失败
    """
    if not file:
        raise HTTPException(status_code=400, detail="未提供文件")

    # 验证文件名
    clean_filename = sanitize_filename(file.filename)

    # 验证扩展名
    validate_file_extension(clean_filename, allowed_extensions)

    # 读取文件内容
    try:
        content = await file.read()
    except Exception as e:
        logger.error("读取文件失败: %s", e)
        raise HTTPException(status_code=500, detail="读取文件失败")

    # 验证文件大小
    file_size = len(content)
    if file_size == 0:
        logger.warning("文件内容为空: %s", clean_filename)
        raise HTTPException(status_code=400, detail=f"文件 {clean_filename} 内容为空")

    if file_size > max_size:
        logger.warning(
            "文件过大: %s (%s bytes > %s bytes)", clean_filename, file_size, max_size
        )
        raise HTTPException(
            status_code=413,
            detail=f"文件 {clean_filename} 过大（最大 {max_size // 1024 // 1024}MB）"
        )

    # 验证文件签名（魔术字节）
    ext = Path(clean_filename).suffix.lower()
    if check_signature and not verify_file_signature(content, ext):
        raise HTTPException(
            status_code=400,
            detail=f"文件 {clean_filename} 的内容与扩展名不匹配"
        )

    # 检查恶意内容
    if check_content:
        check_for_malicious_content(content, clean_filename)

    logger.info(
        "文件验证通过: %s (%sKB)", clean_filename, file_size // 1024
    )

    return clean_filename, content


async def validate_multiple_files(
    files: list[UploadFile],
    max_total_size: int = MAX_TOTAL_SIZE,
    max_files: int = 50
) -> list[tuple[str, bytes]]:
    """
    验证多个上传的文件

    Args:
        files: 文件列表
        max_total_size: 总大小限制
        max_files: 最大文件数量

    Returns:
        list[tuple[str, bytes]]: (文件名, 内容) 列表

    Raises:
        HTTPException: 验证失败
    """
    if not files:
        raise HTTPException(status_code=400, detail="未提供文件")

    # 检查文件数量
    if len(files) > max_files:
        raise HTTPException(
            status_code=400,
            detail=f"文件数量过多（最多 {max_files} 个）"
        )

    validated_files = []
    total_size = 0

    for file in files:
        clean_filename, content = await validate_upload_file(file)
        total_size += len(content)

        # 检查总大小
        if total_size > max_total_size:
            logger.warning("上传文件总大小超限: %s > %s", total_size, max_total_size)
            raise HTTPException(
                status_code=413,
                detail=f"上传文件总大小超过 {max_total_size // 1024 // 1024}MB 限制"
            )

        validated_files.append((clean_filename, content))

    logger.info(
        "批量文件验证通过: %s 个文件，总计 %sKB", len(validated_files), total_size // 1024
    )

    return validated_files
