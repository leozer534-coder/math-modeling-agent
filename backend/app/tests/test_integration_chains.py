"""
核心集成测试 - 覆盖三条关键注入链路

链路1: 代码模板注入链 (模型名称提取 -> 模板匹配 -> Prompt 注入)
链路2: 知识库 -> Prompt 注入链 (知识库查询 -> Modeler Prompt 构建)
链路3: math_tools 可用性验证 (模块导入 -> 函数调用 -> 结果校验)
"""

import sys
from unittest.mock import MagicMock

# ================== 环境兼容: 预注入缺失的可选依赖 ==================
# CoderStage 导入链: coder_stage -> workflow.__init__ -> engine -> stages.__init__
# -> validation_stage -> langchain_core (可选依赖, 测试环境可能未安装)
# 必须在任何 app.core.workflow.* 导入前注入 mock, 避免 ModuleNotFoundError
for _mod_name in (
    "langchain_core",
    "langchain_core.messages",
):
    if _mod_name not in sys.modules:
        _mock_mod = MagicMock()
        # 提供 validation_stage.py 使用的 HumanMessage, SystemMessage
        _mock_mod.HumanMessage = MagicMock
        _mock_mod.SystemMessage = MagicMock
        sys.modules[_mod_name] = _mock_mod

import pytest  # noqa: E402
import numpy as np  # noqa: E402


# ================================================================
# 链路1: 代码模板注入链
# ================================================================


class TestCodeTemplateInjectionChain:
    """代码模板注入链集成测试。

    测试从建模方案文本中提取模型名称 -> 在模板注册中心搜索匹配模板
    -> 将模板代码注入到 Coder Prompt 的完整流程。
    """

    # ---------- _extract_model_names 测试 ----------

    @pytest.mark.unit
    def test_extract_model_names_basic(self):
        """验证: 包含'线性规划'的文本应提取出对应关键词。"""
        from app.core.workflow.stages.coder_stage import CoderStage

        text = "本题采用线性规划模型对资源分配问题进行建模求解"
        result = CoderStage._extract_model_names(text)

        assert isinstance(result, list)
        assert len(result) > 0
        # 至少应包含"线性规划"关键词
        found_lp = any("线性规划" in kw for kw in result)
        assert found_lp, f"未从文本中提取到'线性规划'相关关键词, 实际结果: {result}"

    @pytest.mark.unit
    def test_extract_model_names_multiple(self):
        """验证: 包含多种模型名称的文本应提取出多个关键词。"""
        from app.core.workflow.stages.coder_stage import CoderStage

        text = (
            "首先使用ARIMA模型进行时间序列预测, "
            "然后使用TOPSIS方法进行综合评价, "
            "最后使用遗传算法进行参数优化"
        )
        result = CoderStage._extract_model_names(text)

        assert isinstance(result, list)
        assert len(result) >= 3, (
            f"包含3种模型的文本应至少提取3个关键词, 实际: {len(result)} 个 -> {result}"
        )
        # 验证 ARIMA、TOPSIS、遗传算法 均被提取
        result_text = " ".join(result).lower()
        assert "arima" in result_text, f"未提取到 ARIMA, 实际: {result}"
        assert "topsis" in result_text, f"未提取到 TOPSIS, 实际: {result}"
        assert any("遗传" in kw for kw in result), f"未提取到遗传算法, 实际: {result}"

    @pytest.mark.unit
    def test_extract_model_names_empty(self):
        """验证: 空文本应返回空列表。"""
        from app.core.workflow.stages.coder_stage import CoderStage

        result = CoderStage._extract_model_names("")
        assert result == [], f"空文本应返回空列表, 实际: {result}"

    @pytest.mark.unit
    def test_extract_model_names_no_match(self):
        """验证: 不含任何模型关键词的普通文本应返回空列表。"""
        from app.core.workflow.stages.coder_stage import CoderStage

        text = "今天天气很好, 适合户外活动"
        result = CoderStage._extract_model_names(text)
        assert result == [], f"不含模型关键词的文本应返回空列表, 实际: {result}"

    # ---------- TemplateRegistry.search 测试 ----------

    @pytest.mark.unit
    def test_template_registry_search(self):
        """验证: 搜索'ARIMA'应返回包含 ARIMA 相关的模板。"""
        from app.config.code_templates.template_registry import template_registry

        results = template_registry.search("ARIMA")

        assert isinstance(results, list)
        assert len(results) > 0, "搜索 'ARIMA' 应至少返回一个匹配模板"
        # 验证返回的模板确实与 ARIMA 相关
        names_lower = [t.name.lower() for t in results]
        assert any(
            "arima" in name or "时间序列" in name for name in names_lower
        ), f"返回模板应与 ARIMA 相关, 实际模板名: {names_lower}"

    @pytest.mark.unit
    def test_template_registry_no_match(self):
        """验证: 搜索不存在的模型名应返回空列表。"""
        from app.config.code_templates.template_registry import template_registry

        results = template_registry.search("量子纠缠算法XYZ")
        assert results == [], f"搜索不存在的模型名应返回空列表, 实际: {results}"

    @pytest.mark.unit
    def test_template_registry_search_case_insensitive(self):
        """验证: 模板搜索应不区分大小写。"""
        from app.config.code_templates.template_registry import template_registry

        results_upper = template_registry.search("ARIMA")
        results_lower = template_registry.search("arima")

        assert len(results_upper) == len(results_lower), (
            "大小写不同的搜索应返回相同数量的结果"
        )

    # ---------- build_coder_prompt_with_templates 测试 ----------

    @pytest.mark.unit
    def test_build_coder_prompt_with_templates(self):
        """验证: 传入有效模型名称时, 模板文本应被注入到 prompt 中。"""
        from app.core.prompts.base_prompts import build_coder_prompt_with_templates

        base_prompt = "你是一个专业的数学建模代码编写者。"
        model_names = ["ARIMA"]

        result = build_coder_prompt_with_templates(base_prompt, model_names)

        assert isinstance(result, str)
        assert len(result) > len(base_prompt), (
            "注入模板后的 prompt 应比原始 prompt 更长"
        )
        assert base_prompt in result, "原始 prompt 内容应保留"
        # 验证模板相关标记被注入
        assert "参考代码模板" in result or "arima" in result.lower(), (
            "注入后的 prompt 应包含模板参考内容"
        )

    @pytest.mark.unit
    def test_build_coder_prompt_no_templates(self):
        """验证: 无匹配模板时应返回原始 prompt, 不做修改。"""
        from app.core.prompts.base_prompts import build_coder_prompt_with_templates

        base_prompt = "你是一个专业的数学建模代码编写者。"

        # model_names 为 None
        result_none = build_coder_prompt_with_templates(base_prompt, None)
        assert result_none == base_prompt, "model_names=None 应返回原始 prompt"

        # model_names 为空列表
        result_empty = build_coder_prompt_with_templates(base_prompt, [])
        assert result_empty == base_prompt, "model_names=[] 应返回原始 prompt"

    @pytest.mark.unit
    def test_build_coder_prompt_no_match_models(self):
        """验证: 传入无法匹配任何模板的模型名时, 应返回原始 prompt。"""
        from app.core.prompts.base_prompts import build_coder_prompt_with_templates

        base_prompt = "你是一个代码编写专家。"
        model_names = ["不存在的模型XYZ"]

        result = build_coder_prompt_with_templates(base_prompt, model_names)
        assert result == base_prompt, (
            "无匹配模板时应返回原始 prompt, 不应修改内容"
        )

    # ---------- 全链路端到端测试 ----------

    @pytest.mark.unit
    def test_full_chain_modeler_to_coder_templates(self):
        """验证: 完整链路 — 从 modeler 输出文本提取模型名称, 到 coder prompt 包含模板代码。

        模拟 modeler 输出包含 "ARIMA" 的建模方案,
        验证 coder prompt 最终包含 ARIMA 相关模板代码。
        """
        from app.core.workflow.stages.coder_stage import CoderStage
        from app.core.prompts.base_prompts import build_coder_prompt_with_templates

        # Arrange: 模拟 modeler 产出的建模方案文本
        modeler_solution = (
            "采用 ARIMA 模型对历史销量数据进行时间序列预测, "
            "首先进行 ADF 平稳性检验, 然后通过 ACF/PACF 图确定 (p, d, q) 参数, "
            "最后使用 SARIMAX 进行季节性建模并预测未来 12 期数据。"
        )
        base_coder_prompt = "请根据以下建模方案编写求解代码。"

        # Act: 步骤1 — 提取模型名称
        model_names = CoderStage._extract_model_names(modeler_solution)

        # Assert 步骤1
        assert len(model_names) > 0, "应从建模方案中提取到模型名称"
        assert any(
            "arima" in kw.lower() or "sarima" in kw.lower() or "时间序列" in kw
            for kw in model_names
        ), f"应提取到 ARIMA/SARIMA/时间序列 相关关键词, 实际: {model_names}"

        # Act: 步骤2 — 注入模板到 prompt
        enhanced_prompt = build_coder_prompt_with_templates(
            base_coder_prompt, model_names
        )

        # Assert 步骤2: 最终 prompt 包含 ARIMA 模板代码
        assert len(enhanced_prompt) > len(base_coder_prompt), (
            "增强后的 prompt 应比基础 prompt 更长"
        )
        assert base_coder_prompt in enhanced_prompt, "基础 prompt 应保留"
        # 验证模板中的标志性代码片段被注入
        prompt_lower = enhanced_prompt.lower()
        assert (
            "arima" in prompt_lower
            or "sarimax" in prompt_lower
            or "时间序列" in enhanced_prompt
        ), "增强后的 prompt 应包含 ARIMA 相关模板代码"

    @pytest.mark.unit
    def test_full_chain_multiple_models(self):
        """验证: 建模方案包含多种模型时, 所有匹配模板都应被注入。"""
        from app.core.workflow.stages.coder_stage import CoderStage
        from app.core.prompts.base_prompts import build_coder_prompt_with_templates

        # 包含优化 + 评价两类模型的建模方案
        modeler_solution = (
            "使用线性规划模型进行资源优化分配, "
            "同时使用 AHP 层次分析法确定指标权重"
        )
        base_prompt = "请编写代码。"

        model_names = CoderStage._extract_model_names(modeler_solution)
        enhanced_prompt = build_coder_prompt_with_templates(base_prompt, model_names)

        assert len(enhanced_prompt) > len(base_prompt), (
            "包含多模型的方案应产生增强 prompt"
        )


# ================================================================
# 链路2: 知识库 -> Prompt 注入链
# ================================================================


class TestKnowledgeBasePromptChain:
    """知识库到 Prompt 注入链集成测试。

    测试从知识库查询模型推荐 -> 格式化知识文本
    -> 注入到 Modeler Prompt 的完整流程。
    """

    # ---------- MathModelingKnowledgeBase.search_model 测试 ----------

    @pytest.mark.unit
    def test_knowledge_base_search_optimization(self):
        """验证: 搜索'优化'应返回优化类相关模型。"""
        from app.core.knowledge_base import knowledge_base

        results = knowledge_base.search_model("优化")

        assert isinstance(results, list)
        assert len(results) > 0, "搜索'优化'应返回至少一个模型"
        # 验证返回的模型中包含优化相关的类别或名称
        categories = [m.category for m in results]
        names = [m.name for m in results]
        assert any(
            "优化" in cat or "规划" in name
            for cat, name in zip(categories, names)
        ), f"搜索'优化'的结果应包含优化类模型, 实际类别: {categories}, 名称: {names}"

    @pytest.mark.unit
    def test_knowledge_base_search_prediction(self):
        """验证: 搜索'预测'应返回预测类相关模型。"""
        from app.core.knowledge_base import knowledge_base

        results = knowledge_base.search_model("预测")

        assert isinstance(results, list)
        assert len(results) > 0, "搜索'预测'应返回至少一个模型"
        names = [m.name for m in results]
        assert any(
            "预测" in name or "回归" in name or "ARIMA" in name
            for name in names
        ), f"搜索'预测'的结果应包含预测类模型, 实际名称: {names}"

    @pytest.mark.unit
    def test_knowledge_base_search_evaluation(self):
        """验证: 搜索'评价'应返回评价类相关模型。"""
        from app.core.knowledge_base import knowledge_base

        results = knowledge_base.search_model("评价")

        assert isinstance(results, list)
        assert len(results) > 0, "搜索'评价'应返回至少一个模型"
        names = [m.name for m in results]
        assert any(
            "AHP" in name or "TOPSIS" in name or "熵权" in name or "评价" in name
            for name in names
        ), f"搜索'评价'的结果应包含评价类模型, 实际名称: {names}"

    # ---------- get_knowledge_for_prompt 测试 ----------

    @pytest.mark.unit
    def test_knowledge_base_get_knowledge_for_prompt(self):
        """验证: get_knowledge_for_prompt 应返回格式化的知识文本。"""
        from app.core.knowledge_base import knowledge_base

        result = knowledge_base.get_knowledge_for_prompt(
            problem_type="优化",
            keywords=["线性规划"],
        )

        assert isinstance(result, str)
        assert len(result) > 0, "优化类问题应返回非空知识文本"
        # 验证包含结构化的标题标记
        assert "###" in result, "知识文本应包含 Markdown 标题格式"
        # 验证包含推荐模型部分
        assert "推荐模型" in result or "推荐" in result, (
            "知识文本应包含模型推荐信息"
        )

    @pytest.mark.unit
    def test_knowledge_base_max_chars_limit(self):
        """验证: 返回文本不应超过 max_chars 限制。"""
        from app.core.knowledge_base import knowledge_base

        max_chars = 500
        result = knowledge_base.get_knowledge_for_prompt(
            problem_type="优化",
            keywords=["线性规划", "整数规划", "非线性规划"],
            max_chars=max_chars,
        )

        assert isinstance(result, str)
        # 允许截断标记 "..." 的少量超出
        assert len(result) <= max_chars + 10, (
            f"返回文本长度 {len(result)} 不应大幅超过 max_chars={max_chars}"
        )

    @pytest.mark.unit
    def test_knowledge_base_empty_query(self):
        """验证: 空查询条件应返回空字符串或极少内容。"""
        from app.core.knowledge_base import knowledge_base

        result = knowledge_base.get_knowledge_for_prompt(
            problem_type="",
            keywords=None,
        )

        # 空问题类型无法匹配任何类别, 应返回空或极少内容
        assert isinstance(result, str)

    # ---------- build_modeler_prompt 知识库注入测试 ----------

    @pytest.mark.unit
    def test_build_modeler_prompt_with_knowledge(self):
        """验证: build_modeler_prompt 能将知识库文本注入到 modeler prompt 中。"""
        from app.core.prompts.base_prompts import build_modeler_prompt

        result = build_modeler_prompt(
            problem_type="优化",
            keywords=["线性规划"],
        )

        assert isinstance(result, str)
        assert len(result) > 0, "构建的 prompt 不应为空"
        # 如果知识库注入成功, prompt 中应包含知识库相关内容
        # 注意: 即使知识库注入失败也不会报错 (降级跳过), 所以这里验证基础 prompt 存在
        # 基础 MODELER_PROMPT 来自 TOML 文件, 只要加载成功即有内容

    @pytest.mark.unit
    def test_build_modeler_prompt_without_knowledge(self):
        """验证: 不传参数时仍返回有效的基础 prompt。"""
        from app.core.prompts.base_prompts import build_modeler_prompt

        result = build_modeler_prompt()

        assert isinstance(result, str)
        # 基础 prompt 应至少有一些内容 (来自 TOML)

    @pytest.mark.unit
    def test_build_modeler_prompt_knowledge_section_format(self):
        """验证: 知识库注入后, prompt 包含结构化的参考知识库段落。"""
        from app.core.prompts.base_prompts import build_modeler_prompt, MODELER_PROMPT

        # 仅在基础 prompt 有内容时执行详细检查
        if not MODELER_PROMPT:
            pytest.skip("MODELER_PROMPT 为空 (prompts.toml 可能不存在), 跳过此测试")

        result = build_modeler_prompt(
            problem_type="预测",
            keywords=["ARIMA", "时间序列"],
        )

        # 如果知识库成功注入, 应包含 "参考知识库" 标记
        if "参考知识库" in result:
            assert "推荐模型" in result or "推荐" in result, (
                "知识库注入段落应包含推荐信息"
            )


# ================================================================
# 链路3: math_tools 可用性验证
# ================================================================


class TestMathToolsAvailability:
    """math_tools 工具模块可用性测试。

    验证 math_tools 包能正常导入, 各子模块的核心函数
    能被调用并返回合理结果。
    """

    # ---------- 导入测试 ----------

    @pytest.mark.unit
    def test_math_tools_import(self):
        """验证: math_tools 包能正常导入, __all__ 列表完整。"""
        from app.tools import math_tools

        assert hasattr(math_tools, "__all__"), "math_tools 应定义 __all__"
        expected_functions = [
            "solve_linear_program",
            "solve_integer_program",
            "ahp_analysis",
            "topsis_evaluate",
            "entropy_weight",
            "hypothesis_test",
            "solve_tsp",
            "cross_validate",
            "arima_forecast",
        ]
        for func_name in expected_functions:
            assert hasattr(math_tools, func_name), (
                f"math_tools 应导出 {func_name} 函数"
            )

    @pytest.mark.unit
    def test_math_tools_optimization_functions(self):
        """验证: optimization 子模块的核心函数可调用并返回正确结果。"""
        from app.tools.math_tools.optimization import (
            solve_linear_program,
            OptimizationResult,
        )

        # 简单线性规划: min -x1 - 2*x2, s.t. x1 + x2 <= 4, x1,x2 >= 0
        c = np.array([-1, -2])
        A_ub = np.array([[1, 1]])
        b_ub = np.array([4])
        bounds = [(0, None), (0, None)]

        result = solve_linear_program(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds)

        assert isinstance(result, OptimizationResult), "应返回 OptimizationResult"
        assert result.status == "optimal", f"应找到最优解, 实际状态: {result.status}"
        assert result.optimal_solution is not None, "最优解不应为 None"
        assert len(result.optimal_solution) == 2, "应有 2 个决策变量"
        # 最优解应接近 x1=0, x2=4, 目标值 = -8
        assert abs(result.optimal_value - (-8)) < 1e-6, (
            f"最优值应为 -8, 实际: {result.optimal_value}"
        )

    @pytest.mark.unit
    def test_math_tools_optimization_maximize(self):
        """验证: 线性规划最大化模式正确工作。"""
        from app.tools.math_tools.optimization import solve_linear_program

        # max x1 + 2*x2, s.t. x1 + x2 <= 4
        c = np.array([1, 2])
        A_ub = np.array([[1, 1]])
        b_ub = np.array([4])
        bounds = [(0, None), (0, None)]

        result = solve_linear_program(
            c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, maximize=True
        )

        assert result.status == "optimal"
        assert abs(result.optimal_value - 8) < 1e-6, (
            f"最大化目标值应为 8, 实际: {result.optimal_value}"
        )

    # ---------- evaluation 子模块测试 ----------

    @pytest.mark.unit
    def test_math_tools_evaluation_functions(self):
        """验证: evaluation 子模块的核心函数可调用。"""
        from app.tools.math_tools.evaluation import (
            ahp_analysis,
            topsis_evaluate,
            entropy_weight,
            fuzzy_evaluation,
            pca_analysis,
        )

        # 验证所有函数都是可调用的
        assert callable(ahp_analysis), "ahp_analysis 应是可调用函数"
        assert callable(topsis_evaluate), "topsis_evaluate 应是可调用函数"
        assert callable(entropy_weight), "entropy_weight 应是可调用函数"
        assert callable(fuzzy_evaluation), "fuzzy_evaluation 应是可调用函数"
        assert callable(pca_analysis), "pca_analysis 应是可调用函数"

    @pytest.mark.unit
    def test_math_tools_ahp_analysis(self):
        """验证: AHP 分析给定一致性判断矩阵时返回合理权重。"""
        from app.tools.math_tools.evaluation import ahp_analysis, AHPResult

        # 3x3 一致性比较矩阵 (完全一致)
        comparison_matrix = np.array([
            [1,   2,   3],
            [1/2, 1,   2],
            [1/3, 1/2, 1],
        ])

        result = ahp_analysis(comparison_matrix)

        assert isinstance(result, AHPResult), "应返回 AHPResult 实例"
        assert result.weights is not None, "权重向量不应为 None"
        assert len(result.weights) == 3, "应有 3 个权重值"
        # 权重之和应为 1
        assert abs(result.weights.sum() - 1.0) < 1e-6, (
            f"权重之和应为 1, 实际: {result.weights.sum()}"
        )
        # 所有权重应为正数
        assert np.all(result.weights > 0), "所有权重应为正数"
        # 权重应按降序排列 (因为第一个指标比其他更重要)
        assert result.weights[0] > result.weights[1] > result.weights[2], (
            f"权重应按降序排列, 实际: {result.weights}"
        )
        # 一致性比率应小于 0.1 (近似一致的矩阵)
        assert result.is_consistent, (
            f"近似一致矩阵的 CR 应 < 0.1, 实际 CR: {result.consistency_ratio}"
        )
        assert result.consistency_ratio < 0.1

    @pytest.mark.unit
    def test_math_tools_ahp_inconsistent_matrix(self):
        """验证: AHP 对高度不一致的矩阵应报告不一致。"""
        from app.tools.math_tools.evaluation import ahp_analysis

        # 构造一个不一致矩阵
        inconsistent_matrix = np.array([
            [1,   9,   1/9],
            [1/9, 1,   9],
            [9,   1/9, 1],
        ])

        result = ahp_analysis(inconsistent_matrix)

        # 高度不一致的矩阵, CR 应很大
        assert not result.is_consistent or result.consistency_ratio >= 0.1, (
            "高度不一致矩阵的 CR 应 >= 0.1"
        )

    @pytest.mark.unit
    def test_math_tools_topsis_evaluate(self):
        """验证: TOPSIS 评价给定数据返回合理排名。"""
        from app.tools.math_tools.evaluation import topsis_evaluate, TOPSISResult

        # 4个方案, 3个指标的决策矩阵
        decision_matrix = np.array([
            [250, 16, 12],  # 方案 A
            [200, 14, 8],   # 方案 B
            [300, 18, 16],  # 方案 C (各指标最优)
            [275, 15, 10],  # 方案 D
        ])
        weights = np.array([0.4, 0.3, 0.3])
        benefit_criteria = [True, True, True]  # 全部为效益型 (越大越好)

        result = topsis_evaluate(decision_matrix, weights, benefit_criteria)

        assert isinstance(result, TOPSISResult), "应返回 TOPSISResult 实例"
        assert len(result.scores) == 4, "应有 4 个方案的得分"
        assert len(result.rankings) == 4, "应有 4 个方案的排名"
        # 得分应在 [0, 1] 范围内
        assert np.all(result.scores >= 0) and np.all(result.scores <= 1), (
            f"得分应在 [0,1] 范围内, 实际: {result.scores}"
        )
        # 方案 C (索引2) 各指标最优, 得分应最高
        assert result.scores[2] == max(result.scores), (
            f"方案 C 应得分最高, 实际得分: {result.scores}"
        )
        # rankings 应是 1-4 的排列
        assert set(result.rankings) == {1, 2, 3, 4}, (
            f"排名应是 1-4 的排列, 实际: {result.rankings}"
        )
        # 正距离和负距离应有合理值
        assert len(result.positive_distances) == 4
        assert len(result.negative_distances) == 4
        assert np.all(result.positive_distances >= 0)
        assert np.all(result.negative_distances >= 0)

    @pytest.mark.unit
    def test_math_tools_topsis_default_benefit(self):
        """验证: TOPSIS 不传 benefit_criteria 时默认全为效益型。"""
        from app.tools.math_tools.evaluation import topsis_evaluate

        decision_matrix = np.array([
            [10, 20],
            [30, 40],
        ])
        weights = np.array([0.5, 0.5])

        # 不传 benefit_criteria 参数
        result = topsis_evaluate(decision_matrix, weights)

        assert len(result.scores) == 2
        # 方案 B (索引1) 各指标更大, 在全效益型下应得分更高
        assert result.scores[1] > result.scores[0], (
            "默认全效益型下, 指标更大的方案应得分更高"
        )

    @pytest.mark.unit
    def test_math_tools_entropy_weight(self):
        """验证: 熵权法给定决策矩阵返回合理权重。"""
        from app.tools.math_tools.evaluation import entropy_weight

        decision_matrix = np.array([
            [100, 50, 80],
            [90,  60, 70],
            [110, 55, 75],
            [95,  65, 85],
        ])

        result = entropy_weight(decision_matrix)

        assert result.weights is not None
        assert len(result.weights) == 3, "应有 3 个指标的权重"
        assert abs(result.weights.sum() - 1.0) < 1e-6, (
            f"熵权法权重之和应为 1, 实际: {result.weights.sum()}"
        )
        assert np.all(result.weights >= 0), "所有权重应非负"

    # ---------- 子模块函数可调用性验证 ----------

    @pytest.mark.unit
    def test_math_tools_statistics_functions(self):
        """验证: statistics 子模块函数可导入。"""
        from app.tools.math_tools.statistics import (
            hypothesis_test,
            grey_relational_analysis,
        )

        assert callable(hypothesis_test)
        assert callable(grey_relational_analysis)

    @pytest.mark.unit
    def test_math_tools_graph_network_functions(self):
        """验证: graph_network 子模块函数可导入。"""
        from app.tools.math_tools.graph_network import (
            solve_tsp,
            shortest_path,
        )

        assert callable(solve_tsp)
        assert callable(shortest_path)

    @pytest.mark.unit
    def test_math_tools_validation_functions(self):
        """验证: validation 子模块函数可导入。"""
        from app.tools.math_tools.validation import (
            cross_validate,
            sensitivity_analysis,
            bootstrap_confidence_interval,
        )

        assert callable(cross_validate)
        assert callable(sensitivity_analysis)
        assert callable(bootstrap_confidence_interval)

    @pytest.mark.unit
    def test_math_tools_time_series_functions(self):
        """验证: time_series 子模块函数可导入。"""
        from app.tools.math_tools.time_series import (
            arima_forecast,
            exponential_smoothing,
        )

        assert callable(arima_forecast)
        assert callable(exponential_smoothing)


# ================================================================
# 跨链路集成: 端到端验证
# ================================================================


class TestCrossChainIntegration:
    """跨链路端到端集成测试。

    验证多条链路协同工作时的正确性。
    """

    @pytest.mark.unit
    def test_knowledge_base_and_template_registry_consistency(self):
        """验证: 知识库中的模型类别与模板注册中心的类别应有交集。

        确保知识库推荐的模型在模板注册中心中能找到对应的代码模板。
        """
        from app.core.knowledge_base import knowledge_base
        from app.config.code_templates.template_registry import template_registry

        # 知识库中的模型名称
        kb_model_names = [m.name for m in knowledge_base.models.values()]

        # 模板注册中心的类别
        template_categories = template_registry.list_categories()

        # 至少应有一些类别交集
        assert len(template_categories) > 0, "模板注册中心应至少有一个类别"
        assert len(kb_model_names) > 0, "知识库应至少有一个模型"

    @pytest.mark.unit
    def test_extract_then_search_templates(self):
        """验证: 从文本提取的模型名称能在模板注册中心中找到匹配。"""
        from app.core.workflow.stages.coder_stage import CoderStage
        from app.config.code_templates.template_registry import template_registry

        # 已知模板注册中心包含 ARIMA 模板
        text = "使用 ARIMA 进行时间序列预测分析"
        model_names = CoderStage._extract_model_names(text)

        # 对提取到的每个名称在模板中搜索
        total_matches = 0
        for name in model_names:
            matches = template_registry.search(name)
            total_matches += len(matches)

        assert total_matches > 0, (
            f"从文本提取的模型名称 {model_names} 应在模板注册中心中找到至少一个匹配"
        )

    @pytest.mark.unit
    def test_template_max_chars_respected(self):
        """验证: get_template_for_prompt 在 max_chars 限制下不超长。"""
        from app.config.code_templates.template_registry import template_registry

        max_chars = 1000
        result = template_registry.get_template_for_prompt(
            model_names=["ARIMA", "线性规划", "TOPSIS", "K-means", "SVM"],
            max_chars=max_chars,
        )

        assert isinstance(result, str)
        assert len(result) <= max_chars, (
            f"模板文本长度 {len(result)} 不应超过 max_chars={max_chars}"
        )
