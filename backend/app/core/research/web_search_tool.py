"""
Web Search Tool - 自动化背景研究工具
支持多个搜索API的可插拔架构
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from app.schemas.contracts import Citation, EvidenceSnippet
from app.utils.log_util import logger


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    published_date: Optional[str] = None
    relevance_score: float = 1.0


class SearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        pass


class TavilySearchProvider(SearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"

    @property
    def name(self) -> str:
        return "tavily"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": num_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        results: List[SearchResult] = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=self.name,
                    relevance_score=item.get("score", 1.0),
                )
            )
        return results


class SerperSearchProvider(SearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://google.serper.dev"

    @property
    def name(self) -> str:
        return "serper"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/search",
                headers={"X-API-KEY": self.api_key},
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()

        results: List[SearchResult] = []
        for item in data.get("organic", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=self.name,
                    relevance_score=1.0 - (item.get("position", 1) / 100),
                )
            )
        return results


class DuckDuckGoSearchProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "duckduckgo"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        try:
            from duckduckgo_search import DDGS  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("duckduckgo_search not installed")
            return []

        results: List[SearchResult] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source=self.name,
                    )
                )
        return results


class WebSearchTool:
    def __init__(self, providers: Optional[List[SearchProvider]] = None) -> None:
        self.providers: List[SearchProvider] = (
            providers if providers is not None else []
        )
        self._result_cache: Dict[str, List[SearchResult]] = {}

    def add_provider(self, provider: SearchProvider) -> None:
        self.providers.append(provider)

    async def search(
        self,
        query: str,
        num_results: int = 10,
        providers: Optional[List[str]] = None,
        deduplicate: bool = True,
    ) -> List[SearchResult]:
        if not self.providers:
            logger.warning("No search providers configured")
            return []

        cache_key = f"{query}:{num_results}:{providers}"
        if cache_key in self._result_cache:
            return self._result_cache[cache_key]

        active_providers = self.providers
        if providers:
            active_providers = [p for p in self.providers if p.name in providers]

        tasks = [p.search(query, num_results) for p in active_providers]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: List[SearchResult] = []
        for results in results_lists:
            if isinstance(results, BaseException):
                logger.error("Search error: %s", results)
                continue
            all_results.extend(results)

        if deduplicate:
            all_results = self._deduplicate(all_results)

        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        all_results = all_results[:num_results]

        self._result_cache[cache_key] = all_results
        return all_results

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        seen_urls: set[str] = set()
        unique: List[SearchResult] = []
        for r in results:
            normalized_url = r.url.rstrip("/").lower()
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique.append(r)
        return unique

    async def search_with_citations(
        self, query: str, num_results: int = 10
    ) -> List[EvidenceSnippet]:
        results = await self.search(query, num_results)

        snippets: List[EvidenceSnippet] = []
        for i, r in enumerate(results):
            citation = Citation(
                source_id=f"web:{r.source}:{i}",
                source_type="web",
                locator=r.url,
                url=r.url,
                title=r.title,
                authors=None,
                year=None,
                quote=r.snippet[:200] if r.snippet else None,
                confidence=r.relevance_score,
            )

            snippets.append(
                EvidenceSnippet(
                    snippet_id=f"snippet_{i}",
                    content=r.snippet,
                    citations=[citation],
                    relevance_score=r.relevance_score,
                    extracted_at=datetime.now().isoformat(),
                )
            )

        return snippets

    async def research_topic(
        self,
        topic: str,
        sub_queries: Optional[List[str]] = None,
        num_results_per_query: int = 5,
    ) -> Dict[str, List[SearchResult]]:
        queries = [topic]
        if sub_queries:
            queries.extend(sub_queries)

        research_results: Dict[str, List[SearchResult]] = {}
        for query in queries:
            results = await self.search(query, num_results_per_query)
            research_results[query] = results

        return research_results


def create_web_search_tool(
    tavily_api_key: Optional[str] = None,
    serper_api_key: Optional[str] = None,
    use_duckduckgo: bool = True,
) -> WebSearchTool:
    providers: List[SearchProvider] = []

    if tavily_api_key:
        providers.append(TavilySearchProvider(tavily_api_key))

    if serper_api_key:
        providers.append(SerperSearchProvider(serper_api_key))

    if use_duckduckgo:
        providers.append(DuckDuckGoSearchProvider())

    return WebSearchTool(providers)
