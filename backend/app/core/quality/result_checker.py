"""
代码执行结果质量检测器
========================

对 CoderAgent 执行完毕后的代码输出进行轻量级质量检测，
检查输出是否包含有效的数值结果、评估指标、图表等关键产物。

设计原则：
- KISS: 基于正则和简单规则，不依赖 LLM 二次推理
- 快速: 全部为同步字符串分析，不阻塞主流程
- 非侵入: 检测结果写入 validation_metrics，不改变原有控制流
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResultQualityReport:
    """结果质量检测报告"""

    # 各维度得分 (0.0 ~ 1.0)
    has_numeric_output: bool = False       # 是否有数值输出
    has_eval_metrics: bool = False         # 是否有评估指标
    has_images: bool = False               # 是否生成了图表
    has_conclusion: bool = False           # 是否有结论性总结
    no_fatal_error: bool = True            # 是否无致命错误

    # 检测到的评估指标列表
    detected_metrics: list[str] = field(default_factory=list)
    # 问题和建议
    issues: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """加权总分 (0.0 ~ 1.0)"""
        weights = {
            "has_numeric_output": 0.25,
            "has_eval_metrics": 0.25,
            "has_images": 0.15,
            "has_conclusion": 0.10,
            "no_fatal_error": 0.25,
        }
        total = 0.0
        for attr, weight in weights.items():
            total += weight * (1.0 if getattr(self, attr) else 0.0)
        return round(total, 3)

    @property
    def passed(self) -> bool:
        """是否通过质量检测 (≥0.4 为通过)"""
        return self.score >= 0.4

    def to_dict(self) -> dict:
        """转为字典，用于填充 CoderToWriter.validation_metrics"""
        return {
            "score": self.score,
            "passed": self.passed,
            "has_numeric_output": self.has_numeric_output,
            "has_eval_metrics": self.has_eval_metrics,
            "has_images": self.has_images,
            "has_conclusion": self.has_conclusion,
            "no_fatal_error": self.no_fatal_error,
            "detected_metrics": self.detected_metrics,
            "issues": self.issues,
        }


class ResultQualityChecker:
    """
    代码执行结果质量检测器

    在 CoderAgent 完成任务后，对代码输出 (code_output) 和生成图片列表
    进行快速质量评估。
    """

    # 常见评估指标的正则模式
    METRIC_PATTERNS: list[tuple[str, str]] = [
        # 回归指标
        (r"R[²2]\s*[:=]\s*[\d.]+", "R²"),
        (r"(?i)r-?squared?\s*[:=]\s*[\d.]+", "R²"),
        (r"(?i)(?:rmse|RMSE)\s*[:=]\s*[\d.]+", "RMSE"),
        (r"(?i)(?:mse|MSE)\s*[:=]\s*[\d.]+", "MSE"),
        (r"(?i)(?:mae|MAE)\s*[:=]\s*[\d.]+", "MAE"),
        (r"(?i)(?:mape|MAPE)\s*[:=]\s*[\d.]+", "MAPE"),
        # 分类指标
        (r"(?i)(?:accuracy|准确率)\s*[:=]\s*[\d.]+", "Accuracy"),
        (r"(?i)(?:precision|精确率)\s*[:=]\s*[\d.]+", "Precision"),
        (r"(?i)(?:recall|召回率)\s*[:=]\s*[\d.]+", "Recall"),
        (r"(?i)(?:f1[\s_-]?score|F1)\s*[:=]\s*[\d.]+", "F1-Score"),
        (r"(?i)(?:auc|AUC)\s*[:=]\s*[\d.]+", "AUC"),
        # 聚类指标
        (r"(?i)(?:silhouette|轮廓系数)\s*[:=]\s*[\d.]+", "Silhouette"),
        (r"(?i)calinski", "Calinski-Harabasz"),
        # 优化指标
        (r"(?i)(?:目标函数|objective)\s*[:=]\s*[\d.]+", "Objective"),
        (r"(?i)(?:最优值|optimal)\s*[:=]\s*[\d.]+", "Optimal"),
        (r"(?i)(?:收敛|converge)", "Convergence"),
    ]

    # 致命错误模式
    FATAL_ERROR_PATTERNS: list[str] = [
        r"(?i)Traceback \(most recent call last\)",
        r"(?i)MemoryError",
        r"(?i)KeyboardInterrupt",
        r"(?i)FileNotFoundError.*(?:data|csv|xlsx|xls)",
        r"(?i)ModuleNotFoundError",
    ]

    # 结论性关键词
    CONCLUSION_KEYWORDS: list[str] = [
        "最终结论", "最优模型", "综合来看", "总结",
        "最佳", "推荐", "结论", "优于", "表现最好",
        "best model", "final result", "conclusion",
    ]

    def check(
        self,
        code_output: str,
        created_images: Optional[list[str]] = None,
        task_type: str = "question",
    ) -> ResultQualityReport:
        """
        执行结果质量检测

        Args:
            code_output: 代码执行的标准输出（print 内容）
            created_images: 生成的图片文件列表
            task_type: 任务类型 ("question" | "eda" | "sensitivity")

        Returns:
            ResultQualityReport 检测报告
        """
        report = ResultQualityReport()
        images = created_images or []

        if not code_output or not code_output.strip():
            report.no_fatal_error = True  # 空输出不算致命错误，但缺少内容
            report.issues.append("代码输出为空，未产生任何打印结果")
            return report

        # 1. 检测致命错误
        report.no_fatal_error = self._check_no_fatal_error(code_output, report)

        # 2. 检测数值输出
        report.has_numeric_output = self._check_numeric_output(code_output, report)

        # 3. 检测评估指标
        report.has_eval_metrics = self._check_eval_metrics(
            code_output, report, task_type
        )

        # 4. 检测图表
        report.has_images = self._check_images(images, report, task_type)

        # 5. 检测结论
        report.has_conclusion = self._check_conclusion(code_output, report)

        return report

    def _check_no_fatal_error(
        self, output: str, report: ResultQualityReport
    ) -> bool:
        """检查是否有致命错误（在输出的最后部分）"""
        # 只检查输出的最后 2000 字符，因为中间可能有已修复的错误
        tail = output[-2000:] if len(output) > 2000 else output

        for pattern in self.FATAL_ERROR_PATTERNS:
            if re.search(pattern, tail):
                report.issues.append(
                    f"代码输出末尾包含致命错误: {pattern.split(')')[-1].strip()}"
                )
                return False
        return True

    def _check_numeric_output(
        self, output: str, report: ResultQualityReport
    ) -> bool:
        """检查是否有有效的数值输出"""
        # 匹配包含数字的行（排除纯行号/索引）
        numeric_lines = re.findall(
            r"^.*\d+\.\d+.*$", output, re.MULTILINE
        )

        if len(numeric_lines) >= 3:
            return True

        # 宽松匹配：至少有一些数字
        any_numbers = re.findall(r"\d+\.?\d*", output)
        if len(any_numbers) >= 5:
            return True

        report.issues.append("代码输出中缺少有效的数值结果")
        return False

    def _check_eval_metrics(
        self, output: str, report: ResultQualityReport, task_type: str
    ) -> bool:
        """检查是否有评估指标"""
        detected = []

        for pattern, metric_name in self.METRIC_PATTERNS:
            if re.search(pattern, output):
                if metric_name not in detected:
                    detected.append(metric_name)

        report.detected_metrics = detected

        # EDA 任务不强制要求评估指标
        if task_type == "eda":
            return len(detected) >= 0  # EDA 总是通过
        # 敏感性分析检查特定指标
        elif task_type == "sensitivity":
            if len(detected) >= 1:
                return True
            # 敏感性分析可能使用其他表述
            sensitivity_keywords = ["敏感", "扰动", "变动", "影响", "sensitivity"]
            if any(kw in output.lower() for kw in sensitivity_keywords):
                return True
            report.issues.append("敏感性分析输出中未检测到评估指标或分析结果")
            return False
        else:
            # 普通问题求解，至少需要 1 个评估指标
            if len(detected) >= 1:
                return True
            report.issues.append(
                "代码输出中未检测到评估指标（如 R², RMSE, Accuracy, F1 等）"
            )
            return False

    def _check_images(
        self,
        images: list[str],
        report: ResultQualityReport,
        task_type: str,
    ) -> bool:
        """检查是否生成了图表"""
        if images and len(images) >= 1:
            return True

        # EDA 和普通问题都应该有图表
        if task_type != "sensitivity":
            report.issues.append("未生成任何可视化图表")
        return False

    def _check_conclusion(
        self, output: str, report: ResultQualityReport
    ) -> bool:
        """检查是否有结论性总结"""
        for keyword in self.CONCLUSION_KEYWORDS:
            if keyword in output:
                return True

        report.issues.append("代码输出中缺少结论性总结（建议使用 print() 输出最终结论）")
        return False
