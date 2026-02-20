"""
Sensitivity Analyzer - 敏感性分析自动化
========================================

功能：
1. 单参数敏感性分析（OAT - One At a Time）
2. 多参数敏感性分析（全局敏感性）
3. 自动生成敏感性分析可视化
4. 生成敏感性分析报告

关键特性：
- 自动识别关键参数
- 生成专业的敏感性分析图表
- 提供参数稳定性评估
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.llm.llm_gateway import chat_completion
from app.schemas.contracts import SensitivityResult
from app.utils.log_util import logger


class SensitivityMethod(Enum):
    """敏感性分析方法"""

    OAT = "oat"  # One-At-a-Time
    MORRIS = "morris"  # Morris方法
    SOBOL = "sobol"  # Sobol方法
    LOCAL = "local"  # 局部敏感性
    TORNADO = "tornado"  # 龙卷风图


class StabilityRating(Enum):
    """稳定性评级"""

    STABLE = "stable"  # 稳定：变化<5%
    MODERATE = "moderate"  # 中等：变化5-20%
    SENSITIVE = "sensitive"  # 敏感：变化>20%


@dataclass
class ParameterSpec:
    """参数规格"""

    name: str
    display_name: str  # 显示名称
    base_value: float  # 基准值
    min_value: float  # 最小值
    max_value: float  # 最大值
    unit: str = ""  # 单位
    description: str = ""  # 描述


@dataclass
class SensitivityAnalysisResult:
    """敏感性分析结果"""

    parameter: str
    display_name: str
    base_value: float
    tested_values: List[float]
    result_values: List[float]
    impact_score: float  # 影响程度 0-1
    elasticity: float  # 弹性系数
    stability_rating: StabilityRating
    max_change_percent: float
    interpretation: str
    visualization_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SensitivityReport:
    """敏感性分析报告"""

    run_id: str
    model_name: str
    base_output: float
    results: List[SensitivityAnalysisResult]
    critical_parameters: List[str]  # 关键参数
    stable_parameters: List[str]  # 稳定参数
    overall_stability: StabilityRating
    recommendations: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SensitivityAnalyzer:
    """敏感性分析器"""

    # 默认变化范围
    DEFAULT_VARIATION_RANGE = [-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3]  # ±30%

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]

    def analyze_oat(
        self,
        model_func: Callable[..., float],
        parameters: List[ParameterSpec],
        base_params: Dict[str, float],
        variation_percents: Optional[List[float]] = None,
        output_name: str = "目标值",
    ) -> SensitivityReport:
        """
        单参数敏感性分析（One-At-a-Time）

        Args:
            model_func: 模型函数，接收参数字典，返回结果
            parameters: 参数规格列表
            base_params: 基准参数值
            variation_percents: 变化百分比列表
            output_name: 输出变量名称

        Returns:
            敏感性分析报告
        """
        if variation_percents is None:
            variation_percents = self.DEFAULT_VARIATION_RANGE

        # 计算基准输出
        base_output = model_func(**base_params)

        results: List[SensitivityAnalysisResult] = []

        for param in parameters:
            result = self._analyze_single_parameter(
                model_func=model_func,
                param=param,
                base_params=base_params,
                base_output=base_output,
                variation_percents=variation_percents,
            )
            results.append(result)

        # 按影响程度排序
        results.sort(key=lambda x: x.impact_score, reverse=True)

        # 识别关键参数和稳定参数
        critical_params = [
            r.parameter
            for r in results
            if r.stability_rating == StabilityRating.SENSITIVE
        ]
        stable_params = [
            r.parameter for r in results if r.stability_rating == StabilityRating.STABLE
        ]

        # 评估整体稳定性
        if len(critical_params) > len(parameters) / 3:
            overall_stability = StabilityRating.SENSITIVE
        elif len(critical_params) == 0:
            overall_stability = StabilityRating.STABLE
        else:
            overall_stability = StabilityRating.MODERATE

        # 生成建议
        recommendations = self._generate_recommendations(results, critical_params)

        return SensitivityReport(
            run_id=self.run_id,
            model_name="",
            base_output=base_output,
            results=results,
            critical_parameters=critical_params,
            stable_parameters=stable_params,
            overall_stability=overall_stability,
            recommendations=recommendations,
        )

    def _analyze_single_parameter(
        self,
        model_func: Callable[..., float],
        param: ParameterSpec,
        base_params: Dict[str, float],
        base_output: float,
        variation_percents: List[float],
    ) -> SensitivityAnalysisResult:
        """分析单个参数"""
        tested_values: List[float] = []
        result_values: List[float] = []

        base_value = param.base_value

        for variation in variation_percents:
            # 计算测试值
            test_value = base_value * (1 + variation)

            # 确保在范围内
            test_value = max(param.min_value, min(param.max_value, test_value))

            # 构建测试参数
            test_params = base_params.copy()
            test_params[param.name] = test_value

            # 运行模型
            try:
                result = model_func(**test_params)
            except Exception as e:
                logger.warning("Model failed for %s=%s: %s", param.name, test_value, e)
                result = base_output

            tested_values.append(test_value)
            result_values.append(result)

        # 计算变化统计
        result_changes = [
            abs((r - base_output) / base_output * 100) if base_output != 0 else 0
            for r in result_values
        ]
        max_change = max(result_changes) if result_changes else 0

        # 计算弹性系数（输出变化率/输入变化率）
        if len(variation_percents) > 1 and base_output != 0:
            len(variation_percents) // 2
            if variation_percents[-1] != 0:
                output_change = (result_values[-1] - base_output) / base_output
                input_change = variation_percents[-1]
                elasticity = (
                    abs(output_change / input_change) if input_change != 0 else 0
                )
            else:
                elasticity = 0
        else:
            elasticity = 0

        # 影响程度评分
        impact_score = min(1.0, max_change / 50)  # 50%变化对应1.0

        # 稳定性评级
        if max_change < 5:
            stability_rating = StabilityRating.STABLE
        elif max_change < 20:
            stability_rating = StabilityRating.MODERATE
        else:
            stability_rating = StabilityRating.SENSITIVE

        # 生成解释
        interpretation = self._generate_interpretation(
            param.display_name, elasticity, max_change, stability_rating
        )

        return SensitivityAnalysisResult(
            parameter=param.name,
            display_name=param.display_name,
            base_value=base_value,
            tested_values=tested_values,
            result_values=result_values,
            impact_score=impact_score,
            elasticity=elasticity,
            stability_rating=stability_rating,
            max_change_percent=max_change,
            interpretation=interpretation,
            visualization_data={
                "x": tested_values,
                "y": result_values,
                "base_x": base_value,
                "base_y": base_output,
            },
        )

    def _generate_interpretation(
        self,
        param_name: str,
        elasticity: float,
        max_change: float,
        stability: StabilityRating,
    ) -> str:
        """生成敏感性解释"""
        if stability == StabilityRating.STABLE:
            return f"{param_name}变化±30%时，结果变化不超过{max_change:.1f}%，模型对该参数不敏感，参数估计误差对结果影响较小。"
        elif stability == StabilityRating.MODERATE:
            return f"{param_name}变化±30%时，结果最大变化{max_change:.1f}%，弹性系数为{elasticity:.2f}，模型对该参数有一定敏感性，需关注其取值准确性。"
        else:
            return f"{param_name}变化±30%时，结果变化高达{max_change:.1f}%，弹性系数为{elasticity:.2f}，模型对该参数高度敏感，该参数的准确估计对结果至关重要。"

    def _generate_recommendations(
        self,
        results: List[SensitivityAnalysisResult],
        critical_params: List[str],
    ) -> List[str]:
        """生成建议"""
        recommendations: List[str] = []

        if critical_params:
            recommendations.append(
                f"需重点关注以下关键参数的取值准确性：{', '.join(critical_params)}"
            )

        sensitive_count = sum(
            1 for r in results if r.stability_rating == StabilityRating.SENSITIVE
        )
        if sensitive_count > 0:
            recommendations.append(
                f"模型对{sensitive_count}个参数高度敏感，建议在实际应用中进行多情景分析。"
            )

        stable_count = sum(
            1 for r in results if r.stability_rating == StabilityRating.STABLE
        )
        if stable_count > 0:
            recommendations.append(
                f"有{stable_count}个参数对结果影响较小，在参数估计时可适当放宽精度要求。"
            )

        if not critical_params:
            recommendations.append("模型整体稳定性良好，结果对参数变化不敏感。")

        return recommendations

    def generate_tornado_data(self, report: SensitivityReport) -> Dict[str, Any]:
        """
        生成龙卷风图数据

        Args:
            report: 敏感性分析报告

        Returns:
            龙卷风图数据
        """
        tornado_data = {
            "parameters": [],
            "low_values": [],
            "high_values": [],
            "base_value": report.base_output,
        }

        for result in report.results:
            if len(result.result_values) > 1:
                tornado_data["parameters"].append(result.display_name)
                tornado_data["low_values"].append(min(result.result_values))
                tornado_data["high_values"].append(max(result.result_values))

        return tornado_data

    def generate_spider_data(self, report: SensitivityReport) -> Dict[str, Any]:
        """
        生成蜘蛛图数据

        Args:
            report: 敏感性分析报告

        Returns:
            蜘蛛图数据
        """
        spider_data = {
            "parameters": [],
            "series": [],
        }

        # 获取共同的变化百分比
        if report.results and len(report.results[0].tested_values) > 0:
            base_value = report.results[0].base_value
            variations = [
                (v - base_value) / base_value * 100
                for v in report.results[0].tested_values
            ]
        else:
            variations = self.DEFAULT_VARIATION_RANGE

        spider_data["variations"] = [f"{v:+.0f}%" for v in variations]

        for result in report.results:
            series = {
                "name": result.display_name,
                "values": [
                    (r - report.base_output) / report.base_output * 100
                    if report.base_output != 0
                    else 0
                    for r in result.result_values
                ],
            }
            spider_data["series"].append(series)

        return spider_data

    def format_report_for_paper(
        self,
        report: SensitivityReport,
        include_figures: bool = True,
    ) -> str:
        """
        将敏感性分析报告格式化为论文格式

        Args:
            report: 敏感性分析报告
            include_figures: 是否包含图表说明

        Returns:
            格式化的文本
        """
        lines: List[str] = []

        lines.append("## 敏感性分析\n")

        lines.append("为验证模型的稳健性，本文对关键参数进行敏感性分析，")
        lines.append("考察参数变化对模型结果的影响。\n")

        # 方法说明
        lines.append("### 分析方法\n")
        lines.append("采用单因素敏感性分析方法（One-At-a-Time），")
        lines.append("在其他参数保持基准值不变的情况下，")
        lines.append("将各参数在基准值的±30%范围内变化，")
        lines.append("观察目标值的变化情况。\n")

        # 结果表格
        lines.append("\n### 分析结果\n")
        lines.append("| 参数 | 基准值 | 弹性系数 | 最大变化 | 稳定性 |")
        lines.append("|------|--------|----------|----------|--------|")

        for result in report.results:
            stability_str = {
                StabilityRating.STABLE: "稳定",
                StabilityRating.MODERATE: "中等",
                StabilityRating.SENSITIVE: "敏感",
            }.get(result.stability_rating, "未知")

            lines.append(
                f"| {result.display_name} | {result.base_value:.4g} | "
                f"{result.elasticity:.2f} | {result.max_change_percent:.1f}% | {stability_str} |"
            )

        # 结果分析
        lines.append("\n### 结果分析\n")

        if report.critical_parameters:
            lines.append(
                f"**关键参数**：{', '.join(report.critical_parameters)}对结果影响显著，"
                f"需确保这些参数的估计准确性。\n"
            )

        for result in report.results:
            if result.stability_rating == StabilityRating.SENSITIVE:
                lines.append(f"- {result.interpretation}\n")

        # 整体评估
        stability_map = {
            StabilityRating.STABLE: "良好",
            StabilityRating.MODERATE: "一般",
            StabilityRating.SENSITIVE: "较差",
        }
        lines.append(
            f"\n模型整体稳定性{stability_map.get(report.overall_stability, '未知')}。"
        )

        # 建议
        if report.recommendations:
            lines.append("\n### 建议\n")
            for rec in report.recommendations:
                lines.append(f"- {rec}\n")

        return "\n".join(lines)

    async def auto_analyze(
        self,
        problem_description: str,
        parameters_description: str,
        base_output: float,
    ) -> Tuple[List[ParameterSpec], str]:
        """
        自动分析问题，识别需要进行敏感性分析的参数

        Args:
            problem_description: 问题描述
            parameters_description: 参数描述
            base_output: 基准输出值

        Returns:
            (参数规格列表, 分析建议)
        """
        prompt = f"""分析以下数学建模问题，识别需要进行敏感性分析的参数：

## 问题描述
{problem_description}

## 参数描述
{parameters_description}

## 基准输出值
{base_output}

请识别3-6个关键参数进行敏感性分析，以JSON格式返回：
{{
    "parameters": [
        {{
            "name": "参数变量名",
            "display_name": "参数显示名",
            "base_value": 100,
            "min_value": 50,
            "max_value": 150,
            "unit": "单位",
            "description": "参数描述"
        }}
    ],
    "analysis_suggestion": "敏感性分析建议"
}}"""

        response = await chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "你是数学建模专家，擅长设计敏感性分析方案。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            run_id=self.run_id,
            agent_id="sensitivity_analyzer",
        )

        parameters: List[ParameterSpec] = []
        suggestion = ""

        try:
            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response.content[json_start:json_end])

                for p in data.get("parameters", []):
                    parameters.append(
                        ParameterSpec(
                            name=p.get("name", ""),
                            display_name=p.get("display_name", ""),
                            base_value=float(p.get("base_value", 0)),
                            min_value=float(p.get("min_value", 0)),
                            max_value=float(p.get("max_value", 0)),
                            unit=p.get("unit", ""),
                            description=p.get("description", ""),
                        )
                    )

                suggestion = data.get("analysis_suggestion", "")
        except json.JSONDecodeError:
            logger.warning("Failed to parse auto-analyze response")

        return parameters, suggestion


def to_sensitivity_result(result: SensitivityAnalysisResult) -> SensitivityResult:
    """转换为标准 SensitivityResult 格式"""
    return SensitivityResult(
        parameter=result.parameter,
        original_value=result.base_value,
        range_tested=result.tested_values,
        result_values=result.result_values,
        impact_score=result.impact_score,
        stability_rating=result.stability_rating.value,
        visualization_path=None,
        interpretation=result.interpretation,
    )


# 便捷函数
def run_sensitivity_analysis(
    model_func: Callable[..., float],
    parameters: List[ParameterSpec],
    base_params: Dict[str, float],
    run_id: Optional[str] = None,
) -> SensitivityReport:
    """
    便捷函数：运行敏感性分析

    Args:
        model_func: 模型函数
        parameters: 参数规格列表
        base_params: 基准参数
        run_id: 运行ID

    Returns:
        敏感性分析报告
    """
    analyzer = SensitivityAnalyzer(run_id=run_id)
    return analyzer.analyze_oat(
        model_func=model_func,
        parameters=parameters,
        base_params=base_params,
    )
