"""
JSON解析器单元测试
"""
import unittest

from app.utils.json_parser import (
    JSONParseError,
    JSONResponseParser,
    extract_json_from_response,
    parse_json_safely,
    repair_json,
    safe_get_nested,
    validate_json_schema,
)


class TestExtractJsonFromResponse(unittest.TestCase):
    """测试JSON提取功能"""

    def test_extract_pure_json_object(self):
        """测试提取纯JSON对象"""
        content = '{"name": "test", "value": 123}'
        result = extract_json_from_response(content)
        self.assertEqual(result, content)

    def test_extract_pure_json_array(self):
        """测试提取纯JSON数组"""
        content = '[1, 2, 3]'
        result = extract_json_from_response(content)
        self.assertEqual(result, content)

    def test_extract_from_json_code_block(self):
        """测试从```json代码块提取"""
        content = '''这是一些文本
```json
{"key": "value"}
```
更多文本'''
        result = extract_json_from_response(content)
        self.assertEqual(result, '{"key": "value"}')

    def test_extract_from_generic_code_block(self):
        """测试从通用代码块提取"""
        content = '''回复内容
```
{"data": [1, 2, 3]}
```
结束'''
        result = extract_json_from_response(content)
        self.assertEqual(result, '{"data": [1, 2, 3]}')

    def test_extract_embedded_json(self):
        """测试提取嵌入在文本中的JSON"""
        content = '这是响应: {"result": true} 结束'
        result = extract_json_from_response(content)
        self.assertEqual(result, '{"result": true}')

    def test_extract_nested_json(self):
        """测试提取嵌套JSON"""
        content = '{"outer": {"inner": {"deep": 1}}}'
        result = extract_json_from_response(content)
        self.assertEqual(result, content)

    def test_empty_content_raises_error(self):
        """测试空内容抛出错误"""
        with self.assertRaises(JSONParseError):
            extract_json_from_response("")

    def test_no_json_raises_error(self):
        """测试无JSON内容抛出错误"""
        with self.assertRaises(JSONParseError):
            extract_json_from_response("这是普通文本，没有JSON")


class TestRepairJson(unittest.TestCase):
    """测试JSON修复功能"""

    def test_remove_trailing_comma_object(self):
        """测试移除对象中的尾随逗号"""
        broken = '{"a": 1, "b": 2,}'
        repaired = repair_json(broken)
        self.assertEqual(repaired, '{"a": 1, "b": 2}')

    def test_remove_trailing_comma_array(self):
        """测试移除数组中的尾随逗号"""
        broken = '[1, 2, 3,]'
        repaired = repair_json(broken)
        self.assertEqual(repaired, '[1, 2, 3]')

    def test_convert_single_quotes(self):
        """测试转换单引号键名为双引号"""
        broken = "{'key': 'value'}"
        repaired = repair_json(broken)
        self.assertIn('"key"', repaired)

    def test_fix_python_bool_true(self):
        """测试修复Python布尔值True"""
        broken = '{"flag": True}'
        repaired = repair_json(broken)
        self.assertEqual(repaired, '{"flag": true}')

    def test_fix_python_bool_false(self):
        """测试修复Python布尔值False"""
        broken = '{"flag": False}'
        repaired = repair_json(broken)
        self.assertEqual(repaired, '{"flag": false}')

    def test_fix_python_none(self):
        """测试修复Python None为null"""
        broken = '{"value": None}'
        repaired = repair_json(broken)
        self.assertEqual(repaired, '{"value": null}')

    def test_remove_javascript_comments(self):
        """测试移除JavaScript风格注释"""
        broken = '{"key": "value" // 这是注释\n}'
        repaired = repair_json(broken)
        self.assertNotIn('//', repaired)

    def test_empty_string(self):
        """测试空字符串"""
        result = repair_json("")
        self.assertEqual(result, "")


class TestParseJsonSafely(unittest.TestCase):
    """测试安全JSON解析"""

    def test_parse_valid_json(self):
        """测试解析有效JSON"""
        content = '{"name": "test"}'
        result = parse_json_safely(content)
        self.assertEqual(result, {"name": "test"})

    def test_parse_with_repair(self):
        """测试带修复的解析"""
        # 包装在代码块中以便 extract_json_from_response 识别
        content = '```json\n{"flag": True, "value": None,}\n```'
        result = parse_json_safely(content, repair=True)
        self.assertEqual(result, {"flag": True, "value": None})

    def test_parse_with_default(self):
        """测试带默认值的解析"""
        content = "invalid json"
        default = {"default": True}
        result = parse_json_safely(content, default=default)
        self.assertEqual(result, default)

    def test_parse_from_code_block(self):
        """测试从代码块解析"""
        content = '```json\n{"data": 123}\n```'
        result = parse_json_safely(content)
        self.assertEqual(result, {"data": 123})


class TestValidateJsonSchema(unittest.TestCase):
    """测试JSON架构验证"""

    def test_validate_with_all_required_keys(self):
        """测试所有必需键都存在"""
        data = {"name": "test", "value": 123}
        is_valid, missing = validate_json_schema(data, ["name", "value"])
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

    def test_validate_with_missing_keys(self):
        """测试缺少必需键"""
        data = {"name": "test"}
        is_valid, missing = validate_json_schema(data, ["name", "value", "type"])
        self.assertFalse(is_valid)
        self.assertIn("value", missing)
        self.assertIn("type", missing)

    def test_validate_non_dict(self):
        """测试非字典数据"""
        is_valid, missing = validate_json_schema([1, 2, 3], ["key"])
        self.assertFalse(is_valid)
        self.assertEqual(missing, ["数据不是字典类型"])

    def test_validate_with_optional_keys(self):
        """测试可选键"""
        data = {"name": "test"}
        is_valid, missing = validate_json_schema(
            data,
            required_keys=["name"],
            optional_keys=["description"]
        )
        self.assertTrue(is_valid)


class TestSafeGetNested(unittest.TestCase):
    """测试安全获取嵌套值"""

    def test_get_simple_key(self):
        """测试获取简单键"""
        data = {"name": "test"}
        result = safe_get_nested(data, "name")
        self.assertEqual(result, "test")

    def test_get_nested_key(self):
        """测试获取嵌套键"""
        data = {"level1": {"level2": {"level3": "deep"}}}
        result = safe_get_nested(data, "level1", "level2", "level3")
        self.assertEqual(result, "deep")

    def test_get_missing_key_with_default(self):
        """测试获取不存在的键返回默认值"""
        data = {"name": "test"}
        result = safe_get_nested(data, "missing", default="default_value")
        self.assertEqual(result, "default_value")

    def test_get_nested_missing_key(self):
        """测试获取嵌套不存在的键"""
        data = {"level1": {"level2": "value"}}
        result = safe_get_nested(data, "level1", "level2", "level3", default=None)
        self.assertIsNone(result)


class TestJSONResponseParser(unittest.TestCase):
    """测试JSON响应解析器"""

    def test_parse_with_required_keys(self):
        """测试带必需键的解析"""
        parser = JSONResponseParser(required_keys=["status", "data"])
        content = '{"status": "ok", "data": []}'
        result = parser.parse(content)
        self.assertEqual(result["status"], "ok")

    def test_parse_missing_required_key_raises_error(self):
        """测试缺少必需键抛出错误"""
        parser = JSONResponseParser(required_keys=["status", "message"])
        content = '{"status": "ok"}'
        with self.assertRaises(JSONParseError):
            parser.parse(content)

    def test_parse_or_default(self):
        """测试解析失败返回默认值"""
        parser = JSONResponseParser(required_keys=["key"])
        result = parser.parse_or_default("invalid", default={"key": "default"})
        self.assertEqual(result, {"key": "default"})

    def test_parse_or_default_empty_dict(self):
        """测试解析失败返回空字典"""
        parser = JSONResponseParser()
        result = parser.parse_or_default("invalid")
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
