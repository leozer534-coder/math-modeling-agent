"""
核心协议定义 - MathModelAgent 改进基础
=====================================

保证与现有 FastAPI + Redis 架构兼容
所有新增模块必须遵循这些协议定义

版本: v1.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypedDict,
    Union,
)


# ==================== 基础类型 ====================

Stage = Literal[
    "coordinator", "research", "modeling", "coding", "validation", "writing"
]

ComplexityLevel = Literal["simple", "moderate", "complex"]

QualityLevel = Literal["excellent", "good", "acceptable", "needs_improvement", "poor"]


# ==================== 引用与证据 ====================


class Citation(TypedDict):
    """引用信息 - Citation-first 设计的核心"""

    source_id: str  # openalex:W... / url:... / local:...
    source_type: str  # paper / web / book / dataset
    locator: str  # chunk_id / section / page
    url: Optional[str]
    title: str
    authors: Optional[str]
    year: Optional[int]
    quote: Optional[str]  # 原文引用片段
    confidence: float  # 置信度 0-1


class EvidenceSnippet(TypedDict):
    """证据片段 - 用于RAG检索结果"""

    snippet_id: str
    content: str
    citations: List[Citation]
    relevance_score: float
    extracted_at: str


# ==================== 运行清单与可复现性 ====================


class InputSpec(TypedDict):
    """输入规格"""

    name: str
    path: str
    hash: str  # SHA256
    size_bytes: int
    type: str  # csv / excel / txt / image


class OutputSpec(TypedDict):
    """输出规格"""

    name: str
    path: str
    hash: str
    type: str  # figure / table / notebook / markdown / latex
    created_at: str


class EnvironmentSpec(TypedDict):
    """环境规格"""

    python_version: str
    pip_freeze: List[str]
    platform: str
    interpreter: str  # local / e2b / daytona
    image_id: Optional[str]


class RunManifest(TypedDict):
    """运行清单 - 保证可复现性的核心"""

    run_id: str
    problem_id: str
    created_at: str
    completed_at: Optional[str]
    status: str  # running / completed / failed
    seeds: Dict[str, int]  # 随机种子
    env: EnvironmentSpec
    inputs: List[InputSpec]
    outputs: List[OutputSpec]
    metrics: Dict[str, float]
    stage_durations: Dict[str, float]
    llm_costs: Dict[str, float]
    error: Optional[str]


# ==================== 协议接口 ====================


class Retriever(Protocol):
    """检索器协议 - RAG知识库必须实现（支持同步或异步）"""

    def upsert(
        self, docs: List[Dict[str, Any]]
    ) -> Union[int, Coroutine[Any, Any, int]]:
        """插入或更新文档，返回成功数量"""
        ...

    def query(
        self, q: str, k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> Union[List[Dict[str, Any]], Coroutine[Any, Any, List[Dict[str, Any]]]]:
        """查询文档，每个结果必须包含Citation信息"""
        ...

    def delete(self, doc_ids: List[str]) -> Union[int, Coroutine[Any, Any, int]]:
        """删除文档，返回成功数量"""
        ...

    def count(self) -> Union[int, Coroutine[Any, Any, int]]:
        """返回文档总数"""
        ...


class Tool(Protocol):
    """工具协议 - 所有外部工具必须实现"""

    name: str
    description: str

    def run(self, payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具，返回结果"""
        ...

    def validate_input(self, payload: Dict[str, Any]) -> bool:
        """验证输入参数"""
        ...


class QualityGate(Protocol):
    """质量闸门协议 - 所有质量检查必须实现"""

    id: str
    name: str

    def check(self, bundle: Dict[str, Any]) -> "GateResult":
        """执行质量检查"""
        ...

    def get_requirements(self) -> List[str]:
        """返回检查项列表"""
        ...


class ModelCandidate(Protocol):
    """模型候选协议 - 数学模型必须实现"""

    name: str
    complexity: ComplexityLevel

    def fit(self, X: Any, y: Any, **kwargs) -> Any:
        """训练模型"""
        ...

    def predict(self, X: Any) -> Any:
        """预测"""
        ...

    def evaluate(self, X: Any, y: Any) -> Dict[str, float]:
        """评估模型，返回指标字典"""
        ...

    def get_params(self) -> Dict[str, Any]:
        """获取模型参数"""
        ...


# ==================== 结果数据类 ====================


@dataclass
class GateResult:
    """质量检查结果"""

    gate_id: str
    passed: bool
    score: float  # 0-1
    level: QualityLevel
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Assumption:
    """假设定义"""

    id: str
    statement: str  # 假设陈述
    justification: str  # 论证理由
    impact_analysis: str  # 影响分析
    confidence: float  # 置信度 0-1
    citations: List[Citation] = field(default_factory=list)
    related_variables: List[str] = field(default_factory=list)


@dataclass
class ResearchPackage:
    """研究包 - 深度分析阶段输出"""

    problem_id: str
    background_summary: str  # 背景综述
    terminology: Dict[str, str]  # 术语表
    related_work_matrix: List[Dict[str, Any]]  # 相关工作矩阵
    evidence_snippets: List[EvidenceSnippet]  # 可引用证据
    competing_hypotheses: List[Dict[str, Any]]  # 竞争假设
    assumptions: List[Assumption]  # 生成的假设
    key_insights: List[str]  # 关键洞察
    suggested_approaches: List[str]  # 建议方法
    citations_used: List[Citation] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ==================== 建模模块 ====================


@dataclass
class ModelRecommendation:
    """模型推荐"""

    model_id: str
    name: str
    category: (
        str  # optimization / prediction / classification / clustering / evaluation
    )
    complexity: ComplexityLevel
    rationale: str  # 推荐理由
    expected_performance: Dict[str, float]
    implementation_complexity: str
    data_requirements: Dict[str, str]
    key_parameters: List[str]
    validation_methods: List[str]
    common_pitfalls: List[str]


@dataclass
class MultiModelPlan:
    """多模型策略计划 - 从简单到复杂"""

    problem_id: str
    baseline: ModelRecommendation  # 基线模型
    improvements: List[ModelRecommendation]  # 改进模型
    innovations: List[ModelRecommendation]  # 创新变体
    comparison_strategy: str  # 对比策略
    evaluation_metrics: List[str]  # 评估指标
    expected_timeline: Dict[str, float]  # 预期耗时
    fallback_plan: Optional[str] = None  # 回退方案


# ==================== 验证模块 ====================


@dataclass
class SensitivityResult:
    """敏感性分析结果"""

    parameter: str
    original_value: float
    range_tested: List[float]
    result_values: List[float]
    impact_score: float  # 影响程度 0-1
    stability_rating: str  # stable / moderate / sensitive
    visualization_path: Optional[str] = None
    interpretation: str = ""


@dataclass
class ValidationReport:
    """验证报告"""

    model_id: str
    model_name: str
    metrics: Dict[str, float]  # 评估指标
    baseline_comparison: Dict[str, Any]  # 基线对比
    sensitivity_results: List[SensitivityResult]
    residual_analysis: Dict[str, Any]
    cross_validation: Dict[str, Any]  # 交叉验证结果
    overall_rating: QualityLevel
    recommendation: str
    issues_found: List[str] = field(default_factory=list)
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ==================== 写作模块 ====================


class AbstractQuality(Enum):
    """摘要质量等级"""

    EXCELLENT = "excellent"  # 结果导向，具体数值，方法清晰
    GOOD = "good"  # 基本完整，略有不足
    NEEDS_IMPROVEMENT = "needs_improvement"  # 流水账或缺少结果
    POOR = "poor"  # 严重问题


@dataclass
class AbstractCheck:
    """摘要质量检查结果"""

    has_background: bool  # 包含背景
    has_methods: bool  # 包含方法描述
    has_results: bool  # 包含具体结果
    has_conclusions: bool  # 包含结论
    is_result_oriented: bool  # 结果导向而非过程导向
    has_specific_numbers: bool  # 包含具体数值
    word_count: int
    quality: AbstractQuality
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PaperQualityReport:
    """论文质量报告"""

    paper_id: str
    abstract_check: AbstractCheck
    structure_completeness: float  # 结构完整度 0-1
    citation_validity: float  # 引用有效性 0-1
    figure_reference_check: bool  # 图表引用一致性
    symbol_table_check: bool  # 符号表完整性
    overall_score: float  # 总体评分 0-1
    overall_quality: QualityLevel
    critical_issues: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)


# ==================== 事件与消息 ====================


class WorkflowEvent(TypedDict):
    """工作流事件 - 用于Redis事件流"""

    run_id: str
    event_type: str  # stage_start / stage_end / error / progress / quality_check
    stage: Stage
    timestamp: str
    payload: Dict[str, Any]


class AgentMessage(TypedDict):
    """Agent消息 - 用于Agent间通信"""

    from_agent: str
    to_agent: str
    message_type: str  # request / response / handoff / error
    content: Dict[str, Any]
    citations: List[Citation]
    run_id: str
    timestamp: str


# ==================== 配置类型 ====================


@dataclass
class LLMConfig:
    """LLM配置"""

    model_name: str
    provider: str
    api_key_env: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120


@dataclass
class RouterConfig:
    """Router配置"""

    primary_model: str
    fallback_models: List[str]
    retry_count: int = 3
    cooldown_seconds: int = 60
    cache_enabled: bool = True
    cache_ttl: int = 3600
    max_budget_usd: float = 100.0


# ==================== 工具函数 ====================


def create_citation(
    source_id: str,
    source_type: str,
    title: str,
    url: Optional[str] = None,
    authors: Optional[str] = None,
    year: Optional[int] = None,
    quote: Optional[str] = None,
    confidence: float = 1.0,
) -> Citation:
    """创建引用对象的便捷函数"""
    return Citation(
        source_id=source_id,
        source_type=source_type,
        locator="",
        url=url,
        title=title,
        authors=authors,
        year=year,
        quote=quote,
        confidence=confidence,
    )


def create_run_manifest(
    run_id: str, problem_id: str, interpreter: str = "local"
) -> RunManifest:
    """创建运行清单的便捷函数"""
    import platform
    import sys

    return RunManifest(
        run_id=run_id,
        problem_id=problem_id,
        created_at=datetime.now().isoformat(),
        completed_at=None,
        status="running",
        seeds={},
        env=EnvironmentSpec(
            python_version=sys.version,
            pip_freeze=[],
            platform=platform.platform(),
            interpreter=interpreter,
            image_id=None,
        ),
        inputs=[],
        outputs=[],
        metrics={},
        stage_durations={},
        llm_costs={},
        error=None,
    )


# ==================== 版本信息 ====================

__version__ = "1.0.0"
__author__ = "MathModelAgent Team"
