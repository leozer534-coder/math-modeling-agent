"""
JSON解析辅助模块
提供更鲁棒的JSON解析功能，用于处理LLM响应
"""
import json
import re
from typing import Any, Optional, TypeVar

from app.utils.log_util import logger


T = TypeVar('T')


class JSONParseError(Exception):
    """JSON解析错误"""
    def __init__(self, message: str, raw_content: str = ""):
        super().__init__(message)
        self.raw_content = raw_content


def clean_json_string(raw: str) -> str:
    """清理 LLM 返回的 JSON 字符串中的常见干扰字符。

    处理以下场景:
    1. 移除 ```json ... ``` 代码块标记
    2. 移除不可见控制字符（ASCII 0x00-0x1F, 0x7F）
    3. 去除首尾空白

    Args:
        raw: LLM 返回的原始字符串

    Returns:
        清理后的纯 JSON 字符串
    """
    if not raw:
        return ""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    cleaned = re.sub(r"[\x00-\x1F\x7F]", "", cleaned)
    return cleaned


def extract_json_from_response(content: str) -> str:
    """
    从LLM响应中提取JSON内容

    支持以下格式：
    1. 纯JSON
    2. 包含在```json...```代码块中
    3. 包含在```...```代码块中
    4. 混合文字和JSON

    Args:
        content: LLM响应内容

    Returns:
        提取出的JSON字符串
    """
    if not content:
        raise JSONParseError("空内容", content)

    content = content.strip()

    # 方法1: 尝试直接解析
    if content.startswith('{') or content.startswith('['):
        # 可能是纯JSON，找到匹配的结束括号
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass

    # 方法2: 提取```json...```代码块
    json_block_pattern = r'```json\s*([\s\S]*?)\s*```'
    matches = re.findall(json_block_pattern, content, re.IGNORECASE)
    if matches:
        return matches[0].strip()

    # 方法3: 提取```...```代码块（不指定语言）
    code_block_pattern = r'```\s*([\s\S]*?)\s*```'
    matches = re.findall(code_block_pattern, content)
    for match in matches:
        match = match.strip()
        if match.startswith('{') or match.startswith('['):
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue

    # 方法4: 查找第一个完整的JSON对象
    # 找到第一个 { 和最后一个 }
    start_idx = content.find('{')
    if start_idx == -1:
        start_idx = content.find('[')

    if start_idx != -1:
        # 尝试找到匹配的结束括号
        bracket_count = 0
        in_string = False
        escape_next = False
        start_char = content[start_idx]
        end_char = '}' if start_char == '{' else ']'

        for i in range(start_idx, len(content)):
            char = content[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == start_char:
                bracket_count += 1
            elif char == end_char:
                bracket_count -= 1
                if bracket_count == 0:
                    json_str = content[start_idx:i + 1]
                    try:
                        json.loads(json_str)
                        return json_str
                    except json.JSONDecodeError:
                        break

    # 方法5: 清理并尝试
    cleaned = content
    # 移除markdown代码块标记
    cleaned = re.sub(r'```\w*\n?', '', cleaned)
    cleaned = cleaned.strip()

    if cleaned.startswith('{') or cleaned.startswith('['):
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass

    raise JSONParseError("无法从响应中提取JSON", content)


def parse_json_safely(
    content: str,
    default: Optional[T] = None,
    repair: bool = True
) -> Any:
    """
    安全地解析JSON，支持自动修复常见错误

    Args:
        content: JSON字符串或包含JSON的文本
        default: 解析失败时返回的默认值
        repair: 是否尝试修复JSON

    Returns:
        解析后的Python对象，或默认值
    """
    try:
        # 首先提取JSON
        json_str = extract_json_from_response(content)

        # 尝试直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            if not repair:
                raise
            logger.debug("JSON解析失败，尝试修复: %s", e)

        # 尝试修复常见问题
        repaired = repair_json(json_str)
        return json.loads(repaired)

    except Exception as e:
        logger.warning("JSON解析失败: %s", e)
        if default is not None:
            return default
        raise JSONParseError(f"JSON解析失败: {e}", content)


def repair_json(json_str: str) -> str:
    """
    尝试修复常见的JSON格式错误

    常见问题：
    1. 尾随逗号
    2. 单引号而非双引号
    3. 未引用的键名
    4. 注释
    5. 特殊字符未转义
    """
    if not json_str:
        return json_str

    repaired = json_str

    # 1. 移除JavaScript风格的注释
    repaired = re.sub(r'//.*$', '', repaired, flags=re.MULTILINE)
    repaired = re.sub(r'/\*[\s\S]*?\*/', '', repaired)

    # 2. 移除尾随逗号（在 } 或 ] 之前的逗号）
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

    # 3. 将单引号键名转换为双引号（简单情况）
    # 注意：这只处理简单的情况，复杂的嵌套可能需要更复杂的处理
    repaired = re.sub(r"'([^']+)'(\s*:)", r'"\1"\2', repaired)

    # 4. 尝试修复未引用的键名
    # 查找模式如 {key: 或 ,key: 并添加引号
    repaired = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', repaired)

    # 5. 修复布尔值和null的大小写
    repaired = re.sub(r'\bTrue\b', 'true', repaired)
    repaired = re.sub(r'\bFalse\b', 'false', repaired)
    repaired = re.sub(r'\bNone\b', 'null', repaired)

    # 6. 修复多余的空白
    repaired = repaired.strip()

    return repaired


def validate_json_schema(
    data: dict,
    required_keys: list[str],
    optional_keys: list[str] = None
) -> tuple[bool, list[str]]:
    """
    验证JSON数据是否符合预期结构

    Args:
        data: 要验证的数据
        required_keys: 必需的键列表
        optional_keys: 可选的键列表

    Returns:
        (is_valid, missing_keys): 是否有效，缺失的键列表
    """
    if not isinstance(data, dict):
        return False, ["数据不是字典类型"]

    missing = []
    for key in required_keys:
        if key not in data:
            missing.append(key)

    return len(missing) == 0, missing


def safe_get_nested(data: dict, *keys, default=None):
    """
    安全地获取嵌套字典中的值

    Args:
        data: 字典数据
        *keys: 键的路径
        default: 默认值

    Returns:
        找到的值或默认值
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


class JSONResponseParser:
    """
    JSON响应解析器

    提供便捷的方法来解析和验证LLM返回的JSON响应
    """

    def __init__(self, required_keys: list[str] = None, optional_keys: list[str] = None):
        self.required_keys = required_keys or []
        self.optional_keys = optional_keys or []

    def parse(self, content: str, repair: bool = True) -> dict:
        """
        解析JSON响应

        Args:
            content: LLM响应内容
            repair: 是否尝试修复JSON

        Returns:
            解析后的字典

        Raises:
            JSONParseError: 解析失败时
        """
        data = parse_json_safely(content, repair=repair)

        if self.required_keys:
            is_valid, missing = validate_json_schema(data, self.required_keys)
            if not is_valid:
                raise JSONParseError(f"缺少必需的字段: {missing}", content)

        return data

    def parse_or_default(self, content: str, default: dict = None) -> dict:
        """
        解析JSON响应，失败时返回默认值

        Args:
            content: LLM响应内容
            default: 默认值

        Returns:
            解析后的字典或默认值
        """
        try:
            return self.parse(content)
        except Exception as e:
            logger.warning("JSON解析失败，使用默认值: %s", e)
            return default if default is not None else {}
