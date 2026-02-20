"""
评测指标单元测试
测试模型评测、论文评测、代码评测、创新性评测
"""
import pytest

from app.core.evaluation.metrics import (
    BenchmarkMetrics,
    CodeMetrics,
    InnovationMetrics,
    MetricCategory,
    MetricConfig,
    MetricResult,
    ModelMetrics,
    PaperMetrics,
)


class TestMetricCategory:
    """测试指标类别枚举"""

    def test_category_values(self):
        """测试类别值"""
        assert MetricCategory.MODEL == "model"
        assert MetricCategory.PAPER == "paper"
        assert MetricCategory.CODE == "code"
        assert MetricCategory.INNOVATION == "innovation"


class TestMetricResult:
    """测试指标评测结果"""

    def test_create_metric_result(self):
        """测试创建评测结果"""
        result = MetricResult(
            metric_name="模型选择合理性",
            score=85.0,
            weight=0.20,
            details="选用了2个模型",
            suggestions=["建议增加对比模型"],
        )
        assert result.metric_name == "模型选择合理性"
        assert result.score == 85.0
        assert result.weight == 0.20

    def test_weighted_score(self):
        """测试加权分数计算"""
        result = MetricResult(
            metric_name="测试指标",
            score=80.0,
            weight=0.25,
        )
        assert result.weighted_score == 20.0


class TestModelMetrics:
    """测试模型评测指标"""

    def test_evaluate_model_selection_multiple_models(self):
        """测试多模型选择评分"""
        result = ModelMetrics.evaluate_model_selection(
            problem_type="optimization",
            selected_models=["线性规划", "遗传算法", "动态规划"],
            problem_description="资源分配问题",
        )
        
        assert result.score > 60  # 多模型应该加分
        assert result.weight == 0.20

    def test_evaluate_model_selection_single_model(self):
        """测试单模型选择评分"""
        result = ModelMetrics.evaluate_model_selection(
            problem_type="prediction",
            selected_models=["ARIMA"],
            problem_description="销量预测",
        )
        
        assert result.score >= 60
        assert len(result.suggestions) > 0  # 应该建议增加对比模型

    def test_evaluate_model_selection_with_improvement(self):
        """测试带改进的模型选择评分"""
        result = ModelMetrics.evaluate_model_selection(
            problem_type="classification",
            selected_models=["改进的随机森林", "SVM"],
            problem_description="客户分类",
        )
        
        # 带"改进"关键词应该获得创新加分
        assert result.score >= 70

    def test_evaluate_math_rigor_many_formulas(self):
        """测试数学严谨性评分 - 多公式"""
        formulas = [
            "$\\min Z = \\sum c_i x_i$",
            "$s.t. \\sum a_{ij} x_j \\leq b_i$",
            "$x_i \\geq 0$",
        ] * 4  # 12个公式
        
        result = ModelMetrics.evaluate_math_rigor(
            formulas=formulas,
            derivation_steps=6,
        )
        
        assert result.score >= 80

    def test_evaluate_math_rigor_few_formulas(self):
        """测试数学严谨性评分 - 少公式"""
        result = ModelMetrics.evaluate_math_rigor(
            formulas=["公式1", "公式2"],
            derivation_steps=1,
        )
        
        assert result.score < 80
        assert len(result.suggestions) > 0


class TestPaperMetrics:
    """测试论文评测指标"""

    def test_required_sections(self):
        """测试必需章节列表"""
        assert "摘要" in PaperMetrics.REQUIRED_SECTIONS
        assert "问题分析" in PaperMetrics.REQUIRED_SECTIONS
        assert "模型建立" in PaperMetrics.REQUIRED_SECTIONS
        assert "模型求解" in PaperMetrics.REQUIRED_SECTIONS

    def test_evaluate_structure_complete(self):
        """测试完整结构评分"""
        content = """
        # 摘要
        本文研究...
        
        # 问题重述
        题目要求...
        
        # 问题分析
        分析问题...
        
        # 模型假设
        假设1...
        
        # 符号说明
        符号定义...
        
        # 模型建立
        建立模型...
        
        # 模型求解
        求解过程...
        
        # 结果分析
        分析结果...
        
        # 模型评价
        模型优缺点...
        
        # 参考文献
        [1] ...
        """
        
        result = PaperMetrics.evaluate_structure(content)
        
        assert result.score == 100
        assert len(result.suggestions) == 0

    def test_evaluate_structure_incomplete(self):
        """测试不完整结构评分"""
        content = """
        # 摘要
        本文研究...
        
        # 问题分析
        分析问题...
        """
        
        result = PaperMetrics.evaluate_structure(content)
        
        assert result.score < 100
        assert len(result.suggestions) > 0

    def test_evaluate_abstract_good_length(self):
        """测试摘要评分 - 合适长度"""
        abstract = "本文针对某问题进行研究，采用模型方法求解得到结果表明有效。" * 15  # 约400字
        
        result = PaperMetrics.evaluate_abstract(abstract)
        
        # 分数应该合理
        assert result.score >= 50

    def test_evaluate_abstract_too_short(self):
        """测试摘要评分 - 过短"""
        abstract = "简短摘要"
        
        result = PaperMetrics.evaluate_abstract(abstract)
        
        assert result.score < 80
        assert len(result.suggestions) > 0

    def test_evaluate_abstract_with_elements(self):
        """测试摘要评分 - 包含关键要素"""
        abstract = """
        本文针对某问题进行研究。
        采用线性规划模型进行建模。
        通过求解得到最优结果。
        结论表明该方法有效。
        """ * 10  # 扩展到合适长度
        
        result = PaperMetrics.evaluate_abstract(abstract)
        
        # 包含问题、方法、结果、结论四要素
        assert result.score >= 70

    def test_evaluate_figures_tables_sufficient(self):
        """测试图表评分 - 数量充足"""
        content = """
        如图1所示...
        见表1...
        图2展示了...
        表2列出了...
        根据图3...
        表3说明...
        图4是...
        表4包含...
        """
        
        result = PaperMetrics.evaluate_figures_tables(
            figure_count=4,
            table_count=4,
            content=content,
        )
        
        # 图表数量充足应获得较高分
        assert result.score >= 65

    def test_evaluate_figures_tables_insufficient(self):
        """测试图表评分 - 数量不足"""
        result = PaperMetrics.evaluate_figures_tables(
            figure_count=1,
            table_count=0,
            content="只有图1...",
        )
        
        assert result.score < 76
        assert len(result.suggestions) > 0


class TestCodeMetrics:
    """测试代码评测指标"""

    def test_evaluate_correctness_valid_code(self):
        """测试代码正确性 - 有效代码"""
        code = """
def solve_problem():
    x = 1 + 2
    return x
"""
        result = CodeMetrics.evaluate_correctness(
            code=code,
            execution_success=True,
            output_valid=True,
        )
        
        assert result.score == 100

    def test_evaluate_correctness_syntax_error(self):
        """测试代码正确性 - 语法错误"""
        code = """
def solve_problem(
    x = 1 + 2  # 缺少括号
    return x
"""
        result = CodeMetrics.evaluate_correctness(
            code=code,
            execution_success=False,
            output_valid=False,
        )
        
        assert result.score == 0
        assert "语法错误" in result.details

    def test_evaluate_correctness_execution_failed(self):
        """测试代码正确性 - 执行失败"""
        code = """
def solve_problem():
    x = 1 / 0  # ZeroDivisionError
    return x
"""
        result = CodeMetrics.evaluate_correctness(
            code=code,
            execution_success=False,
            output_valid=False,
        )
        
        assert result.score == 30  # 只有语法正确分
        assert len(result.suggestions) > 0

    def test_evaluate_code_quality_well_documented(self):
        """测试代码质量 - 良好文档"""
        code = '''
"""
模块说明
"""

def solve_optimization(data):
    """
    求解优化问题
    
    Args:
        data: 输入数据
        
    Returns:
        最优解
    """
    # 初始化
    result = 0
    
    # 计算
    for item in data:
        result += item
    
    # 返回结果
    return result

def validate_result(result):
    """验证结果"""
    # 检查结果有效性
    return result >= 0

def main():
    """主函数"""
    # 准备数据
    data = [1, 2, 3]
    # 求解
    result = solve_optimization(data)
    # 验证
    valid = validate_result(result)
    return result
'''
        result = CodeMetrics.evaluate_code_quality(code)
        
        assert result.score >= 80

    def test_evaluate_code_quality_no_comments(self):
        """测试代码质量 - 无注释"""
        code = """
def f(x):
    return x * 2

def g(y):
    return y + 1
"""
        result = CodeMetrics.evaluate_code_quality(code)
        
        assert result.score < 90


class TestInnovationMetrics:
    """测试创新性评测"""

    def test_evaluate_innovation_with_improvements(self):
        """测试创新性评分 - 有改进"""
        content = """
        本文提出了一种改进的遗传算法。
        通过优化交叉算子，增强了搜索能力。
        创新点在于引入自适应变异率。
        """
        model_improvements = [
            "改进交叉算子",
            "自适应变异率",
        ]
        
        result = InnovationMetrics.evaluate_innovation(
            content=content,
            model_improvements=model_improvements,
        )
        
        assert result.score >= 70

    def test_evaluate_innovation_no_improvements(self):
        """测试创新性评分 - 无改进"""
        content = "使用标准的线性规划模型求解。"
        
        result = InnovationMetrics.evaluate_innovation(
            content=content,
            model_improvements=[],
        )
        
        assert result.score < 70
        assert len(result.suggestions) > 0

    def test_evaluate_innovation_with_sensitivity(self):
        """测试创新性评分 - 包含敏感性分析"""
        content = """
        进行了敏感性分析，研究参数变化对结果的影响。
        """
        
        result = InnovationMetrics.evaluate_innovation(
            content=content,
            model_improvements=[],
        )
        
        # 包含敏感性分析应该加分
        assert result.score >= 55


class TestBenchmarkMetrics:
    """测试综合评测指标管理器"""

    @pytest.fixture
    def benchmark(self):
        return BenchmarkMetrics()

    def test_initialization(self, benchmark):
        """测试初始化"""
        assert benchmark.model_metrics is not None
        assert benchmark.paper_metrics is not None
        assert benchmark.code_metrics is not None
        assert benchmark.innovation_metrics is not None

    def test_get_all_metrics(self, benchmark):
        """测试获取所有指标配置"""
        metrics = benchmark.get_all_metrics()
        
        assert len(metrics) >= 5
        
        # 检查指标配置完整性
        for metric in metrics:
            assert isinstance(metric, MetricConfig)
            assert metric.name is not None
            assert metric.category is not None
            assert 0 < metric.weight <= 1
            assert callable(metric.evaluator)

    def test_metrics_weights_sum(self, benchmark):
        """测试指标权重总和"""
        metrics = benchmark.get_all_metrics()
        total_weight = sum(m.weight for m in metrics)
        
        # 权重总和应该接近1.0
        assert 0.95 <= total_weight <= 1.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
