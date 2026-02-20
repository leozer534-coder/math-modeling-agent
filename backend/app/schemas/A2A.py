import re

from pydantic import BaseModel, Field, field_validator


class ProblemRelation(BaseModel):
    """子问题之间的逻辑关联关系。"""

    from_ques: str = Field(alias="from", description="源子问题标识，如 ques1")
    to_ques: str = Field(alias="to", description="目标子问题标识，如 ques2")
    relation: str = Field(
        description="关系类型: 递进/并列/因果"
    )
    description: str = Field(
        default="", description="关系的简要说明"
    )

    model_config = {"populate_by_name": True}


class RiskAssessmentItem(BaseModel):
    """单个子问题的风险评估。"""

    question: str = Field(description="子问题标识，如 ques1")
    risk: str = Field(description="风险等级: 低/中/高")
    reason: str = Field(default="", description="风险原因简述")


class CompetitionStrategy(BaseModel):
    """竞赛战略分析结果。"""

    priority_order: list[str] = Field(
        default_factory=list,
        description="按解题优先级排列的子问题列表",
    )
    scoring_focus: str = Field(
        default="", description="评审重点关注的方面描述"
    )
    innovation_opportunities: list[str] = Field(
        default_factory=list, description="可创新的具体方向列表"
    )
    risk_assessment: list[RiskAssessmentItem] = Field(
        default_factory=list, description="各子问题的风险评估"
    )


class CoordinatorToModeler(BaseModel):
    """Coordinator 传递给 Modeler 的结构化问题数据。"""

    questions: dict
    ques_count: int
    difficulty: str | None = None  # 整体难度: 简单/中等/困难
    data_description: str | None = None  # 对附件数据的简要描述
    # --- 新增字段（向后兼容，均为可选） ---
    sub_difficulty: dict[str, str] | None = Field(
        default=None,
        description="各子问题的独立难度评估，如 {'ques1': '简单', 'ques2': '困难'}",
    )
    problem_relations: list[ProblemRelation] | None = Field(
        default=None,
        description="子问题之间的逻辑关联关系列表",
    )
    strategy: CompetitionStrategy | None = Field(
        default=None,
        description="竞赛战略分析（优先级、得分重点、创新方向、风险评估）",
    )


class ModelSolution(BaseModel):
    """单个问题的结构化建模方案。"""

    model_name: str = Field(default="", description="推荐的主要模型名称")
    model_category: str = Field(
        default="",
        description=(
            "模型类别: optimization/prediction/evaluation/"
            "classification/fitting/graph/ode/probability/game"
        ),
    )
    approach_baseline: str = Field(
        default="", description="基线模型方案（经典方法）"
    )
    approach_improved: str = Field(default="", description="改进模型方案")
    approach_innovative: str = Field(default="", description="创新模型方案")
    mathematical_formulation: str = Field(
        default="",
        description="数学形式化描述（目标函数、约束条件、决策变量）",
    )
    evaluation_metrics: list[str] = Field(
        default_factory=list, description="评估指标列表"
    )
    python_libraries: list[str] = Field(
        default_factory=list, description="所需 Python 库列表"
    )
    data_requirements: str = Field(default="", description="数据需求描述")
    visualization_plan: str = Field(default="", description="可视化规划")
    solution_text: str = Field(
        default="",
        description="完整的建模方案文本（兼容旧格式，保留完整的自然语言描述）",
    )

    @classmethod
    def from_text(cls, text: str) -> "ModelSolution":
        """从文本中解析结构化建模方案。

        尝试从文本中提取 [MODEL_CONFIG]...[/MODEL_CONFIG] 块，
        如果找到则解析其中的 key: value 对填充字段；
        如果未找到则将整个文本作为 solution_text，其余字段使用默认值。
        """
        config_pattern = re.compile(
            r"\[MODEL_CONFIG\](.*?)\[/MODEL_CONFIG\]", re.DOTALL
        )
        match = config_pattern.search(text)

        if not match:
            return cls(solution_text=text)

        config_block = match.group(1)
        # 解析 key: value 对（支持多行值，直到遇到下一个 key 或块结束）
        kv_pattern = re.compile(
            r"^\s*([\w_]+)\s*:\s*(.*?)(?=^\s*[\w_]+\s*:|$)",
            re.MULTILINE | re.DOTALL,
        )
        pairs: dict[str, str] = {}
        for kv_match in kv_pattern.finditer(config_block):
            key = kv_match.group(1).strip()
            value = kv_match.group(2).strip()
            pairs[key] = value

        # 列表字段：逗号分隔解析
        def _parse_list(raw: str) -> list[str]:
            """将逗号分隔的字符串解析为列表，过滤空项。"""
            if not raw:
                return []
            return [item.strip() for item in raw.split(",") if item.strip()]

        return cls(
            model_name=pairs.get("model_name", ""),
            model_category=pairs.get("model_category", ""),
            approach_baseline=pairs.get("approach_baseline", ""),
            approach_improved=pairs.get("approach_improved", ""),
            approach_innovative=pairs.get("approach_innovative", ""),
            mathematical_formulation=pairs.get(
                "mathematical_formulation", ""
            ),
            evaluation_metrics=_parse_list(
                pairs.get("evaluation_metrics", "")
            ),
            python_libraries=_parse_list(
                pairs.get("python_libraries", "")
            ),
            data_requirements=pairs.get("required_data_format", pairs.get("data_requirements", "")),
            visualization_plan=pairs.get("visualization_plan", ""),
            solution_text=text,
        )


class ModelerToCoder(BaseModel):
    """Modeler 传递给 Coder 的建模方案数据，兼容新旧两种格式。"""

    questions_solution: dict[str, str | ModelSolution] = Field(
        default_factory=dict,
        description="各问题的建模方案，值可以是纯文本(旧格式)或 ModelSolution(新格式)",
    )
    assumptions: list[str] = Field(
        default_factory=list, description="模型假设列表"
    )

    def get_solution_text(self, key: str) -> str:
        """智能获取指定问题的方案文本。

        如果值是 ModelSolution，返回其 solution_text；
        如果值是 str，直接返回（兼容旧格式）。

        Args:
            key: 问题标识键。

        Returns:
            对应问题的方案文本，键不存在时返回空字符串。
        """
        value = self.questions_solution.get(key)
        if value is None:
            return ""
        if isinstance(value, ModelSolution):
            return value.solution_text
        return value

    def get_model_config(self, key: str) -> ModelSolution | None:
        """获取指定问题的结构化配置。

        如果值是 ModelSolution，返回它；
        如果值是 str，返回 None。

        Args:
            key: 问题标识键。

        Returns:
            ModelSolution 实例或 None。
        """
        value = self.questions_solution.get(key)
        if isinstance(value, ModelSolution):
            return value
        return None


class CoderToWriter(BaseModel):
    code_response: str | None = None
    code_output: str | None = None
    created_images: list[str] | None = None
    failed: bool = False  # 标记任务是否失败（向后兼容，默认 False）


class WriterResponse(BaseModel):
    """Writer Agent 的输出结果。"""

    response_content: str = ""
    footnotes: list[tuple[str, str]] | None = None

    @field_validator("response_content", mode="before")
    @classmethod
    def _coerce_to_str(cls, v: object) -> str:
        """兼容旧调用方：将 None / 非字符串强制转为 str。"""
        if v is None:
            return ""
        return str(v)


class CoderFeedbackToModeler(BaseModel):
    """Coder 反馈给 Modeler 的修订请求"""
    subtask_key: str
    error_summary: str
    failed_approach: str = ""
    alternative_suggestion: str = ""
    retry_count: int = 0


class ModelComparisonEntry(BaseModel):
    """单个问题的多模型对比结果"""

    question_key: str
    models_evaluated: list[str] = Field(default_factory=list, description="已评估的模型列表")
    best_model: str | None = None
    improvement_over_baseline: dict[str, float] | None = None
    comparison_table_markdown: str | None = None
    metrics: dict[str, dict[str, float]] | None = None


class ModelComparisonResult(BaseModel):
    """全局多模型对比结果"""

    per_question: list[ModelComparisonEntry] = Field(default_factory=list, description="各问题的对比结果")
    overall_ranking: list[str] | None = None
    comparison_summary: str | None = None
    evaluation_metrics_used: list[str] = Field(default_factory=list, description="使用的评估指标列表")
