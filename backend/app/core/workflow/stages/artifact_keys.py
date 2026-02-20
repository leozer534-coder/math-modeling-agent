"""Pipeline artifact key 常量定义。

所有 Stage 读写 ctx.artifacts 时必须使用此模块中的常量，
避免硬编码字符串导致的拼写错误和键名不一致。
"""


class ArtifactKeys:
    """ctx.artifacts 中使用的所有键名常量。"""

    # ---- DataPreviewStage ----
    DATA_SUMMARY = "data_summary"

    # ---- EDAStage ----
    EDA_RESULT = "eda_result"
    EDA_DATA_SUMMARY = "eda_data_summary"

    # ---- ProblemAnalysisStage ----
    PROBLEM_ANALYSIS = "problem_analysis"
    PROBLEM_TYPE = "problem_type"
    RECOMMENDED_APPROACHES = "recommended_approaches"

    # ---- ModelSelectionStage ----
    MODEL_RECOMMENDATION = "model_recommendation"
    RECOMMENDED_PRIMARY_MODEL = "recommended_primary_model"

    # ---- ModelerStage ----
    RECOMMENDED_VALIDATION = "recommended_validation"
    RECOMMENDED_METRICS = "recommended_metrics"
    # NOTE: 当前无生产者 Stage。CoordinatorStage 和 ModelerStage 有消费逻辑，
    #       但运行时始终为 None。预留给未来 ResearchStage 扩展（参见旧 award_winning_workflow.py）。
    RESEARCH_REPORT = "research_report"

    # ---- SmartModelerStage ----
    INNOVATIVE_MODEL_PLAN = "innovative_model_plan"

    # ---- ValidationStage ----
    VALIDATION_REPORT = "validation_report"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"

    # ---- ReviewStage ----
    REVIEW_RESULT = "review_result"
    REVIEW_FEEDBACK = "review_feedback"

    # ---- ConsistencyCheckStage ----
    CONSISTENCY_ISSUES = "consistency_issues"

    # ---- AbstractStage ----
    ABSTRACT_CONTENT = "abstract_content"
    KEYWORDS = "keywords"

    # ---- SymbolTableStage ----
    SYMBOL_TABLE = "symbol_table"  # 结构化符号列表（dict），当前仅生产无消费；SYMBOL_TABLE_TEXT 被 WriterStage 消费
    SYMBOL_TABLE_TEXT = "symbol_table_text"

    # ---- CoderStage 结构化标记解析结果 ----
    CODE_METRICS = "code_metrics"          # dict[str, dict[str, float]] — 按子问题聚合的评估指标
    CODE_FIGURES = "code_figures"          # dict[str, list[dict[str, str]]] — 按子问题聚合的图表清单
    RESULT_SUMMARIES = "result_summaries"  # dict[str, list[dict[str, str]]] — 按子问题聚合的结论摘要

    # ---- 获奖模式 ----
    # NOTE: 当前无生产者 Stage。WriterStage 有消费逻辑，
    #       但运行时始终为 None。预留给未来 AwardContextStage 扩展（参见旧 award_winning_workflow.py）。
    AWARD_CONTEXT = "award_context"
