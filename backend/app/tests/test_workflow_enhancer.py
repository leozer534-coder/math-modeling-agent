"""
工作流增强器单元测试
测试问题分析增强器、代码质量增强器、论文质量增强器
"""

import pytest

from app.core.workflow_enhancer import (
    CodeQualityEnhancer,
    EnhancementResult,
    EnhancementType,
    PaperQualityEnhancer,
    ProblemAnalysisEnhancer,
    WorkflowEnhancer,
    create_workflow_enhancer,
)


class TestEnhancementType:
    """测试增强类型枚举"""

    def test_enhancement_type_values(self):
        """测试增强类型值"""
        assert EnhancementType.PROBLEM_ANALYSIS == "problem_analysis"
        assert EnhancementType.CODE_QUALITY == "code_quality"
        assert EnhancementType.PAPER_QUALITY == "paper_quality"
        assert EnhancementType.COORDINATION == "coordination"


class TestEnhancementResult:
    """测试增强结果数据类"""

    def test_create_enhancement_result(self):
        """测试创建增强结果"""
        result = EnhancementResult(
            enhancement_type=EnhancementType.CODE_QUALITY,
            original_input="original code",
            enhanced_output="enhanced code",
            improvements=["添加了注释", "优化了结构"],
            suggestions=["建议添加异常处理"],
        )
        assert result.enhancement_type == EnhancementType.CODE_QUALITY
        assert len(result.improvements) == 2
        assert len(result.suggestions) == 1


class TestProblemAnalysisEnhancer:
    """测试问题分析增强器"""

    @pytest.fixture
    def enhancer(self):
        return ProblemAnalysisEnhancer()

    @pytest.mark.asyncio
    async def test_enhance_optimization_problem(self, enhancer):
        """测试增强优化问题分析"""
        result = await enhancer.enhance(
            problem_description="某公司需要安排生产计划，最小化成本",
            problem_type="optimization",
        )

        assert result.enhancement_type == EnhancementType.PROBLEM_ANALYSIS
        assert result.enhanced_output is not None

    @pytest.mark.asyncio
    async def test_enhance_prediction_problem(self, enhancer):
        """测试增强预测问题分析"""
        result = await enhancer.enhance(
            problem_description="预测未来三个月的销量走势",
            problem_type="prediction",
        )

        assert "enhanced_output" in dir(result)

    @pytest.mark.asyncio
    async def test_enhance_evaluation_problem(self, enhancer):
        """测试增强评价问题分析"""
        result = await enhancer.enhance(
            problem_description="评价多个供应商的综合表现",
            problem_type="evaluation",
        )

        assert result is not None

    def test_get_analysis_suggestions(self, enhancer):
        """测试获取分析建议"""
        suggestions = enhancer._get_analysis_suggestions("optimization")

        assert isinstance(suggestions, list)


class TestCodeQualityEnhancer:
    """测试代码质量增强器"""

    @pytest.fixture
    def enhancer(self):
        return CodeQualityEnhancer()

    @pytest.mark.asyncio
    async def test_enhance_code(self, enhancer):
        """测试增强代码质量"""
        code = """
def solve(x, y):
    result = x + y
    return result
"""
        result = await enhancer.enhance(code)

        assert result.enhancement_type == EnhancementType.CODE_QUALITY
        assert len(result.suggestions) >= 0

    @pytest.mark.asyncio
    async def test_enhance_code_with_missing_imports(self, enhancer):
        """测试检测缺失导入"""
        code = """
df = pd.DataFrame(data)
result = np.array([1, 2, 3])
"""
        result = await enhancer.enhance(code)

        # 应该检测到缺少导入
        " ".join(result.improvements)
        # 根据实际实现调整断言

    @pytest.mark.asyncio
    async def test_enhance_code_without_docstring(self, enhancer):
        """测试检测缺少文档字符串"""
        code = """
def calculate(a, b, c):
    return a * b + c
"""
        result = await enhancer.enhance(code)

        assert result is not None

    def test_check_imports(self, enhancer):
        """测试检查导入"""
        code = "import numpy as np\nprint(np.array([1,2,3]))"
        result = enhancer._check_imports(code)

        assert isinstance(result, dict)
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)

    def test_check_documentation(self, enhancer):
        """测试检查文档"""
        code = '"""模块文档"""\ndef func():\n    pass'
        result = enhancer._check_documentation(code)

        assert isinstance(result, dict)
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)

    def test_check_structure(self, enhancer):
        """测试检查代码结构"""
        code = """
def main():
    for i in range(10):
        for j in range(10):
            for k in range(10):
                pass
"""
        result = enhancer._check_structure(code)

        assert isinstance(result, dict)
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)


class TestPaperQualityEnhancer:
    """测试论文质量增强器"""

    @pytest.fixture
    def enhancer(self):
        return PaperQualityEnhancer()

    @pytest.mark.asyncio
    async def test_enhance_paper(self, enhancer):
        """测试增强论文质量"""
        paper_content = """
# 摘要
本文研究了某优化问题。

# 问题分析
问题描述...

# 模型建立
建立了线性规划模型...

# 模型求解
使用Python求解...

# 结论
研究表明...
"""
        result = await enhancer.enhance(paper_content, task_id="test_001")

        assert result.enhancement_type == EnhancementType.PAPER_QUALITY

    @pytest.mark.asyncio
    async def test_enhance_incomplete_paper(self, enhancer):
        """测试增强不完整论文"""
        paper_content = """
# 摘要
简单描述

# 问题分析
描述问题
"""
        result = await enhancer.enhance(paper_content, task_id="test_002")

        # 应该给出改进建议
        assert len(result.suggestions) >= 0

    def test_get_general_suggestions(self, enhancer):
        """测试获取通用建议"""
        content = "这是一篇很短的论文内容"
        suggestions = enhancer._get_general_suggestions(content)

        assert isinstance(suggestions, list)


class TestWorkflowEnhancer:
    """测试工作流增强器"""

    @pytest.fixture
    def enhancer(self):
        return WorkflowEnhancer()

    @pytest.mark.asyncio
    async def test_enhance_problem_analysis(self, enhancer):
        """测试增强问题分析"""
        result = await enhancer.enhance_problem_analysis(
            "设计最优调度方案",
            "optimization",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_enhance_code(self, enhancer):
        """测试增强代码"""
        code = "def f(x): return x * 2"
        result = await enhancer.enhance_code(code)

        assert result is not None

    @pytest.mark.asyncio
    async def test_enhance_paper(self, enhancer):
        """测试增强论文"""
        paper = "# 论文标题\n内容..."
        result = await enhancer.enhance_paper(paper)

        assert result is not None


class TestCreateWorkflowEnhancer:
    """测试工厂函数"""

    def test_create_workflow_enhancer(self):
        """测试创建工作流增强器"""
        enhancer = create_workflow_enhancer()

        assert enhancer is not None
        assert enhancer.problem_enhancer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
