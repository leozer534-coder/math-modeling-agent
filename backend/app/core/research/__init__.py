"""Research模块初始化"""

from app.core.research.assumption_generator import (
    AssumptionCategory,
    AssumptionGenerator,
    GeneratedAssumption,
    generate_assumptions,
)
from app.core.research.problem_rewriter import (
    ProblemAnalysis,
    ProblemPerspective,
    ProblemRewriter,
    SubProblem,
    rewrite_problem,
)
from app.core.research.rag_store import (
    Document,
    EmbeddingProvider,
    RAGStore,
    VectorStore,
    create_rag_store,
)
from app.core.research.research_planner import (
    ResearchPlan,
    ResearchPlanner,
)
from app.core.research.web_search_tool import (
    DuckDuckGoSearchProvider,
    SearchProvider,
    SearchResult,
    SerperSearchProvider,
    TavilySearchProvider,
    WebSearchTool,
    create_web_search_tool,
)


__all__ = [
    # Web Search
    "WebSearchTool",
    "SearchResult",
    "SearchProvider",
    "TavilySearchProvider",
    "SerperSearchProvider",
    "DuckDuckGoSearchProvider",
    "create_web_search_tool",
    # RAG Store
    "RAGStore",
    "Document",
    "EmbeddingProvider",
    "VectorStore",
    "create_rag_store",
    # Assumption Generator
    "AssumptionGenerator",
    "AssumptionCategory",
    "GeneratedAssumption",
    "generate_assumptions",
    # Problem Rewriter
    "ProblemRewriter",
    "ProblemAnalysis",
    "SubProblem",
    "ProblemPerspective",
    "rewrite_problem",
    # Research Planner
    "ResearchPlanner",
    "ResearchPlan",
]
