"""
图像分析器单元测试
测试图像分析功能的核心逻辑
"""

from unittest.mock import MagicMock, patch

import pytest

from app.tools.image_analyzer import (
    ImageAnalysisResult,
    ImageAnalyzer,
    create_image_analyzer,
)


class TestImageAnalysisResult:
    """测试图像分析结果数据类"""

    def test_create_result(self):
        """测试创建分析结果"""
        result = ImageAnalysisResult(
            description="这是一张柱状图",
            extracted_text="销量数据",
            extracted_data={"sales": [100, 200, 300]},
            chart_type="bar_chart",
            formulas=["y = ax + b"],
            insights=["销量呈上升趋势"],
        )

        assert result.description == "这是一张柱状图"
        assert result.chart_type == "bar_chart"
        assert len(result.formulas) == 1

    def test_default_values(self):
        """测试默认值"""
        result = ImageAnalysisResult(
            description="基本描述",
        )

        assert result.extracted_text is None
        assert result.extracted_data is None
        assert result.formulas is not None  # 默认空列表
        assert result.insights is not None

    def test_post_init(self):
        """测试后初始化处理"""
        # 传入None时应该初始化为空列表
        result = ImageAnalysisResult(
            description="测试",
            formulas=None,
            insights=None,
        )

        assert result.formulas == []
        assert result.insights == []


class TestImageAnalyzer:
    """测试图像分析器"""

    @pytest.fixture
    def analyzer(self):
        return ImageAnalyzer(
            task_id="test_task",
            api_key="test_api_key",
            model="gpt-4o-mini",
        )

    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.task_id == "test_task"
        assert analyzer.model == "gpt-4o-mini"

    def test_initialization_with_base_url(self):
        """测试带基础URL初始化"""
        analyzer = ImageAnalyzer(
            task_id="test_task",
            api_key="test_key",
            model="gpt-4o",
            base_url="https://api.example.com",
        )

        assert analyzer.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_prepare_image_content_url(self, analyzer):
        """测试准备URL图片内容"""
        image_url = "https://example.com/image.png"
        content = await analyzer._prepare_image_content(image_url)

        assert content is not None
        assert "url" in str(content).lower() or image_url in str(content)

    @pytest.mark.asyncio
    async def test_prepare_image_content_base64(self, analyzer):
        """测试准备Base64图片内容"""
        import base64

        # 创建一个简单的测试图片数据
        test_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        base64_image = f"data:image/png;base64,{base64.b64encode(test_data).decode()}"

        content = await analyzer._prepare_image_content(base64_image)

        assert content is not None

    def test_get_analysis_prompt_general(self, analyzer):
        """测试获取通用分析提示"""
        prompt = analyzer._get_analysis_prompt("general")

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_analysis_prompt_chart(self, analyzer):
        """测试获取图表分析提示"""
        prompt = analyzer._get_analysis_prompt("chart")

        assert isinstance(prompt, str)

    def test_get_analysis_prompt_formula(self, analyzer):
        """测试获取公式分析提示"""
        prompt = analyzer._get_analysis_prompt("formula")

        assert isinstance(prompt, str)

    def test_get_analysis_prompt_diagram(self, analyzer):
        """测试获取图示分析提示"""
        prompt = analyzer._get_analysis_prompt("diagram")

        assert isinstance(prompt, str)

    @pytest.mark.asyncio
    async def test_parse_analysis_response_general(self, analyzer):
        """测试解析通用分析响应"""
        response_content = """
        这是一张展示数据趋势的图表。
        图表显示了过去一年的销售数据变化。
        主要洞察：销量呈上升趋势。
        """

        result = analyzer._parse_analysis_response(response_content, "general")

        assert isinstance(result, ImageAnalysisResult)
        assert result.description is not None

    @pytest.mark.asyncio
    async def test_parse_analysis_response_chart(self, analyzer):
        """测试解析图表分析响应"""
        response_content = """
        图表类型：柱状图
        数据点：
        - 1月: 100
        - 2月: 150
        - 3月: 200
        趋势分析：销量持续增长
        """

        result = analyzer._parse_analysis_response(response_content, "chart")

        assert isinstance(result, ImageAnalysisResult)

    @pytest.mark.asyncio
    async def test_parse_analysis_response_formula(self, analyzer):
        """测试解析公式分析响应"""
        response_content = """
        识别到的公式：
        1. $y = mx + b$
        2. $E = mc^2$
        
        公式说明：线性方程和质能方程
        """

        result = analyzer._parse_analysis_response(response_content, "formula")

        assert isinstance(result, ImageAnalysisResult)


class TestImageAnalyzerWithMock:
    """使用Mock的图像分析器测试"""

    @pytest.fixture
    def analyzer(self):
        return ImageAnalyzer(
            task_id="test_task",
            api_key="test_api_key",
            model="gpt-4o-mini",
        )

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, analyzer):
        """测试成功分析图片（Mock）"""
        with patch("litellm.acompletion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content="这是一张数据可视化图表，展示了销售趋势。"
                    )
                )
            ]
            mock_completion.return_value = mock_response

            result = await analyzer.analyze_image(
                image_source="https://example.com/chart.png",
                analysis_type="general",
            )

            assert isinstance(result, ImageAnalysisResult)

    @pytest.mark.asyncio
    async def test_analyze_multiple_images(self, analyzer):
        """测试分析多张图片（Mock）"""
        with patch.object(analyzer, "analyze_image") as mock_analyze:
            mock_analyze.return_value = ImageAnalysisResult(description="分析结果")

            results = await analyzer.analyze_multiple_images(
                image_sources=[
                    "https://example.com/img1.png",
                    "https://example.com/img2.png",
                ],
                context="数学建模问题",
            )

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_extract_chart_data(self, analyzer):
        """测试提取图表数据（Mock）"""
        with patch.object(analyzer, "analyze_image") as mock_analyze:
            mock_analyze.return_value = ImageAnalysisResult(
                description="柱状图",
                chart_type="bar",
                extracted_data={
                    "labels": ["A", "B", "C"],
                    "values": [10, 20, 30],
                },
            )

            data = await analyzer.extract_chart_data("https://example.com/chart.png")

            assert data is not None

    @pytest.mark.asyncio
    async def test_extract_formulas(self, analyzer):
        """测试提取公式（Mock）"""
        with patch.object(analyzer, "analyze_image") as mock_analyze:
            mock_analyze.return_value = ImageAnalysisResult(
                description="数学公式图片",
                formulas=["y = ax^2 + bx + c", "\\int f(x) dx"],
            )

            formulas = await analyzer.extract_formulas(
                "https://example.com/formula.png"
            )

            assert len(formulas) == 2


class TestCreateImageAnalyzer:
    """测试工厂函数"""

    def test_create_image_analyzer(self):
        """测试创建图像分析器"""
        analyzer = create_image_analyzer(
            task_id="factory_test",
            api_key="test_key",
            model="gpt-4o",
        )

        assert analyzer is not None
        assert analyzer.task_id == "factory_test"
        assert analyzer.model == "gpt-4o"

    def test_create_image_analyzer_with_base_url(self):
        """测试带基础URL创建"""
        analyzer = create_image_analyzer(
            task_id="factory_test",
            api_key="test_key",
            base_url="https://custom.api.com",
        )

        assert analyzer.base_url == "https://custom.api.com"


class TestImageAnalyzerEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def analyzer(self):
        return ImageAnalyzer(
            task_id="edge_test",
            api_key="test_key",
        )

    @pytest.mark.asyncio
    async def test_empty_image_source(self, analyzer):
        """测试空图片源"""
        with pytest.raises(Exception):
            await analyzer.analyze_image(
                image_source="",
                analysis_type="general",
            )

    @pytest.mark.asyncio
    async def test_invalid_analysis_type(self, analyzer):
        """测试无效分析类型"""
        # 应该使用默认提示或返回通用分析
        prompt = analyzer._get_analysis_prompt("invalid_type")

        # 应该返回某种提示（可能是默认的）
        assert isinstance(prompt, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
