from abc import ABC, abstractmethod

from app.core.agents import WriterAgent, CoderAgent, CoordinatorAgent, ModelerAgent
from app.schemas.A2A import CoderFeedbackToModeler
from app.schemas.request import Problem
from app.schemas.response import SystemMessage, ProgressMessage
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.log_util import logger
from app.utils.common_utils import create_work_dir, get_config_template, generate_data_summary
from app.models.user_output import UserOutput
from app.config.setting import settings
from app.tools.interpreter_factory import create_interpreter
from app.services.redis_manager import redis_manager
from app.tools.notebook_serializer import NotebookSerializer
import asyncio
import os

from app.core.flows import Flows
from app.core.llm.llm_factory import LLMFactory
from app.core.prompts.base_prompts import build_coder_prompt_with_templates
from app.core.prompts import CODER_PROMPT as _BASE_CODER_PROMPT


class WorkFlow(ABC):
    """工作流抽象基类，定义工作流的统一接口。"""

    @abstractmethod
    async def execute(self, problem: Problem) -> None:
        """执行工作流。

        Args:
            problem: 用户提交的建模问题。
        """
        ...


class MathModelWorkFlow(WorkFlow):
    task_id: str  #
    work_dir: str  # worklow work dir
    ques_count: int = 0  # 问题数量

    def __init__(self):
        super().__init__()
        # 在 __init__ 中初始化可变默认值，避免类级别共享
        self.questions: dict[str, str | int] = {}

    async def execute(self, problem: Problem):
        self.task_id = problem.task_id
        self.work_dir = create_work_dir(self.task_id)

        llm_factory = LLMFactory(self.task_id)
        coordinator_llm, modeler_llm, coder_llm, writer_llm = llm_factory.get_all_llms()

        coordinator_agent = CoordinatorAgent(self.task_id, coordinator_llm)

        await redis_manager.publish_message(
            self.task_id,
            ProgressMessage(
                content="识别用户意图和拆解问题ing...",
                percent=5,
                phase="problem_analysis",
                message="识别用户意图和拆解问题ing...",
            ),
        )

        try:
            coordinator_response = await coordinator_agent.run(problem.ques_all)
            self.questions = coordinator_response.questions
            self.ques_count = coordinator_response.ques_count
        except Exception as e:
            #  非数学建模问题
            logger.error("CoordinatorAgent 执行失败: %s", e)
            raise

        await redis_manager.publish_message(
            self.task_id,
            ProgressMessage(
                content="识别用户意图和拆解问题完成",
                percent=10,
                phase="problem_analysis",
                message="识别用户意图和拆解问题完成",
            ),
        )

        await redis_manager.publish_message(
            self.task_id,
            ProgressMessage(
                content="正在预览数据文件...",
                percent=12,
                phase="data_preview",
                message="正在预览数据文件...",
            ),
        )

        # 生成数据摘要，为 Modeler 提供数据感知
        # generate_data_summary 是同步 I/O 函数，使用 to_thread 避免阻塞事件循环
        data_context = await asyncio.to_thread(generate_data_summary, self.work_dir)
        if data_context:
            logger.info("数据摘要已生成，长度: %d 字符", len(data_context))

        await redis_manager.publish_message(
            self.task_id,
            ProgressMessage(
                content="建模手开始建模ing...",
                percent=15,
                phase="modeling",
                message="建模手开始建模ing...",
            ),
        )

        modeler_agent = ModelerAgent(self.task_id, modeler_llm)

        modeler_response = await modeler_agent.run(
            coordinator_response, data_context=data_context
        )

        user_output = UserOutput(
            work_dir=self.work_dir,
            ques_count=self.ques_count,
            comp_template=problem.comp_template,
        )

        await redis_manager.publish_message(
            self.task_id,
            ProgressMessage(
                content="正在创建代码沙盒环境",
                percent=20,
                phase="sandbox_init",
                message="正在创建代码沙盒环境",
            ),
        )

        notebook_serializer = NotebookSerializer(work_dir=self.work_dir)

        # 使用 try/finally 确保 code_interpreter 资源被正确清理
        code_interpreter = None
        solution_error: Exception | None = None
        try:
            code_interpreter = await create_interpreter(
                kind="local",
                task_id=self.task_id,
                work_dir=self.work_dir,
                notebook_serializer=notebook_serializer,
                timeout=3000,
            )
            scholar = OpenAlexScholar(task_id=self.task_id, email=settings.OPENALEX_EMAIL)

            await redis_manager.publish_message(
                self.task_id,
                ProgressMessage(
                    content="代码沙盒创建完成，初始化代码手",
                    percent=25,
                    phase="sandbox_init",
                    message="代码沙盒创建完成，初始化代码手",
                ),
            )

            # 提取所有模型名称用于代码模板匹配
            model_names: list[str] = []
            for i in range(1, self.ques_count + 1):
                config = modeler_response.get_model_config(f"ques{i}")
                if config and config.model_name:
                    model_names.append(config.model_name)

            # 构建增强的 Coder system prompt（注入匹配的代码模板）
            enhanced_coder_prompt = None
            if model_names:
                try:
                    enhanced_coder_prompt = build_coder_prompt_with_templates(
                        _BASE_CODER_PROMPT, model_names=model_names
                    )
                    logger.info("代码模板注入成功，匹配模型: %s", model_names)
                except Exception as e:
                    logger.warning("代码模板注入失败，使用默认 prompt: %s", e)

            # 初始化 CoderAgent（传入增强 prompt）
            coder_agent = CoderAgent(
                task_id=problem.task_id,
                model=coder_llm,
                work_dir=self.work_dir,
                max_chat_turns=settings.MAX_CHAT_TURNS,
                max_retries=settings.MAX_RETRIES,
                code_interpreter=code_interpreter,
                system_prompt=enhanced_coder_prompt,
            )

            writer_agent = WriterAgent(
                task_id=problem.task_id,
                model=writer_llm,
                comp_template=problem.comp_template,
                format_output=problem.format_output,
                scholar=scholar,
            )

            flows = Flows(self.questions)

            ################################################ solution steps
            solution_flows = flows.get_solution_flows(self.questions, modeler_response)
            config_template = get_config_template(problem.comp_template, problem.format_output)

            MAX_FEEDBACK_ITERATIONS = 2  # 最大反馈迭代次数

            # 跨问题结果上下文：积累前序问题的关键结果供后续问题参考
            cross_question_context: dict[str, str] = {}
            eda_data_files: list[str] = []  # EDA阶段产出的清洗后数据文件
            MAX_CROSS_CONTEXT_TOTAL_CHARS = 5000  # 跨问题上下文总字符数上限

            total_solution_steps = len(solution_flows)

            for idx, (key, value) in enumerate(solution_flows.items()):
                step_percent = 30 + (idx * 50) // max(total_solution_steps, 1)
                await redis_manager.publish_message(
                    self.task_id,
                    ProgressMessage(
                        content=f"代码手开始求解{key}",
                        percent=step_percent,
                        phase="solution",
                        message=f"代码手开始求解{key}（{idx + 1}/{total_solution_steps}）",
                    ),
                )

                coder_prompt = value["coder_prompt"]

                # 如果是 ques 类型且有前序结果，注入跨问题上下文
                # sensitivity_analysis 和 model_comparison 也可以消费所有 ques 的上下文
                if (
                    key.startswith("ques")
                    or key == "sensitivity_analysis"
                    or key == "model_comparison"
                ) and cross_question_context:
                    try:
                        context_text = Flows.build_cross_question_context(
                            cross_question_context
                        )
                        coder_prompt = f"{coder_prompt}\n\n{context_text}"
                    except Exception as e:
                        logger.warning(
                            "跨问题上下文注入失败，跳过: %s", e
                        )

                # 注入 EDA 清洗数据文件路径（独立于跨问题上下文）
                if eda_data_files and (
                    key.startswith("ques")
                    or key == "sensitivity_analysis"
                    or key == "model_comparison"
                ):
                    files_list = "\n".join(f"  - {f}" for f in eda_data_files[:10])
                    coder_prompt += (
                        f"\n\n【EDA阶段产出的清洗数据文件（请优先使用，避免重复清洗）】\n"
                        f"{files_list}\n"
                    )

                coder_response = await coder_agent.run(
                    prompt=coder_prompt, subtask_title=key
                )

                # 检查 Coder 是否失败并触发反馈闭环
                feedback_count = 0
                while (
                    coder_response.failed
                    and feedback_count < MAX_FEEDBACK_ITERATIONS
                ):
                    feedback_count += 1
                    logger.warning(
                        "Coder 求解 %s 失败（第 %d 次），触发 Modeler 修订",
                        key, feedback_count,
                    )

                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(
                            content=f"代码手求解{key}失败，反馈给建模手修订方案（第{feedback_count}次）",
                            type="warning",
                        ),
                    )

                    # 构建反馈
                    feedback = CoderFeedbackToModeler(
                        subtask_key=key,
                        error_summary=(coder_response.code_response or "")[:500],
                        failed_approach=value.get("coder_prompt", "")[:200],
                        retry_count=feedback_count,
                    )

                    # 请求 Modeler 修订
                    revised_response = await modeler_agent.revise(
                        original_response=modeler_response,
                        feedback=feedback,
                        coordinator_to_modeler=coordinator_response,
                        data_context=data_context,
                    )

                    # 选择性合并：仅替换失败子任务的方案，保护其他子任务
                    revised_key = feedback.subtask_key
                    if revised_key in revised_response.questions_solution:
                        modeler_response.questions_solution[revised_key] = (
                            revised_response.questions_solution[revised_key]
                        )
                        logger.info(
                            "选择性合并: 仅替换 %s 的建模方案", revised_key
                        )
                    else:
                        # 修订响应中未找到目标子任务的方案，使用完整替换作为降级
                        modeler_response = revised_response
                        logger.warning(
                            "修订响应中未找到 %s 的方案，使用完整替换",
                            revised_key,
                        )

                    # 重建该子任务的 coder prompt
                    revised_flows = flows.get_solution_flows(
                        self.questions, modeler_response
                    )
                    if key in revised_flows:
                        coder_prompt = revised_flows[key]["coder_prompt"]

                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(
                            content=f"建模手已修订{key}方案，代码手重新求解",
                        ),
                    )

                    # 重新执行 Coder
                    coder_response = await coder_agent.run(
                        prompt=coder_prompt,
                        subtask_title=key,  # 使用原始 key，确保 section_output 与下游读取一致
                    )

                if coder_response.failed:
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(
                            content=f"代码手求解{key}最终失败，使用降级结果继续",
                            type="error",
                        ),
                    )
                else:
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(
                            content=f"代码手求解成功{key}", type="success"
                        ),
                    )

                # === 结果验证与指标提取 ===
                code_output_text = code_interpreter.get_code_output(key)
                if not code_output_text:
                    logger.debug("子任务 %s 没有代码输出记录，跳过指标提取", key)
                    code_output_text = None

                # EDA 阶段完成后收集清洗数据文件
                if key == "eda":
                    try:
                        eda_data_files = code_interpreter.get_created_data_files("eda")
                        if eda_data_files:
                            logger.info("EDA 产出数据文件: %s", eda_data_files)
                    except Exception as e:
                        logger.warning("收集 EDA 数据文件失败: %s", e)

                if code_output_text:
                    metrics = Flows.extract_metrics_from_code_output(code_output_text)
                    figures = Flows.extract_figures_from_code_output(code_output_text)
                    result_summaries = Flows.extract_result_summaries(code_output_text)

                    if metrics:
                        logger.info("子任务 %s 提取到指标: %s", key, metrics)
                        user_output.set_metrics(key, metrics)

                    if figures:
                        logger.info("子任务 %s 提取到 %d 张图表", key, len(figures))

                    if result_summaries:
                        logger.info("子任务 %s 提取到结果摘要: %s", key, result_summaries)

                # 积累跨问题上下文（ques 和 eda 类型参与生产）
                if key.startswith("ques") or key == "eda":
                    try:
                        context_parts: list[str] = []
                        if coder_response.code_response:
                            # 截取代码响应的关键部分（避免过长）
                            context_parts.append(
                                coder_response.code_response[:800]
                            )
                        if code_output_text:
                            # 复用第336/338行已提取的 metrics 和 result_summaries，避免重复调用
                            if metrics:
                                metrics_str = ", ".join(
                                    f"{k}={v}" for k, v in metrics.items()
                                )
                                context_parts.append(
                                    f"评估指标: {metrics_str}"
                                )
                            if result_summaries:
                                for s in result_summaries:
                                    summary_str = (
                                        f"模型: {s.get('model', '未知')}, "
                                        f"结论: {s.get('conclusion', '无')}"
                                    )
                                    context_parts.append(summary_str)
                        if context_parts:
                            new_context = "\n".join(context_parts)
                            # 检查总量是否超限
                            current_total = sum(
                                len(v) for v in cross_question_context.values()
                            )
                            if (
                                current_total + len(new_context)
                                > MAX_CROSS_CONTEXT_TOTAL_CHARS
                            ):
                                # 截断新上下文以适应限制
                                remaining = (
                                    MAX_CROSS_CONTEXT_TOTAL_CHARS - current_total
                                )
                                if remaining > 200:
                                    new_context = new_context[:remaining]
                                    logger.warning(
                                        "跨问题上下文即将超限，截断 %s 至 %d 字符",
                                        key,
                                        remaining,
                                    )
                                else:
                                    logger.warning(
                                        "跨问题上下文已达上限 (%d 字符)，跳过 %s",
                                        MAX_CROSS_CONTEXT_TOTAL_CHARS,
                                        key,
                                    )
                                    new_context = None
                            if new_context:
                                cross_question_context[key] = new_context
                                logger.info(
                                    "已积累 %s 的跨问题上下文（%d 字符）",
                                    key,
                                    len(cross_question_context[key]),
                                )
                    except Exception as e:
                        logger.warning(
                            "积累 %s 跨问题上下文失败，跳过: %s", key, e
                        )

                # === Coder 失败时的 Writer 降级策略 ===
                if coder_response.failed:
                    _degraded_parts = [
                        f"## 写作任务：{key}（降级模式）\n",
                        (
                            "**重要提示**：本问题的代码求解未能成功完成。\n"
                            "请仅基于建模手的方案撰写【模型建立】部分，包括：\n"
                            "1. 理论描述和数学公式推导\n"
                            "2. 算法步骤和流程说明\n"
                            "3. 模型的适用条件和假设\n\n"
                            "**禁止事项**：\n"
                            "- 不要编造任何数值结果、表格数据或图表引用\n"
                            "- 不要假装有计算结果\n"
                            "- 在章节末尾注明'由于计算资源限制，"
                            "本问题的数值求解结果待补充'\n"
                        ),
                    ]
                    # 从建模方案中提取该子任务的方法论描述
                    _mc = (
                        modeler_response.get_model_config(key)
                        if modeler_response
                        else None
                    )
                    if _mc:
                        _method_parts: list[str] = []
                        if _mc.model_name:
                            _method_parts.append(
                                f"模型名称: {_mc.model_name}"
                            )
                        if _mc.model_category:
                            _method_parts.append(
                                f"模型类别: {_mc.model_category}"
                            )
                        if getattr(_mc, "approach_baseline", None):
                            _method_parts.append(
                                f"基准方法: {_mc.approach_baseline}"
                            )
                        if getattr(_mc, "approach_improved", None):
                            _method_parts.append(
                                f"改进方法: {_mc.approach_improved}"
                            )
                        if _method_parts:
                            _degraded_parts.append(
                                "\n### 建模方案\n"
                                + "\n".join(_method_parts)
                                + "\n"
                            )

                    _template = config_template.get(key, "")
                    if _template:
                        _degraded_parts.append(
                            f"\n### 参考模板格式\n{_template}\n"
                        )

                    writer_prompt = "\n".join(_degraded_parts)
                    logger.info(
                        "子任务 %s Coder 失败，使用降级 Writer prompt", key
                    )
                else:
                    writer_prompt = flows.get_writer_prompt(
                        key,
                        coder_response.code_response or "",
                        code_interpreter,
                        config_template,
                        modeler_response=modeler_response,
                        cross_question_context=(
                            cross_question_context
                            if key.startswith("ques")
                            or key == "sensitivity_analysis"
                            or key == "model_comparison"
                            else None
                        ),
                    )

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"论文手开始写{key}部分"),
                )
                # === 图片文件存在性验证 ===
                validated_images = []
                if coder_response.created_images:
                    for img_path in coder_response.created_images:
                        full_path = (
                            os.path.join(self.work_dir, img_path)
                            if not os.path.isabs(img_path)
                            else img_path
                        )
                        if os.path.isfile(full_path):
                            validated_images.append(img_path)
                        else:
                            logger.warning("图片文件不存在，跳过: %s", img_path)

                writer_response = await writer_agent.run(
                    writer_prompt,
                    available_images=validated_images if validated_images else None,
                    sub_title=key,
                )

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content=f"论文手完成{key}部分"),
                )

                user_output.set_res(key, writer_response)
                # 增量持久化：每完成一个子任务立即保存，防止崩溃丢失已完成的结果
                try:
                    user_output.save_result()
                    logger.debug("子任务 %s 增量保存成功", key)
                except Exception as save_err:
                    logger.warning("子任务 %s 增量保存失败: %s", key, save_err)

        except Exception as e:
            solution_error = e
            logger.error("Solution 阶段发生异常: %s", e)
            # 尝试保存已完成的部分结果
            try:
                user_output.save_result()
                logger.info("Solution 异常时已保存部分结果")
            except Exception:
                logger.error("Solution 异常时保存部分结果也失败")
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(
                    content=f"求解阶段发生异常: {str(e)[:200]}，尝试保存已完成的部分结果",
                    type="error",
                ),
            )
        finally:
            # 确保无论是否异常都清理沙盒资源
            if code_interpreter is not None:
                await code_interpreter.cleanup()

        # === 写作阶段（即使 solution 部分失败也尝试写作已完成的部分） ===
        try:
            # === 指标汇总注入写作上下文 ===
            comparison_summary = user_output.generate_comparison_summary()
            if comparison_summary:
                logger.info("生成模型对比摘要:\n%s", comparison_summary)
                # 将对比摘要存入 user_output 供写作阶段使用
                user_output.model_comparison_data = comparison_summary

            ################################################ write steps

            write_flows = flows.get_write_flows(
                user_output,
                config_template,
                problem.ques_all,
                modeler_response=modeler_response,
                comp_template=problem.comp_template,
            )
            total_write_steps = len(write_flows)

            for idx, (key, value) in enumerate(write_flows.items()):
                write_step_percent = 80 + (idx * 12) // max(total_write_steps, 1)
                await redis_manager.publish_message(
                    self.task_id,
                    ProgressMessage(
                        content=f"论文手开始写{key}部分",
                        percent=write_step_percent,
                        phase="writing",
                        message=f"论文手开始写{key}部分（{idx + 1}/{total_write_steps}）",
                    ),
                )

                # 注入已完成章节摘要，保持论文连贯性
                completed_summaries = user_output.get_completed_chapter_summaries(
                    max_per_chapter=150, max_total=2000
                )
                if completed_summaries:
                    value += (
                        f"\n\n【前序已完成章节摘要（请保持论述连贯性和术语一致性）】\n"
                        f"{completed_summaries}\n"
                    )

                writer_response = await writer_agent.run(prompt=value, sub_title=key)

                user_output.set_res(key, writer_response)

            logger.debug(user_output.get_res())

            user_output.save_result()
        except Exception as write_err:
            logger.error("写作阶段发生异常: %s", write_err)
            # 尝试保存已有的部分结果
            try:
                user_output.save_result()
                logger.info("已保存部分论文结果")
            except Exception:
                logger.error("保存部分结果也失败")
            # 如果 solution 阶段没有异常，则将写作异常作为主异常抛出
            if solution_error is None:
                solution_error = write_err

        # === 质量评审阶段 ===
        if settings.ENABLE_REVIEW and solution_error is None:
            try:
                await redis_manager.publish_message(
                    self.task_id,
                    ProgressMessage(
                        content="质量评审中...",
                        percent=93,
                        phase="review",
                        message="AI 评审员正在审核论文质量",
                    ),
                )

                from app.core.agents.reviewer import Reviewer

                reviewer = Reviewer(task_id=self.task_id, model=writer_llm)
                await reviewer.setup()

                # 构造 Reviewer 期望的数据格式
                modeling_results = {
                    "paper_content": user_output.get_result_to_save(),
                    "sections": [k for k in user_output.seq if k in user_output.res],
                    "metrics": getattr(user_output, "metrics_store", {}),
                    "model_comparison": getattr(
                        user_output, "model_comparison_data", ""
                    ),
                    "ques_count": user_output.ques_count,
                }

                quality_review = await reviewer.execute(modeling_results)

                # 保存评审报告
                import json as _json

                review_report_path = os.path.join(
                    self.work_dir, "quality_review.json"
                )
                review_dict: dict = {}
                if hasattr(quality_review, "__dict__"):
                    review_dict = {
                        k: (v.value if hasattr(v, "value") else v)
                        for k, v in quality_review.__dict__.items()
                    }
                with open(review_report_path, "w", encoding="utf-8") as f:
                    _json.dump(
                        review_dict, f, ensure_ascii=False, indent=2, default=str
                    )

                # 发送评审结果到前端
                overall_rating = getattr(quality_review, "overall_rating", 0)
                review_status = getattr(quality_review, "review_status", None)
                status_text = (
                    review_status.value
                    if hasattr(review_status, "value")
                    else str(review_status)
                )

                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(
                        content=f"论文质量评审完成: {status_text}（{overall_rating}/5）",
                        type=(
                            "success"
                            if overall_rating >= settings.REVIEW_MIN_SCORE
                            else "warning"
                        ),
                    ),
                )

                # 如果评分低于阈值，记录关键问题（但不阻塞流程）
                critical_issues = getattr(quality_review, "critical_issues", [])
                if critical_issues:
                    issues_summary = "; ".join(
                        (
                            issue.get("description", str(issue))[:100]
                            if isinstance(issue, dict)
                            else str(issue)[:100]
                        )
                        for issue in critical_issues[:3]
                    )
                    logger.warning("评审发现关键问题: %s", issues_summary)

                logger.info(
                    "质量评审完成: 评分=%d/5, 状态=%s, 关键问题=%d个",
                    overall_rating,
                    status_text,
                    len(critical_issues),
                )

            except Exception as review_err:
                logger.warning(
                    "质量评审阶段失败（不影响论文输出）: %s", review_err
                )
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(
                        content="质量评审跳过（评审过程出错）", type="warning"
                    ),
                )

        # 如果 solution 或写作阶段有异常，在写作完成后重新抛出
        if solution_error:
            # 发送明确的错误终止消息，通知前端任务异常终止
            await redis_manager.publish_message(
                self.task_id,
                ProgressMessage(
                    content="任务异常终止",
                    percent=-1,
                    phase="error",
                    message=str(solution_error)[:200],
                    type="error",
                ),
            )
            # 清理任务文件锁，防止内存泄漏
            redis_manager.cleanup_task_lock(self.task_id)
            raise solution_error

        await redis_manager.publish_message(
            self.task_id,
            ProgressMessage(
                content="任务完成",
                percent=100,
                phase="completed",
                message="任务完成",
                type="success",
            ),
        )

        # 任务完成后清理文件锁，防止内存泄漏
        redis_manager.cleanup_task_lock(self.task_id)
