"""
core/modeling 子包测试

覆盖:
  - model_registry.py: ExtendedModelKnowledge, ModelRegistry, NEW_MODELS, 便捷函数
  - auto_validator.py: AutoValidator 指标计算、残差诊断、交叉验证、基线对比
  - sensitivity_analyzer.py: SensitivityAnalyzer OAT分析、龙卷风图/蜘蛛图、报告格式化
  - multi_model_strategy.py: MultiModelStrategy 模型推荐、评价指标、MODEL_KNOWLEDGE_BASE
"""

import sys
from unittest.mock import MagicMock

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
for _mod_name in ("langchain_core", "langchain_core.messages"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        _mock.HumanMessage = MagicMock
        _mock.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from app.core.modeling.model_registry import (  # noqa: E402
    ExtendedModelKnowledge,
    ModelRegistry,
    NEW_MODELS,
    get_model_info,
    search_models,
)
from app.core.modeling.auto_validator import (  # noqa: E402
    AutoValidator,
    BaselineComparison,
    CrossValidationResult,
    ResidualDiagnostics,
)
from app.core.modeling.sensitivity_analyzer import (  # noqa: E402
    ParameterSpec,
    SensitivityAnalysisResult,
    SensitivityAnalyzer,
    SensitivityMethod,
    SensitivityReport,
    StabilityRating,
    run_sensitivity_analysis,
    to_sensitivity_result,
)
from app.core.modeling.multi_model_strategy import (  # noqa: E402
    DataCharacteristic,
    ModelInfo,
    MultiModelStrategy,
    ProblemCategory,
)


# ================================================================
# ModelRegistry 测试
# ================================================================


class TestExtendedModelKnowledge:
    """ExtendedModelKnowledge 数据类测试"""

    @pytest.mark.unit
    def test_create_basic(self):
        """验证: 基本创建"""
        model = ExtendedModelKnowledge(
            model_id="test_model",
            name="测试模型",
            category="optimization",
            description="测试用模型",
            applicable_problems=["线性规划"],
            advantages=["简单"],
            disadvantages=["受限"],
            complexity="low",
            implementation_difficulty="easy",
            data_requirements={"min_samples": "10"},
            key_parameters=["c", "A"],
            validation_methods=["交叉验证"],
            common_pitfalls=["过拟合"],
        )
        assert model.model_id == "test_model"
        assert model.name == "测试模型"
        assert model.category == "optimization"

    @pytest.mark.unit
    def test_default_extended_fields(self):
        """验证: 扩展字段有默认值"""
        model = ExtendedModelKnowledge(
            model_id="m1",
            name="M1",
            category="cat",
            description="desc",
            applicable_problems=[],
            advantages=[],
            disadvantages=[],
            complexity="low",
            implementation_difficulty="easy",
            data_requirements={},
            key_parameters=[],
            validation_methods=[],
            common_pitfalls=[],
        )
        assert model.versions == []
        assert model.performance_benchmarks == {}
        assert model.applicable_data_types == []
        assert model.required_packages == []
        assert model.example_code == ""
        assert model.tags == []
        assert model.related_models == []

    @pytest.mark.unit
    def test_from_model_knowledge(self):
        """验证: 从 ModelKnowledge 转换"""
        from app.core.knowledge_base import ModelKnowledge

        mk = ModelKnowledge(
            name="线性回归",
            category="prediction",
            description="线性回归模型",
            applicable_problems=["预测"],
            advantages=["解释性强"],
            disadvantages=["仅线性"],
            complexity="low",
            implementation_difficulty="easy",
            data_requirements={"min_samples": "30"},
            key_parameters=["alpha"],
            validation_methods=["交叉验证"],
            common_pitfalls=["多重共线性"],
        )
        ext = ExtendedModelKnowledge.from_model_knowledge("lr", mk)
        assert ext.model_id == "lr"
        assert ext.name == "线性回归"
        assert ext.category == "prediction"
        assert "解释性强" in ext.advantages


class TestNEW_MODELS:
    """NEW_MODELS 常量验证"""

    @pytest.mark.unit
    def test_new_models_not_empty(self):
        """验证: NEW_MODELS 不为空"""
        assert len(NEW_MODELS) > 0

    @pytest.mark.unit
    def test_new_models_values_are_extended_knowledge(self):
        """验证: 所有值均为 ExtendedModelKnowledge"""
        for model_id, model in NEW_MODELS.items():
            assert isinstance(model, ExtendedModelKnowledge), f"{model_id} 类型错误"
            assert model.model_id == model_id

    @pytest.mark.unit
    def test_new_models_have_required_fields(self):
        """验证: 所有模型具有必填字段"""
        for model_id, model in NEW_MODELS.items():
            assert model.name, f"{model_id} 缺少 name"
            assert model.category, f"{model_id} 缺少 category"
            assert model.description, f"{model_id} 缺少 description"

    @pytest.mark.unit
    def test_known_models_present(self):
        """验证: 关键模型存在"""
        expected = {"topsis", "entropy_weight", "dynamic_programming"}
        assert expected.issubset(set(NEW_MODELS.keys()))


class TestModelRegistry:
    """ModelRegistry 类测试"""

    def _make_registry(self) -> ModelRegistry:
        return ModelRegistry()

    @pytest.mark.unit
    def test_initialization(self):
        """验证: 初始化成功，包含基础知识库模型"""
        registry = self._make_registry()
        assert registry.get_model_count() > 0

    @pytest.mark.unit
    def test_register_and_get_model(self):
        """验证: 注册后可检索"""
        registry = self._make_registry()
        model = ExtendedModelKnowledge(
            model_id="custom_test",
            name="自定义测试",
            category="test_cat",
            description="测试用",
            applicable_problems=["测试"],
            advantages=["快"],
            disadvantages=["假"],
            complexity="low",
            implementation_difficulty="easy",
            data_requirements={},
            key_parameters=[],
            validation_methods=[],
            common_pitfalls=[],
        )
        result_id = registry.register_model(model)
        assert result_id == "custom_test"

        retrieved = registry.get_model("custom_test")
        assert retrieved is not None
        assert retrieved.name == "自定义测试"

    @pytest.mark.unit
    def test_get_nonexistent_model(self):
        """验证: 不存在的模型返回 None"""
        registry = self._make_registry()
        assert registry.get_model("nonexistent_xyz_999") is None

    @pytest.mark.unit
    def test_list_models_all(self):
        """验证: list_models 返回所有模型"""
        registry = self._make_registry()
        all_models = registry.list_models()
        assert len(all_models) > 0

    @pytest.mark.unit
    def test_list_models_by_category(self):
        """验证: 按类别过滤"""
        registry = self._make_registry()
        categories = registry.get_categories()
        assert len(categories) > 0

        # 按第一个类别过滤
        filtered = registry.list_models(category=categories[0])
        assert all(m.category == categories[0] for m in filtered)

    @pytest.mark.unit
    def test_search_by_scenario(self):
        """验证: 按场景搜索返回推荐"""
        registry = self._make_registry()
        results = registry.search_by_scenario("线性规划优化问题")
        # 应返回列表（可能为空，取决于知识库内容）
        assert isinstance(results, list)

    @pytest.mark.unit
    def test_record_and_get_performance(self):
        """验证: 记录和查询性能"""
        registry = self._make_registry()
        # 获取一个已有模型
        models = registry.list_models()
        if not models:
            pytest.skip("注册表为空")

        model_id = models[0].model_id
        registry.record_performance(
            model_id=model_id,
            metrics={"r2": 0.95, "rmse": 0.12},
            problem_id="test_problem_001",
            notes="测试记录",
        )
        history = registry.get_performance_history(model_id)
        assert len(history) >= 1
        assert history[-1].metrics["r2"] == 0.95

    @pytest.mark.unit
    def test_compare_models(self):
        """验证: 模型对比"""
        registry = self._make_registry()
        models = registry.list_models()
        if len(models) < 2:
            pytest.skip("模型不足")

        ids = [m.model_id for m in models[:2]]
        comparison = registry.compare_models(ids)
        assert isinstance(comparison, dict)
        assert "models" in comparison

    @pytest.mark.unit
    def test_get_model_count(self):
        """验证: 模型计数正确"""
        registry = self._make_registry()
        count = registry.get_model_count()
        all_models = registry.list_models()
        assert count == len(all_models)

    @pytest.mark.unit
    def test_get_categories(self):
        """验证: 获取类别列表"""
        registry = self._make_registry()
        categories = registry.get_categories()
        assert isinstance(categories, list)
        # 类别应无重复
        assert len(categories) == len(set(categories))


class TestModelRegistryConvenience:
    """模块级便捷函数测试"""

    @pytest.mark.unit
    def test_search_models_function(self):
        """验证: search_models 便捷函数"""
        results = search_models("优化")
        assert isinstance(results, list)

    @pytest.mark.unit
    def test_get_model_info_existing(self):
        """验证: get_model_info 对已知模型返回信息"""
        # 使用 NEW_MODELS 中已知的 ID
        known_id = next(iter(NEW_MODELS.keys()))
        info = get_model_info(known_id)
        # 应返回非 None（具体返回类型取决于实现）
        assert info is not None

    @pytest.mark.unit
    def test_get_model_info_nonexistent(self):
        """验证: get_model_info 对不存在模型的处理"""
        info = get_model_info("totally_fake_model_xyz_999")
        assert info is None


# ================================================================
# AutoValidator 测试
# ================================================================


class TestAutoValidatorMetrics:
    """AutoValidator 指标计算测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_compute_rmse(self):
        """验证: RMSE 计算"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.1, 2.1, 3.1])
        result = v._compute_metric("rmse", y_true, y_pred)
        assert result is not None
        assert result == pytest.approx(0.1, abs=1e-6)

    @pytest.mark.unit
    def test_compute_mse(self):
        """验证: MSE 计算"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.0, 2.0, 4.0])
        result = v._compute_metric("mse", y_true, y_pred)
        assert result is not None
        assert result == pytest.approx(1.0 / 3.0, abs=1e-6)

    @pytest.mark.unit
    def test_compute_mae(self):
        """验证: MAE 计算"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.5, 2.5, 3.5])
        result = v._compute_metric("mae", y_true, y_pred)
        assert result is not None
        assert result == pytest.approx(0.5, abs=1e-6)

    @pytest.mark.unit
    def test_compute_mape(self):
        """验证: MAPE 计算"""
        v = self._make_validator()
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([110.0, 190.0])
        result = v._compute_metric("mape", y_true, y_pred)
        assert result is not None
        # (10/100 + 10/200) / 2 * 100 = 7.5
        assert result == pytest.approx(7.5, abs=1e-6)

    @pytest.mark.unit
    def test_compute_mape_zero_true(self):
        """验证: MAPE 当 y_true 包含 0 时只计算非零样本"""
        v = self._make_validator()
        y_true = np.array([0.0, 100.0])
        y_pred = np.array([10.0, 110.0])
        result = v._compute_metric("mape", y_true, y_pred)
        # 只有 y_true=100 参与: |10/100| * 100 = 10
        assert result is not None
        assert result == pytest.approx(10.0, abs=1e-6)

    @pytest.mark.unit
    def test_compute_r2_perfect(self):
        """验证: R² 完美拟合"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = y_true.copy()
        result = v._compute_metric("r2", y_true, y_pred)
        assert result is not None
        assert result == pytest.approx(1.0, abs=1e-10)

    @pytest.mark.unit
    def test_compute_r2_poor(self):
        """验证: R² 差的拟合"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
        result = v._compute_metric("r2", y_true, y_pred)
        assert result is not None
        assert result < 0  # 反向拟合 R² < 0

    @pytest.mark.unit
    def test_compute_accuracy(self):
        """验证: 准确率计算"""
        v = self._make_validator()
        y_true = np.array([0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 0, 1])
        result = v._compute_metric("accuracy", y_true, y_pred)
        assert result is not None
        assert result == pytest.approx(4.0 / 5.0, abs=1e-6)

    @pytest.mark.unit
    def test_compute_precision_recall_f1(self):
        """验证: 精确率、召回率、F1 计算"""
        v = self._make_validator()
        y_true = np.array([1, 1, 0, 0, 1, 0])
        y_pred = np.array([1, 0, 0, 0, 1, 1])
        # TP=2, FP=1, FN=1
        precision = v._compute_metric("precision", y_true, y_pred)
        recall = v._compute_metric("recall", y_true, y_pred)
        f1 = v._compute_metric("f1", y_true, y_pred)
        assert precision == pytest.approx(2.0 / 3.0, abs=1e-6)
        assert recall == pytest.approx(2.0 / 3.0, abs=1e-6)
        assert f1 == pytest.approx(2.0 / 3.0, abs=1e-6)

    @pytest.mark.unit
    def test_compute_unknown_metric(self):
        """验证: 未知指标返回 None"""
        v = self._make_validator()
        result = v._compute_metric("unknown_xyz", np.array([1]), np.array([1]))
        assert result is None


class TestAutoValidatorNormalization:
    """指标名称归一化测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_normalize_r2_variants(self):
        """验证: R² 各种写法归一化"""
        v = self._make_validator()
        assert v._normalize_metric_name("R²") == "r2"
        assert v._normalize_metric_name("R^2") == "r2"
        assert v._normalize_metric_name("r2") == "r2"
        assert v._normalize_metric_name("RMSE") == "rmse"

    @pytest.mark.unit
    def test_normalize_chinese_names(self):
        """验证: 中文指标名归一化"""
        v = self._make_validator()
        assert v._normalize_metric_name("准确率") == "accuracy"
        assert v._normalize_metric_name("精确率") == "precision"
        assert v._normalize_metric_name("召回率") == "recall"
        assert v._normalize_metric_name("F1分数") == "f1"

    @pytest.mark.unit
    def test_normalize_unknown_passthrough(self):
        """验证: 未知指标名保持原样"""
        v = self._make_validator()
        assert v._normalize_metric_name("silhouette") == "silhouette"


class TestAutoValidatorProblemType:
    """问题类型推断测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_infer_regression(self):
        """验证: 连续值推断为回归"""
        v = self._make_validator()
        y_true = np.array([1.1, 2.3, 3.7, 4.5])
        y_pred = np.array([1.2, 2.4, 3.6, 4.4])
        assert v._infer_problem_type(y_true, y_pred) == "regression"

    @pytest.mark.unit
    def test_infer_classification_integer_labels(self):
        """验证: 少量整数标签推断为分类"""
        v = self._make_validator()
        y_true = np.array([0, 1, 0, 1, 0, 1, 0, 1])
        y_pred = np.array([0, 1, 1, 1, 0, 0, 0, 1])
        assert v._infer_problem_type(y_true, y_pred) == "classification"

    @pytest.mark.unit
    def test_infer_classification_binary_probs(self):
        """验证: 二值标签+概率输出推断为分类"""
        v = self._make_validator()
        y_true = np.array([0, 1, 0, 1])
        y_pred = np.array([0.1, 0.9, 0.3, 0.8])
        assert v._infer_problem_type(y_true, y_pred) == "classification"


class TestAutoValidatorResiduals:
    """残差诊断测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_diagnose_residuals_normal(self):
        """验证: 正常残差诊断"""
        v = self._make_validator()
        np.random.seed(42)
        y_true = np.linspace(0, 10, 100)
        noise = np.random.normal(0, 0.1, 100)
        y_pred = y_true + noise
        diag = v.diagnose_residuals(y_true, y_pred)
        assert isinstance(diag, ResidualDiagnostics)
        assert isinstance(diag.normality_test, dict)
        assert isinstance(diag.issues, list)

    @pytest.mark.unit
    def test_diagnose_residuals_small_sample(self):
        """验证: 小样本残差诊断不崩溃"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0])
        y_pred = np.array([1.1, 2.2])
        diag = v.diagnose_residuals(y_true, y_pred)
        assert isinstance(diag, ResidualDiagnostics)

    @pytest.mark.unit
    def test_detect_outliers(self):
        """验证: 异常值检测"""
        v = self._make_validator()
        residuals = np.zeros(100)
        residuals[50] = 100.0  # 明显异常值
        outliers = v._detect_outliers(residuals)
        assert 50 in outliers

    @pytest.mark.unit
    def test_detect_outliers_empty(self):
        """验证: 空数组不崩溃"""
        v = self._make_validator()
        outliers = v._detect_outliers(np.array([]))
        assert outliers == []

    @pytest.mark.unit
    def test_test_normality(self):
        """验证: 正态性检验返回结构"""
        v = self._make_validator()
        np.random.seed(42)
        residuals = np.random.normal(0, 1, 50)
        result = v._test_normality(residuals)
        assert "test" in result
        assert result["test"] == "Shapiro-Wilk"
        assert "passed" in result

    @pytest.mark.unit
    def test_test_autocorrelation(self):
        """验证: Durbin-Watson 自相关检验"""
        v = self._make_validator()
        np.random.seed(42)
        residuals = np.random.normal(0, 1, 50)
        result = v._test_autocorrelation(residuals)
        assert result["test"] == "Durbin-Watson"
        assert "statistic" in result
        assert "passed" in result


class TestAutoValidatorSplits:
    """数据分割测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_kfold_splits(self):
        """验证: K-Fold 分割"""
        v = self._make_validator()
        y = np.arange(100)
        splits = v._build_splits(y, "k-fold", 5)
        assert len(splits) == 5
        for train_idx, test_idx in splits:
            assert len(train_idx) + len(test_idx) == 100

    @pytest.mark.unit
    def test_timeseries_splits(self):
        """验证: 时间序列分割"""
        v = self._make_validator()
        y = np.arange(100)
        splits = v._build_splits(y, "time-series", 5)
        assert len(splits) > 0
        # 时间序列分割: 训练集结束 < 测试集开始
        for train_idx, test_idx in splits:
            assert train_idx[-1] < test_idx[0]

    @pytest.mark.unit
    def test_stratified_splits(self):
        """验证: 分层分割"""
        v = self._make_validator()
        y = np.array([0] * 50 + [1] * 50)
        splits = v._build_splits(y, "stratified", 5)
        assert len(splits) == 5


class TestAutoValidatorScoring:
    """评分和质量等级测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_score_to_quality_excellent(self):
        """验证: 高分 → excellent"""
        v = self._make_validator()
        assert v._score_to_quality(0.9) == "excellent"

    @pytest.mark.unit
    def test_score_to_quality_good(self):
        """验证: 中高分 → good"""
        v = self._make_validator()
        assert v._score_to_quality(0.75) == "good"

    @pytest.mark.unit
    def test_score_to_quality_acceptable(self):
        """验证: 中分 → acceptable"""
        v = self._make_validator()
        assert v._score_to_quality(0.6) == "acceptable"

    @pytest.mark.unit
    def test_score_to_quality_needs_improvement(self):
        """验证: 低分 → needs_improvement"""
        v = self._make_validator()
        assert v._score_to_quality(0.45) == "needs_improvement"

    @pytest.mark.unit
    def test_score_to_quality_poor(self):
        """验证: 极低分 → poor"""
        v = self._make_validator()
        assert v._score_to_quality(0.2) == "poor"

    @pytest.mark.unit
    def test_evaluate_report_score_empty_metrics(self):
        """验证: 空指标返回 0"""
        v = self._make_validator()
        diag = ResidualDiagnostics(
            normality_test={},
            homoscedasticity_test={},
            autocorrelation_test={},
            outlier_indices=[],
            diagnostics_passed=True,
            issues=[],
        )
        score = v._evaluate_report_score({}, diag, {})
        assert score == 0.0


class TestAutoValidatorComparison:
    """基线对比测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_compare_to_baseline(self):
        """验证: 基线对比生成结果"""
        v = self._make_validator()
        np.random.seed(42)
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        target_pred = np.array([1.1, 2.0, 3.1, 3.9, 5.1])
        baseline_pred = np.array([1.5, 2.5, 3.5, 4.5, 5.5])
        result = v.compare_to_baseline(
            target_predictions=target_pred,
            baseline_predictions=baseline_pred,
            y_true=y_true,
            metrics=["rmse", "mae", "r2"],
        )
        assert isinstance(result, BaselineComparison)
        assert result.winner in {"target", "baseline", "tie"}
        assert 0 <= result.confidence <= 1.0

    @pytest.mark.unit
    def test_compare_identical_predictions(self):
        """验证: 相同预测 → tie"""
        v = self._make_validator()
        y_true = np.array([1.0, 2.0, 3.0])
        pred = np.array([1.0, 2.0, 3.0])
        result = v.compare_to_baseline(pred, pred, y_true, ["rmse"])
        assert result.winner == "tie"


class TestAutoValidatorCrossValidation:
    """交叉验证测试"""

    def _make_validator(self) -> AutoValidator:
        from app.core.knowledge_base import knowledge_base
        return AutoValidator(knowledge_base)

    @pytest.mark.unit
    def test_cross_validate_simple_model(self):
        """验证: 简单模型交叉验证"""
        v = self._make_validator()

        # 创建一个简单的 mock 模型
        class SimpleModel:
            def fit(self, X, y):
                self.mean_ = np.mean(y)

            def predict(self, X):
                return np.full(len(X), self.mean_)

        np.random.seed(42)
        X = np.random.randn(50, 2)
        y = X[:, 0] * 2 + X[:, 1] + np.random.randn(50) * 0.1

        result = v.cross_validate(SimpleModel(), X, y, n_splits=3)
        assert isinstance(result, CrossValidationResult)
        assert result.method == "k-fold"
        assert result.n_splits == 3
        assert len(result.scores) > 0
        assert 0 <= result.mean_score <= 1.0


class TestAutoValidatorDataclasses:
    """AutoValidator 数据类测试"""

    @pytest.mark.unit
    def test_baseline_comparison_creation(self):
        """验证: BaselineComparison 创建"""
        bc = BaselineComparison(
            baseline_model="lr",
            target_model="rf",
            metrics_comparison={"r2": {"baseline": 0.8, "target": 0.9, "improvement": 12.5}},
            statistical_tests={"paired_ttest": {"p_value": 0.03, "significant": True}},
            winner="target",
            confidence=0.85,
        )
        assert bc.winner == "target"
        assert bc.confidence == 0.85

    @pytest.mark.unit
    def test_residual_diagnostics_creation(self):
        """验证: ResidualDiagnostics 创建"""
        rd = ResidualDiagnostics(
            normality_test={"test": "Shapiro-Wilk", "passed": True},
            homoscedasticity_test={"test": "Breusch-Pagan", "passed": True},
            autocorrelation_test={"test": "Durbin-Watson", "passed": True},
            outlier_indices=[],
            diagnostics_passed=True,
            issues=[],
        )
        assert rd.diagnostics_passed is True
        assert rd.issues == []

    @pytest.mark.unit
    def test_cross_validation_result_creation(self):
        """验证: CrossValidationResult 创建"""
        cvr = CrossValidationResult(
            method="k-fold",
            n_splits=5,
            scores=[0.8, 0.85, 0.82, 0.79, 0.83],
            mean_score=0.818,
            std_score=0.022,
            fold_details=[],
        )
        assert cvr.n_splits == 5
        assert len(cvr.scores) == 5


# ================================================================
# SensitivityAnalyzer 测试
# ================================================================


class TestSensitivityEnums:
    """敏感性分析枚举测试"""

    @pytest.mark.unit
    def test_sensitivity_method_values(self):
        """验证: SensitivityMethod 枚举值"""
        assert SensitivityMethod.OAT.value == "oat"
        assert SensitivityMethod.MORRIS.value == "morris"
        assert SensitivityMethod.SOBOL.value == "sobol"
        assert SensitivityMethod.LOCAL.value == "local"
        assert SensitivityMethod.TORNADO.value == "tornado"

    @pytest.mark.unit
    def test_stability_rating_values(self):
        """验证: StabilityRating 枚举值"""
        assert StabilityRating.STABLE.value == "stable"
        assert StabilityRating.MODERATE.value == "moderate"
        assert StabilityRating.SENSITIVE.value == "sensitive"


class TestParameterSpec:
    """ParameterSpec 数据类测试"""

    @pytest.mark.unit
    def test_create_basic(self):
        """验证: 基本创建"""
        spec = ParameterSpec(
            name="alpha",
            display_name="学习率",
            base_value=0.01,
            min_value=0.001,
            max_value=0.1,
        )
        assert spec.name == "alpha"
        assert spec.display_name == "学习率"
        assert spec.unit == ""
        assert spec.description == ""

    @pytest.mark.unit
    def test_create_with_optional(self):
        """验证: 包含可选字段"""
        spec = ParameterSpec(
            name="beta",
            display_name="衰减率",
            base_value=0.9,
            min_value=0.0,
            max_value=1.0,
            unit="%",
            description="动量衰减",
        )
        assert spec.unit == "%"
        assert spec.description == "动量衰减"


class TestSensitivityAnalyzer:
    """SensitivityAnalyzer 类测试"""

    def _simple_model(self, x=1.0, y=1.0) -> float:
        """简单测试模型: f(x,y) = 2*x + 3*y"""
        return 2.0 * x + 3.0 * y

    def _make_params(self) -> list:
        return [
            ParameterSpec(
                name="x", display_name="参数X",
                base_value=1.0, min_value=0.1, max_value=10.0,
            ),
            ParameterSpec(
                name="y", display_name="参数Y",
                base_value=1.0, min_value=0.1, max_value=10.0,
            ),
        ]

    @pytest.mark.unit
    def test_init_default_run_id(self):
        """验证: 默认生成 run_id"""
        analyzer = SensitivityAnalyzer()
        assert analyzer.run_id is not None
        assert len(analyzer.run_id) == 8

    @pytest.mark.unit
    def test_init_custom_run_id(self):
        """验证: 自定义 run_id"""
        analyzer = SensitivityAnalyzer(run_id="test123")
        assert analyzer.run_id == "test123"

    @pytest.mark.unit
    def test_analyze_oat_basic(self):
        """验证: OAT 分析基本流程"""
        analyzer = SensitivityAnalyzer(run_id="test_oat")
        params = self._make_params()
        base_params = {"x": 1.0, "y": 1.0}

        report = analyzer.analyze_oat(
            model_func=self._simple_model,
            parameters=params,
            base_params=base_params,
        )
        assert isinstance(report, SensitivityReport)
        assert report.run_id == "test_oat"
        assert report.base_output == pytest.approx(5.0, abs=1e-6)
        assert len(report.results) == 2

    @pytest.mark.unit
    def test_analyze_oat_results_sorted_by_impact(self):
        """验证: 结果按影响程度排序"""
        analyzer = SensitivityAnalyzer()

        def model(x=1.0, y=1.0):
            return 10.0 * x + 0.1 * y  # x 影响远大于 y

        params = self._make_params()
        report = analyzer.analyze_oat(
            model_func=model,
            parameters=params,
            base_params={"x": 1.0, "y": 1.0},
        )
        # 影响大的参数排在前面
        assert report.results[0].impact_score >= report.results[1].impact_score

    @pytest.mark.unit
    def test_analyze_oat_stability_rating(self):
        """验证: 稳定性评级正确"""
        analyzer = SensitivityAnalyzer()

        # 常数模型 → 所有参数 STABLE
        def constant_model(x=1.0, y=1.0):
            return 42.0

        params = self._make_params()
        report = analyzer.analyze_oat(
            model_func=constant_model,
            parameters=params,
            base_params={"x": 1.0, "y": 1.0},
        )
        for result in report.results:
            assert result.stability_rating == StabilityRating.STABLE
            assert result.max_change_percent == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.unit
    def test_analyze_oat_sensitive_parameter(self):
        """验证: 敏感参数识别"""
        analyzer = SensitivityAnalyzer()

        def sensitive_model(x=1.0, y=1.0):
            return x ** 3 + y  # x 的三次方 → 高敏感

        params = self._make_params()
        report = analyzer.analyze_oat(
            model_func=sensitive_model,
            parameters=params,
            base_params={"x": 1.0, "y": 1.0},
        )
        x_result = next(r for r in report.results if r.parameter == "x")
        assert x_result.stability_rating in {
            StabilityRating.MODERATE,
            StabilityRating.SENSITIVE,
        }

    @pytest.mark.unit
    def test_overall_stability_all_stable(self):
        """验证: 所有参数稳定 → 整体稳定"""
        analyzer = SensitivityAnalyzer()

        def constant_model(x=1.0, y=1.0):
            return 42.0

        report = analyzer.analyze_oat(
            model_func=constant_model,
            parameters=self._make_params(),
            base_params={"x": 1.0, "y": 1.0},
        )
        assert report.overall_stability == StabilityRating.STABLE
        assert len(report.critical_parameters) == 0

    @pytest.mark.unit
    def test_recommendations_generated(self):
        """验证: 建议列表非空"""
        analyzer = SensitivityAnalyzer()
        report = analyzer.analyze_oat(
            model_func=self._simple_model,
            parameters=self._make_params(),
            base_params={"x": 1.0, "y": 1.0},
        )
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0

    @pytest.mark.unit
    def test_custom_variation_percents(self):
        """验证: 自定义变化百分比"""
        analyzer = SensitivityAnalyzer()
        variations = [-0.1, 0, 0.1]
        report = analyzer.analyze_oat(
            model_func=self._simple_model,
            parameters=self._make_params(),
            base_params={"x": 1.0, "y": 1.0},
            variation_percents=variations,
        )
        # 每个参数测试 3 个变化值
        for result in report.results:
            assert len(result.tested_values) == 3

    @pytest.mark.unit
    def test_generate_tornado_data(self):
        """验证: 龙卷风图数据生成"""
        analyzer = SensitivityAnalyzer()
        report = analyzer.analyze_oat(
            model_func=self._simple_model,
            parameters=self._make_params(),
            base_params={"x": 1.0, "y": 1.0},
        )
        tornado = analyzer.generate_tornado_data(report)
        assert "parameters" in tornado
        assert "low_values" in tornado
        assert "high_values" in tornado
        assert "base_value" in tornado
        assert len(tornado["parameters"]) == 2

    @pytest.mark.unit
    def test_generate_spider_data(self):
        """验证: 蜘蛛图数据生成"""
        analyzer = SensitivityAnalyzer()
        report = analyzer.analyze_oat(
            model_func=self._simple_model,
            parameters=self._make_params(),
            base_params={"x": 1.0, "y": 1.0},
        )
        spider = analyzer.generate_spider_data(report)
        assert "series" in spider
        assert len(spider["series"]) == 2

    @pytest.mark.unit
    def test_format_report_for_paper(self):
        """验证: 论文格式报告生成"""
        analyzer = SensitivityAnalyzer()
        report = analyzer.analyze_oat(
            model_func=self._simple_model,
            parameters=self._make_params(),
            base_params={"x": 1.0, "y": 1.0},
        )
        text = analyzer.format_report_for_paper(report)
        assert isinstance(text, str)
        assert "敏感性分析" in text
        assert "分析方法" in text
        assert "分析结果" in text
        assert "参数X" in text
        assert "参数Y" in text


class TestSensitivityConvenience:
    """便捷函数测试"""

    @pytest.mark.unit
    def test_run_sensitivity_analysis(self):
        """验证: run_sensitivity_analysis 便捷函数"""
        def model(a=1.0, b=2.0):
            return a + b

        params = [
            ParameterSpec(name="a", display_name="A", base_value=1.0, min_value=0.1, max_value=10.0),
            ParameterSpec(name="b", display_name="B", base_value=2.0, min_value=0.1, max_value=10.0),
        ]
        report = run_sensitivity_analysis(
            model_func=model,
            parameters=params,
            base_params={"a": 1.0, "b": 2.0},
        )
        assert isinstance(report, SensitivityReport)
        assert len(report.results) == 2

    @pytest.mark.unit
    def test_to_sensitivity_result(self):
        """验证: to_sensitivity_result 转换"""
        result = SensitivityAnalysisResult(
            parameter="alpha",
            display_name="学习率",
            base_value=0.01,
            tested_values=[0.007, 0.01, 0.013],
            result_values=[90.0, 95.0, 92.0],
            impact_score=0.3,
            elasticity=0.5,
            stability_rating=StabilityRating.MODERATE,
            max_change_percent=5.3,
            interpretation="测试",
        )
        converted = to_sensitivity_result(result)
        assert converted.parameter == "alpha"
        assert converted.original_value == 0.01
        assert converted.impact_score == 0.3
        assert converted.stability_rating == "moderate"


# ================================================================
# MultiModelStrategy 测试
# ================================================================


class TestMultiModelStrategyEnums:
    """MultiModelStrategy 枚举测试"""

    @pytest.mark.unit
    def test_problem_category_values(self):
        """验证: ProblemCategory 枚举完整"""
        categories = list(ProblemCategory)
        assert len(categories) >= 10
        assert ProblemCategory.OPTIMIZATION in categories
        assert ProblemCategory.PREDICTION in categories
        assert ProblemCategory.CLASSIFICATION in categories
        assert ProblemCategory.EVALUATION in categories

    @pytest.mark.unit
    def test_data_characteristic_values(self):
        """验证: DataCharacteristic 枚举完整"""
        chars = list(DataCharacteristic)
        assert len(chars) >= 8
        assert DataCharacteristic.TIME_SERIES in chars
        assert DataCharacteristic.HIGH_DIMENSIONAL in chars
        assert DataCharacteristic.SPARSE in chars


class TestModelInfo:
    """ModelInfo 数据类测试"""

    @pytest.mark.unit
    def test_create_model_info(self):
        """验证: ModelInfo 创建"""
        info = ModelInfo(
            id="test_model",
            name="测试模型",
            category="optimization",
            complexity="medium",
            description="测试",
            advantages=["快"],
            disadvantages=["慢"],
            applicable_scenarios=["线性规划"],
            data_requirements="结构化数据",
            key_parameters=["c"],
            python_implementation="scipy.optimize.linprog",
            validation_methods=["交叉验证"],
        )
        assert info.id == "test_model"
        assert info.name == "测试模型"


class TestMultiModelStrategyKnowledgeBase:
    """MODEL_KNOWLEDGE_BASE 验证"""

    @pytest.mark.unit
    def test_knowledge_base_not_empty(self):
        """验证: 知识库非空"""
        from app.core.modeling.multi_model_strategy import MODEL_KNOWLEDGE_BASE
        assert len(MODEL_KNOWLEDGE_BASE) > 0

    @pytest.mark.unit
    def test_knowledge_base_categories(self):
        """验证: 知识库包含主要类别"""
        from app.core.modeling.multi_model_strategy import MODEL_KNOWLEDGE_BASE
        expected = {"optimization", "prediction", "evaluation"}
        assert expected.issubset(set(MODEL_KNOWLEDGE_BASE.keys()))

    @pytest.mark.unit
    def test_knowledge_base_values_are_model_info_lists(self):
        """验证: 所有值为 ModelInfo 列表"""
        from app.core.modeling.multi_model_strategy import MODEL_KNOWLEDGE_BASE
        for category, models in MODEL_KNOWLEDGE_BASE.items():
            assert isinstance(models, list), f"{category} 不是列表"
            for model in models:
                assert isinstance(model, ModelInfo), f"{category} 中包含非 ModelInfo"

    @pytest.mark.unit
    def test_knowledge_base_models_have_required_fields(self):
        """验证: 所有模型具有必填字段"""
        from app.core.modeling.multi_model_strategy import MODEL_KNOWLEDGE_BASE
        for category, models in MODEL_KNOWLEDGE_BASE.items():
            for model in models:
                assert model.id, f"{category} 中模型缺少 id"
                assert model.name, f"{category}/{model.id} 缺少 name"
                assert model.description, f"{category}/{model.id} 缺少 description"


class TestMultiModelStrategy:
    """MultiModelStrategy 类测试"""

    @pytest.mark.unit
    def test_initialization(self):
        """验证: 初始化成功"""
        strategy = MultiModelStrategy()
        assert strategy is not None

    @pytest.mark.unit
    def test_initialization_with_run_id(self):
        """验证: 自定义 run_id"""
        strategy = MultiModelStrategy(run_id="test_run")
        assert strategy.run_id == "test_run"

    @pytest.mark.unit
    def test_get_model_recommendations_optimization(self):
        """验证: 优化问题推荐"""
        strategy = MultiModelStrategy()
        recs = strategy.get_model_recommendations(
            problem_category=ProblemCategory.OPTIMIZATION,
            data_characteristics=[],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    @pytest.mark.unit
    def test_get_model_recommendations_prediction(self):
        """验证: 预测问题推荐"""
        strategy = MultiModelStrategy()
        recs = strategy.get_model_recommendations(
            problem_category=ProblemCategory.PREDICTION,
            data_characteristics=[DataCharacteristic.TIME_SERIES],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    @pytest.mark.unit
    def test_get_model_recommendations_classification(self):
        """验证: 分类问题推荐"""
        strategy = MultiModelStrategy()
        recs = strategy.get_model_recommendations(
            problem_category=ProblemCategory.CLASSIFICATION,
            data_characteristics=[],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    @pytest.mark.unit
    def test_get_model_recommendations_evaluation(self):
        """验证: 评价问题推荐"""
        strategy = MultiModelStrategy()
        recs = strategy.get_model_recommendations(
            problem_category=ProblemCategory.EVALUATION,
            data_characteristics=[],
        )
        assert isinstance(recs, list)
        assert len(recs) > 0

    @pytest.mark.unit
    def test_get_evaluation_metrics_optimization(self):
        """验证: 优化类评价指标"""
        strategy = MultiModelStrategy()
        metrics = strategy._get_evaluation_metrics(ProblemCategory.OPTIMIZATION)
        assert isinstance(metrics, list)
        assert len(metrics) > 0

    @pytest.mark.unit
    def test_get_evaluation_metrics_prediction(self):
        """验证: 预测类评价指标"""
        strategy = MultiModelStrategy()
        metrics = strategy._get_evaluation_metrics(ProblemCategory.PREDICTION)
        assert isinstance(metrics, list)
        assert any("R²" in m or "RMSE" in m for m in metrics)

    @pytest.mark.unit
    def test_get_evaluation_metrics_classification(self):
        """验证: 分类类评价指标"""
        strategy = MultiModelStrategy()
        metrics = strategy._get_evaluation_metrics(ProblemCategory.CLASSIFICATION)
        assert isinstance(metrics, list)
        assert any("准确率" in m or "F1" in m for m in metrics)

    @pytest.mark.unit
    def test_get_evaluation_metrics_all_categories(self):
        """验证: 所有类别都有评价指标"""
        strategy = MultiModelStrategy()
        for category in ProblemCategory:
            metrics = strategy._get_evaluation_metrics(category)
            assert isinstance(metrics, list), f"{category} 无评价指标"
            assert len(metrics) > 0, f"{category} 评价指标为空"
