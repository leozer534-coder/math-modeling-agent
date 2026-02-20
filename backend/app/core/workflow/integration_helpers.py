"""
整合辅助模块 - Integration Helpers
====================================

将已有的高质量模块整合到增强工作流中，提供统一的适配层。

整合清单：
1. KnowledgeBase → 知识库查询适配
2. Reviewer → 标准化评审接口
3. ModelRegistry → 模型推荐上下文生成（补充 engine.py 的整合）
4. ErrorRecovery → 阶段级错误恢复包装
5. QualityGates → 论文/代码质量闸门
6. Benchmark → 综合评测报告生成
7. Agent 任务评估 → enable_task_evaluation 配置
"""

from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.utils.log_util import logger


# ================== 1. KnowledgeBase 整合 ==================


def query_knowledge_base_for_context(
    problem_description: str,
    problem_type: str = "",
    keywords: Optional[List[str]] = None,
) -> str:
    """
    查询知识库并格式化为可注入 ModelerAgent prompt 的上下文字符串。

    委托给统一知识库的 get_knowledge_for_prompt() 方法。

    Args:
        problem_description: 问题描述
        problem_type: 问题类型（如 "优化"、"预测"、"分类"）
        keywords: 搜索关键词

    Returns:
        格式化的知识库上下文字符串
    """
    try:
        from app.core.knowledge_base import knowledge_base

        # 合并 problem_description 和 problem_type 作为查询类型
        effective_type = problem_type or problem_description

        # 委托给统一知识库的格式化方法
        result = knowledge_base.get_knowledge_for_prompt(
            problem_type=effective_type,
            keywords=keywords,
            max_chars=3000,
        )

        if not result:
            return ""

        header = "# 知识库参考信息\n\n> 以下信息来自数学建模知识库，供建模决策参考。\n\n"
        return header + result

    except Exception as e:
        logger.warning("知识库查询失败 (非关键): %s", e)
        return ""


# ================== 2. ModelRegistry 上下文生成 ==================


def get_model_recommendations_context(
    scenario: str,
    top_k: int = 5,
) -> str:
    """
    从模型注册中心获取推荐并格式化为上下文字符串。

    补充 engine.py 中已有的 _enhance_model_selection，
    此函数返回可直接注入 prompt 的文本。

    Args:
        scenario: 应用场景描述
        top_k: 返回推荐数量

    Returns:
        格式化的模型推荐上下文
    """
    try:
        from app.core.modeling.model_registry import model_registry

        recommendations = model_registry.search_by_scenario(scenario, top_k=top_k)

        if not recommendations:
            return ""

        lines = ["# 模型注册中心推荐\n"]
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"## {i}. {rec.name} ({rec.category})")
            lines.append(f"- 模型ID: {rec.model_id}")
            lines.append(f"- 复杂度: {rec.complexity}")
            lines.append(f"- 推荐理由: {rec.rationale}")
            if rec.key_parameters:
                lines.append(f"- 关键参数: {', '.join(rec.key_parameters[:4])}")
            if rec.validation_methods:
                lines.append(f"- 验证方法: {', '.join(rec.validation_methods[:3])}")
            if rec.common_pitfalls:
                lines.append(f"- 常见陷阱: {', '.join(rec.common_pitfalls[:2])}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.warning("模型注册中心查询失败 (非关键): %s", e)
        return ""


# ================== 3. Reviewer 标准化评审适配 ==================


async def run_quality_review(
    task_id: str,
    model,
    modeling_results: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    运行 Reviewer Agent 进行质量评审。

    适配层：确保 Reviewer 的输入/输出格式与增强工作流兼容。

    Args:
        task_id: 任务ID
        model: LLM 模型实例
        modeling_results: 建模结果字典，包含:
            - code_results: 代码执行结果
            - model_plan: 建模方案
            - paper_content: 论文内容（可选）

    Returns:
        标准化评审结果字典，包含评分维度和改进建议；
        评审失败时返回 None
    """
    try:
        from app.core.agents.reviewer import QualityReview, Reviewer

        reviewer = Reviewer(task_id=task_id, model=model)
        review: QualityReview = await reviewer.execute(modeling_results)

        # 转换为标准化字典格式
        result = {
            "overall_rating": review.overall_rating,
            "review_status": review.review_status.value,
            "dimensions": {
                "math_rigor": review.methodology_quality.get("average_score", 0),
                "code_correctness": review.result_quality.get("average_score", 0),
                "innovation": review.innovation_assessment.get("average_score", 0),
                "visualization": review.writing_quality.get(
                    "figures_tables", 0
                ),
                "paper_quality": review.writing_quality.get("average_score", 0),
            },
            "content_quality": review.content_quality,
            "methodology_quality": review.methodology_quality,
            "result_quality": review.result_quality,
            "writing_quality": review.writing_quality,
            "innovation_assessment": review.innovation_assessment,
            "critical_issues": review.critical_issues,
            "suggestions": review.suggestions_for_improvement,
            "final_recommendation": review.final_recommendation,
            "reviewer_comments": review.reviewer_comments,
        }

        logger.info(
            "质量评审完成: %s分 (%s)", review.overall_rating, review.review_status.value
        )
        return result

    except Exception as e:
        logger.warning("质量评审失败 (非关键): %s", e)
        return None


# ================== 4. ErrorRecovery 阶段级包装 ==================


async def execute_with_error_recovery(
    stage_name: str,
    func: Callable[..., Coroutine[Any, Any, Any]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    fallback_result: Any = None,
    on_retry_callback: Optional[Callable[[int, Exception], None]] = None,
    **kwargs,
) -> Any:
    """
    使用错误恢复机制包装阶段执行。

    结合 RetryManager 的指数退避重试和 ErrorClassifier 的智能错误分类，
    在所有重试失败后返回 fallback_result 而非抛出异常（优雅降级）。

    Args:
        stage_name: 阶段名称（用于日志）
        func: 要执行的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟秒数
        fallback_result: 所有重试失败后的降级返回值
        on_retry_callback: 重试时的回调
        *args, **kwargs: 传递给 func 的参数

    Returns:
        执行结果或 fallback_result
    """
    try:
        from app.core.error_recovery import (
            RecoveryAction,
            RetryManager,
        )

        retry_manager = RetryManager(
            max_retries=max_retries,
            base_delay=base_delay,
        )

        recovery_result = await retry_manager.execute_with_retry(
            func,
            *args,
            on_retry=on_retry_callback,
            **kwargs,
        )

        if recovery_result.success:
            return recovery_result.result_data

        # 所有重试失败，记录错误信息
        if recovery_result.error_info:
            error_info = recovery_result.error_info
            logger.error(
                "阶段 [%s] 恢复失败: 类别=%s, 严重程度=%s, 建议操作=%s",
                stage_name,
                error_info.category.value,
                error_info.severity.value,
                error_info.suggested_action.value,
            )

            # 根据建议操作决定行为
            if error_info.suggested_action == RecoveryAction.SKIP:
                logger.info("阶段 [%s] 按策略跳过", stage_name)
                return fallback_result
            elif error_info.suggested_action == RecoveryAction.ABORT:
                raise RuntimeError(
                    f"阶段 [{stage_name}] 致命错误，无法恢复: {error_info.message}"
                )

        logger.warning("阶段 [%s] 降级返回默认值", stage_name)
        return fallback_result

    except ImportError:
        logger.warning("error_recovery 模块不可用，直接执行")
        return await func(*args, **kwargs)
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("错误恢复包装异常: %s", e)
        if fallback_result is not None:
            return fallback_result
        raise


def create_stage_error_handler(task_id: str):
    """
    创建阶段级错误处理器。

    返回一个 ErrorRecoveryManager 实例，可注册各阶段的备选处理器。

    Args:
        task_id: 任务ID

    Returns:
        ErrorRecoveryManager 实例，不可用时返回 None
    """
    try:
        from app.core.error_recovery import ErrorRecoveryManager

        manager = ErrorRecoveryManager()
        logger.info("为任务 %s 创建错误恢复管理器", task_id)
        return manager
    except Exception as e:
        logger.warning("创建错误恢复管理器失败: %s", e)
        return None


def create_progress_tracker(task_id: str):
    """
    创建进度事件发射器。

    Args:
        task_id: 任务ID

    Returns:
        ProgressEventEmitter 实例，不可用时返回 None
    """
    try:
        from app.core.error_recovery import ProgressEventEmitter

        emitter = ProgressEventEmitter(task_id)
        return emitter
    except Exception as e:
        logger.warning("创建进度跟踪器失败: %s", e)
        return None


# ================== 5. QualityGates 质量闸门整合 ==================


def check_paper_quality(paper_content: str) -> Optional[Dict[str, Any]]:
    """
    使用 PaperQualityGate 检查论文质量。

    在 WRITE 阶段后调用，评分过低时触发重写。

    Args:
        paper_content: 论文 Markdown 内容

    Returns:
        质量检查结果字典，包含 passed/score/issues/suggestions；
        检查失败时返回 None
    """
    try:
        from app.core.quality.quality_gates import PaperQualityGate

        gate = PaperQualityGate()
        result = gate.check({"content": paper_content, "figures": [], "tables": []})

        return {
            "passed": result.passed,
            "score": result.score,
            "level": result.level,
            "issues": result.issues,
            "suggestions": result.suggestions,
            "details": result.details,
        }
    except Exception as e:
        logger.warning("论文质量检查失败 (非关键): %s", e)
        return None


def check_code_quality(code: str) -> Optional[Dict[str, Any]]:
    """
    使用 CodeQualityGate 检查代码质量。

    在 CODE 阶段后调用。

    Args:
        code: Python 代码内容

    Returns:
        质量检查结果字典；检查失败时返回 None
    """
    try:
        from app.core.quality.quality_gates import CodeQualityGate

        gate = CodeQualityGate()
        result = gate.check({"code": code, "language": "python"})

        return {
            "passed": result.passed,
            "score": result.score,
            "level": result.level,
            "issues": result.issues,
            "suggestions": result.suggestions,
            "details": result.details,
        }
    except Exception as e:
        logger.warning("代码质量检查失败 (非关键): %s", e)
        return None


def run_all_quality_checks(
    code: str,
    paper_content: str,
    code_path: str = "",
) -> Optional[Dict[str, Any]]:
    """
    运行所有质量检查（代码 + 论文 + 可复现性）。

    Args:
        code: 代码内容
        paper_content: 论文内容
        code_path: 代码目录路径

    Returns:
        综合质量报告字典；检查失败时返回 None
    """
    try:
        from app.core.quality.quality_gates import QualityChecker

        checker = QualityChecker()
        results = checker.run_all_checks(code, paper_content, code_path)
        overall_score = checker.get_overall_score(results)
        report = checker.format_report(results)

        return {
            "overall_score": overall_score,
            "report_markdown": report,
            "gate_results": {
                gate_id: {
                    "passed": result.passed,
                    "score": result.score,
                    "level": result.level,
                    "issues": result.issues,
                    "suggestions": result.suggestions,
                }
                for gate_id, result in results.items()
            },
            "all_passed": all(r.passed for r in results.values()),
        }
    except Exception as e:
        logger.warning("综合质量检查失败 (非关键): %s", e)
        return None


def should_trigger_rewrite(
    paper_quality_result: Optional[Dict[str, Any]],
    min_score: float = 0.6,
) -> bool:
    """
    判断是否应触发论文重写。

    Args:
        paper_quality_result: check_paper_quality 的返回值
        min_score: 最低通过分数

    Returns:
        True 表示需要重写
    """
    if paper_quality_result is None:
        return False

    return not paper_quality_result.get("passed", True) or paper_quality_result.get(
        "score", 1.0
    ) < min_score


# ================== 6. Benchmark 评测整合 ==================


def generate_benchmark_report(
    task_id: str,
    paper_content: str,
    code: str = "",
    problem_type: str = "optimization",
    problem_description: str = "",
    selected_models: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    使用 PaperBenchmark 生成综合评测报告。

    在 FINALIZE 阶段调用，结果可通过 WebSocket 推送给前端。

    Args:
        task_id: 任务ID
        paper_content: 论文内容
        code: 代码内容
        problem_type: 问题类型
        problem_description: 问题描述
        selected_models: 选用的模型列表
        output_dir: 评测报告输出目录

    Returns:
        评测结果字典，包含分数/等级/建议/优点/Markdown报告；
        评测失败时返回 None
    """
    try:
        from app.core.evaluation.benchmark import PaperBenchmark, PaperBundle

        benchmark = PaperBenchmark(output_dir=output_dir)

        bundle = PaperBundle(
            task_id=task_id,
            problem_type=problem_type,
            problem_description=problem_description,
            paper_content=paper_content,
            code=code,
            selected_models=selected_models or [],
        )

        result = benchmark.evaluate(bundle)

        return {
            "benchmark_id": result.benchmark_id,
            "overall_score": result.overall_score,
            "grade": result.grade.value,
            "dimension_scores": result.dimension_scores,
            "suggestions": result.suggestions,
            "strengths": result.strengths,
            "markdown_report": result.to_markdown(),
            "evaluated_at": result.evaluated_at,
        }
    except Exception as e:
        logger.warning("评测报告生成失败 (非关键): %s", e)
        return None


# ================== 7. Agent 任务评估配置 ==================


def configure_agent_with_evaluation(
    agent_class,
    task_id: str,
    model,
    enable_task_evaluation: bool = True,
    enable_memory_system: bool = False,
    **kwargs,
):
    """
    创建 Agent 实例并启用任务评估。

    在增强工作流中创建 Agent 时使用，确保 enable_task_evaluation=True。

    Args:
        agent_class: Agent 类（Agent 基类或子类）
        task_id: 任务ID
        model: LLM 模型实例
        enable_task_evaluation: 是否启用任务评估
        enable_memory_system: 是否启用记忆系统
        **kwargs: 传递给 Agent 构造函数的其他参数

    Returns:
        配置好的 Agent 实例
    """
    try:
        agent = agent_class(
            task_id=task_id,
            model=model,
            enable_task_evaluation=enable_task_evaluation,
            enable_memory_system=enable_memory_system,
            **kwargs,
        )
        logger.info(
            "创建 %s (task_eval=%s)", agent_class.__name__, enable_task_evaluation
        )
        return agent
    except TypeError:
        # Agent 子类可能不接受 enable_task_evaluation 参数
        logger.info(
            "%s 不支持 enable_task_evaluation，使用默认构造",
            agent_class.__name__,
        )
        return agent_class(task_id=task_id, model=model, **kwargs)


# ================== 8. 综合整合入口 ==================


async def enrich_modeling_context(
    problem_description: str,
    problem_type: str = "",
    keywords: Optional[List[str]] = None,
) -> str:
    """
    综合多个知识源，生成丰富的建模上下文。

    在 RESEARCH 阶段调用，合并知识库和模型注册中心的推荐结果。

    Args:
        problem_description: 问题描述
        problem_type: 问题类型
        keywords: 搜索关键词

    Returns:
        综合上下文字符串
    """
    parts: List[str] = []

    # 知识库上下文
    kb_context = query_knowledge_base_for_context(
        problem_description, problem_type, keywords
    )
    if kb_context:
        parts.append(kb_context)

    # 模型注册中心推荐
    registry_context = get_model_recommendations_context(
        f"{problem_description} {problem_type}".strip(),
        top_k=5,
    )
    if registry_context:
        parts.append(registry_context)

    return "\n\n---\n\n".join(parts) if parts else ""


async def run_finalize_checks(
    task_id: str,
    paper_content: str,
    code: str = "",
    problem_type: str = "optimization",
    problem_description: str = "",
    selected_models: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    运行最终检查流程（质量闸门 + 评测报告）。

    在论文写作完成后调用，一次性完成所有检查。

    Args:
        task_id: 任务ID
        paper_content: 论文内容
        code: 代码内容
        problem_type: 问题类型
        problem_description: 问题描述
        selected_models: 选用的模型列表
        output_dir: 评测报告输出目录

    Returns:
        综合检查结果字典
    """
    result: Dict[str, Any] = {
        "task_id": task_id,
        "quality_gates": None,
        "benchmark": None,
        "needs_rewrite": False,
    }

    # 1. 质量闸门检查
    quality_result = run_all_quality_checks(code, paper_content)
    result["quality_gates"] = quality_result

    # 2. 论文专项检查（用于判断是否需要重写）
    paper_result = check_paper_quality(paper_content)
    result["needs_rewrite"] = should_trigger_rewrite(paper_result)

    # 3. 综合评测
    benchmark_result = generate_benchmark_report(
        task_id=task_id,
        paper_content=paper_content,
        code=code,
        problem_type=problem_type,
        problem_description=problem_description,
        selected_models=selected_models,
        output_dir=output_dir,
    )
    result["benchmark"] = benchmark_result

    return result
