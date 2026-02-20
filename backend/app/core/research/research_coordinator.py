"""
背景研究协调器 - Research Coordinator
核心职责：自动化背景研究，为建模提供可信的文献支撑和数据证据

MCM评委评价标准强调：
"正确使用现有研究是获奖论文的关键特征之一"
"模型必须建立在坚实的研究之上"
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.config.setting import settings
from app.core.agents.expert_agent import AgentRole, ExpertAgent
from app.core.research.rag_store import (
    RAGStore,
    create_rag_store,
)
from app.core.research.web_search_tool import (
    SearchResult,
    WebSearchTool,
    create_web_search_tool,
)
from app.schemas.contracts import Citation, EvidenceSnippet
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.log_util import logger


class ResearchType(Enum):
    BACKGROUND = "背景研究"
    METHODOLOGY = "方法论研究"
    DATA_SOURCE = "数据来源"
    VALIDATION = "验证参考"
    BENCHMARK = "对标分析"


@dataclass
class ResearchQuery:
    query: str
    research_type: ResearchType
    keywords: List[str] = field(default_factory=list)
    required_sources: int = 5


@dataclass
class ResearchFinding:
    source_type: str
    title: str
    url: Optional[str]
    snippet: str
    relevance_score: float
    citation: Citation
    research_type: ResearchType
    extracted_insights: List[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    problem_summary: str
    research_queries: List[ResearchQuery]
    findings: List[ResearchFinding]
    academic_papers: List[Dict[str, Any]]
    web_sources: List[SearchResult]
    key_insights: List[str]
    methodology_references: List[str]
    data_sources: List[str]
    citations: List[Citation]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_citation_count(self) -> int:
        return len(self.citations)
    
    def get_formatted_references(self) -> str:
        refs = []
        for i, citation in enumerate(self.citations, 1):
            ref = f"[{i}] "
            if citation.authors:
                ref += f"{citation.authors}. "
            if citation.title:
                ref += f"{citation.title}. "
            if citation.year:
                ref += f"({citation.year}). "
            if citation.url:
                ref += f"{citation.url}"
            refs.append(ref)
        return "\n".join(refs)


class ResearchCoordinator(ExpertAgent):
    """
    背景研究协调器 - 整合多个研究工具进行自动化文献调研
    
    整合能力：
    1. OpenAlex学术搜索 - 学术论文和引用
    2. Web搜索 - 行业报告、新闻、政府数据
    3. RAG知识库 - 存储和检索已有知识
    """
    
    def __init__(
        self,
        task_id: str,
        model,
        openalex_email: Optional[str] = None,
        enable_web_search: bool = True,
        enable_rag: bool = True
    ):
        super().__init__(
            task_id=task_id,
            model=model,
            role=AgentRole.BACKGROUND_RESEARCH_AGENT,
            max_reflections=2,
            max_chat_turns=20
        )
        
        self.openalex_email = openalex_email or getattr(settings, 'OPENALEX_EMAIL', None)
        self.enable_web_search = enable_web_search
        self.enable_rag = enable_rag
        
        self._scholar: Optional[OpenAlexScholar] = None
        self._web_search: Optional[WebSearchTool] = None
        self._rag_store: Optional[RAGStore] = None
        
    async def _initialize_tools(self):
        if self.openalex_email:
            self._scholar = OpenAlexScholar(
                task_id=self.task_id,
                email=self.openalex_email
            )
            logger.info("OpenAlex学术搜索已初始化")
        
        if self.enable_web_search:
            self._web_search = create_web_search_tool(
                use_duckduckgo=True
            )
            logger.info("Web搜索已初始化")
        
        if self.enable_rag:
            self._rag_store = create_rag_store(
                use_openai=False,
                use_chroma=False
            )
            logger.info("RAG知识库已初始化")
    
    def get_system_prompt(self) -> str:
        return """
# 背景研究协调器 - Research Coordinator

你是一位资深的学术研究员，专门为数学建模项目进行背景调研。

## 核心职责

1. **问题背景研究**: 理解问题的领域背景、实际意义和研究现状
2. **方法论调研**: 寻找相关领域的经典方法和前沿技术
3. **数据来源发现**: 识别可用于建模的数据集和参数来源
4. **对标分析**: 寻找可用于验证模型的基准和参考

## 研究标准

- 优先使用学术来源（论文、期刊、学术会议）
- 数据来源必须可信（政府、行业协会、知名机构）
- 所有引用必须可追溯
- 避免博客、论坛等非权威来源

## 输出要求

每次研究必须提供：
1. 关键发现摘要
2. 完整的引用信息
3. 对建模的具体启示
"""

    async def execute(
        self,
        problem_description: str,
        research_focus: Optional[List[ResearchType]] = None,
        max_sources: int = 15,
        **kwargs
    ) -> ResearchReport:
        await self.setup()
        await self._initialize_tools()
        await self.send_message("开始自动化背景研究...", "info")
        
        if research_focus is None:
            research_focus = [
                ResearchType.BACKGROUND,
                ResearchType.METHODOLOGY,
                ResearchType.DATA_SOURCE
            ]
        
        research_queries = await self._generate_research_queries(
            problem_description, 
            research_focus
        )
        
        all_findings: List[ResearchFinding] = []
        academic_papers: List[Dict[str, Any]] = []
        web_sources: List[SearchResult] = []
        
        for query in research_queries:
            await self.send_message(f"正在搜索: {query.query[:50]}...", "info")
            
            if self._scholar:
                papers = await self._search_academic(query)
                academic_papers.extend(papers)
                for paper in papers[:3]:
                    finding = self._paper_to_finding(paper, query.research_type)
                    all_findings.append(finding)
            
            if self._web_search:
                web_results = await self._search_web(query)
                web_sources.extend(web_results)
                for result in web_results[:3]:
                    finding = self._web_to_finding(result, query.research_type)
                    all_findings.append(finding)
        
        key_insights = await self._synthesize_insights(all_findings, problem_description)
        methodology_refs = self._extract_methodology_references(all_findings)
        data_sources = self._extract_data_sources(all_findings)
        citations = self._compile_citations(all_findings)
        
        if self._rag_store and all_findings:
            await self._store_findings_in_rag(all_findings)
        
        report = ResearchReport(
            problem_summary=problem_description[:500],
            research_queries=research_queries,
            findings=all_findings[:max_sources],
            academic_papers=academic_papers,
            web_sources=web_sources,
            key_insights=key_insights,
            methodology_references=methodology_refs,
            data_sources=data_sources,
            citations=citations[:20]
        )
        
        await self.send_message(
            f"背景研究完成！发现 {len(academic_papers)} 篇学术论文，"
            f"{len(web_sources)} 个网络来源，提炼 {len(key_insights)} 条关键洞察",
            "success"
        )
        
        return report
    
    async def _generate_research_queries(
        self,
        problem_description: str,
        research_focus: List[ResearchType]
    ) -> List[ResearchQuery]:
        
        prompt = f"""
基于以下问题描述，为不同研究目的生成搜索查询：

## 问题描述
{problem_description}

## 需要的研究类型
{[rt.value for rt in research_focus]}

请为每种研究类型生成2-3个精确的搜索查询。

以JSON格式返回：
```json
{{
    "queries": [
        {{
            "query": "搜索查询文本",
            "type": "背景研究/方法论研究/数据来源/验证参考/对标分析",
            "keywords": ["关键词1", "关键词2"]
        }}
    ]
}}
```
"""
        
        response = await self.think(prompt, use_tools=False)
        
        queries = []
        try:
            import json
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            type_mapping = {
                "背景研究": ResearchType.BACKGROUND,
                "方法论研究": ResearchType.METHODOLOGY,
                "数据来源": ResearchType.DATA_SOURCE,
                "验证参考": ResearchType.VALIDATION,
                "对标分析": ResearchType.BENCHMARK
            }
            
            for q in data.get("queries", []):
                rt = type_mapping.get(q.get("type", ""), ResearchType.BACKGROUND)
                queries.append(ResearchQuery(
                    query=q.get("query", ""),
                    research_type=rt,
                    keywords=q.get("keywords", [])
                ))
        except Exception as e:
            logger.warning("解析研究查询失败: %s", e)
            queries.append(ResearchQuery(
                query=problem_description[:100],
                research_type=ResearchType.BACKGROUND
            ))
        
        return queries
    
    async def _search_academic(self, query: ResearchQuery) -> List[Dict[str, Any]]:
        if not self._scholar:
            return []
        
        try:
            results = await asyncio.to_thread(
                self._scholar.search,
                query.query,
                max_results=query.required_sources
            )
            return results if results else []
        except Exception as e:
            logger.warning("学术搜索失败: %s", e)
            return []
    
    async def _search_web(self, query: ResearchQuery) -> List[SearchResult]:
        if not self._web_search:
            return []
        
        try:
            results = await self._web_search.search(
                query.query,
                num_results=query.required_sources
            )
            return results
        except Exception as e:
            logger.warning("Web搜索失败: %s", e)
            return []
    
    def _paper_to_finding(
        self, 
        paper: Dict[str, Any], 
        research_type: ResearchType
    ) -> ResearchFinding:
        
        authors = paper.get("authors", [])
        author_str = ", ".join(authors[:3]) if authors else "Unknown"
        
        citation = Citation(
            source_id=f"paper:{paper.get('id', '')}",
            source_type="academic",
            locator=paper.get("doi", ""),
            url=paper.get("url", ""),
            title=paper.get("title", ""),
            authors=author_str,
            year=str(paper.get("year", "")),
            quote=paper.get("abstract", "")[:200] if paper.get("abstract") else None,
            confidence=0.9
        )
        
        return ResearchFinding(
            source_type="academic",
            title=paper.get("title", ""),
            url=paper.get("url"),
            snippet=paper.get("abstract", "")[:300] if paper.get("abstract") else "",
            relevance_score=paper.get("relevance_score", 0.8),
            citation=citation,
            research_type=research_type
        )
    
    def _web_to_finding(
        self, 
        result: SearchResult, 
        research_type: ResearchType
    ) -> ResearchFinding:
        
        citation = Citation(
            source_id=f"web:{result.source}:{hash(result.url)}",
            source_type="web",
            locator=result.url,
            url=result.url,
            title=result.title,
            authors=None,
            year=result.published_date[:4] if result.published_date else None,
            quote=result.snippet[:200] if result.snippet else None,
            confidence=result.relevance_score * 0.8
        )
        
        return ResearchFinding(
            source_type="web",
            title=result.title,
            url=result.url,
            snippet=result.snippet,
            relevance_score=result.relevance_score,
            citation=citation,
            research_type=research_type
        )
    
    async def _synthesize_insights(
        self,
        findings: List[ResearchFinding],
        problem_description: str
    ) -> List[str]:
        
        if not findings:
            return ["未找到相关研究资料"]
        
        findings_text = "\n".join([
            f"- [{f.source_type}] {f.title}: {f.snippet[:150]}..."
            for f in findings[:10]
        ])
        
        prompt = f"""
基于以下研究发现，提炼对建模有价值的关键洞察：

## 问题描述
{problem_description}

## 研究发现
{findings_text}

请提炼5-8条关键洞察，每条洞察应该：
1. 直接与建模相关
2. 可操作或可引用
3. 简洁明确

以JSON数组格式返回：
["洞察1", "洞察2", ...]
"""
        
        response = await self.think(prompt, use_tools=False)
        
        try:
            import json
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            insights = json.loads(json_str.strip())
            return insights if isinstance(insights, list) else [str(insights)]
        except Exception as e:
            logger.warning("解析研究洞察 JSON 失败，使用兜底结果: %s", e)
            return ["研究发现需要进一步分析"]
    
    def _extract_methodology_references(
        self, 
        findings: List[ResearchFinding]
    ) -> List[str]:
        methodology_findings = [
            f for f in findings 
            if f.research_type == ResearchType.METHODOLOGY
        ]
        return [f.title for f in methodology_findings[:5]]
    
    def _extract_data_sources(
        self, 
        findings: List[ResearchFinding]
    ) -> List[str]:
        data_findings = [
            f for f in findings 
            if f.research_type == ResearchType.DATA_SOURCE
        ]
        return [f"{f.title}: {f.url}" for f in data_findings[:5] if f.url]
    
    def _compile_citations(
        self, 
        findings: List[ResearchFinding]
    ) -> List[Citation]:
        seen_ids = set()
        unique_citations = []
        
        for f in findings:
            if f.citation.source_id not in seen_ids:
                seen_ids.add(f.citation.source_id)
                unique_citations.append(f.citation)
        
        unique_citations.sort(key=lambda c: c.confidence or 0, reverse=True)
        return unique_citations
    
    async def _store_findings_in_rag(self, findings: List[ResearchFinding]):
        if not self._rag_store:
            return
        
        try:
            docs = []
            for f in findings:
                docs.append({
                    "content": f"{f.title}\n\n{f.snippet}",
                    "citations": [f.citation.__dict__],
                    "metadata": {
                        "source_type": f.source_type,
                        "research_type": f.research_type.value,
                        "relevance_score": f.relevance_score
                    }
                })
            
            await self._rag_store.upsert(docs)
            logger.info("已存储 %s 条研究发现到RAG知识库", len(docs))
        except Exception as e:
            logger.warning("存储到RAG失败: %s", e)
    
    async def query_knowledge_base(
        self, 
        query: str, 
        k: int = 5
    ) -> List[EvidenceSnippet]:
        if not self._rag_store:
            return []
        
        try:
            return await self._rag_store.query_with_evidence(query, k)
        except Exception as e:
            logger.warning("查询知识库失败: %s", e)
            return []
