from __future__ import annotations

import re

from app.models.user_output import UserOutput
from app.schemas.enums import CompTemplate
from app.tools.base_interpreter import BaseCodeInterpreter
from app.schemas.A2A import ModelerToCoder
from app.utils.log_util import logger


class Flows:
    # 流程序列前缀（论文前置章节）
    _FLOW_PREFIX = (
        "firstPage",
        "RepeatQues",
        "analysisQues",
        "modelAssumption",
        "symbol",
        "eda",
    )

    # 流程序列后缀（论文后置章节）
    _FLOW_SUFFIX = (
        "sensitivity_analysis",
        "model_comparison",
        "judge",
        "conclusion",
    )

    @classmethod
    def _get_flow_suffix(cls, comp_template: CompTemplate | None = None) -> tuple:
        """根据竞赛模板类型返回后缀流程序列。

        MCM/ICM (AMERICAN) 模板包含 innovation_benchmark（Strengths and Weaknesses）章节，
        且 judge 对应 Conclusions，conclusion 对应 Letter to the Decision Maker (Memo)。
        中文模板 (CHINA) 使用默认后缀序列。

        Args:
            comp_template: 竞赛模板类型，None 时使用默认值。

        Returns:
            后缀章节名称的元组。
        """
        if comp_template == CompTemplate.AMERICAN:
            return (
                "sensitivity_analysis",
                "model_comparison",
                "innovation_benchmark",
                "judge",
                "conclusion",
            )
        return cls._FLOW_SUFFIX

    # Writer 任务描述映射
    WRITER_TASK_DESC: dict[str, str] = {
        "firstPage": "撰写标题、摘要、关键词",
        "RepeatQues": "撰写问题重述",
        "analysisQues": "撰写问题分析",
        "modelAssumption": "撰写模型假设",
        "symbol": "撰写符号说明部分",
        "eda": "撰写数据预处理部分",
        "sensitivity_analysis": "撰写灵敏度分析部分",
        "model_comparison": "撰写多模型对比分析部分",
        "innovation_benchmark": "撰写模型优缺点分析部分",
        "judge": "撰写模型评价、改进与推广",
        "conclusion": "撰写结论与建议",
    }

    # 指标提取正则模式：(正则模式, 标准化键名)
    _METRIC_PATTERNS: tuple[tuple[str, str], ...] = (
        (r"(?:R²|R2|r2_score|R\u00b2)\s*[=:：]\s*(-?\d+\.?\d*)", "R²"),
        (r"RMSE\s*[=:：]\s*(-?\d+\.?\d*)", "RMSE"),
        (r"(?:MAE|mae)\s*[=:：]\s*(-?\d+\.?\d*)", "MAE"),
        (r"(?:MSE|mse)\s*[=:：]\s*(-?\d+\.?\d*)", "MSE"),
        (r"(?:MAPE|mape)\s*[=:：]\s*(-?\d+\.?\d*)", "MAPE"),
        (r"(?:Accuracy|accuracy|准确率)\s*[=:：]\s*(-?\d+\.?\d*)", "Accuracy"),
        (r"(?:F1[-_]?[Ss]core|F1)\s*[=:：]\s*(-?\d+\.?\d*)", "F1"),
        (r"(?:AUC|auc)\s*[=:：]\s*(-?\d+\.?\d*)", "AUC"),
        (r"(?:Precision|precision|精确率)\s*[=:：]\s*(-?\d+\.?\d*)", "Precision"),
        (r"(?:Recall|recall|召回率)\s*[=:：]\s*(-?\d+\.?\d*)", "Recall"),
        (r"(?:Silhouette|silhouette|轮廓系数)\s*[=:：]\s*(-?\d+\.?\d*)", "Silhouette"),
    )

    # 结构化输出标记协议（唯一定义点，Coder prompt 和解析器共同引用）
    METRICS_START_MARKER = "===METRICS_START==="
    METRICS_END_MARKER = "===METRICS_END==="
    FIGURE_MARKER_PATTERN = r"===FIGURE:\s*(.+?)\s*\|\s*(.+?)\s*==="
    # 旧格式降级匹配: ===FIGURE===filename.png 或 ===FIGURE===filename.png===
    FIGURE_LEGACY_PATTERN = r"===FIGURE===\s*(.+?\.\w+)\s*(?:===)?"
    RESULT_SUMMARY_START = "===RESULT_SUMMARY==="
    RESULT_SUMMARY_END = "===RESULT_END==="
    TABLE_START_MARKER = "===TABLE_START==="
    TABLE_END_MARKER = "===TABLE_END==="

    def __init__(self, questions: dict[str, str | int]):
        self.flows: dict[str, dict] = {}
        self.questions: dict[str, str | int] = questions

    @classmethod
    def _build_sequence(
        cls,
        ques_count: int,
        comp_template: CompTemplate | None = None,
    ) -> list[str]:
        """构建完整的流程序列（唯一定义点）。

        Args:
            ques_count: 子问题数量。
            comp_template: 竞赛模板类型，用于决定后缀序列。
        """
        ques_str = [f"ques{i}" for i in range(1, ques_count + 1)]
        suffix = cls._get_flow_suffix(comp_template)
        return [*cls._FLOW_PREFIX, *ques_str, *suffix]

    def set_flows(
        self,
        ques_count: int,
        comp_template: CompTemplate | None = None,
    ) -> None:
        """初始化流程字典。"""
        seq = self._build_sequence(ques_count, comp_template)
        self.flows = {key: {} for key in seq}

    def get_solution_flows(
        self, questions: dict[str, str | int], modeler_response: ModelerToCoder
    ) -> dict[str, dict[str, str]]:
        """构建代码手的求解任务流程。

        根据 Modeler 的结构化方案为每个问题构建 Coder 的执行 prompt。
        支持 ModelSolution 结构化输出和纯文本两种格式。

        Args:
            questions: 问题字典，包含 ques1, ques2 等键值对。
            modeler_response: Modeler 输出的建模方案数据。

        Returns:
            各子任务的 coder_prompt 字典。
        """
        questions_quesx = {
            key: value
            for key, value in questions.items()
            if re.match(r"^ques\d+$", key)
        }

        ques_flow: dict[str, dict[str, str]] = {}
        for key, value in questions_quesx.items():
            solution_text = modeler_response.get_solution_text(key)
            model_config = modeler_response.get_model_config(key)

            # 构建增强版 coder prompt
            coder_prompt_parts = [
                f"参考建模手给出的解决方案：\n{solution_text}",
            ]

            # 如果有结构化配置，注入完整的结构化建模指导
            if model_config and model_config.model_name:
                guidance_lines: list[str] = []
                if model_config.model_name:
                    guidance_lines.append(
                        f"- 推荐模型: {model_config.model_name}"
                    )
                if model_config.model_category:
                    guidance_lines.append(
                        f"- 模型类别: {model_config.model_category}"
                    )
                if model_config.evaluation_metrics:
                    guidance_lines.append(
                        f"- 推荐评估指标: {', '.join(model_config.evaluation_metrics)}"
                    )
                if model_config.python_libraries:
                    guidance_lines.append(
                        f"- 推荐Python库: {', '.join(model_config.python_libraries)}"
                    )
                if model_config.data_requirements:
                    guidance_lines.append(
                        f"- 数据格式要求: {model_config.data_requirements}"
                    )
                if model_config.visualization_plan:
                    guidance_lines.append(
                        f"- 可视化规划: {model_config.visualization_plan}"
                    )
                if model_config.mathematical_formulation:
                    guidance_lines.append(
                        f"- 数学形式化: {model_config.mathematical_formulation}"
                    )
                if guidance_lines:
                    coder_prompt_parts.append(
                        "\n【结构化建模指导】\n"
                        + "\n".join(guidance_lines)
                    )

            # 注入分层实现方案（baseline/improved/innovative）
            if model_config:
                layered_approaches: list[str] = []
                if model_config.approach_baseline:
                    layered_approaches.append(
                        f"- Baseline方案（经典方法）: {model_config.approach_baseline}"
                    )
                if model_config.approach_improved:
                    layered_approaches.append(
                        f"- 改进方案: {model_config.approach_improved}"
                    )
                if model_config.approach_innovative:
                    layered_approaches.append(
                        f"- 创新方案: {model_config.approach_innovative}"
                    )
                if layered_approaches:
                    coder_prompt_parts.append(
                        "\n【分层实现方案】\n"
                        "请按以下分层策略依次实现，优先确保Baseline方案可运行，"
                        "再尝试改进和创新方案：\n"
                        + "\n".join(layered_approaches)
                    )

            # 注入匹配的代码模板参考（如果有）
            if model_config and model_config.model_name:
                try:
                    from app.config.code_templates.template_registry import (
                        template_registry,
                    )

                    matched = template_registry.search(model_config.model_name)
                    if matched:
                        template = matched[0]
                        coder_prompt_parts.append(
                            f"\n参考代码框架（请根据实际数据调整，不可直接照搬）：\n"
                            f"```python\n{template.code}\n```"
                        )
                except Exception as e:
                    logger.debug("代码模板搜索失败（非关键）: %s", e)

            coder_prompt_parts.append(f"\n完成如下问题：\n{value}")

            ques_flow[key] = {
                "coder_prompt": "\n".join(coder_prompt_parts),
            }

        # EDA 和灵敏度分析
        eda_solution = modeler_response.get_solution_text("eda")
        sensitivity_solution = modeler_response.get_solution_text(
            "sensitivity_analysis"
        )

        # 收集前序模型的参数信息，供灵敏度分析 Coder 参考
        ques_count = len(questions_quesx)
        model_params_info: list[str] = []
        for i in range(1, ques_count + 1):
            ques_key = f"ques{i}"
            model_config = (
                modeler_response.get_model_config(ques_key)
                if modeler_response
                else None
            )
            if model_config:
                info = f"- {ques_key}: 模型={model_config.model_name or '未知'}"
                if model_config.evaluation_metrics:
                    info += (
                        f", 评估指标="
                        f"{', '.join(model_config.evaluation_metrics)}"
                    )
                if model_config.mathematical_formulation:
                    info += (
                        f", 数学形式化={model_config.mathematical_formulation[:120]}"
                    )
                if model_config.python_libraries:
                    info += (
                        f", 使用库="
                        f"{', '.join(model_config.python_libraries[:5])}"
                    )
                if model_config.approach_baseline:
                    info += (
                        f", 基准方法={model_config.approach_baseline[:80]}"
                    )
                if model_config.approach_improved:
                    info += (
                        f", 改进方法={model_config.approach_improved[:80]}"
                    )
                model_params_info.append(info)

        model_params_section = ""
        if model_params_info:
            model_params_section = (
                f"\n### 0. 前序模型参数参考\n"
                f"以下是各子问题使用的模型及其评估指标，请从中识别关键参数进行敏感性分析：\n"
                + "\n".join(model_params_info)
                + "\n\n"
            )

        eda_coder_prompt = (
            f"参考建模手给出的探索性数据分析方案：\n{eda_solution}\n\n"
            f"## 你的任务：对当前目录下的数据进行全面的 EDA（探索性数据分析）\n\n"
            f"### 1. 数据概览\n"
            f"- 读取所有数据文件，输出各数据集的 shape、dtypes、前 5 行预览\n"
            f"- 输出描述性统计（describe()），包含均值、标准差、分位数\n\n"
            f"### 2. 数据质量分析\n"
            f"- 检查缺失值比例，可视化缺失值分布（missingno 或热力图）\n"
            f"- 检查重复值\n"
            f"- 检测异常值（箱线图或 3σ 原则）\n\n"
            f"### 3. 变量关系分析\n"
            f"- 数值型变量相关性热力图（Pearson/Spearman）\n"
            f"- 关键变量分布直方图或 KDE 图\n"
            f"- 类别变量频数统计柱状图\n\n"
            f"### 4. 数据清洗\n"
            f"- 处理缺失值（填充或删除，说明策略）\n"
            f"- 处理异常值（说明处理策略）\n"
            f"- 清洗后的数据保存到当前目录（CSV 格式）\n\n"
            f"### 输出要求\n"
            f"- 每张图表保存后打印 ===FIGURE: 文件名 | 描述===\n"
            f"- 关键统计量使用 ===METRICS_START=== / ===METRICS_END=== 标记输出，例如：\n"
            f"  ```python\n"
            f"  print(\"===METRICS_START===\")\n"
            f"  print(f\"总样本数: {{total_rows}}\")\n"
            f"  print(f\"总特征数: {{total_cols}}\")\n"
            f"  print(f\"缺失值比例: {{missing_ratio:.4f}}\")\n"
            f"  print(f\"重复值数量: {{dup_count}}\")\n"
            f"  print(f\"异常值数量: {{outlier_count}}\")\n"
            f"  print(\"===METRICS_END===\")\n"
            f"  ```\n"
            f"- 数据清洗完成后打印结果摘要：\n"
            f"  ```python\n"
            f"  print(\"===RESULT_SUMMARY===\")\n"
            f"  print(\"问题: EDA\")\n"
            f"  print(\"使用模型: 探索性数据分析\")\n"
            f"  print(f\"主要结论: {{一句话总结数据特征和清洗结果}}\")\n"
            f"  print(\"===RESULT_END===\")\n"
            f"  ```\n"
            f"- **不需要复杂的模型**，聚焦于数据理解和清洗\n"
        )

        flows = {
            "eda": {
                "coder_prompt": eda_coder_prompt,
            },
            **ques_flow,
            "sensitivity_analysis": {
                "coder_prompt": (
                    f"参考建模手给出的解决方案：\n{sensitivity_solution}\n\n"
                    f"## 灵敏度分析任务要求\n\n"
                    f"{model_params_section}"
                    f"### 1. 关键参数识别与扰动\n"
                    f"- 从前序各子问题的模型中，识别 **至少3个关键参数**（如模型超参数、输入数据阈值、权重系数等）\n"
                    f"- 对每个参数在基准值的 **正负10%、20%、30%** 范围内进行单因素扰动分析\n"
                    f"- 记录每次扰动后目标函数值/评估指标的变化量和变化率\n\n"
                    f"### 2. 结构化输出（必须使用标记）\n"
                    f"```python\n"
                    f"print(\"===METRICS_START===\")\n"
                    f"print(f\"参数名: {{param_name}}\")\n"
                    f"print(f\"基准值: {{base_value:.4f}}\")\n"
                    f"print(f\"扰动范围: {{min_val:.4f}} ~ {{max_val:.4f}}\")\n"
                    f"print(f\"结果变化率: {{change_rate:.2%}}\")\n"
                    f"print(\"===METRICS_END===\")\n"
                    f"```\n\n"
                    f"### 3. 可视化要求\n"
                    f"- **龙卷风图（Tornado Chart）**：横轴为目标函数变化量，纵轴为各参数名称，展示各参数敏感度排序\n"
                    f"- **蜘蛛图（Spider Plot）**：横轴为参数变化百分比（-30%~+30%），纵轴为目标函数值，每条线代表一个参数\n"
                    f"- 图表保存后打印: print(\"===FIGURE: sensitivity_tornado.png | 参数灵敏度龙卷风图===\")\n"
                    f"- 图表保存后打印: print(\"===FIGURE: sensitivity_spider.png | 参数灵敏度蜘蛛图===\")\n\n"
                    f"### 4. 定量数据输出\n"
                    f"- 打印参数灵敏度排序表（按影响程度从大到小排列）\n"
                    f"- 每个参数需输出: 参数名、基准值、扰动范围、结果最大变化率、敏感等级（高/中/低）\n"
                    f"- 给出结论：哪些参数对结果影响最大，模型整体鲁棒性如何\n\n"
                    f"### 5. 进阶分析（如时间允许）\n\n"
                    f"#### 5.1 双因素交互分析\n"
                    f"- 选择最敏感的 2-3 个参数，进行双因素交互分析\n"
                    f"- 将两个参数分别在基准值的 ±20% 范围内取 5-10 个等间隔点，计算所有组合下的目标函数值\n"
                    f"- 绘制交互效应热力图（heatmap），展示参数组合对目标函数的影响\n"
                    f"- 图表保存后打印: print(\"===FIGURE: interaction_heatmap.png | 参数交互效应热力图===\")\n"
                    f"- 如果存在明显的交互效应（非线性叠加），在输出中注明\n\n"
                    f"#### 5.2 标准化鲁棒性评价\n"
                    f"对每个分析的参数给出标准化的敏感等级评价：\n"
                    f"- \"高度敏感\"：扰动 ±10% 导致目标变化 >15%\n"
                    f"- \"中等敏感\"：扰动 ±10% 导致目标变化 5%-15%\n"
                    f"- \"不敏感\"：扰动 ±10% 导致目标变化 <5%\n\n"
                    f"使用以下格式输出标准化评价结果：\n"
                    f"```python\n"
                    f"print(\"===RESULT_SUMMARY===\")\n"
                    f"print(f\"参数: {{param_name}}, 敏感等级: {{level}}, 变化幅度: ±{{change_pct:.1f}}%\")\n"
                    f"# 对每个参数重复上述 print\n"
                    f"print(f\"模型整体鲁棒性: {{overall_robustness}}\")\n"
                    f"print(\"===RESULT_END===\")\n"
                    f"```\n\n"
                    f"### 代码实现指导\n"
                    f"1. **模型重建策略**: \n"
                    f"   - 优先从工作目录加载已保存的模型（如 joblib/pickle 文件）\n"
                    f"   - 如无保存文件，请根据前序问题的建模方案重新训练一个简化版模型\n"
                    f"   - 重新训练时，请使用前序问题产出的清洗数据文件\n"
                    f"2. **参数识别优先级**: 模型超参数 > 数据预处理参数 > 物理约束参数\n"
                    f"3. **结果保存**: 灵敏度分析图表请保存为 sensitivity_*.png 格式\n"
                ),
            },
        }

        # === model_comparison: 多模型对比分析 ===
        # 多问题场景：跨问题模型对比；单问题场景：同一问题内多方法对比
        if ques_count >= 2:
            # --- 多问题跨模型对比（保持原有逻辑不变） ---
            model_info_parts: list[str] = []
            for i in range(1, ques_count + 1):
                ques_key = f"ques{i}"
                model_config = (
                    modeler_response.get_model_config(ques_key)
                    if modeler_response
                    else None
                )
                if model_config:
                    model_info_parts.append(
                        f"- {ques_key}: 模型名称={model_config.model_name or '未知'}, "
                        f"类别={model_config.model_category or '未知'}, "
                        f"评估指标={', '.join(model_config.evaluation_metrics) if model_config.evaluation_metrics else '未指定'}"
                    )

            model_info_text = (
                "\n".join(model_info_parts) if model_info_parts else "暂无结构化模型信息"
            )
            comparison_coder_prompt = (
                f"你的任务是对前面各子问题中使用的模型进行统一的对比分析和可视化。\n\n"
                f"## 各子问题模型信息\n{model_info_text}\n\n"
                f"## 要求\n\n"
                f"### 1. 汇总对比表格\n"
                f"创建一个 Markdown 格式的汇总表格，包含：问题编号、模型名称、各评估指标值、综合排名。\n"
                f"使用结构化标记输出表格：\n"
                f"```python\n"
                f"print(\"===TABLE_START===\")\n"
                f"print(\"| 问题 | 模型名称 | 指标1 | 指标2 | ... | 综合排名 |\")\n"
                f"print(\"| --- | --- | --- | --- | ... | --- |\")\n"
                f"# ...填充实际数据行...\n"
                f"print(\"===TABLE_END===\")\n"
                f"```\n\n"
                f"### 2. 对比可视化（至少生成2张图表）\n"
                f"- **分组柱状图**：横轴为各问题/模型，纵轴为关键指标值，不同指标用不同颜色区分\n"
                f"- **雷达图（Spider/Radar Chart）**：展示各模型在不同评估维度上的表现\n"
                f"- 图表保存后打印: print(\"===FIGURE: comparison_bar.png | 多模型指标对比柱状图===\")\n"
                f"- 图表保存后打印: print(\"===FIGURE: comparison_radar.png | 多模型雷达图===\")\n\n"
                f"### 3. 指标数据输出\n"
                f"使用结构化标记输出各模型的关键指标：\n"
                f"```python\n"
                f"print(\"===METRICS_START===\")\n"
                f"print(f\"问题: {{ques_key}}\")\n"
                f"print(f\"模型: {{model_name}}\")\n"
                f"print(f\"指标名: {{value}}\")\n"
                f"print(\"===METRICS_END===\")\n"
                f"```\n\n"
                f"### 4. 重要注意事项\n"
                f"- 如果前面的子问题已经有部分结果输出，请从这些输出中提取**实际数值**来填充对比表格\n"
                f"- 如果某些指标缺失，在表格中标注\"未获取\"，不要使用假数据\n"
                f"- 对比分析应给出明确结论：哪个模型综合表现最优、各模型的优劣势\n"
            )
            flows["model_comparison"] = {
                "coder_prompt": comparison_coder_prompt,
            }
        elif ques_count == 1:
            # --- 单问题多方法对比（Baseline / Improved / Innovative） ---
            ques1_config = (
                modeler_response.get_model_config("ques1")
                if modeler_response
                else None
            )
            if ques1_config:
                baseline = ques1_config.approach_baseline or ""
                improved = ques1_config.approach_improved or ""
                innovative = ques1_config.approach_innovative or ""

                # 构建方法描述列表，仅保留非空方案
                approach_entries: list[tuple[str, str]] = []
                if baseline.strip():
                    approach_entries.append(
                        ("Baseline（经典方法）", baseline.strip())
                    )
                if improved.strip():
                    approach_entries.append(
                        ("Improved（改进方法）", improved.strip())
                    )
                if innovative.strip():
                    approach_entries.append(
                        ("Innovative（创新方法）", innovative.strip())
                    )

                # 至少有 2 种方法时才生成对比
                if len(approach_entries) >= 2:
                    approach_info_lines = "\n".join(
                        f"- **{name}**: {desc}"
                        for name, desc in approach_entries
                    )
                    approach_names = "、".join(
                        name for name, _ in approach_entries
                    )
                    eval_metrics_text = (
                        "、".join(ques1_config.evaluation_metrics)
                        if ques1_config.evaluation_metrics
                        else "R2, RMSE, MAE 等适用指标"
                    )

                    single_comparison_prompt = (
                        f"你的任务是对本问题中使用的多种求解方法进行对比分析和可视化。\n\n"
                        f"## 问题概述\n"
                        f"本问题采用了分层建模策略，共设计了 {len(approach_entries)} 种方法：\n"
                        f"{approach_info_lines}\n\n"
                        f"## 要求\n\n"
                        f"### 1. 各方法独立求解与指标收集\n"
                        f"- 确保 {approach_names} 各方法均已在前序步骤中运行并产出结果\n"
                        f"- 从前序代码输出中提取各方法的评估指标（推荐指标: {eval_metrics_text}）\n"
                        f"- 如果前序步骤未产出某方法的结果，请重新运行该方法并收集指标\n\n"
                        f"### 2. 汇总对比表格\n"
                        f"创建 Markdown 格式的对比表格，包含：方法名称、各评估指标值、"
                        f"运行耗时（如可获取）、综合排名。\n"
                        f"使用结构化标记输出表格：\n"
                        f"```python\n"
                        f"print(\"===TABLE_START===\")\n"
                        f"print(\"| 方法 | {' | '.join(eval_metrics_text.split('、'))} | 综合排名 |\")\n"
                        f"print(\"| --- |{'| --- ' * len(eval_metrics_text.split('、'))}| --- |\")\n"
                        f"# ...填充各方法的实际指标数据行...\n"
                        f"print(\"===TABLE_END===\")\n"
                        f"```\n\n"
                        f"### 3. 对比可视化（至少生成2张图表）\n"
                        f"- **分组柱状图**：横轴为各方法名称（{approach_names}），"
                        f"纵轴为关键指标值，不同指标用不同颜色区分\n"
                        f"- **雷达图（Spider/Radar Chart）**：展示各方法在不同评估维度上的表现差异\n"
                        f"- 图表保存后打印: print(\"===FIGURE: comparison_bar.png | 多方法指标对比柱状图===\")\n"
                        f"- 图表保存后打印: print(\"===FIGURE: comparison_radar.png | 多方法雷达图===\")\n\n"
                        f"### 4. 指标数据输出\n"
                        f"使用结构化标记输出各方法的关键指标：\n"
                        f"```python\n"
                        f"print(\"===METRICS_START===\")\n"
                        f"print(f\"方法: {{method_name}}\")\n"
                        f"print(f\"指标名: {{value}}\")\n"
                        f"print(\"===METRICS_END===\")\n"
                        f"```\n\n"
                        f"### 5. 重要注意事项\n"
                        f"- 从前序子问题的代码输出中提取**实际数值**，不要使用假数据\n"
                        f"- 如果某方法的指标缺失，在表格中标注\"未获取\"\n"
                        f"- 对比分析应给出明确结论：哪种方法综合表现最优，改进方法相比基线提升了多少\n"
                        f"- 竞赛论文中\"多模型/多方法对比\"是评审加分项，请确保分析深入、结论清晰\n"
                    )
                    flows["model_comparison"] = {
                        "coder_prompt": single_comparison_prompt,
                    }

        return flows

    # 各章节的上下文注入策略配置
    # solve_mode: "none" 不注入求解结果, "truncated" 截取前 N 字符, "full" 完整注入
    # overview_mode: True 注入建模方案摘要, False 不注入
    _CHAPTER_CONTEXT_POLICY: dict[str, dict] = {
        "firstPage": {"solve_mode": "truncated", "solve_limit": 1500, "overview": True},
        "RepeatQues": {"solve_mode": "none", "overview": False},
        "analysisQues": {"solve_mode": "none", "overview": True},
        "modelAssumption": {"solve_mode": "none", "overview": True},
        "symbol": {"solve_mode": "none", "overview": True},
        "model_comparison": {"solve_mode": "full", "overview": True},
        "innovation_benchmark": {"solve_mode": "truncated", "solve_limit": 2000, "overview": True},
        "judge": {"solve_mode": "truncated", "solve_limit": 2000, "overview": True},
        "conclusion": {"solve_mode": "truncated", "solve_limit": 3000, "overview": True},
    }

    @staticmethod
    def _build_metrics_summary(
        user_output: "UserOutput",
        max_length: int = 2000,
    ) -> str:
        """从 user_output.metrics_store 构建各子问题的结构化指标摘要文本。

        遍历所有已存储的子问题指标，格式化为 Writer 可直接引用的列表。
        当摘要文本超过 max_length 时进行截断，防止 prompt 膨胀。

        Args:
            user_output: 用户输出对象，包含 metrics_store 字典。
            max_length: 摘要文本的最大字符数，超过时截断。

        Returns:
            格式化的指标摘要文本，无指标数据时返回空字符串。
        """
        if not hasattr(user_output, "metrics_store") or not user_output.metrics_store:
            return ""

        parts: list[str] = []
        for ques_key, metrics in user_output.metrics_store.items():
            if not metrics:
                continue
            metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
            parts.append(f"- {ques_key}: {metrics_str}")

        if not parts:
            return ""

        summary = "\n".join(parts)
        if len(summary) > max_length:
            summary = summary[:max_length] + "\n...（更多指标已省略）"
        return summary

    @classmethod
    def _build_chapter_context(
        cls,
        chapter_key: str,
        model_build_solve: str,
        modeling_overview: str,
    ) -> str:
        """根据章节类型构建精简的上下文字符串，减少不必要的 Token 消耗。

        不同章节对上下文的需求不同：
          - RepeatQues（问题重述）：不需要求解结果和建模方案
          - symbol（符号说明）：仅需建模方案中的变量定义
          - analysisQues / modelAssumption：仅需建模方案概要
          - firstPage / conclusion：需要截取版求解结果 + 建模方案
          - judge：需要较长的截取版求解结果 + 建模方案
          - model_comparison：需要完整求解结果（含指标数据）

        Args:
            chapter_key: 章节标识，如 "firstPage", "RepeatQues" 等。
            model_build_solve: 完整的各子问题求解结果文本。
            modeling_overview: 建模方案摘要文本。

        Returns:
            拼接好的上下文字符串，可直接嵌入 prompt。
        """
        policy = cls._CHAPTER_CONTEXT_POLICY.get(
            chapter_key,
            {"solve_mode": "full", "overview": True},
        )

        parts: list[str] = []

        # 按策略注入求解结果
        solve_mode = policy.get("solve_mode", "full")
        if solve_mode == "full":
            parts.append(f"根据模型的求解的信息{model_build_solve}")
        elif solve_mode == "truncated":
            limit = policy.get("solve_limit", 1500)
            if len(model_build_solve) > limit:
                truncated = model_build_solve[:limit] + "...（更多求解细节已省略）"
            else:
                truncated = model_build_solve
            parts.append(f"根据模型的求解的信息{truncated}")
        # solve_mode == "none" 时不注入求解结果

        # 按策略注入建模方案摘要
        if policy.get("overview", True) and modeling_overview:
            parts.append(modeling_overview)

        return "，".join(parts) if parts else ""

    def get_write_flows(
        self,
        user_output: UserOutput,
        config_template: dict,
        bg_ques_all: str,
        modeler_response: ModelerToCoder | None = None,
        comp_template: CompTemplate | None = None,
    ) -> dict[str, str]:
        """构建论文前置/后置章节的写作任务流程。

        将建模手的建模方案摘要（模型假设、各子问题方案概览）注入到前置章节中，
        使 Writer 在撰写摘要、问题分析、模型假设等章节时能感知到使用了什么模型。

        各章节按需注入精简后的上下文，避免为每个章节都塞入完整的求解结果，
        从而减少不必要的 Token 消耗。精简策略参见 _CHAPTER_CONTEXT_POLICY。

        包含所有前置章节（firstPage ~ symbol）和后置章节，
        确保与 _get_flow_suffix 和 user_output._init_seq 完全对齐。

        当 comp_template == AMERICAN 时，额外生成 innovation_benchmark（Strengths and Weaknesses），
        并将 judge 语义映射为 Conclusions，conclusion 语义映射为 Letter to the Decision Maker。

        Args:
            user_output: 用户输出对象，包含各子任务的求解结果。
            config_template: 论文模板配置。
            bg_ques_all: 完整的问题背景描述。
            modeler_response: Modeler 输出的建模方案数据，默认为 None 以保持向后兼容。
            comp_template: 竞赛模板类型，默认为 None（中文模板）以保持向后兼容。

        Returns:
            各前置/后置章节的 writer prompt 字典。
        """
        model_build_solve = user_output.get_model_build_solve()

        # 构建建模方案摘要，供前置章节参考
        modeling_overview = ""
        if modeler_response:
            overview_parts: list[str] = []
            # 注入模型假设
            if modeler_response.assumptions:
                assumptions_text = "\n".join(
                    f"  {i + 1}. {a}" for i, a in enumerate(modeler_response.assumptions)
                )
                overview_parts.append(f"模型假设：\n{assumptions_text}")
            # 注入各子问题的建模方案概览
            for qkey in self.get_questions_quesx_keys():
                solution_text = modeler_response.get_solution_text(qkey)
                model_config = modeler_response.get_model_config(qkey)
                if solution_text or model_config:
                    part = f"{qkey} 建模方案："
                    if model_config and model_config.model_name:
                        part += f"（推荐模型: {model_config.model_name}）"
                    if solution_text:
                        part += f"\n  {solution_text[:500]}"
                    overview_parts.append(part)
            if overview_parts:
                modeling_overview = "\n建模手的整体建模方案：\n" + "\n".join(overview_parts)

        # 记录原始上下文长度，用于日志对比
        full_solve_len = len(model_build_solve)
        full_overview_len = len(modeling_overview)

        # 获取模型对比数据（由 workflow 在 solution steps 后注入到 user_output）
        comparison_data = user_output.model_comparison_data or "暂无对比数据"

        # 获取 model_comparison 模板，注入对比数据占位符
        model_comparison_template = config_template.get("model_comparison", "")
        if "{comparison_data}" in model_comparison_template:
            model_comparison_template = model_comparison_template.replace(
                "{comparison_data}", comparison_data
            )

        # 构建各子问题的结构化指标摘要，供 firstPage/conclusion/judge 引用
        metrics_summary = self._build_metrics_summary(user_output)

        # 为每个章节构建精简后的上下文
        def _ctx(key: str) -> str:
            return self._build_chapter_context(key, model_build_solve, modeling_overview)

        ctx_first = _ctx("firstPage")
        ctx_repeat = _ctx("RepeatQues")
        ctx_analysis = _ctx("analysisQues")
        ctx_assumption = _ctx("modelAssumption")
        ctx_symbol = _ctx("symbol")
        ctx_comparison = _ctx("model_comparison")
        ctx_innovation = _ctx("innovation_benchmark")
        ctx_judge = _ctx("judge")
        ctx_conclusion = _ctx("conclusion")

        is_american = comp_template == CompTemplate.AMERICAN

        flows: dict[str, str] = {
            "firstPage": f"""问题背景{bg_ques_all},不需要编写代码,{ctx_first}，按照如下模板撰写：{config_template.get("firstPage", "")}，撰写标题，摘要，关键词""",
            "RepeatQues": f"""问题背景{bg_ques_all},不需要编写代码,按照如下模板撰写：{config_template.get("RepeatQues", "")}，撰写问题重述""" if not ctx_repeat else f"""问题背景{bg_ques_all},不需要编写代码,{ctx_repeat}，按照如下模板撰写：{config_template.get("RepeatQues", "")}，撰写问题重述""",
            "analysisQues": f"""问题背景{bg_ques_all},不需要编写代码,{ctx_analysis}，按照如下模板撰写：{config_template.get("analysisQues", "")}，撰写问题分析""",
            "modelAssumption": f"""问题背景{bg_ques_all},不需要编写代码,{ctx_assumption}，按照如下模板撰写：{config_template.get("modelAssumption", "")}，撰写模型假设""",
            "symbol": f"""不需要编写代码,{ctx_symbol}，按照如下模板撰写：{config_template.get("symbol", "")}，撰写符号说明部分""" if ctx_symbol else f"""不需要编写代码,按照如下模板撰写：{config_template.get("symbol", "")}，撰写符号说明部分""",
            "model_comparison": f"""不需要编写代码,{ctx_comparison}，模型对比数据如下：\n{comparison_data}\n按照如下模板撰写：{model_comparison_template}，撰写多模型对比分析""",
        }

        # MCM/ICM (AMERICAN) 模板：添加 innovation_benchmark 章节，调整 judge/conclusion 语义
        if is_american:
            flows["innovation_benchmark"] = (
                f"""问题背景{bg_ques_all},不需要编写代码,{ctx_innovation}，"""
                f"""按照如下模板撰写：{config_template.get("innovation_benchmark", "")}，"""
                f"""撰写模型的优缺点分析（Strengths and Weaknesses）。"""
                f"""要求包含：1.模型的优势（Strengths，至少4条，需结合具体工作和数据支撑）"""
                f""" 2.模型的不足（Weaknesses，至少2条，需客观诚实）"""
                f""" 3.未来改进方向（Future Improvements，针对每个不足提出具体改进方案）"""
            )
            flows["judge"] = (
                f"""问题背景{bg_ques_all},不需要编写代码,{ctx_judge}，"""
                f"""按照如下模板撰写：{config_template.get("judge", "")}，"""
                f"""撰写结论部分（Conclusions）。"""
                f"""要求系统总结各问题的关键发现和贡献："""
                f"""1.每个问题用2-3句话总结核心结论，必须包含关键数值结果 """
                f"""2.强调各问题之间的逻辑关系和整体结论 """
                f"""3.讨论模型的实际应用价值和推广场景"""
            )
            flows["conclusion"] = (
                f"""问题背景{bg_ques_all},不需要编写代码,{ctx_conclusion}，"""
                f"""按照如下模板撰写：{config_template.get("conclusion", "")}，"""
                f"""撰写致决策者的备忘录/信函（Letter to the Decision Maker / Memo）。"""
                f"""要求使用专业、非技术性的语言，便于决策者理解："""
                f"""1.简述研究背景（1-2句话） """
                f"""2.列出3-5条关键发现，附带数据支撑 """
                f"""3.提出可操作的建议 """
                f"""4.简要说明潜在风险或局限性 """
                f"""5.以前瞻性陈述结尾 """
                f"""6.使用正式备忘录格式（含 To/From/Date/Subject 表头）"""
            )
        else:
            # 中文模板 (CHINA) 保持原有语义
            flows["judge"] = (
                f"""问题背景{bg_ques_all},不需要编写代码,{ctx_judge}，"""
                f"""按照如下模板撰写：{config_template.get("judge", "")}，"""
                f"""撰写模型的评价、改进方向和推广应用。"""
                f"""要求包含：1.模型的优点（至少3条）"""
                f"""2.模型的不足（至少2条）"""
                f"""3.改进方向和具体方案 4.模型的推广应用场景"""
            )
            flows["conclusion"] = (
                f"""问题背景{bg_ques_all},不需要编写代码,{ctx_conclusion}，"""
                f"""按照如下模板撰写：{config_template.get("conclusion", "")}，"""
                f"""撰写结论与建议"""
            )

        # 为 firstPage / conclusion / judge / innovation_benchmark 追加结构化指标摘要
        if metrics_summary:
            flows["firstPage"] += (
                f"\n\n## 各子问题量化结果（摘要中必须引用这些精确数值）\n"
                f"{metrics_summary}\n"
            )
            flows["conclusion"] += (
                f"\n\n## 各子问题关键指标（结论中必须引用量化结果）\n"
                f"{metrics_summary}\n"
            )
            flows["judge"] += (
                f"\n\n## 各子问题关键指标（评价模型优缺点时必须引用具体数值）\n"
                f"{metrics_summary}\n"
            )
            if "innovation_benchmark" in flows:
                flows["innovation_benchmark"] += (
                    f"\n\n## 各子问题关键指标（分析模型优缺点时必须引用具体数值）\n"
                    f"{metrics_summary}\n"
                )

        # 为 conclusion 追加模型对比摘要数据
        if (
            hasattr(user_output, "model_comparison_data")
            and user_output.model_comparison_data
        ):
            flows["conclusion"] += (
                f"\n\n## 模型对比摘要\n"
                f"{user_output.model_comparison_data[:1500]}\n"
            )

        # 记录每个章节的 prompt 字符数，便于监控 Token 消耗
        total_chars = 0
        for key, prompt_text in flows.items():
            prompt_len = len(prompt_text)
            total_chars += prompt_len
            logger.info(
                "get_write_flows: 章节=%s, prompt长度=%d 字符",
                key,
                prompt_len,
            )
        logger.info(
            "get_write_flows: 全部章节 prompt 合计=%d 字符 "
            "(原始 solve=%d, overview=%d)",
            total_chars,
            full_solve_len,
            full_overview_len,
        )

        # === 注入模型速查表到 firstPage 和 conclusion ===
        if modeler_response:
            model_quick_ref: list[str] = []
            for qkey in self.get_questions_quesx_keys():
                mc = modeler_response.get_model_config(qkey)
                if mc and mc.model_name:
                    category = getattr(mc, "model_category", "")
                    ref_line = f"- {qkey}: {mc.model_name}"
                    if category:
                        ref_line += f" ({category})"
                    model_quick_ref.append(ref_line)
            if model_quick_ref:
                quick_ref_text = (
                    "\n\n## 各问题使用的模型（摘要/结论中必须准确使用这些模型名称）\n"
                    + "\n".join(model_quick_ref)
                )
                if "firstPage" in flows:
                    flows["firstPage"] += quick_ref_text
                if "conclusion" in flows:
                    flows["conclusion"] += quick_ref_text

        return flows

    def get_writer_prompt(
        self,
        key: str,
        coder_response: str,
        code_interpreter: BaseCodeInterpreter,
        config_template: dict,
        modeler_response: ModelerToCoder | None = None,
        cross_question_context: dict[str, str] | None = None,
    ) -> str:
        """根据不同的key生成对应的writer_prompt

        按需构建单个 key 对应的 prompt，避免为所有 key 构建全量字典的开销。
        将建模手的数学建模方案与代码手的执行结果一并注入 writer prompt，
        使 Writer 能够准确描述所用模型、公式和理论依据。

        Args:
            key: 任务类型（如 ques1, eda, sensitivity_analysis）
            coder_response: 代码执行结果
            code_interpreter: 代码解释器实例，用于获取代码输出
            config_template: 论文模板配置
            modeler_response: Modeler 输出的建模方案数据，默认为 None 以保持向后兼容
            cross_question_context: 前序问题的结果上下文，默认为 None 以保持向后兼容

        Returns:
            str: 生成的writer_prompt
        """
        code_output = code_interpreter.get_code_output(key)
        bgc = self.questions["background"]

        # 构建跨问题上下文（对 ques 类型、sensitivity_analysis 和 model_comparison 有效）
        cross_context_text = ""
        if cross_question_context and (
            key.startswith("ques")
            or key == "sensitivity_analysis"
            or key == "model_comparison"
        ):
            cross_context_text = self.build_cross_question_context(
                cross_question_context, max_chars_per_question=400
            )

        if key == "eda":
            eda_scheme = modeler_response.get_solution_text("eda") if modeler_response else "无"
            prompt_parts = [
                f"问题背景{bgc},不需要编写代码,",
                f"建模手的EDA方案如下：{eda_scheme},",
                f"代码手得到的EDA结果{coder_response},{code_output},",
            ]

            # 注入 Coder 产出的结构化信息（图表、指标、结果摘要）
            if code_output:
                figures = Flows.extract_figures_from_code_output(code_output)
                if figures:
                    fig_lines = []
                    for i, fig in enumerate(figures, 1):
                        fig_lines.append(
                            f"  - 图{i}: 文件名={fig.get('filename', '未知')}, "
                            f"描述={fig.get('description', '无描述')}"
                        )
                    prompt_parts.append(
                        f"\n\n【代码生成的图表清单（必须全部引用）】\n"
                        + "\n".join(fig_lines)
                        + "\n引用时请使用精确文件名，格式: ![描述](文件名)\n"
                    )

                metrics = Flows.extract_metrics_from_code_output(code_output)
                if metrics:
                    metrics_text = "\n".join(
                        f"- {k}: {v}" for k, v in metrics.items()
                    )
                    prompt_parts.append(
                        f"\n## 数据统计指标（请在论文中准确引用这些数值）\n{metrics_text}\n"
                    )

                result_summaries = Flows.extract_result_summaries(code_output)
                if result_summaries:
                    summaries_text = "\n".join(
                        f"- 模型: {s.get('model', '未知')}, 结论: {s.get('conclusion', '无')}"
                        for s in result_summaries
                    )
                    prompt_parts.append(
                        f"\n## EDA结果摘要\n{summaries_text}\n"
                    )

            prompt_parts.append(
                f"按照如下模板撰写：{config_template.get('eda', '')}"
            )
            return "\n".join(prompt_parts)

        if key == "sensitivity_analysis":
            sensitivity_scheme = modeler_response.get_solution_text("sensitivity_analysis") if modeler_response else "无"
            prompt_parts = [
                f"问题背景{bgc},不需要编写代码,",
                f"建模手的建模方案如下：{sensitivity_scheme},",
                f"代码手得到的结果{coder_response},{code_output},",
            ]

            # 注入 Coder 产出的结构化信息（图表、指标、结果摘要）
            if code_output:
                figures = Flows.extract_figures_from_code_output(code_output)
                if figures:
                    fig_lines = []
                    for i, fig in enumerate(figures, 1):
                        fig_lines.append(
                            f"  - 图{i}: 文件名={fig.get('filename', '未知')}, "
                            f"描述={fig.get('description', '无描述')}"
                        )
                    prompt_parts.append(
                        f"\n\n【代码生成的图表清单（必须全部引用）】\n"
                        + "\n".join(fig_lines)
                        + "\n引用时请使用精确文件名，格式: ![描述](文件名)\n"
                    )

                metrics = Flows.extract_metrics_from_code_output(code_output)
                if metrics:
                    metrics_text = "\n".join(
                        f"- {k}: {v}" for k, v in metrics.items()
                    )
                    prompt_parts.append(
                        f"\n## 模型评估指标（请在论文中准确引用这些数值）\n{metrics_text}\n"
                    )

                result_summaries = Flows.extract_result_summaries(code_output)
                if result_summaries:
                    summaries_text = "\n".join(
                        f"- 模型: {s.get('model', '未知')}, 结论: {s.get('conclusion', '无')}"
                        for s in result_summaries
                    )
                    prompt_parts.append(
                        f"\n## 求解结果摘要\n{summaries_text}\n"
                    )

            if cross_context_text:
                prompt_parts.append(cross_context_text)

            # 注入模型速查表，帮助 Writer 准确引用模型名称
            if modeler_response:
                model_refs: list[str] = []
                for qkey in self.get_questions_quesx_keys():
                    mc = modeler_response.get_model_config(qkey)
                    if mc and mc.model_name:
                        model_refs.append(f"- {qkey}: {mc.model_name}")
                if model_refs:
                    prompt_parts.append(
                        "\n\n## 各问题使用的模型名称\n"
                        + "\n".join(model_refs)
                    )

            prompt_parts.append(
                f"按照如下模板撰写：{config_template.get('sensitivity_analysis', '')}"
            )
            return "\n".join(prompt_parts)

        if key == "model_comparison":
            prompt_parts = [
                f"问题背景{bgc},不需要编写代码,",
                f"代码手得到的多模型对比分析结果{coder_response},{code_output},",
            ]

            # 注入 Coder 产出的结构化信息（图表、指标、表格）
            if code_output:
                figures = Flows.extract_figures_from_code_output(code_output)
                if figures:
                    fig_lines = []
                    for i, fig in enumerate(figures, 1):
                        fig_lines.append(
                            f"  - 图{i}: 文件名={fig.get('filename', '未知')}, "
                            f"描述={fig.get('description', '无描述')}"
                        )
                    prompt_parts.append(
                        f"\n\n【代码生成的图表清单（必须全部引用）】\n"
                        + "\n".join(fig_lines)
                        + "\n引用时请使用精确文件名，格式: ![描述](文件名)\n"
                    )

                metrics = Flows.extract_metrics_from_code_output(code_output)
                if metrics:
                    metrics_text = "\n".join(
                        f"- {k}: {v}" for k, v in metrics.items()
                    )
                    prompt_parts.append(
                        f"\n## 模型评估指标（请在论文中准确引用这些数值）\n{metrics_text}\n"
                    )

                tables = Flows.extract_tables_from_code_output(code_output)
                if tables:
                    prompt_parts.append(
                        f"\n## 对比表格数据（请在论文中直接引用）\n{tables}\n"
                    )

                result_summaries = Flows.extract_result_summaries(code_output)
                if result_summaries:
                    summaries_text = "\n".join(
                        f"- 模型: {s.get('model', '未知')}, 结论: {s.get('conclusion', '无')}"
                        for s in result_summaries
                    )
                    prompt_parts.append(
                        f"\n## 求解结果摘要\n{summaries_text}\n"
                    )

            if cross_context_text:
                prompt_parts.append(cross_context_text)

            # 注入模型速查表，帮助 Writer 准确引用模型名称
            if modeler_response:
                model_refs: list[str] = []
                for qkey in self.get_questions_quesx_keys():
                    mc = modeler_response.get_model_config(qkey)
                    if mc and mc.model_name:
                        model_refs.append(f"- {qkey}: {mc.model_name}")
                if model_refs:
                    prompt_parts.append(
                        "\n\n## 各问题使用的模型名称\n"
                        + "\n".join(model_refs)
                    )

            prompt_parts.append(
                f"按照如下模板撰写：{config_template.get('model_comparison', '')}，"
                f"撰写多模型对比分析部分。要求包含：1.各模型的适用条件和选择依据 "
                f"2.对比表格和可视化图表的引用与分析 3.综合评价结论"
            )
            return "\n".join(prompt_parts)

        if key == "innovation_benchmark":
            prompt_parts = [
                f"问题背景{bgc},不需要编写代码,",
                f"代码手得到的结果{coder_response},{code_output},",
            ]

            # 注入模型速查表，帮助 Writer 准确引用模型名称
            if modeler_response:
                model_refs: list[str] = []
                for qkey in self.get_questions_quesx_keys():
                    mc = modeler_response.get_model_config(qkey)
                    if mc and mc.model_name:
                        model_refs.append(f"- {qkey}: {mc.model_name}")
                if model_refs:
                    prompt_parts.append(
                        "\n\n## 各问题使用的模型名称\n"
                        + "\n".join(model_refs)
                    )

            prompt_parts.append(
                f"按照如下模板撰写：{config_template.get('innovation_benchmark', '')}，"
                f"撰写模型优缺点分析（Strengths and Weaknesses）部分。"
                f"要求包含：1.模型的优势（Strengths，至少4条，结合具体工作和数据支撑）"
                f" 2.模型的不足（Weaknesses，至少2条，客观诚实）"
                f" 3.未来改进方向（针对每个不足提出具体改进方案）"
            )
            return "\n".join(prompt_parts)

        # quesN 类型
        if key in self.get_questions_quesx_keys():
            scheme = modeler_response.get_solution_text(key) if modeler_response else "无"
            prompt_parts = [
                f"问题背景{bgc},不需要编写代码,",
                f"建模手的建模方案如下：{scheme},",
                f"代码手得到的结果{coder_response},{code_output},",
            ]

            # 注入建模方案精炼摘要（优先使用结构化字段）
            model_config = modeler_response.get_model_config(key) if modeler_response else None
            if model_config:
                modeling_summary = (
                    f"模型名称: {model_config.model_name or '未指定'}\n"
                    f"模型类别: {model_config.model_category or '未指定'}\n"
                    f"评估指标: {', '.join(model_config.evaluation_metrics) if model_config.evaluation_metrics else '未指定'}\n"
                    f"数学形式化: {model_config.mathematical_formulation or '见方案文本'}\n"
                )
                prompt_parts.append(
                    f"\n## 建模方案摘要\n{modeling_summary}\n"
                )

            # 注入 Coder 产出的结构化信息（图表、指标、结果摘要）
            if code_output:
                figures = Flows.extract_figures_from_code_output(code_output)
                if figures:
                    fig_lines = []
                    for i, fig in enumerate(figures, 1):
                        fig_lines.append(
                            f"  - 图{i}: 文件名={fig.get('filename', '未知')}, "
                            f"描述={fig.get('description', '无描述')}"
                        )
                    prompt_parts.append(
                        f"\n\n【代码生成的图表清单（必须全部引用）】\n"
                        + "\n".join(fig_lines)
                        + "\n引用时请使用精确文件名，格式: ![描述](文件名)\n"
                    )

                metrics = Flows.extract_metrics_from_code_output(code_output)
                if metrics:
                    metrics_text = "\n".join(
                        f"- {k}: {v}" for k, v in metrics.items()
                    )
                    prompt_parts.append(
                        f"\n## 模型评估指标（请在论文中准确引用这些数值）\n{metrics_text}\n"
                    )

                result_summaries = Flows.extract_result_summaries(code_output)
                if result_summaries:
                    summaries_text = "\n".join(
                        f"- 模型: {s.get('model', '未知')}, 结论: {s.get('conclusion', '无')}"
                        for s in result_summaries
                    )
                    prompt_parts.append(
                        f"\n## 求解结果摘要\n{summaries_text}\n"
                    )

            if cross_context_text:
                prompt_parts.append(cross_context_text)

            prompt_parts.append(
                f"按照如下模板撰写：{config_template.get(key, '')}"
            )
            return "\n".join(prompt_parts)

        raise ValueError(f"未知的任务类型: {key}")

    def get_questions_quesx_keys(self) -> list[str]:
        """获取问题1,2...的键"""
        return list(self.get_questions_quesx().keys())

    def get_questions_quesx(self) -> dict[str, str]:
        """获取问题1,2,3...的键值对"""
        questions_quesx = {
            key: value
            for key, value in self.questions.items()
            if re.match(r"^ques\d+$", key)
        }
        return questions_quesx

    def get_seq(
        self,
        ques_count: int,
        comp_template: CompTemplate | None = None,
    ) -> dict[str, str]:
        """获取章节序列字典。"""
        seq = self._build_sequence(ques_count, comp_template)
        return {key: "" for key in seq}

    @staticmethod
    def extract_metrics_from_code_output(code_output: str | None) -> dict[str, float]:
        """从代码输出中提取评估指标（优先使用结构化标记，降级为正则）

        提取策略:
          1. 优先从 ===METRICS_START=== / ===METRICS_END=== 标记块中提取
          2. 如果标记块不存在或为空，降级使用传统正则匹配

        Args:
            code_output: Coder 的文本输出

        Returns:
            dict[str, float]: 提取到的指标名称和数值
        """
        if not code_output:
            return {}

        # 策略1: 优先从结构化标记块提取
        metrics = Flows._extract_metrics_from_markers(code_output)
        if metrics:
            return metrics

        # 策略2: 降级为传统正则匹配（兼容旧版 Coder 输出）
        return Flows._extract_metrics_by_regex(code_output)

    @classmethod
    def _extract_metrics_from_markers(cls, code_output: str) -> dict[str, float]:
        """从 ===METRICS_START=== / ===METRICS_END=== 标记块中提取指标"""
        pattern = rf"{cls.METRICS_START_MARKER}(.*?){cls.METRICS_END_MARKER}"
        blocks = re.findall(pattern, code_output, re.DOTALL)
        if not blocks:
            return {}

        metrics: dict[str, float] = {}
        # 指标行格式: "指标名: 数值" 或 "指标名 = 数值"
        line_pattern = r"^\s*([\w²\-]+)\s*[=:：]\s*(-?\d+\.?\d*)"
        for block in blocks:
            for line in block.strip().splitlines():
                match = re.match(line_pattern, line.strip())
                if match:
                    name = match.group(1).strip()
                    try:
                        value = float(match.group(2))
                        if name not in metrics:
                            metrics[name] = value
                    except ValueError:
                        continue
        return metrics

    @staticmethod
    def _extract_metrics_by_regex(code_output: str) -> dict[str, float]:
        """传统正则匹配方式提取指标（降级方案）"""
        metrics: dict[str, float] = {}
        for pattern, metric_name in Flows._METRIC_PATTERNS:
            if metric_name in metrics:
                continue
            match = re.search(pattern, code_output)
            if match:
                try:
                    metrics[metric_name] = float(match.group(1))
                except (ValueError, IndexError):
                    continue
        return metrics

    @staticmethod
    def build_cross_question_context(
        previous_results: dict[str, str],
        max_chars_per_question: int = 600,
    ) -> str:
        """构建跨问题结果上下文文本。

        将前序问题的关键结果和指标格式化为上下文提示，
        供后续问题的 Coder 或 Writer 参考，实现问题间的信息传递。

        Args:
            previous_results: 前序问题的结果摘要字典，键为问题标识（如 "ques1"）。
            max_chars_per_question: 每个问题的上下文最大字符数，避免 prompt 膨胀。

        Returns:
            格式化的跨问题上下文文本，如果无前序结果则返回空字符串。
        """
        if not previous_results:
            return ""

        parts: list[str] = [
            "【前序问题的求解结果（供参考和引用）】",
        ]
        for qkey, result_text in previous_results.items():
            truncated = result_text[:max_chars_per_question]
            if len(result_text) > max_chars_per_question:
                truncated += "..."
            parts.append(f"\n--- {qkey} 的结果 ---\n{truncated}")

        parts.append(
            "\n注意：可以引用上述前序问题的结果进行对比或衔接，"
            "但不要重复求解已完成的问题。"
        )
        return "\n".join(parts)

    @classmethod
    def extract_figures_from_code_output(
        cls,
        code_output: str | None,
    ) -> list[dict[str, str]]:
        """从代码输出中提取图表清单

        优先解析标准格式 ===FIGURE: filename.png | 描述===，
        若未匹配到任何结果，则降级解析旧格式 ===FIGURE===filename.png===。

        Args:
            code_output: Coder 的文本输出

        Returns:
            图表信息列表，每项包含 filename 和 description
        """
        if not code_output:
            return []

        # 标准格式解析: ===FIGURE: filename | description===
        figures: list[dict[str, str]] = []
        seen_filenames: set[str] = set()
        for match in re.finditer(cls.FIGURE_MARKER_PATTERN, code_output):
            filename = match.group(1).strip()
            figures.append({
                "filename": filename,
                "description": match.group(2).strip(),
            })
            seen_filenames.add(filename)

        # 旧格式降级解析: ===FIGURE===filename.png 或 ===FIGURE===filename.png===
        # 仅补充标准格式未覆盖的文件，避免重复
        for match in re.finditer(cls.FIGURE_LEGACY_PATTERN, code_output):
            filename = match.group(1).strip()
            if filename not in seen_filenames:
                figures.append({
                    "filename": filename,
                    "description": filename,
                })
                seen_filenames.add(filename)

        return figures

    @classmethod
    def extract_tables_from_code_output(
        cls,
        code_output: str | None,
    ) -> str:
        """从代码输出中提取结构化表格内容。

        解析 ===TABLE_START=== / ===TABLE_END=== 标记块，
        将所有表格内容拼接返回。

        Args:
            code_output: Coder 的文本输出

        Returns:
            提取到的表格文本，多个表格间以换行分隔；无表格时返回空字符串。
        """
        if not code_output:
            return ""

        pattern = rf"{cls.TABLE_START_MARKER}(.*?){cls.TABLE_END_MARKER}"
        blocks = re.findall(pattern, code_output, re.DOTALL)
        if not blocks:
            return ""

        return "\n\n".join(block.strip() for block in blocks if block.strip())

    @classmethod
    def extract_result_summaries(
        cls,
        code_output: str | None,
    ) -> list[dict[str, str]]:
        """从代码输出中提取结果摘要

        解析 ===RESULT_SUMMARY=== / ===RESULT_END=== 标记块。

        Args:
            code_output: Coder 的文本输出

        Returns:
            结果摘要列表，每项包含 question、model、conclusion
        """
        if not code_output:
            return []

        summaries: list[dict[str, str]] = []
        pattern = rf"{cls.RESULT_SUMMARY_START}(.*?){cls.RESULT_SUMMARY_END}"
        blocks = re.findall(pattern, code_output, re.DOTALL)

        for block in blocks:
            summary: dict[str, str] = {}
            for line in block.strip().splitlines():
                line = line.strip()
                if line.startswith("问题:") or line.startswith("问题："):
                    summary["question"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                elif line.startswith("使用模型:") or line.startswith("使用模型："):
                    summary["model"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                elif line.startswith("主要结论:") or line.startswith("主要结论："):
                    summary["conclusion"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            if summary:
                summaries.append(summary)
        return summaries
