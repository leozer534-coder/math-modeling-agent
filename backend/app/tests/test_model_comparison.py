"""
多模型对比分析功能测试模块

覆盖范围：
- TestMetricsExtraction: 从代码输出中提取评估指标
- TestMultiModelExtraction: 从代码输出中解析多模型结果
- TestComparisonTable: Markdown 对比表格生成
- TestBaselineImprovement: 改进幅度计算
- TestBestModelDetermination: 最优模型选择
- TestOverallRanking: 全局模型排名
- TestComparisonSummary: 对比总结生成
- TestSchemaBackwardCompat: 新 Schema 向后兼容性
- TestFlowsSequenceUpdate: Flows 序列更新验证
- TestWriterTaskDesc: Writer 任务描述映射更新
"""



# ============================================================
# 指标提取测试
# ============================================================


class TestMetricsExtraction:
    """测试从代码输出中提取评估指标"""

    def test_extract_r2_standard(self):
        """测试提取标准 R² 格式"""
        from app.core.flows import Flows

        output = "模型评估结果:\nR² = 0.9523\nRMSE = 0.1234"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "R²" in metrics
        assert abs(metrics["R²"] - 0.9523) < 1e-6

    def test_extract_r2_variants(self):
        """测试 R² 的多种写法（R2, r2_score）"""
        from app.core.flows import Flows

        output1 = "R2 = 0.85"
        metrics1 = Flows.extract_metrics_from_code_output(output1)
        assert "R²" in metrics1
        assert abs(metrics1["R²"] - 0.85) < 1e-6

        output2 = "r2_score: 0.92"
        metrics2 = Flows.extract_metrics_from_code_output(output2)
        assert "R²" in metrics2
        assert abs(metrics2["R²"] - 0.92) < 1e-6

    def test_extract_rmse(self):
        """测试提取 RMSE"""
        from app.core.flows import Flows

        output = "RMSE = 0.0456"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "RMSE" in metrics
        assert abs(metrics["RMSE"] - 0.0456) < 1e-6

    def test_extract_mae(self):
        """测试提取 MAE"""
        from app.core.flows import Flows

        output = "MAE: 0.032"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "MAE" in metrics
        assert abs(metrics["MAE"] - 0.032) < 1e-6

    def test_extract_accuracy_english(self):
        """测试提取英文 Accuracy"""
        from app.core.flows import Flows

        output = "Accuracy = 0.9876"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "Accuracy" in metrics
        assert abs(metrics["Accuracy"] - 0.9876) < 1e-6

    def test_extract_accuracy_chinese(self):
        """测试提取中文准确率"""
        from app.core.flows import Flows

        output = "准确率：0.95"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "Accuracy" in metrics
        assert abs(metrics["Accuracy"] - 0.95) < 1e-6

    def test_extract_f1_score(self):
        """测试提取 F1-Score"""
        from app.core.flows import Flows

        output = "F1_Score = 0.88"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "F1" in metrics
        assert abs(metrics["F1"] - 0.88) < 1e-6

    def test_extract_multiple_metrics(self):
        """测试同时提取多个指标"""
        from app.core.flows import Flows

        output = """
模型评估结果:
R² = 0.95
RMSE = 0.12
MAE = 0.08
MSE = 0.0144
MAPE = 3.5
Accuracy = 0.92
F1 = 0.89
AUC = 0.96
"""
        metrics = Flows.extract_metrics_from_code_output(output)
        assert len(metrics) >= 7
        assert "R²" in metrics
        assert "RMSE" in metrics
        assert "MAE" in metrics
        assert "MSE" in metrics
        assert "Accuracy" in metrics
        assert "F1" in metrics
        assert "AUC" in metrics

    def test_extract_empty_output(self):
        """测试空输出返回空字典"""
        from app.core.flows import Flows

        assert Flows.extract_metrics_from_code_output("") == {}
        assert Flows.extract_metrics_from_code_output(None) == {}

    def test_extract_no_metrics(self):
        """测试无指标文本返回空字典"""
        from app.core.flows import Flows

        output = "代码执行完成，生成了数据可视化图表。"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert metrics == {}

    def test_extract_chinese_colon(self):
        """测试中文冒号分隔符"""
        from app.core.flows import Flows

        output = "R²：0.87\nRMSE：0.15"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "R²" in metrics
        assert "RMSE" in metrics

    def test_extract_silhouette(self):
        """测试提取轮廓系数"""
        from app.core.flows import Flows

        output = "轮廓系数: 0.72"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "Silhouette" in metrics
        assert abs(metrics["Silhouette"] - 0.72) < 1e-6

    def test_extract_negative_value(self):
        """测试提取负数值（如负 R²）"""
        from app.core.flows import Flows

        output = "R² = -0.05"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert "R²" in metrics
        assert abs(metrics["R²"] - (-0.05)) < 1e-6

    def test_first_match_wins(self):
        """测试同一指标多次出现时取第一个值"""
        from app.core.flows import Flows

        output = "R² = 0.85\n其他信息...\nR² = 0.92"
        metrics = Flows.extract_metrics_from_code_output(output)
        assert abs(metrics["R²"] - 0.85) < 1e-6


# ============================================================
# 多模型结果解析测试
# ============================================================


class TestMultiModelExtraction:
    """测试从代码输出中解析多模型结果"""

    def test_extract_model_pattern(self):
        """测试 'Model: name' 模式的解析"""
        from app.core.math_model_workflow import MathModelWorkFlow

        output = """
Model: LinearRegression
R² = 0.85
RMSE = 0.12

Model: XGBoost
R² = 0.92
RMSE = 0.08
"""
        models = MathModelWorkFlow._extract_multi_model_results(output)
        assert len(models) >= 2
        names = [m["name"] for m in models]
        assert "LinearRegression" in names
        assert "XGBoost" in names

    def test_extract_chinese_model_pattern(self):
        """测试中文 '模型: name' 模式"""
        from app.core.math_model_workflow import MathModelWorkFlow

        output = """
模型: 线性回归
R² = 0.80
RMSE = 0.15
"""
        models = MathModelWorkFlow._extract_multi_model_results(output)
        assert len(models) >= 1
        assert models[0]["name"] == "线性回归"

    def test_extract_separator_block_pattern(self):
        """测试 '=== ModelName ===' 分块模式"""
        from app.core.math_model_workflow import MathModelWorkFlow

        output = """
=== RandomForest ===
R² = 0.88
RMSE = 0.10

=== GradientBoosting ===
R² = 0.91
RMSE = 0.09
"""
        models = MathModelWorkFlow._extract_multi_model_results(output)
        assert len(models) >= 2
        names = [m["name"] for m in models]
        assert "RandomForest" in names
        assert "GradientBoosting" in names

    def test_extract_empty_output(self):
        """测试空输出返回空列表"""
        from app.core.math_model_workflow import MathModelWorkFlow

        assert MathModelWorkFlow._extract_multi_model_results("") == []
        assert MathModelWorkFlow._extract_multi_model_results(None) == []

    def test_extract_no_model_blocks(self):
        """测试无模型块的输出"""
        from app.core.math_model_workflow import MathModelWorkFlow

        output = "数据处理完成，共读取 1000 行数据。"
        models = MathModelWorkFlow._extract_multi_model_results(output)
        assert models == []


# ============================================================
# 对比表格生成测试
# ============================================================


class TestComparisonTable:
    """测试 Markdown 对比表格生成"""

    def test_basic_table(self):
        """测试基础表格生成"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "线性回归": {"R²": 0.85, "RMSE": 0.12},
            "XGBoost": {"R²": 0.92, "RMSE": 0.08},
        }
        table = MathModelWorkFlow._generate_comparison_table(metrics_dict, "ques1")

        assert "| 模型 |" in table
        assert "线性回归" in table
        assert "XGBoost" in table
        assert "0.8500" in table
        assert "0.9200" in table

    def test_single_model_table(self):
        """测试单模型表格"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "默认模型": {"Accuracy": 0.95},
        }
        table = MathModelWorkFlow._generate_comparison_table(metrics_dict, "ques1")
        assert "默认模型" in table
        assert "0.9500" in table

    def test_empty_metrics(self):
        """测试空指标返回空字符串"""
        from app.core.math_model_workflow import MathModelWorkFlow

        table = MathModelWorkFlow._generate_comparison_table({}, "ques1")
        assert table == ""

    def test_missing_metrics_show_dash(self):
        """测试缺失指标显示 '-'"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "ModelA": {"R²": 0.85, "RMSE": 0.12},
            "ModelB": {"R²": 0.90},  # 缺少 RMSE
        }
        table = MathModelWorkFlow._generate_comparison_table(metrics_dict, "ques1")
        assert "-" in table

    def test_table_has_header_and_separator(self):
        """测试表格包含表头和分隔行"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "A": {"R²": 0.9},
        }
        table = MathModelWorkFlow._generate_comparison_table(metrics_dict, "ques1")
        lines = [line for line in table.strip().split("\n") if line.strip()]
        assert len(lines) >= 3  # 表头 + 分隔 + 至少一行数据
        assert "|---" in lines[1]


# ============================================================
# 改进幅度计算测试
# ============================================================


class TestBaselineImprovement:
    """测试改进幅度计算"""

    def test_basic_improvement(self):
        """测试基本改进幅度计算"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "Baseline": {"R²": 0.80, "RMSE": 0.20},
            "Improved": {"R²": 0.92, "RMSE": 0.10},
        }
        result = MathModelWorkFlow._compute_baseline_improvement(metrics_dict)
        assert result is not None
        # R² 改进: (0.92 - 0.80) / 0.80 = 0.15
        assert abs(result["R²"] - 0.15) < 1e-4
        # RMSE 改进: (0.10 - 0.20) / 0.20 = -0.5
        assert abs(result["RMSE"] - (-0.5)) < 1e-4

    def test_single_model_returns_none(self):
        """测试单模型返回 None"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "OnlyModel": {"R²": 0.85},
        }
        result = MathModelWorkFlow._compute_baseline_improvement(metrics_dict)
        assert result is None

    def test_empty_metrics_returns_none(self):
        """测试空输入返回 None"""
        from app.core.math_model_workflow import MathModelWorkFlow

        result = MathModelWorkFlow._compute_baseline_improvement({})
        assert result is None

    def test_zero_baseline_value(self):
        """测试基线值为 0 的情况（避免除零）"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "Baseline": {"R²": 0.0},
            "Improved": {"R²": 0.85},
        }
        result = MathModelWorkFlow._compute_baseline_improvement(metrics_dict)
        assert result is not None
        # 基线为 0 时使用绝对差值
        assert abs(result["R²"] - 0.85) < 1e-4

    def test_three_models_uses_first_and_last(self):
        """测试三个模型时使用第一个和最后一个对比"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "Baseline": {"R²": 0.70},
            "Improved": {"R²": 0.85},
            "Innovative": {"R²": 0.95},
        }
        result = MathModelWorkFlow._compute_baseline_improvement(metrics_dict)
        assert result is not None
        # (0.95 - 0.70) / 0.70 ≈ 0.3571
        assert abs(result["R²"] - 0.3571) < 1e-3


# ============================================================
# 最优模型选择测试
# ============================================================


class TestBestModelDetermination:
    """测试最优模型选择逻辑"""

    def test_best_by_r2(self):
        """测试按 R² 选择最优"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "ModelA": {"R²": 0.85},
            "ModelB": {"R²": 0.92},
        }
        best = MathModelWorkFlow._determine_best_model(metrics_dict)
        assert best == "ModelB"

    def test_best_by_accuracy(self):
        """测试无 R² 时按 Accuracy 选择"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "ModelA": {"Accuracy": 0.90},
            "ModelB": {"Accuracy": 0.95},
        }
        best = MathModelWorkFlow._determine_best_model(metrics_dict)
        assert best == "ModelB"

    def test_best_by_negative_rmse(self):
        """测试仅有 RMSE 时选择最小值"""
        from app.core.math_model_workflow import MathModelWorkFlow

        metrics_dict = {
            "ModelA": {"RMSE": 0.15},
            "ModelB": {"RMSE": 0.08},
        }
        best = MathModelWorkFlow._determine_best_model(metrics_dict)
        assert best == "ModelB"  # RMSE 越小越好，-0.08 > -0.15

    def test_empty_returns_none(self):
        """测试空输入返回 None"""
        from app.core.math_model_workflow import MathModelWorkFlow

        best = MathModelWorkFlow._determine_best_model({})
        assert best is None


# ============================================================
# 全局排名测试
# ============================================================


class TestOverallRanking:
    """测试全局模型排名"""

    def test_basic_ranking(self):
        """测试基本排名（按平均得分降序）"""
        from app.core.math_model_workflow import MathModelWorkFlow

        model_scores = {
            "ModelA": [0.85, 0.80],
            "ModelB": [0.92, 0.90],
            "ModelC": [0.88, 0.87],
        }
        ranking = MathModelWorkFlow._compute_overall_ranking(model_scores)
        assert ranking is not None
        assert ranking[0] == "ModelB"  # 均分 0.91
        assert ranking[1] == "ModelC"  # 均分 0.875
        assert ranking[2] == "ModelA"  # 均分 0.825

    def test_empty_scores_returns_none(self):
        """测试空输入返回 None"""
        from app.core.math_model_workflow import MathModelWorkFlow

        assert MathModelWorkFlow._compute_overall_ranking({}) is None

    def test_single_model(self):
        """测试单模型排名"""
        from app.core.math_model_workflow import MathModelWorkFlow

        model_scores = {"OnlyModel": [0.90]}
        ranking = MathModelWorkFlow._compute_overall_ranking(model_scores)
        assert ranking == ["OnlyModel"]


# ============================================================
# 对比总结生成测试
# ============================================================


class TestComparisonSummary:
    """测试对比总结文本生成"""

    def test_basic_summary(self):
        """测试基本总结生成"""
        from app.core.math_model_workflow import MathModelWorkFlow
        from app.schemas.A2A import ModelComparisonEntry

        entries = [
            ModelComparisonEntry(
                question_key="ques1",
                models_evaluated=["线性回归", "XGBoost"],
                best_model="XGBoost",
            ),
        ]
        summary = MathModelWorkFlow._generate_comparison_summary(
            entries, ["XGBoost", "线性回归"]
        )
        assert "1 个问题" in summary
        assert "XGBoost" in summary
        assert "线性回归" in summary

    def test_empty_entries(self):
        """测试空列表生成默认提示"""
        from app.core.math_model_workflow import MathModelWorkFlow

        summary = MathModelWorkFlow._generate_comparison_summary([], None)
        assert "未能提取" in summary

    def test_summary_with_ranking(self):
        """测试包含全局排名的总结"""
        from app.core.math_model_workflow import MathModelWorkFlow
        from app.schemas.A2A import ModelComparisonEntry

        entries = [
            ModelComparisonEntry(
                question_key="ques1",
                models_evaluated=["A", "B"],
                best_model="B",
            ),
        ]
        summary = MathModelWorkFlow._generate_comparison_summary(
            entries, ["B", "A"]
        )
        assert "综合排名" in summary
        assert "B > A" in summary


# ============================================================
# Schema 向后兼容测试
# ============================================================


class TestSchemaBackwardCompat:
    """测试新 Schema 的向后兼容性"""

    def test_model_comparison_entry_optional_fields(self):
        """测试 ModelComparisonEntry 所有可选字段默认 None"""
        from app.schemas.A2A import ModelComparisonEntry

        entry = ModelComparisonEntry(question_key="ques1")
        assert entry.question_key == "ques1"
        assert entry.models_evaluated == []
        assert entry.best_model is None
        assert entry.improvement_over_baseline is None
        assert entry.comparison_table_markdown is None
        assert entry.metrics is None

    def test_model_comparison_result_optional_fields(self):
        """测试 ModelComparisonResult 所有可选字段默认值"""
        from app.schemas.A2A import ModelComparisonResult

        result = ModelComparisonResult()
        assert result.per_question == []
        assert result.overall_ranking is None
        assert result.comparison_summary is None
        assert result.evaluation_metrics_used == []

    def test_model_comparison_result_serialization(self):
        """测试 ModelComparisonResult JSON 序列化/反序列化"""
        from app.schemas.A2A import ModelComparisonEntry, ModelComparisonResult

        result = ModelComparisonResult(
            per_question=[
                ModelComparisonEntry(
                    question_key="ques1",
                    models_evaluated=["A", "B"],
                    best_model="B",
                    improvement_over_baseline={"R²": 0.15},
                )
            ],
            overall_ranking=["B", "A"],
            comparison_summary="B 优于 A",
            evaluation_metrics_used=["R²", "RMSE"],
        )
        json_data = result.model_dump()
        restored = ModelComparisonResult(**json_data)
        assert restored.per_question[0].question_key == "ques1"
        assert restored.overall_ranking == ["B", "A"]

    def test_question_solution_backward_compat(self):
        """测试 QuestionSolution 新增字段不影响旧数据"""
        from app.schemas.tool_result import QuestionSolution

        # 不传新字段 — 模拟旧数据
        sol = QuestionSolution(description="测试方案")
        assert sol.alternative_models is None
        assert sol.baseline_model is None
        assert sol.improvement_model is None
        assert sol.innovation_model is None

    def test_question_solution_to_text_with_models(self):
        """测试 QuestionSolution.to_text() 包含模型信息"""
        from app.schemas.tool_result import QuestionSolution

        sol = QuestionSolution(
            description="线性规划方案",
            baseline_model="线性回归",
            improvement_model="XGBoost",
            innovation_model="Transformer",
            alternative_models=["随机森林", "SVM"],
        )
        text = sol.to_text()
        assert "基线模型: 线性回归" in text
        assert "改进模型: XGBoost" in text
        assert "创新模型: Transformer" in text
        assert "备选模型: 随机森林, SVM" in text

    def test_question_solution_to_text_without_models(self):
        """测试不含模型信息时 to_text() 不输出多余内容"""
        from app.schemas.tool_result import QuestionSolution

        sol = QuestionSolution(description="测试方案")
        text = sol.to_text()
        assert "基线模型" not in text
        assert "改进模型" not in text


# ============================================================
# Flows 序列更新验证
# ============================================================


class TestFlowsSequenceUpdate:
    """测试 Flows 流程序列中 model_comparison 的正确位置"""

    def test_flow_suffix_contains_model_comparison(self):
        """测试 _FLOW_SUFFIX 包含 model_comparison"""
        from app.core.flows import Flows

        assert "model_comparison" in Flows._FLOW_SUFFIX

    def test_flow_suffix_order(self):
        """测试 model_comparison 在 sensitivity_analysis 之后"""
        from app.core.flows import Flows

        suffix = Flows._FLOW_SUFFIX
        sa_idx = suffix.index("sensitivity_analysis")
        mc_idx = suffix.index("model_comparison")
        judge_idx = suffix.index("judge")

        assert sa_idx < mc_idx < judge_idx

    def test_set_flows_includes_model_comparison(self):
        """测试 set_flows 生成的流程包含 model_comparison"""
        from app.core.flows import Flows

        flows = Flows(questions={"ques1": "问题1", "ques_count": 1})
        flows.set_flows(ques_count=1)

        assert "model_comparison" in flows.flows

    def test_set_flows_model_comparison_order(self):
        """测试 model_comparison 在生成的流程中的位置正确"""
        from app.core.flows import Flows

        flows = Flows(questions={"ques1": "q1", "ques_count": 1})
        flows.set_flows(ques_count=1)

        keys = list(flows.flows.keys())
        sa_idx = keys.index("sensitivity_analysis")
        mc_idx = keys.index("model_comparison")
        judge_idx = keys.index("judge")

        assert sa_idx < mc_idx < judge_idx


class TestWriterTaskDesc:
    """测试 Writer 任务描述映射更新"""

    def test_model_comparison_in_writer_task_desc(self):
        """测试 WRITER_TASK_DESC 包含 model_comparison"""
        from app.core.flows import Flows

        assert "model_comparison" in Flows.WRITER_TASK_DESC
        assert "多模型对比" in Flows.WRITER_TASK_DESC["model_comparison"]


# ============================================================
# 检查点阶段列表测试
# ============================================================


class TestCheckpointStages:
    """测试检查点工作流阶段列表更新"""

    def test_model_comparison_in_stages(self):
        """测试 STANDARD_WORKFLOW_STAGES 包含 model_comparison"""
        from app.core.workflow.checkpoint_manager import STANDARD_WORKFLOW_STAGES

        assert "model_comparison" in STANDARD_WORKFLOW_STAGES

    def test_model_comparison_stage_order(self):
        """测试 model_comparison 在 sensitivity 和 write 之间"""
        from app.core.workflow.checkpoint_manager import STANDARD_WORKFLOW_STAGES

        sa_idx = STANDARD_WORKFLOW_STAGES.index("sensitivity")
        mc_idx = STANDARD_WORKFLOW_STAGES.index("model_comparison")
        wr_idx = STANDARD_WORKFLOW_STAGES.index("write")

        assert sa_idx < mc_idx < wr_idx


# ============================================================
# FormatComparisonForWriter 测试
# ============================================================


class TestFormatComparisonForWriter:
    """测试格式化对比数据给 Writer"""

    def test_format_with_full_data(self):
        """测试完整数据的格式化"""
        from app.core.math_model_workflow import MathModelWorkFlow
        from app.schemas.A2A import ModelComparisonEntry, ModelComparisonResult

        result = ModelComparisonResult(
            per_question=[
                ModelComparisonEntry(
                    question_key="ques1",
                    models_evaluated=["A", "B"],
                    best_model="B",
                    improvement_over_baseline={"R²": 0.15},
                    comparison_table_markdown="| 模型 | R² |\n|---|---|\n| A | 0.80 |\n| B | 0.92 |",
                )
            ],
            overall_ranking=["B", "A"],
            comparison_summary="B 表现最优",
        )
        text = MathModelWorkFlow._format_comparison_for_writer(result)

        assert "多模型对比分析数据" in text
        assert "ques1" in text
        assert "最优模型" in text
        assert "B" in text
        assert "综合模型排名" in text
        assert "B > A" in text

    def test_format_empty_result(self):
        """测试空结果返回空字符串"""
        from app.core.math_model_workflow import MathModelWorkFlow

        assert MathModelWorkFlow._format_comparison_for_writer(None) == ""

    def test_format_minimal_data(self):
        """测试最小数据的格式化"""
        from app.core.math_model_workflow import MathModelWorkFlow
        from app.schemas.A2A import ModelComparisonResult

        result = ModelComparisonResult()
        text = MathModelWorkFlow._format_comparison_for_writer(result)
        assert "多模型对比分析数据" in text
