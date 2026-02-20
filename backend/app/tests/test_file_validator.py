"""
文件验证器单元测试
"""
import unittest

from fastapi import HTTPException

from app.utils.file_validator import (
    ALLOWED_DATA_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    DANGEROUS_EXTENSIONS,
    FILE_SIGNATURES,
    check_for_malicious_content,
    sanitize_filename,
    validate_file_extension,
    verify_file_signature,
)


class TestSanitizeFilename(unittest.TestCase):
    """测试文件名清理"""

    def test_valid_filename(self):
        """测试有效文件名"""
        result = sanitize_filename("data.csv")
        self.assertEqual(result, "data.csv")

    def test_chinese_filename(self):
        """测试中文文件名"""
        result = sanitize_filename("数据文件.xlsx")
        self.assertEqual(result, "数据文件.xlsx")

    def test_filename_with_spaces(self):
        """测试带空格的文件名"""
        result = sanitize_filename("my data file.csv")
        self.assertEqual(result, "my data file.csv")

    def test_filename_with_underscore_dash(self):
        """测试带下划线和横线的文件名"""
        result = sanitize_filename("my_data-file.csv")
        self.assertEqual(result, "my_data-file.csv")

    def test_empty_filename(self):
        """测试空文件名"""
        with self.assertRaises(HTTPException) as context:
            sanitize_filename("")
        self.assertEqual(context.exception.status_code, 400)

    def test_path_traversal_attack(self):
        """测试路径遍历攻击"""
        # os.path.basename 应该移除路径
        result = sanitize_filename("../../../etc/passwd")
        self.assertEqual(result, "passwd")

    def test_windows_path_traversal(self):
        """测试Windows路径遍历"""
        result = sanitize_filename("..\\..\\system32\\config")
        self.assertEqual(result, "config")

    def test_illegal_characters(self):
        """测试非法字符"""
        with self.assertRaises(HTTPException) as context:
            sanitize_filename("file<script>.csv")
        self.assertEqual(context.exception.status_code, 400)

    def test_long_filename(self):
        """测试过长文件名"""
        long_name = "a" * 300 + ".csv"
        with self.assertRaises(HTTPException) as context:
            sanitize_filename(long_name)
        self.assertEqual(context.exception.status_code, 400)

    def test_double_extension(self):
        """测试双扩展名"""
        result = sanitize_filename("file.txt.exe")
        # 应该处理双扩展名
        self.assertIn("_", result)


class TestValidateFileExtension(unittest.TestCase):
    """测试文件扩展名验证"""

    def test_valid_data_extension(self):
        """测试有效的数据文件扩展名"""
        result = validate_file_extension("data.csv")
        self.assertTrue(result)

    def test_valid_xlsx_extension(self):
        """测试有效的xlsx扩展名"""
        result = validate_file_extension("report.xlsx")
        self.assertTrue(result)

    def test_valid_json_extension(self):
        """测试有效的json扩展名"""
        result = validate_file_extension("config.json")
        self.assertTrue(result)

    def test_dangerous_extension_exe(self):
        """测试危险的exe扩展名"""
        with self.assertRaises(HTTPException) as context:
            validate_file_extension("virus.exe")
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("安全风险", context.exception.detail)

    def test_dangerous_extension_bat(self):
        """测试危险的bat扩展名"""
        with self.assertRaises(HTTPException) as context:
            validate_file_extension("script.bat")
        self.assertEqual(context.exception.status_code, 400)

    def test_unsupported_extension(self):
        """测试不支持的扩展名"""
        with self.assertRaises(HTTPException) as context:
            validate_file_extension("video.mp4")
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("不支持的文件类型", context.exception.detail)

    def test_custom_allowed_extensions(self):
        """测试自定义允许的扩展名"""
        result = validate_file_extension(
            "image.png",
            allowed_extensions=ALLOWED_IMAGE_EXTENSIONS
        )
        self.assertTrue(result)

    def test_case_insensitive(self):
        """测试扩展名大小写不敏感"""
        result = validate_file_extension("DATA.CSV")
        self.assertTrue(result)


class TestVerifyFileSignature(unittest.TestCase):
    """测试文件签名验证"""

    def test_png_signature(self):
        """测试PNG签名"""
        png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result = verify_file_signature(png_header, ".png")
        self.assertTrue(result)

    def test_jpg_signature(self):
        """测试JPG签名"""
        jpg_header = b'\xff\xd8\xff' + b'\x00' * 100
        result = verify_file_signature(jpg_header, ".jpg")
        self.assertTrue(result)

    def test_jpeg_signature(self):
        """测试JPEG签名"""
        jpeg_header = b'\xff\xd8\xff' + b'\x00' * 100
        result = verify_file_signature(jpeg_header, ".jpeg")
        self.assertTrue(result)

    def test_gif_signature(self):
        """测试GIF签名"""
        gif_header = b'GIF89a' + b'\x00' * 100
        result = verify_file_signature(gif_header, ".gif")
        self.assertTrue(result)

    def test_xlsx_signature(self):
        """测试XLSX签名（ZIP格式）"""
        xlsx_header = b'PK\x03\x04' + b'\x00' * 100
        result = verify_file_signature(xlsx_header, ".xlsx")
        self.assertTrue(result)

    def test_xls_signature(self):
        """测试XLS签名（OLE2格式）"""
        xls_header = b'\xd0\xcf\x11\xe0' + b'\x00' * 100
        result = verify_file_signature(xls_header, ".xls")
        self.assertTrue(result)

    def test_json_signature(self):
        """测试JSON签名"""
        json_content = b'{"key": "value"}'
        result = verify_file_signature(json_content, ".json")
        self.assertTrue(result)

    def test_json_array_signature(self):
        """测试JSON数组签名"""
        json_content = b'[1, 2, 3]'
        result = verify_file_signature(json_content, ".json")
        self.assertTrue(result)

    def test_invalid_signature(self):
        """测试无效签名"""
        fake_png = b'NOT_A_PNG_FILE'
        result = verify_file_signature(fake_png, ".png")
        self.assertFalse(result)

    def test_unknown_extension(self):
        """测试未知扩展名（跳过验证）"""
        content = b'some random content'
        result = verify_file_signature(content, ".unknown")
        self.assertTrue(result)

    def test_csv_no_signature(self):
        """测试CSV（无签名要求）"""
        csv_content = b'a,b,c\n1,2,3'
        result = verify_file_signature(csv_content, ".csv")
        self.assertTrue(result)


class TestCheckForMaliciousContent(unittest.TestCase):
    """测试恶意内容检测"""

    def test_safe_csv_content(self):
        """测试安全的CSV内容"""
        content = b"name,age\nAlice,30\nBob,25"
        result = check_for_malicious_content(content, "data.csv")
        self.assertTrue(result)

    def test_safe_json_content(self):
        """测试安全的JSON内容"""
        content = b'{"users": [{"name": "Alice"}, {"name": "Bob"}]}'
        result = check_for_malicious_content(content, "data.json")
        self.assertTrue(result)

    def test_script_injection(self):
        """测试脚本注入"""
        content = b'<script>alert("xss")</script>'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "data.csv")
        self.assertEqual(context.exception.status_code, 400)

    def test_javascript_protocol(self):
        """测试JavaScript协议"""
        content = b'href="javascript:alert(1)"'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "data.txt")
        self.assertEqual(context.exception.status_code, 400)

    def test_event_handler_injection(self):
        """测试事件处理器注入"""
        content = b'<img onerror="alert(1)">'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "data.csv")
        self.assertEqual(context.exception.status_code, 400)

    def test_eval_call(self):
        """测试eval调用"""
        content = b'eval("malicious code")'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "data.txt")
        self.assertEqual(context.exception.status_code, 400)

    def test_python_import(self):
        """测试Python __import__"""
        content = b'__import__("os").system("rm -rf /")'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "script.txt")
        self.assertEqual(context.exception.status_code, 400)

    def test_subprocess_call(self):
        """测试subprocess调用"""
        content = b'import subprocess; subprocess.run(["cmd"])'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "code.txt")
        self.assertEqual(context.exception.status_code, 400)

    def test_os_system_call(self):
        """测试os.system调用"""
        content = b'os.system("cat /etc/passwd")'
        with self.assertRaises(HTTPException) as context:
            check_for_malicious_content(content, "script.txt")
        self.assertEqual(context.exception.status_code, 400)

    def test_binary_file_skip(self):
        """测试二进制文件跳过检查"""
        # PNG文件是二进制，应该跳过文本检查
        content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        result = check_for_malicious_content(content, "image.png")
        self.assertTrue(result)

    def test_xlsx_binary_skip(self):
        """测试XLSX二进制跳过检查"""
        # XLSX是ZIP格式的二进制文件
        content = b'PK\x03\x04' + b'\x00' * 100
        result = check_for_malicious_content(content, "data.xlsx")
        self.assertTrue(result)


class TestExtensionSets(unittest.TestCase):
    """测试扩展名集合"""

    def test_data_extensions_complete(self):
        """测试数据扩展名集合完整"""
        expected = {'.csv', '.xlsx', '.xls', '.txt', '.json', '.dat', '.tsv', '.xml', '.parquet'}
        self.assertEqual(ALLOWED_DATA_EXTENSIONS, expected)

    def test_image_extensions_complete(self):
        """测试图片扩展名集合完整"""
        expected = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg'}
        self.assertEqual(ALLOWED_IMAGE_EXTENSIONS, expected)

    def test_dangerous_extensions_complete(self):
        """测试危险扩展名集合包含常见危险类型"""
        self.assertIn('.exe', DANGEROUS_EXTENSIONS)
        self.assertIn('.dll', DANGEROUS_EXTENSIONS)
        self.assertIn('.bat', DANGEROUS_EXTENSIONS)
        self.assertIn('.sh', DANGEROUS_EXTENSIONS)
        self.assertIn('.ps1', DANGEROUS_EXTENSIONS)

    def test_file_signatures_defined(self):
        """测试文件签名已定义"""
        self.assertIn('.png', FILE_SIGNATURES)
        self.assertIn('.jpg', FILE_SIGNATURES)
        self.assertIn('.xlsx', FILE_SIGNATURES)
        self.assertIn('.xls', FILE_SIGNATURES)


if __name__ == "__main__":
    unittest.main()
