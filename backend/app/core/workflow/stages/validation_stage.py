"""
验证阶段 - 使用 ValidationExpert 验证求解结果

职责:
  1. 从 ctx.solution_results 获取求解结果
  2. 从 ctx.artifacts["recommended_validation"] 获取推荐验证方法
  3. 从 ctx.artifacts["recommended_metrics"] 获取推荐评价指标
  4. 调用 ValidationExpert 进行验证
  5. 将验证报告写入 ctx.artifacts["validation_report"]
  6. 独立执行参数敏感性分析，写入 ctx.artifacts["sensitivity_analysis"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.agents.validation_expert import ValidationExpert
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.utils.json_parser import parse_json_safely
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class ValidationStage:
    """结果验证阶段（可选）"""

    @property
    def name(self) -> str:
        return "validation"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行求解结果验证"""
        await ctx.send_progress("正在验证求解结果...", 71)

        # 创建 ValidationExpert，复用 modeler 的 LLM
        validator = ValidationExpert(
            task_id=ctx.task_id,
            model=ctx.llms["modeler"],
        )

        # 收集求解结果作为验证输入
        model_results = self._collect_model_results(ctx)
        if not model_results:
            logger.warning("ValidationStage: 无求解结果可验证，跳过")
            return

        # 收集实验数据
        experiment_data = self._collect_experiment_data(ctx)

        # 获取推荐的评价指标
        evaluation_metrics = ctx.artifacts.get(ArtifactKeys.RECOMMENDED_METRICS, [])

        try:
            validation_report = await validator.execute(
                model_results=model_results,
                experiment_data=experiment_data,
                evaluation_metrics=evaluation_metrics,
            )

            # 将报告转为字典存储
            report_dict = validation_report.__dict__
            ctx.artifacts[ArtifactKeys.VALIDATION_REPORT] = report_dict

            # 提取验证状态
            overall = report_dict.get("overall_assessment", {})
            status = overall.get("validation_status", "未知")

            await ctx.send_progress(
                f"结果验证完成，状态: {status}", 73
            )
            logger.info("ValidationStage 完成: status=%s", status)

        except Exception as e:
            logger.error(
                "ValidationStage 验证失败: %s [task_id=%s]",
                e,
                ctx.task_id,
            )
            # award 模式下此 Stage 是必选的，必须传播异常
            if ctx.workflow_mode == "award":
                raise
            # 其他模式下是可选的，记录警告并保存部分结果
            logger.warning(
                "ValidationStage 为可选阶段，跳过失败继续执行"
            )
            ctx.artifacts[ArtifactKeys.VALIDATION_REPORT] = {
                "overall_assessment": {
                    "validation_status": "验证异常",
                    "error": str(e),
                },
            }

        # 敏感性分析（失败不中断）
        try:
            sensitivity_result = await self._run_sensitivity_analysis(ctx)
            if sensitivity_result:
                ctx.artifacts[ArtifactKeys.SENSITIVITY_ANALYSIS] = sensitivity_result
                logger.info("ValidationStage: 敏感性分析完成")
        except Exception as e:
            logger.warning("敏感性分析失败（非关键）: %s", e)

    async def _run_sensitivity_analysis(
        self, ctx: PipelineContext
    ) -> dict[str, Any] | None:
        """执行参数敏感性分析

        基于建模方案中的关键参数，分析参数变化对结果的影响。
        使用 LLM 生成敏感性分析报告（因为实际代码执行在 CoderStage 中）。

        Args:
            ctx: 管线上下文

        Returns:
            结构化的敏感性分析结果字典，无可用数据时返回 None
        """
        # 1. 从 modeler_response 提取关键参数
        modeler_response = ctx.modeler_response
        if not modeler_response:
            logger.info("敏感性分析跳过: 无建模方案数据")
            return None

        # 将建模方案转为文本摘要
        if hasattr(modeler_response, "__dict__"):
            modeler_text = str(modeler_response.__dict__)[:3000]
        else:
            modeler_text = str(modeler_response)[:3000]

        # 2. 从 solution_results 提取求解结果
        solution_results = ctx.solution_results
        if not solution_results:
            logger.info("敏感性分析跳过: 无求解结果")
            return None

        solution_summary_parts: list[str] = []
        for key, value in solution_results.items():
            if key in ("flows", "config_template"):
                continue
            if isinstance(value, dict):
                output = str(value.get("code_output", ""))[:500]
                success = value.get("success", False)
                solution_summary_parts.append(
                    f"[{key}] 成功={success}, 输出={output}"
                )
            else:
                solution_summary_parts.append(
                    f"[{key}] {str(value)[:500]}"
                )
        solution_text = "\n".join(solution_summary_parts)

        if not solution_text.strip():
            logger.info("敏感性分析跳过: 求解结果为空")
            return None

        await ctx.send_progress("正在执行参数敏感性分析...", 74)

        # 3. 构造 prompt 让 LLM 分析敏感性
        system_prompt = (
            "你是一位数学建模专家，擅长参数敏感性分析。"
            "请根据提供的建模方案和求解结果，分析模型中关键参数的敏感性。\n"
            "你需要评估:\n"
            "- 哪些参数最敏感（对结果影响最大）\n"
            "- 参数变化 +/-10%、+/-20% 对结果的影响方向和程度\n"
            "- 模型整体稳定性评估\n\n"
            "请严格按照以下 JSON 格式输出，不要输出其他内容:\n"
            "```json\n"
            "{\n"
            '    "sensitive_parameters": [\n'
            "        {\n"
            '            "parameter": "参数名",\n'
            '            "sensitivity_level": "高/中/低",\n'
            '            "impact_description": "该参数变化对结果的影响描述",\n'
            '            "recommended_range": "建议取值范围"\n'
            "        }\n"
            "    ],\n"
            '    "stability_assessment": "整体稳定性评估",\n'
            '    "recommendations": ["改进建议1", "改进建议2"]\n'
            "}\n"
            "```"
        )

        user_prompt = (
            f"## 建模方案\n{modeler_text}\n\n"
            f"## 求解结果\n{solution_text}\n\n"
            "请对以上模型进行参数敏感性分析，输出 JSON 格式结果。"
        )

        # 4. 调用 LLM（复用 modeler 实例）
        llm = ctx.llms.get("modeler")
        if not llm:
            logger.warning("敏感性分析跳过: 无可用的 modeler LLM 实例")
            return None

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm.ainvoke(messages)
        response_text = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )

        if not response_text or not response_text.strip():
            logger.warning("敏感性分析: LLM 返回空响应")
            return None

        # 5. 解析 JSON 响应（容错处理）
        default_result: dict[str, Any] = {
            "sensitive_parameters": [],
            "stability_assessment": "分析结果解析失败，请参考验证报告",
            "recommendations": [],
        }

        result = parse_json_safely(response_text, default=default_result)

        # 基本结构校验：确保关键字段存在
        if not isinstance(result, dict):
            logger.warning("敏感性分析: 解析结果不是字典类型")
            return default_result

        if "sensitive_parameters" not in result:
            result["sensitive_parameters"] = []
        if "stability_assessment" not in result:
            result["stability_assessment"] = "未提供"
        if "recommendations" not in result:
            result["recommendations"] = []

        return result

    @staticmethod
    def _collect_model_results(ctx: PipelineContext) -> dict[str, Any]:
        """从 ctx.solution_results 收集模型求解结果"""
        results: dict[str, Any] = {}

        solution = ctx.solution_results
        if not solution:
            return results

        # 收集各子问题的求解结果
        for key, value in solution.items():
            if key in ("flows", "config_template"):
                continue
            if isinstance(value, dict):
                results[key] = {
                    "success": value.get("success", False),
                    "code_output": str(value.get("code_output", ""))[:2000],
                    "remodel_attempts": value.get("remodel_attempts", 0),
                }
            else:
                results[key] = str(value)[:1000]

        return results

    @staticmethod
    def _collect_experiment_data(ctx: PipelineContext) -> dict[str, Any]:
        """收集实验数据上下文"""
        data: dict[str, Any] = {}

        # EDA 结果
        eda_result = ctx.artifacts.get(ArtifactKeys.EDA_RESULT, "")
        if eda_result:
            data["eda_summary"] = str(eda_result)[:2000]

        # 数据摘要
        data_summary = ctx.artifacts.get(ArtifactKeys.DATA_SUMMARY, "")
        if data_summary:
            data["data_summary"] = str(data_summary)[:1000]

        # 问题分析
        problem_analysis = ctx.artifacts.get(ArtifactKeys.PROBLEM_ANALYSIS)
        if problem_analysis:
            if hasattr(problem_analysis, "__dict__"):
                data["problem_analysis"] = str(problem_analysis.__dict__)[:1000]
            else:
                data["problem_analysis"] = str(problem_analysis)[:1000]

        # 推荐的验证方法
        recommended_validation = ctx.artifacts.get(ArtifactKeys.RECOMMENDED_VALIDATION, [])
        if recommended_validation:
            data["recommended_validation"] = recommended_validation

        return data
