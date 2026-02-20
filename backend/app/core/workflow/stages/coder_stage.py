"""
代码求解阶段 - CoderAgent 执行代码并求解各子问题

职责:
  1. 根据 Modeler 方案和子问题依赖关系分组
  2. 同组内独立子问题可并行执行（各自隔离的 Coder + Interpreter）
  3. 支持反馈环路: Coder 失败时回传 Modeler 修订方案
  4. 每题求解后串行执行 WriterAgent 写入论文
  5. 将求解结果写入 ctx.solution_results
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app.config.setting import settings
from app.core.agents import CoderAgent
from app.core.flows import Flows
from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.core.workflow.stages.stage_constants import MAX_REMODEL_ATTEMPTS
from app.schemas.A2A import CoderFeedbackToModeler
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.base_interpreter import BaseCodeInterpreter
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.utils.common_utils import get_config_template
from app.core.prompts import build_coder_prompt_with_templates
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class CoderStage:
    """代码求解阶段 - 支持依赖感知的并行执行"""

    MAX_REMODEL_ATTEMPTS: int = MAX_REMODEL_ATTEMPTS

    @property
    def name(self) -> str:
        return "solve"

    async def execute(self, ctx: PipelineContext) -> None:
        """执行代码求解（错误处理层）"""
        try:
            await self._do_execute(ctx)
        except Exception:
            logger.error(
                "CoderStage 执行失败, task_id=%s",
                ctx.task_id,
                exc_info=True,
            )
            raise

    async def _do_execute(self, ctx: PipelineContext) -> None:
        """执行代码求解（业务逻辑）"""
        flows = Flows(ctx.questions)
        solution_flows = flows.get_solution_flows(
            ctx.questions, ctx.modeler_response
        )
        config_template = get_config_template(ctx.problem.comp_template, ctx.problem.format_output)

        # 获取依赖关系并分组
        dependencies = None
        if hasattr(ctx.coordinator_response, "sub_problem_dependencies"):
            dependencies = ctx.coordinator_response.sub_problem_dependencies

        parallel_groups = Flows.get_parallel_groups(
            solution_flows, dependencies
        )
        logger.info("并行分组结果: %s", parallel_groups)

        total_solution_steps = len(solution_flows)
        writer_agent = ctx.agents["writer"]
        modeler_agent = ctx.agents["modeler"]

        completed_outputs: dict[str, str] = {}
        solution_results: dict[str, Any] = {}
        step_idx = 0

        # 收集并行分支创建的 interpreter，最后统一清理
        parallel_interpreters: list[BaseCodeInterpreter] = []

        for group_idx, group in enumerate(parallel_groups):
            group_size = len(group)
            is_parallel = group_size > 1

            if is_parallel:
                await ctx.send_progress(
                    f"并行求解组 {group_idx + 1}: "
                    f"{', '.join(group)} ({group_size} 题并行)",
                    40 + (step_idx / total_solution_steps) * 30,
                )

            if is_parallel:
                # 并行执行 Coder
                coder_tasks = []
                coder_contexts: list[
                    tuple[str, CoderAgent, BaseCodeInterpreter]
                ] = []

                for key in group:
                    coder_agent, code_interpreter = (
                        await self._create_isolated_coder(ctx, key)
                    )
                    parallel_interpreters.append(code_interpreter)
                    coder_contexts.append(
                        (key, coder_agent, code_interpreter)
                    )

                    flow_meta = solution_flows[key]
                    progress = 40 + (step_idx / total_solution_steps) * 30

                    coder_tasks.append(
                        self._solve_coder_only(
                            ctx=ctx,
                            key=key,
                            flow_meta=flow_meta,
                            coder_agent=coder_agent,
                            code_interpreter=code_interpreter,
                            modeler_agent=modeler_agent,
                            modeler_response=ctx.modeler_response,
                            completed_outputs=completed_outputs,
                            progress_base=progress,
                        )
                    )
                    step_idx += 1

                coder_results = await asyncio.gather(
                    *coder_tasks, return_exceptions=True
                )

                # 收集结果，串行执行写作
                for i, result in enumerate(coder_results):
                    key, _coder_agent, code_interpreter = coder_contexts[i]

                    if isinstance(result, Exception):
                        logger.error("并行求解 %s 异常: %s", key, result)
                        solution_results[key] = {
                            "success": False,
                            "error": str(result),
                        }
                        continue

                    if not result.get("success"):
                        solution_results[key] = result
                        continue

                    if result.get("code_output"):
                        completed_outputs[key] = result["code_output"]

                    # 串行写作
                    try:
                        writer_prompt = flows.get_writer_prompt(
                            key,
                            result["coder_response"].code_response,
                            code_interpreter,
                            config_template,
                        )
                        progress = (
                            40 + (step_idx / total_solution_steps) * 30
                        )
                        await ctx.send_progress(
                            f"正在撰写: {key}", progress + 5
                        )
                        writer_response = await writer_agent.run(
                            writer_prompt,
                            available_images=result[
                                "coder_response"
                            ].created_images,
                            sub_title=key,
                        )
                        ctx.user_output.set_res(key, writer_response)

                        solution_results[key] = {
                            "coder_response": result["coder_response"],
                            "writer_response": writer_response,
                            "remodel_attempts": result.get(
                                "remodel_attempts", 0
                            ),
                            "success": True,
                        }
                    except Exception as e:
                        logger.error("[task_id=%s] 写作 %s 失败: %s", ctx.task_id, key, e, exc_info=True)
                        solution_results[key] = {
                            "success": False,
                            "error": str(e),
                        }

            else:
                # 串行组
                for key in group:
                    step_idx += 1
                    flow_meta = solution_flows[key]
                    progress = 40 + (step_idx / total_solution_steps) * 30

                    result = await self._solve_single_question(
                        ctx=ctx,
                        key=key,
                        flow_meta=flow_meta,
                        coder_agent=ctx.agents["coder"],
                        code_interpreter=ctx.code_interpreter,
                        modeler_agent=modeler_agent,
                        writer_agent=writer_agent,
                        modeler_response=ctx.modeler_response,
                        completed_outputs=completed_outputs,
                        flows=flows,
                        config_template=config_template,
                        progress_base=progress,
                    )
                    solution_results[key] = result
                    if result.get("success") and result.get("code_output"):
                        completed_outputs[key] = result["code_output"]

        # 清理主代码解释器
        if ctx.code_interpreter:
            await ctx.code_interpreter.cleanup()
            ctx.code_interpreter = None

        # 清理并行分支的解释器
        for interp in parallel_interpreters:
            try:
                await interp.cleanup()
            except Exception as e:
                logger.warning("清理并行 interpreter 失败: %s", e)

        ctx.solution_results = {
            "results": solution_results,
            "flows": flows,
            "config_template": config_template,
        }

        # 聚合所有子问题的结构化标记解析结果到 ctx.artifacts
        all_metrics: dict[str, dict[str, float]] = {}
        all_figures: dict[str, list[dict[str, str]]] = {}
        all_summaries: dict[str, list[dict[str, str]]] = {}

        for key, result in solution_results.items():
            if not result.get("success"):
                continue
            if result.get("parsed_metrics"):
                all_metrics[key] = result["parsed_metrics"]
            if result.get("parsed_figures"):
                all_figures[key] = result["parsed_figures"]
            if result.get("parsed_summaries"):
                all_summaries[key] = result["parsed_summaries"]

        if all_metrics:
            ctx.artifacts[ArtifactKeys.CODE_METRICS] = all_metrics
            logger.info(
                "CoderStage: 提取评估指标 (%d 个子问题)", len(all_metrics)
            )
        if all_figures:
            ctx.artifacts[ArtifactKeys.CODE_FIGURES] = all_figures
            logger.info(
                "CoderStage: 提取图表清单 (%d 个子问题)", len(all_figures)
            )
        if all_summaries:
            ctx.artifacts[ArtifactKeys.RESULT_SUMMARIES] = all_summaries
            logger.info(
                "CoderStage: 提取结论摘要 (%d 个子问题)", len(all_summaries)
            )

    # ==================== 私有辅助方法 ====================

    @staticmethod
    def _extract_model_names(text: str) -> list[str]:
        """从建模方案文本中提取模型名称关键词"""
        # 常见模型名称关键词（按类别分组）
        keywords = [
            # ---- 优化类 ----
            "线性规划", "LP", "linear_programming",
            "整数规划", "MILP", "0-1规划", "integer_programming",
            "非线性规划", "NLP", "nonlinear_programming",
            "NSGA-II", "多目标优化", "Pareto", "nsga2",
            "模拟退火", "SA", "simulated_annealing",
            "粒子群", "PSO", "particle_swarm",
            "遗传算法", "GA", "genetic_algorithm",
            "蒙特卡洛", "Monte Carlo", "monte_carlo", "随机模拟",
            # ---- 预测类 ----
            "ARIMA", "SARIMA", "时间序列", "time_series",
            "Prophet", "prophet", "Facebook Prophet",
            "指数平滑", "Holt-Winters", "exponential_smoothing", "ETS",
            "XGBoost", "LightGBM", "GBDT", "梯度提升",
            "随机森林", "random_forest",
            "神经网络", "BP神经网络", "neural_network", "MLP",
            "灰色预测", "GM(1,1)", "grey_prediction",
            # ---- 分类类 ----
            "逻辑回归", "Logistic", "logistic_regression", "二分类",
            "决策树", "Decision Tree", "decision_tree",
            "CART", "ID3", "C4.5",
            "Random Forest", "RF", "集成学习",
            "SVM", "支持向量机", "SVC", "Support Vector",
            # ---- 聚类类 ----
            "K-means", "KMeans", "kmeans", "K均值",
            "DBSCAN", "聚类", "基于密度",
            "层次聚类", "Hierarchical", "hierarchical_clustering", "Ward",
            "GMM", "高斯混合", "gaussian_mixture",
            "EM算法", "GaussianMixture",
            # ---- 评价类 ----
            "AHP", "TOPSIS", "熵权法", "层次分析",
            "模糊评价", "模糊综合评价", "fuzzy_evaluation",
            "PCA", "主成分分析", "降维",
            "DEA", "数据包络分析", "data_envelopment_analysis",
            "entropy_weight", "客观赋权",
            # ---- 微分方程 ----
            "ODE", "常微分方程", "微分方程", "动力系统", "数值积分",
            "Lotka-Volterra", "捕食模型", "种群动力学", "生态模型", "捕食者",
            "SIR", "SEIR",
            "传染病模型", "感染模型", "流行病",
            "潜伏期", "隔离模型", "传染病扩展",
            # ---- 动态规划 ----
            "动态规划", "背包", "Knapsack", "knapsack",
            "LCS", "最长公共子序列", "子序列匹配", "序列比对",
            "马尔可夫", "Markov", "markov", "转移矩阵", "随机过程",
            "资源分配", "多阶段决策", "DP资源", "资源优化",
            # ---- 图论/路径 ----
            "TSP", "最短路径", "Dijkstra", "Floyd",
            "旅行商", "路径优化", "shortest_path",
            # ---- 统计/验证 ----
            "灰色关联", "GRA", "Grey Relational", "灰色系统",
            "灰色模型", "Grey Prediction",
            "假设检验", "t检验", "卡方检验", "ANOVA",
            "显著性检验", "统计检验",
            "贝叶斯", "Bayesian", "后验推断", "先验",
            "交叉验证", "cross_validation", "模型验证",
            "敏感性分析", "sensitivity_analysis", "参数分析",
            "bootstrap", "Bootstrap", "置信区间",
        ]
        found = []
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                found.append(kw)
        return found

    async def _create_isolated_coder(
        self, ctx: PipelineContext, question_key: str
    ) -> tuple[CoderAgent, BaseCodeInterpreter]:
        """为并行分支创建隔离的 CoderAgent + CodeInterpreter"""
        notebook_serializer = NotebookSerializer(
            work_dir=ctx.work_dir,
            notebook_name=f"notebook_{question_key}.ipynb",
        )
        code_interpreter = await create_interpreter(
            kind="auto",
            task_id=ctx.task_id,
            work_dir=ctx.work_dir,
            notebook_serializer=notebook_serializer,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
        )
        coder_llm = ctx.llm_factory.get_single_llm("coder")
        coder_agent = CoderAgent(
            task_id=ctx.task_id,
            model=coder_llm,
            work_dir=ctx.work_dir,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            code_interpreter=code_interpreter,
            enable_memory_system=settings.ENABLE_MEMORY_SYSTEM,
            comp_template=ctx.problem.comp_template,
        )
        return coder_agent, code_interpreter

    async def _solve_single_question(
        self,
        ctx: PipelineContext,
        key: str,
        flow_meta: dict,
        coder_agent: CoderAgent,
        code_interpreter: BaseCodeInterpreter,
        modeler_agent: Any,
        writer_agent: Any,
        modeler_response: Any,
        completed_outputs: dict[str, str],
        flows: Flows,
        config_template: dict,
        progress_base: float,
    ) -> dict:
        """执行单个子问题的求解 + 写作"""
        try:
            await ctx.send_progress(f"正在求解: {key}", progress_base)

            core_result = await self._execute_coder_core(
                ctx=ctx,
                key=key,
                flow_meta=flow_meta,
                coder_agent=coder_agent,
                code_interpreter=code_interpreter,
                modeler_agent=modeler_agent,
                modeler_response=modeler_response,
                completed_outputs=completed_outputs,
                progress_base=progress_base,
            )

            coder_response = core_result["coder_response"]

            # 写作
            writer_prompt = flows.get_writer_prompt(
                key,
                coder_response.code_response,
                code_interpreter,
                config_template,
            )
            await ctx.send_progress(
                f"正在撰写: {key}", progress_base + 5
            )
            writer_response = await writer_agent.run(
                writer_prompt,
                available_images=coder_response.created_images,
                sub_title=key,
            )
            ctx.user_output.set_res(key, writer_response)

            return {
                **core_result,
                "writer_response": writer_response,
                "success": True,
            }

        except Exception as e:
            logger.error("求解 %s 失败 [task_id=%s]: %s", key, ctx.task_id, e)
            await redis_manager.publish_message(
                ctx.task_id,
                SystemMessage(
                    content=f"警告: {key} 求解遇到问题，已跳过",
                    type="warning",
                ),
            )
            return {"success": False, "error": str(e)}

    async def _solve_coder_only(
        self,
        ctx: PipelineContext,
        key: str,
        flow_meta: dict,
        coder_agent: CoderAgent,
        code_interpreter: BaseCodeInterpreter,
        modeler_agent: Any,
        modeler_response: Any,
        completed_outputs: dict[str, str],
        progress_base: float,
    ) -> dict:
        """仅执行 Coder 求解（并行安全版本，不含写作）"""
        try:
            core_result = await self._execute_coder_core(
                ctx=ctx,
                key=key,
                flow_meta=flow_meta,
                coder_agent=coder_agent,
                code_interpreter=code_interpreter,
                modeler_agent=modeler_agent,
                modeler_response=modeler_response,
                completed_outputs=completed_outputs,
                progress_base=progress_base,
            )
            return {**core_result, "success": True}

        except Exception as e:
            logger.error("[并行] 求解 %s 失败 [task_id=%s]: %s", key, ctx.task_id, e)
            return {"success": False, "error": str(e)}

    async def _execute_coder_core(
        self,
        ctx: PipelineContext,
        key: str,
        flow_meta: dict,
        coder_agent: CoderAgent,
        code_interpreter: BaseCodeInterpreter,
        modeler_agent: Any,
        modeler_response: Any,
        completed_outputs: dict[str, str],
        progress_base: float,
    ) -> dict:
        """执行 Coder 核心逻辑（prompt构建 -> 求解 -> remodel -> 输出收集 -> 标记解析）

        Returns:
            包含 coder_response, remodel_attempts, code_output,
            parsed_metrics, parsed_figures, parsed_summaries 的字典
        """
        context = Flows.build_cross_question_context(completed_outputs)
        current_model_config = None
        if modeler_response.model_configs:
            current_model_config = modeler_response.model_configs.get(key)

        coder_prompt = Flows.build_coder_prompt(
            flow_meta,
            context=context,
            model_config=current_model_config,
        )
        # 注入代码模板
        try:
            model_names_for_q = self._extract_model_names(
                str(flow_meta.get("solution", ""))
            )
            if model_names_for_q:
                coder_prompt = build_coder_prompt_with_templates(
                    coder_prompt, model_names_for_q
                )
        except Exception as e:
            logger.debug("代码模板注入跳过: %s", e)

        coder_response = await coder_agent.run(
            prompt=coder_prompt, subtask_title=key
        )

        # 反馈环路
        remodel_attempt = 0
        while (
            coder_response.needs_remodel
            and remodel_attempt < self.MAX_REMODEL_ATTEMPTS
        ):
            remodel_attempt += 1
            logger.info(
                "子任务 %s 需要重新建模 (第 %d/%d 次)",
                key,
                remodel_attempt,
                self.MAX_REMODEL_ATTEMPTS,
            )
            coder_response = await self._remodel_and_retry(
                ctx=ctx,
                key=key,
                flow_meta=flow_meta,
                coder_agent=coder_agent,
                modeler_agent=modeler_agent,
                modeler_response=modeler_response,
                coder_response=coder_response,
                context=context,
                remodel_attempt=remodel_attempt,
                progress_base=progress_base,
            )

        # 收集代码输出
        code_output = ""
        try:
            code_output = code_interpreter.get_code_output(key)
        except Exception:
            logger.debug("获取 %s 的代码输出失败，跳过", key)

        # 解析结构化标记（指标、图表、结论）
        parsed_metrics = Flows.extract_metrics_from_code_output(code_output)
        parsed_figures = Flows.extract_figures_from_code_output(code_output)
        parsed_summaries = Flows.extract_result_summaries(code_output)

        return {
            "coder_response": coder_response,
            "remodel_attempts": remodel_attempt,
            "code_output": code_output,
            "parsed_metrics": parsed_metrics,
            "parsed_figures": parsed_figures,
            "parsed_summaries": parsed_summaries,
        }

    async def _remodel_and_retry(
        self,
        ctx: PipelineContext,
        key: str,
        flow_meta: dict,
        coder_agent: CoderAgent,
        modeler_agent: Any,
        modeler_response: Any,
        coder_response: Any,
        context: str,
        remodel_attempt: int,
        progress_base: float,
    ) -> Any:
        """反馈环路: 回传 Modeler 修订后重新执行 Coder"""
        await ctx.send_progress(
            f"正在为 {key} 重新设计方案... "
            f"(尝试 {remodel_attempt}/{self.MAX_REMODEL_ATTEMPTS})",
            progress_base,
        )

        feedback = CoderFeedbackToModeler(
            subtask_key=key,
            error_summary=coder_response.error_summary or "代码执行多次失败",
            failed_approach=coder_response.code_response or "",
            alternative_suggestion="请使用更简单、更可靠的数学方法",
            retry_count=remodel_attempt,
        )

        revised = await modeler_agent.revise(
            feedback=feedback,
            original_solution=modeler_response.questions_solution,
        )

        revised_meta = {
            "type": flow_meta["type"],
            "solution": revised.questions_solution.get(key, ""),
        }
        if flow_meta["type"] == "question":
            revised_meta["question"] = flow_meta.get("question", "")

        revised_model_config = None
        if revised.model_configs:
            revised_model_config = revised.model_configs.get(key)

        revised_prompt = Flows.build_coder_prompt(
            revised_meta,
            context=context,
            model_config=revised_model_config,
        )
        # 注入代码模板
        try:
            model_names_for_q = self._extract_model_names(
                str(revised_meta.get("solution", ""))
            )
            if model_names_for_q:
                revised_prompt = build_coder_prompt_with_templates(
                    revised_prompt, model_names_for_q
                )
        except Exception as e:
            logger.debug("代码模板注入跳过: %s", e)

        coder_agent.reset_counters()

        await ctx.send_progress(
            f"正在用新方案重新求解: {key}", progress_base
        )
        return await coder_agent.run(
            prompt=revised_prompt, subtask_title=key
        )
