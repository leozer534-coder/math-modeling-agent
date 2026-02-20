"""
通用工具函数测试模块
"""
import unittest

from app.utils.common_utils import split_footnotes


class TestCommonUtils(unittest.TestCase):
    def test_split_footnotes(self):
        """测试脚注拆分：主文本保留行内引用标记，脚注定义被提取。

        split_footnotes 的实际行为：
        - 从文本末尾移除脚注定义行 ([^1]: ...)
        - 行内脚注引用 ([^1]) 保留在主文本中
        - 返回 (主文本, [(编号, 内容), ...])
        """
        text = "Example[^1]\n\n[^1]: Footnote content"
        main, notes = split_footnotes(text)
        # 主文本保留行内引用标记，脚注定义行被移除
        self.assertEqual(main, "Example[^1]")
        self.assertEqual(notes, [("1", "Footnote content")])

    def test_split_footnotes_no_footnotes(self):
        """测试无脚注的文本"""
        text = "Plain text without footnotes"
        main, notes = split_footnotes(text)
        self.assertEqual(main, "Plain text without footnotes")
        self.assertEqual(notes, [])

    def test_split_footnotes_multiple(self):
        """测试多个脚注"""
        text = "A[^1] and B[^2]\n\n[^1]: First note\n[^2]: Second note"
        main, notes = split_footnotes(text)
        self.assertIn("A[^1]", main)
        self.assertIn("B[^2]", main)
        self.assertEqual(len(notes), 2)


if __name__ == "__main__":
    unittest.main()
