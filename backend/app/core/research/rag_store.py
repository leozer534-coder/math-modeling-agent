"""
RAG Store - Citation-first 向量检索知识库
支持本地与远程知识源，强制引用追踪
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.schemas.contracts import Citation, EvidenceSnippet
from app.utils.log_util import logger


@dataclass
class Document:
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    citations: List[Citation]
    embedding: Optional[List[float]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class OpenAIEmbedding(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self.api_key = api_key
        self.model = model
        self._dimension = 1536

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()

        embeddings: List[List[float]] = [item["embedding"] for item in data["data"]]
        return embeddings


class LocalEmbedding(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any = None
        self._dimension = 384

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import (
                    SentenceTransformer,  # type: ignore[import-not-found]
                )

                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise

    async def embed(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if self._model is None:
            raise RuntimeError("Model failed to load")
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()  # type: ignore[no-any-return]


class VectorStore(ABC):
    @abstractmethod
    async def add(
        self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        pass

    @abstractmethod
    async def search(self, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete(self, doc_ids: List[str]) -> int:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._vectors: Dict[str, Dict[str, Any]] = {}

    async def add(
        self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        self._vectors[doc_id] = {"embedding": embedding, "metadata": metadata}

    async def search(self, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        if not self._vectors:
            return []

        scores: List[tuple[str, float, Dict[str, Any]]] = []
        for doc_id, data in self._vectors.items():
            score = self._cosine_similarity(embedding, data["embedding"])
            scores.append((doc_id, score, data["metadata"]))

        scores.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for doc_id, score, metadata in scores[:k]:
            results.append({"doc_id": doc_id, "score": score, "metadata": metadata})
        return results

    async def delete(self, doc_ids: List[str]) -> int:
        deleted = 0
        for doc_id in doc_ids:
            if doc_id in self._vectors:
                del self._vectors[doc_id]
                deleted += 1
        return deleted

    async def count(self) -> int:
        return len(self._vectors)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        import math

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class ChromaVectorStore(VectorStore):
    def __init__(
        self,
        collection_name: str = "math_modeling_kb",
        persist_directory: Optional[str] = None,
    ) -> None:
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._collection: Any = None

    def _get_collection(self) -> Any:
        if self._collection is None:
            try:
                import chromadb  # type: ignore[import-not-found]

                if self.persist_directory:
                    client = chromadb.PersistentClient(path=self.persist_directory)
                else:
                    client = chromadb.Client()
                self._collection = client.get_or_create_collection(self.collection_name)
            except ImportError:
                logger.error("chromadb not installed")
                raise
        return self._collection

    async def add(
        self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        collection = self._get_collection()
        collection.add(ids=[doc_id], embeddings=[embedding], metadatas=[metadata])

    async def search(self, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        collection = self._get_collection()
        results = collection.query(query_embeddings=[embedding], n_results=k)

        output: List[Dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        distances = (
            results.get("distances", [[]])[0] if results.get("distances") else []
        )
        metadatas = (
            results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        )

        for i, doc_id in enumerate(ids):
            score = 1 - distances[i] if i < len(distances) else 1.0
            meta = metadatas[i] if i < len(metadatas) else {}
            output.append({"doc_id": doc_id, "score": score, "metadata": meta})
        return output

    async def delete(self, doc_ids: List[str]) -> int:
        collection = self._get_collection()
        collection.delete(ids=doc_ids)
        return len(doc_ids)

    async def count(self) -> int:
        return self._get_collection().count()  # type: ignore[no-any-return]


class RAGStore:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._documents: Dict[str, Document] = {}

    def _generate_doc_id(self, content: str, citations: List[Citation]) -> str:
        hash_input = content + json.dumps([c.get("source_id", "") for c in citations])
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks

    async def upsert(self, docs: List[Dict[str, Any]]) -> int:
        count = 0
        for doc in docs:
            content = doc.get("content", "")
            citations = doc.get("citations", [])
            metadata = doc.get("metadata", {})

            if not citations:
                logger.warning("Document without citations, skipping")
                continue

            chunks = self._chunk_text(content)
            embeddings = await self.embedding_provider.embed(chunks)

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"{self._generate_doc_id(content, citations)}_{i}"

                document = Document(
                    doc_id=doc_id,
                    content=chunk,
                    metadata={
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "citations": citations,
                    },
                    citations=citations,
                    embedding=embedding,
                )

                self._documents[doc_id] = document
                await self.vector_store.add(doc_id, embedding, document.metadata)
                count += 1

        return count

    async def query(
        self, q: str, k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        embeddings = await self.embedding_provider.embed([q])
        query_embedding = embeddings[0]

        results = await self.vector_store.search(query_embedding, k)

        output: List[Dict[str, Any]] = []
        for r in results:
            doc_id = r["doc_id"]
            if doc_id in self._documents:
                doc = self._documents[doc_id]
                output.append(
                    {
                        "doc_id": doc_id,
                        "content": doc.content,
                        "citations": doc.citations,
                        "score": r["score"],
                        "metadata": doc.metadata,
                    }
                )
            else:
                output.append(
                    {
                        "doc_id": doc_id,
                        "content": r["metadata"].get("content", ""),
                        "citations": r["metadata"].get("citations", []),
                        "score": r["score"],
                        "metadata": r["metadata"],
                    }
                )

        return output

    async def delete(self, doc_ids: List[str]) -> int:
        deleted = await self.vector_store.delete(doc_ids)
        for doc_id in doc_ids:
            self._documents.pop(doc_id, None)
        return deleted

    async def count(self) -> int:
        return await self.vector_store.count()

    async def query_with_evidence(self, q: str, k: int = 10) -> List[EvidenceSnippet]:
        results = await self.query(q, k)

        snippets: List[EvidenceSnippet] = []
        for r in results:
            snippets.append(
                EvidenceSnippet(
                    snippet_id=r["doc_id"],
                    content=r["content"],
                    citations=r["citations"],
                    relevance_score=r["score"],
                    extracted_at=datetime.now().isoformat(),
                )
            )

        return snippets


def create_rag_store(
    use_openai: bool = False,
    openai_api_key: Optional[str] = None,
    use_chroma: bool = False,
    chroma_persist_dir: Optional[str] = None,
) -> RAGStore:
    embedding_provider: EmbeddingProvider
    if use_openai and openai_api_key:
        embedding_provider = OpenAIEmbedding(openai_api_key)
    else:
        embedding_provider = LocalEmbedding()

    vector_store: VectorStore
    if use_chroma:
        vector_store = ChromaVectorStore(persist_directory=chroma_persist_dir)
    else:
        vector_store = InMemoryVectorStore()

    return RAGStore(embedding_provider, vector_store)
