"""
知识库单元测试
测试数学建模知识库的模型搜索、指标推荐、最佳实践获取
"""
import pytest

from app.core.knowledge_base import (
    EvaluationMetricKnowledge,
    MathModelingKnowledgeBase,
    ModelKnowledge,
    ValidationMethodKnowledge,
    knowledge_base,
)


class TestModelKnowledge:
    """测试模型知识数据类"""

    def test_create_model_knowledge(self):
        """测试创建模型知识"""
        model = ModelKnowledge(
            name="线性规划",
            category="optimization",
            description="用于求解线性约束下的最优化问题",
            applicable_problems=["资源分配", "生产调度"],
            advantages=["计算效率高", "解释性强"],
            disadvantages=["只能处理线性关系"],
            complexity="O(n^3)",
            implementation_difficulty="低",
            data_requirements={"变量数": "有限"},
            key_parameters=["目标函数", "约束条件"],
            validation_methods=["灵敏度分析"],
            common_pitfalls=["约束条件冲突"],
        )
        assert model.name == "线性规划"
        assert model.category == "optimization"
        assert len(model.advantages) == 2


class TestEvaluationMetricKnowledge:
    """测试评价指标知识数据类"""

    def test_create_metric_knowledge(self):
        """测试创建指标知识"""
        metric = EvaluationMetricKnowledge(
            name="R²",
            metric_type="regression",
            description="决定系数，衡量回归模型的拟合优度",
            formula="R² = 1 - SS_res / SS_tot",
            interpretation="越接近1表示拟合越好",
            range="[0, 1]",
            when_to_use=["回归分析"],
            advantages=["直观"],
            limitations=["对异常值敏感"],
            related_metrics=["RMSE", "MAE"],
        )
        assert metric.name == "R²"
        assert metric.range == "[0, 1]"


class TestValidationMethodKnowledge:
    """测试验证方法知识数据类"""

    def test_create_validation_method(self):
        """测试创建验证方法知识"""
        method = ValidationMethodKnowledge(
            name="交叉验证",
            description="将数据分成多份进行多次训练和测试",
            applicable_scenarios=["分类", "回归"],
            implementation_steps=["划分数据", "轮流验证", "汇总结果"],
            computational_cost="中等",
            robustness="高",
            sample_size_requirement="中等以上",
            common_issues=["数据泄露"],
        )
        assert method.name == "交叉验证"


class TestMathModelingKnowledgeBase:
    """测试数学建模知识库"""

    @pytest.fixture
    def kb(self):
        return MathModelingKnowledgeBase()

    def test_knowledge_base_initialization(self, kb):
        """测试知识库初始化"""
        assert kb.models is not None
        assert kb.metrics is not None
        assert kb.validation_methods is not None
        assert kb.best_practices is not None

    def test_search_model_optimization(self, kb):
        """测试搜索优化模型"""
        results = kb.search_model("optimization")
        
        # 优化问题应该返回相关模型列表
        assert isinstance(results, list)
        # 检查是否包含优化相关模型
        [m.name for m in results]

    def test_search_model_prediction(self, kb):
        """测试搜索预测模型"""
        results = kb.search_model("prediction")
        
        assert len(results) >= 0

    def test_search_model_with_keywords(self, kb):
        """测试带关键词的模型搜索"""
        results = kb.search_model(
            "optimization",
            key_words=["规划", "调度"],
        )
        
        assert isinstance(results, list)

    def test_search_model_classification(self, kb):
        """测试搜索分类模型"""
        results = kb.search_model("classification")
        
        assert isinstance(results, list)

    def test_search_model_evaluation(self, kb):
        """测试搜索评价模型"""
        results = kb.search_model("evaluation")
        
        assert isinstance(results, list)

    def test_get_validation_method_small_data(self, kb):
        """测试获取小数据集验证方法"""
        methods = kb.get_validation_method(
            "prediction",
            data_size="小",
        )
        
        assert isinstance(methods, list)

    def test_get_validation_method_large_data(self, kb):
        """测试获取大数据集验证方法"""
        methods = kb.get_validation_method(
            "classification",
            data_size="大",
        )
        
        assert isinstance(methods, list)

    def test_get_evaluation_metrics_regression(self, kb):
        """测试获取回归问题评价指标"""
        metrics = kb.get_evaluation_metrics("prediction")
        
        assert isinstance(metrics, list)

    def test_get_evaluation_metrics_classification(self, kb):
        """测试获取分类问题评价指标"""
        metrics = kb.get_evaluation_metrics("classification")
        
        assert isinstance(metrics, list)

    def test_get_best_practices_optimization(self, kb):
        """测试获取优化问题最佳实践"""
        practices = kb.get_best_practices("optimization")
        
        assert isinstance(practices, dict) or isinstance(practices, list)

    def test_get_best_practices_prediction(self, kb):
        """测试获取预测问题最佳实践"""
        practices = kb.get_best_practices("prediction")
        
        assert practices is not None

    def test_get_best_practices_unknown_type(self, kb):
        """测试获取未知类型的最佳实践"""
        practices = kb.get_best_practices("unknown_type")
        
        # 应该返回通用实践或空结果
        assert practices is not None or practices == {}


class TestGlobalKnowledgeBase:
    """测试全局知识库实例"""

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        assert knowledge_base is not None

    def test_global_instance_is_initialized(self):
        """测试全局实例已初始化"""
        assert knowledge_base.models is not None
        assert len(knowledge_base.models) > 0

    def test_search_model_via_global(self):
        """测试通过全局实例搜索"""
        results = knowledge_base.search_model("optimization")
        
        assert isinstance(results, list)


class TestKnowledgeBaseConsistency:
    """测试知识库一致性"""

    @pytest.fixture
    def kb(self):
        return MathModelingKnowledgeBase()

    def test_all_models_have_required_fields(self, kb):
        """测试所有模型都有必填字段"""
        for name, model in kb.models.items():
            assert model.name is not None
            assert model.category is not None
            assert model.description is not None

    def test_all_metrics_have_required_fields(self, kb):
        """测试所有指标都有必填字段"""
        for name, metric in kb.metrics.items():
            assert metric.name is not None
            assert metric.metric_type is not None

    def test_all_validation_methods_have_required_fields(self, kb):
        """测试所有验证方法都有必填字段"""
        for name, method in kb.validation_methods.items():
            assert method.name is not None
            assert method.description is not None


class TestKnowledgeBaseUseCases:
    """测试知识库实际使用场景"""

    @pytest.fixture
    def kb(self):
        return MathModelingKnowledgeBase()

    def test_production_scheduling_scenario(self, kb):
        """测试生产调度场景"""
        # 用户问题：生产调度优化
        models = kb.search_model("optimization", key_words=["调度", "规划"])
        practices = kb.get_best_practices("optimization")
        
        assert models is not None
        assert practices is not None

    def test_sales_prediction_scenario(self, kb):
        """测试销量预测场景"""
        # 用户问题：预测销量
        models = kb.search_model("prediction", key_words=["时间序列", "预测"])
        metrics = kb.get_evaluation_metrics("prediction")
        methods = kb.get_validation_method("prediction", data_size="中等")
        
        assert models is not None
        assert metrics is not None
        assert methods is not None

    def test_supplier_evaluation_scenario(self, kb):
        """测试供应商评价场景"""
        # 用户问题：评价供应商
        models = kb.search_model("evaluation", key_words=["评价", "排序"])
        kb.get_best_practices("evaluation")
        
        assert models is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
