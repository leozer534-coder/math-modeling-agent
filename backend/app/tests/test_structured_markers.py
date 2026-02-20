"""
结构化标记解析器测试模块。

覆盖 Flows 类中三个静态方法:
  - extract_metrics_from_code_output()
  - extract_figures_from_code_output()
  - extract_result_summaries()
"""

import pytest

from app.core.flows import Flows


# ================== TestExtractMetrics ==================


class TestExtractMetrics:
    """extract_metrics_from_code_output 测试集。"""

    @pytest.mark.unit
    def test_extract_metrics_from_marker_block(self):
        """验证: 包含 METRICS 标记块时，正确提取 R2、RMSE、MAE。"""
        code_output = (
            "模型训练完成\n"
            "===METRICS_START===\n"
            "R2: 0.95\n"
            "RMSE: 1.23\n"
            "MAE: 0.87\n"
            "===METRICS_END===\n"
            "任务结束"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result == {"R2": 0.95, "RMSE": 1.23, "MAE": 0.87}

    @pytest.mark.unit
    def test_extract_metrics_fallback_to_regex(self):
        """验证: 无标记块时，降级到正则提取传统 print 格式的指标。"""
        code_output = (
            "训练结果:\n"
            "R2: 0.92\n"
            "RMSE: 2.15\n"
            "MAE: 1.05\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        # 正则模式将 R2 标准化为 "R\u00b2"
        assert result["R\u00b2"] == 0.92
        assert result["RMSE"] == 2.15
        assert result["MAE"] == 1.05

    @pytest.mark.unit
    def test_extract_metrics_marker_priority(self):
        """验证: 同时存在标记块和散布文本时，标记块优先。"""
        code_output = (
            "散布的指标 R2: 0.50\n"
            "RMSE = 9.99\n"
            "===METRICS_START===\n"
            "R2: 0.95\n"
            "RMSE: 1.23\n"
            "===METRICS_END===\n"
            "另一个散布的 MAE: 5.00\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        # 标记块存在且非空，应使用标记块的值，忽略散布文本
        assert result == {"R2": 0.95, "RMSE": 1.23}
        # 散布文本中的 MAE 不应被提取（因为标记块已返回有效结果）
        assert "MAE" not in result

    @pytest.mark.unit
    def test_extract_metrics_multiple_blocks(self):
        """验证: 多个 METRICS 标记块时，全部合并。"""
        code_output = (
            "===METRICS_START===\n"
            "R2: 0.91\n"
            "RMSE: 1.50\n"
            "===METRICS_END===\n"
            "中间输出...\n"
            "===METRICS_START===\n"
            "MAE: 0.78\n"
            "MSE: 2.34\n"
            "===METRICS_END===\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result["R2"] == 0.91
        assert result["RMSE"] == 1.50
        assert result["MAE"] == 0.78
        assert result["MSE"] == 2.34
        assert len(result) == 4

    @pytest.mark.unit
    def test_extract_metrics_multiple_blocks_first_wins(self):
        """验证: 多个标记块中出现重复指标名时，首次出现的值优先。"""
        code_output = (
            "===METRICS_START===\n"
            "R2: 0.91\n"
            "===METRICS_END===\n"
            "===METRICS_START===\n"
            "R2: 0.99\n"
            "===METRICS_END===\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        # 第一个块中的 R2=0.91 应被保留
        assert result["R2"] == 0.91

    @pytest.mark.unit
    def test_extract_metrics_empty_string(self):
        """验证: 空字符串输入返回空字典。"""
        result = Flows.extract_metrics_from_code_output("")
        assert result == {}

    @pytest.mark.unit
    def test_extract_metrics_none(self):
        """验证: None 输入返回空字典。"""
        result = Flows.extract_metrics_from_code_output(None)
        assert result == {}

    @pytest.mark.unit
    def test_extract_metrics_malformed_block(self):
        """验证: 标记块内格式不规范（缺少数值）时不崩溃，跳过无效行。"""
        code_output = (
            "===METRICS_START===\n"
            "R2:\n"                     # 缺少数值
            "RMSE: abc\n"               # 非数字
            "MAE: 0.87\n"               # 有效行
            "这是一行无关文字\n"          # 不匹配格式
            "===METRICS_END===\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        # 只有 MAE 被成功提取
        assert result == {"MAE": 0.87}

    @pytest.mark.unit
    def test_extract_metrics_equals_separator(self):
        """验证: 标记块内使用等号分隔符也能正确提取。"""
        code_output = (
            "===METRICS_START===\n"
            "R2 = 0.88\n"
            "RMSE = 3.14\n"
            "===METRICS_END===\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result == {"R2": 0.88, "RMSE": 3.14}

    @pytest.mark.unit
    def test_extract_metrics_chinese_colon_separator(self):
        """验证: 标记块内使用中文冒号也能正确提取。"""
        code_output = (
            "===METRICS_START===\n"
            "R2\uff1a0.88\n"
            "RMSE\uff1a3.14\n"
            "===METRICS_END===\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result == {"R2": 0.88, "RMSE": 3.14}

    @pytest.mark.unit
    def test_extract_metrics_negative_values(self):
        """验证: 负数指标值能正确提取。"""
        code_output = (
            "===METRICS_START===\n"
            "R2: -0.15\n"
            "===METRICS_END===\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result == {"R2": -0.15}

    @pytest.mark.unit
    def test_extract_metrics_regex_various_patterns(self):
        """验证: 降级正则能识别多种指标格式（Accuracy、F1、AUC 等）。"""
        code_output = (
            "Accuracy: 0.96\n"
            "F1-Score: 0.89\n"
            "AUC: 0.93\n"
            "Precision: 0.91\n"
            "Recall: 0.87\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result["Accuracy"] == 0.96
        assert result["F1"] == 0.89
        assert result["AUC"] == 0.93
        assert result["Precision"] == 0.91
        assert result["Recall"] == 0.87

    @pytest.mark.unit
    def test_extract_metrics_regex_chinese_names(self):
        """验证: 降级正则能识别中文指标名（准确率、精确率、召回率等）。"""
        code_output = (
            "准确率: 0.95\n"
            "精确率: 0.92\n"
            "召回率: 0.88\n"
            "轮廓系数: 0.73\n"
        )

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result["Accuracy"] == 0.95
        assert result["Precision"] == 0.92
        assert result["Recall"] == 0.88
        assert result["Silhouette"] == 0.73

    @pytest.mark.unit
    def test_extract_metrics_no_match(self):
        """验证: 输出中无任何指标信息时返回空字典。"""
        code_output = "模型训练完成，没有任何数字输出。"

        result = Flows.extract_metrics_from_code_output(code_output)

        assert result == {}


# ================== TestExtractFigures ==================


class TestExtractFigures:
    """extract_figures_from_code_output 测试集。"""

    @pytest.mark.unit
    def test_extract_figures_single(self):
        """验证: 单个 FIGURE 标记正确提取文件名和描述。"""
        code_output = (
            "数据分析完成\n"
            "===FIGURE: ques1_heatmap.png | 相关性热力图===\n"
            "任务结束"
        )

        result = Flows.extract_figures_from_code_output(code_output)

        assert len(result) == 1
        assert result[0]["filename"] == "ques1_heatmap.png"
        assert result[0]["description"] == "相关性热力图"

    @pytest.mark.unit
    def test_extract_figures_multiple(self):
        """验证: 多个 FIGURE 标记全部正确提取。"""
        code_output = (
            "===FIGURE: ques1_scatter.png | 散点图===\n"
            "中间输出...\n"
            "===FIGURE: ques2_bar.png | 柱状图===\n"
            "更多输出...\n"
            "===FIGURE: ques3_line.png | 趋势折线图===\n"
        )

        result = Flows.extract_figures_from_code_output(code_output)

        assert len(result) == 3
        assert result[0]["filename"] == "ques1_scatter.png"
        assert result[0]["description"] == "散点图"
        assert result[1]["filename"] == "ques2_bar.png"
        assert result[1]["description"] == "柱状图"
        assert result[2]["filename"] == "ques3_line.png"
        assert result[2]["description"] == "趋势折线图"

    @pytest.mark.unit
    def test_extract_figures_empty(self):
        """验证: 无 FIGURE 标记时返回空列表。"""
        code_output = "模型训练完成，无图表输出。"

        result = Flows.extract_figures_from_code_output(code_output)

        assert result == []

    @pytest.mark.unit
    def test_extract_figures_none_input(self):
        """验证: None 输入返回空列表。"""
        result = Flows.extract_figures_from_code_output(None)
        assert result == []

    @pytest.mark.unit
    def test_extract_figures_empty_string(self):
        """验证: 空字符串输入返回空列表。"""
        result = Flows.extract_figures_from_code_output("")
        assert result == []

    @pytest.mark.unit
    def test_extract_figures_with_spaces(self):
        """验证: 文件名和描述前后有多余空格时自动去除。"""
        code_output = (
            "===FIGURE:   ques1_heatmap.png   |   相关性热力图   ===\n"
        )

        result = Flows.extract_figures_from_code_output(code_output)

        assert len(result) == 1
        assert result[0]["filename"] == "ques1_heatmap.png"
        assert result[0]["description"] == "相关性热力图"

    @pytest.mark.unit
    def test_extract_figures_complex_filenames(self):
        """验证: 包含路径和特殊字符的文件名能正确提取。"""
        code_output = (
            "===FIGURE: output/model_comparison_v2.png | 多模型对比结果===\n"
        )

        result = Flows.extract_figures_from_code_output(code_output)

        assert len(result) == 1
        assert result[0]["filename"] == "output/model_comparison_v2.png"
        assert result[0]["description"] == "多模型对比结果"


# ================== TestExtractSummaries ==================


class TestExtractSummaries:
    """extract_result_summaries 测试集。"""

    @pytest.mark.unit
    def test_extract_summaries_single(self):
        """验证: 单个 RESULT_SUMMARY 块正确提取问题/模型/结论。"""
        code_output = (
            "计算完成\n"
            "===RESULT_SUMMARY===\n"
            "问题:线性规划求解\n"
            "使用模型:单纯形法\n"
            "主要结论:最优解为 x1=3, x2=5\n"
            "===RESULT_END===\n"
        )

        result = Flows.extract_result_summaries(code_output)

        assert len(result) == 1
        assert result[0]["question"] == "线性规划求解"
        assert result[0]["model"] == "单纯形法"
        assert result[0]["conclusion"] == "最优解为 x1=3, x2=5"

    @pytest.mark.unit
    def test_extract_summaries_multiple(self):
        """验证: 多个 RESULT_SUMMARY 块全部正确提取。"""
        code_output = (
            "===RESULT_SUMMARY===\n"
            "问题:问题一求解\n"
            "使用模型:线性回归\n"
            "主要结论:R2=0.95\n"
            "===RESULT_END===\n"
            "中间输出...\n"
            "===RESULT_SUMMARY===\n"
            "问题:问题二求解\n"
            "使用模型:随机森林\n"
            "主要结论:准确率达到98%\n"
            "===RESULT_END===\n"
        )

        result = Flows.extract_result_summaries(code_output)

        assert len(result) == 2
        assert result[0]["question"] == "问题一求解"
        assert result[0]["model"] == "线性回归"
        assert result[0]["conclusion"] == "R2=0.95"
        assert result[1]["question"] == "问题二求解"
        assert result[1]["model"] == "随机森林"
        assert result[1]["conclusion"] == "准确率达到98%"

    @pytest.mark.unit
    def test_extract_summaries_empty(self):
        """验证: 无 RESULT_SUMMARY 标记时返回空列表。"""
        code_output = "模型训练完成，无摘要输出。"

        result = Flows.extract_result_summaries(code_output)

        assert result == []

    @pytest.mark.unit
    def test_extract_summaries_none_input(self):
        """验证: None 输入返回空列表。"""
        result = Flows.extract_result_summaries(None)
        assert result == []

    @pytest.mark.unit
    def test_extract_summaries_empty_string(self):
        """验证: 空字符串输入返回空列表。"""
        result = Flows.extract_result_summaries("")
        assert result == []

    @pytest.mark.unit
    def test_extract_summaries_partial(self):
        """验证: 摘要块中只有部分字段时不崩溃，返回已有字段。"""
        code_output = (
            "===RESULT_SUMMARY===\n"
            "问题:缺少模型和结论的问题\n"
            "===RESULT_END===\n"
        )

        result = Flows.extract_result_summaries(code_output)

        assert len(result) == 1
        assert result[0]["question"] == "缺少模型和结论的问题"
        assert "model" not in result[0]
        assert "conclusion" not in result[0]

    @pytest.mark.unit
    def test_extract_summaries_chinese_colon(self):
        """验证: 使用中文冒号的字段也能正确提取。"""
        code_output = (
            "===RESULT_SUMMARY===\n"
            "问题\uff1a资源分配优化\n"
            "使用模型\uff1a整数规划\n"
            "主要结论\uff1a最优分配方案使总收益提升30%\n"
            "===RESULT_END===\n"
        )

        result = Flows.extract_result_summaries(code_output)

        assert len(result) == 1
        assert result[0]["question"] == "资源分配优化"
        assert result[0]["model"] == "整数规划"
        assert result[0]["conclusion"] == "最优分配方案使总收益提升30%"

    @pytest.mark.unit
    def test_extract_summaries_mixed_colons(self):
        """验证: 同一块中混用中英文冒号也能正确提取。"""
        code_output = (
            "===RESULT_SUMMARY===\n"
            "问题:聚类分析\n"
            "使用模型\uff1aK-Means\n"
            "主要结论:最佳聚类数为 k=4\n"
            "===RESULT_END===\n"
        )

        result = Flows.extract_result_summaries(code_output)

        assert len(result) == 1
        assert result[0]["question"] == "聚类分析"
        assert result[0]["model"] == "K-Means"
        assert result[0]["conclusion"] == "最佳聚类数为 k=4"

    @pytest.mark.unit
    def test_extract_summaries_empty_block(self):
        """验证: 标记块内全是空行或无关文字时返回空列表。"""
        code_output = (
            "===RESULT_SUMMARY===\n"
            "\n"
            "   \n"
            "===RESULT_END===\n"
        )

        result = Flows.extract_result_summaries(code_output)

        # 块内无有效字段，summary 为空字典，不会被添加
        assert result == []


# ================== TestEndToEnd ==================


class TestEndToEnd:
    """端到端测试: 模拟完整 Coder 输出，验证三个解析函数协同工作。"""

    FULL_CODER_OUTPUT = (
        "======== 代码执行开始 ========\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from sklearn.linear_model import LinearRegression\n"
        "\n"
        "# 加载数据\n"
        "df = pd.read_csv('data.csv')\n"
        "print(f'数据维度: {df.shape}')\n"
        "\n"
        "# 模型训练\n"
        "model = LinearRegression()\n"
        "model.fit(X_train, y_train)\n"
        "\n"
        "# 评估结果\n"
        "===METRICS_START===\n"
        "R2: 0.9521\n"
        "RMSE: 1.2345\n"
        "MAE: 0.8765\n"
        "MSE: 1.524\n"
        "===METRICS_END===\n"
        "\n"
        "# 生成图表\n"
        "===FIGURE: ques1_regression.png | 回归拟合效果图===\n"
        "===FIGURE: ques1_residual.png | 残差分布图===\n"
        "===FIGURE: ques1_feature_importance.png | 特征重要性排序===\n"
        "\n"
        "# 第二个问题的指标\n"
        "===METRICS_START===\n"
        "Accuracy: 0.96\n"
        "F1: 0.93\n"
        "===METRICS_END===\n"
        "\n"
        "===FIGURE: ques2_confusion_matrix.png | 混淆矩阵===\n"
        "\n"
        "# 结果摘要\n"
        "===RESULT_SUMMARY===\n"
        "问题:问题一 - 房价预测\n"
        "使用模型:多元线性回归\n"
        "主要结论:模型 R2=0.95，房屋面积和地段是最重要特征\n"
        "===RESULT_END===\n"
        "\n"
        "===RESULT_SUMMARY===\n"
        "问题\uff1a问题二 - 客户分类\n"
        "使用模型\uff1a随机森林分类器\n"
        "主要结论\uff1a分类准确率达到96%，召回率93%\n"
        "===RESULT_END===\n"
        "\n"
        "======== 代码执行结束 ========\n"
    )

    @pytest.mark.unit
    def test_full_coder_output_parsing(self):
        """验证: 完整 Coder 输出中三个解析函数都能正确提取结果。"""
        # Act
        metrics = Flows.extract_metrics_from_code_output(self.FULL_CODER_OUTPUT)
        figures = Flows.extract_figures_from_code_output(self.FULL_CODER_OUTPUT)
        summaries = Flows.extract_result_summaries(self.FULL_CODER_OUTPUT)

        # Assert - 指标提取（两个 METRICS 块合并）
        assert len(metrics) == 6
        assert metrics["R2"] == 0.9521
        assert metrics["RMSE"] == 1.2345
        assert metrics["MAE"] == 0.8765
        assert metrics["MSE"] == 1.524
        assert metrics["Accuracy"] == 0.96
        assert metrics["F1"] == 0.93

        # Assert - 图表提取（4 个 FIGURE 标记）
        assert len(figures) == 4
        assert figures[0]["filename"] == "ques1_regression.png"
        assert figures[0]["description"] == "回归拟合效果图"
        assert figures[1]["filename"] == "ques1_residual.png"
        assert figures[2]["filename"] == "ques1_feature_importance.png"
        assert figures[3]["filename"] == "ques2_confusion_matrix.png"
        assert figures[3]["description"] == "混淆矩阵"

        # Assert - 结果摘要提取（2 个 RESULT_SUMMARY 块）
        assert len(summaries) == 2
        assert summaries[0]["question"] == "问题一 - 房价预测"
        assert summaries[0]["model"] == "多元线性回归"
        assert "R2=0.95" in summaries[0]["conclusion"]
        assert summaries[1]["question"] == "问题二 - 客户分类"
        assert summaries[1]["model"] == "随机森林分类器"
        assert "96%" in summaries[1]["conclusion"]

    @pytest.mark.unit
    def test_all_parsers_handle_empty_consistently(self):
        """验证: 三个解析函数对空输入的返回值类型一致。"""
        for input_val in ("", None):
            metrics = Flows.extract_metrics_from_code_output(input_val)
            figures = Flows.extract_figures_from_code_output(input_val)
            summaries = Flows.extract_result_summaries(input_val)

            assert isinstance(metrics, dict)
            assert isinstance(figures, list)
            assert isinstance(summaries, list)
            assert len(metrics) == 0
            assert len(figures) == 0
            assert len(summaries) == 0
