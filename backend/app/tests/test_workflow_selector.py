"""工作流选择器单元测试

覆盖: WorkflowSelector, ComplexityScore, WorkflowType
测试三种模式选择 + AUTO 模式的 7 维度复杂度评估
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def simple_problem():
    """简单题目（应选择标准工作流）"""
    problem = MagicMock()
    problem.ques_all = "某城市需要规划公交线路，请建立数学模型。问题1：求最短路径。问题2：优化频次。"
    problem.task_id = "simple-001"
    return problem


@pytest.fixture
def complex_problem():
    """复杂题目（应选择增强工作流）"""
    problem = MagicMock()
    # 包含多个高级方法关键词、多问题、长文本、创新要求
    problem.ques_all = (
        "本题要求建立多目标优化模型，结合深度学习和蒙特卡罗模拟方法，"
        "对大规模数据集进行分析。需要使用动态规划求解约束优化问题，"
        "并进行灵敏度分析和鲁棒性验证。要求模型具有创新性和改进空间。"
        "问题1：建立多目标优化模型并求解。"
        "问题2：使用机器学习方法进行预测。"
        "问题3：设计启发式算法进行优化。"
        "问题4：进行蒙特卡罗模拟验证。"
        "问题5：对模型进行敏感性分析和创新改进。"
        + "这是一个非常复杂的数学建模问题，" * 100  # 确保文本足够长
    )
    problem.task_id = "complex-001"
    return problem


@pytest.fixture
def medium_problem():
    """中等复杂度题目"""
    problem = MagicMock()
    problem.ques_all = (
        "某工厂需要优化生产计划，在满足约束条件下最大化利润。"
        "问题1：建立线性规划模型。"
        "问题2：求解最优方案。"
        "问题3：进行敏感性分析。"
    )
    problem.task_id = "medium-001"
    return problem


class TestWorkflowType:
    """工作流类型枚举测试"""

    def test_standard_type(self):
        from app.core.workflow.workflow_selector import WorkflowType
        assert WorkflowType.STANDARD.value == "standard"

    def test_enhanced_type(self):
        from app.core.workflow.workflow_selector import WorkflowType
        assert WorkflowType.ENHANCED.value == "enhanced"


class TestComplexityScore:
    """复杂度评分测试"""

    def test_score_below_threshold(self):
        from app.core.workflow.workflow_selector import ComplexityScore
        score = ComplexityScore(0.2, {"long_problem": False, "many_questions": False})
        assert score.is_complex is False

    def test_score_above_threshold(self):
        from app.core.workflow.workflow_selector import ComplexityScore
        score = ComplexityScore(0.6, {"advanced_methods": True, "optimization": True})
        assert score.is_complex is True

    def test_score_at_threshold(self):
        """测试恰好在阈值处"""
        from app.core.workflow.workflow_selector import ComplexityScore
        score = ComplexityScore(0.4, {"long_problem": True})
        assert score.is_complex is True  # >= 0.4

    def test_score_just_below_threshold(self):
        """测试略低于阈值"""
        from app.core.workflow.workflow_selector import ComplexityScore
        score = ComplexityScore(0.39, {"long_problem": True})
        assert score.is_complex is False


class TestWorkflowSelector:
    """工作流选择器测试"""

    def test_select_standard_mode(self, simple_problem):
        """测试 STANDARD 模式直接返回标准工作流"""
        from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType
        from app.schemas.enums import WorkflowMode
        result = WorkflowSelector.select(WorkflowMode.STANDARD, simple_problem)
        assert result == WorkflowType.STANDARD

    def test_select_enhanced_mode(self, simple_problem):
        """测试 ENHANCED 模式直接返回增强工作流"""
        from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType
        from app.schemas.enums import WorkflowMode
        result = WorkflowSelector.select(WorkflowMode.ENHANCED, simple_problem)
        assert result == WorkflowType.ENHANCED

    def test_select_award_mode_maps_to_enhanced(self, simple_problem):
        """测试 AWARD 模式向后兼容，映射到增强工作流"""
        from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType
        from app.schemas.enums import WorkflowMode
        result = WorkflowSelector.select(WorkflowMode.AWARD, simple_problem)
        assert result == WorkflowType.ENHANCED

    def test_select_auto_simple_problem(self, simple_problem):
        """测试 AUTO 模式：简单题目选择标准工作流"""
        from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType
        from app.schemas.enums import WorkflowMode
        result = WorkflowSelector.select(WorkflowMode.AUTO, simple_problem)
        assert result == WorkflowType.STANDARD

    def test_select_auto_complex_problem(self, complex_problem):
        """测试 AUTO 模式：复杂题目选择增强工作流"""
        from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType
        from app.schemas.enums import WorkflowMode
        result = WorkflowSelector.select(WorkflowMode.AUTO, complex_problem)
        assert result == WorkflowType.ENHANCED

    def test_select_auto_no_problem(self):
        """测试 AUTO 模式无题目时默认标准"""
        from app.core.workflow.workflow_selector import WorkflowSelector, WorkflowType
        from app.schemas.enums import WorkflowMode
        result = WorkflowSelector.select(WorkflowMode.AUTO, None)
        assert result == WorkflowType.STANDARD


class TestComplexityAssessment:
    """复杂度评估的 7 维度测试"""

    def test_long_problem_factor(self):
        """测试长文本维度"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        problem = MagicMock()
        problem.ques_all = "x" * 4000  # > 3000 字符
        score = WorkflowSelector.assess_complexity(problem)
        assert score.factors.get("long_problem", False) is True

    def test_short_problem_factor(self):
        """测试短文本不触发"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        problem = MagicMock()
        problem.ques_all = "简单问题描述"
        score = WorkflowSelector.assess_complexity(problem)
        assert score.factors.get("long_problem", False) is False

    def test_many_questions_factor(self):
        """测试多问题维度"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        problem = MagicMock()
        problem.ques_all = "问题1：xxx 问题2：xxx 问题3：xxx 问题4：xxx"
        score = WorkflowSelector.assess_complexity(problem)
        assert score.factors.get("many_questions", False) is True

    def test_advanced_methods_factor(self):
        """测试高级方法关键词维度"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        problem = MagicMock()
        problem.ques_all = "使用蒙特卡罗模拟和深度学习进行多目标优化"
        score = WorkflowSelector.assess_complexity(problem)
        assert score.factors.get("advanced_methods", False) is True

    def test_optimization_factor(self):
        """测试优化+约束同时出现"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        problem = MagicMock()
        problem.ques_all = "在约束条件下进行优化求解"
        score = WorkflowSelector.assess_complexity(problem)
        assert score.factors.get("optimization", False) is True

    def test_innovation_factor(self):
        """测试创新要求维度"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        problem = MagicMock()
        problem.ques_all = "要求提出创新的方法和改进方案"
        score = WorkflowSelector.assess_complexity(problem)
        assert score.factors.get("requires_innovation", False) is True

    def test_score_range(self, simple_problem):
        """测试评分在有效范围 [0, 1]"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        score = WorkflowSelector.assess_complexity(simple_problem)
        assert 0.0 <= score.score <= 1.0

    def test_count_questions_chinese(self):
        """测试中文问题编号匹配"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        count = WorkflowSelector._count_questions("问题1：xxx 问题2：xxx 问题3：xxx")
        assert count >= 3

    def test_count_questions_english(self):
        """测试英文问题编号匹配"""
        from app.core.workflow.workflow_selector import WorkflowSelector
        count = WorkflowSelector._count_questions("Question 1: xxx Question 2: xxx")
        assert count >= 2


class TestGetWorkflowForMode:
    """模块级便捷函数测试"""

    def test_delegates_to_selector(self, simple_problem):
        """测试便捷函数委托给 WorkflowSelector.select"""
        from app.core.workflow.workflow_selector import (
            WorkflowType,
            get_workflow_for_mode,
        )
        from app.schemas.enums import WorkflowMode
        result = get_workflow_for_mode(WorkflowMode.STANDARD, simple_problem)
        assert result == WorkflowType.STANDARD
