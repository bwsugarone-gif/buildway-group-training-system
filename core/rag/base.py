"""
core/rag/base.py
----------------
Abstract interface for RAG (Retrieval-Augmented Generation) operations.
Concrete implementations (Qdrant, local JSON) extend this base.
Placeholder — not connected to a real vector store yet.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Document:
    """A document chunk stored in the knowledge base."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    knowledge_base_id: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """A single result returned from a knowledge base search."""
    document_id: str = ""
    content: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseRAG(ABC):
    """
    Abstract RAG interface.
    All operations are scoped to a tenant_id — no cross-tenant retrieval.
    """

    @abstractmethod
    def ingest_document(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Ingest a document chunk into the knowledge base.
        Returns the document ID.
        """
        ...

    @abstractmethod
    def search_knowledge(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Search the knowledge base for chunks relevant to the query.
        Returns up to top_k results ordered by relevance score (descending).
        """
        ...

    @abstractmethod
    def delete_knowledge_base(self, tenant_id: str, knowledge_base_id: str) -> bool:
        """
        Delete all documents in a knowledge base for a tenant.
        Returns True if successful.
        """
        ...


class InMemoryRAG(BaseRAG):
    """
    In-memory placeholder implementation for local dev and testing.
    Uses simple keyword matching — not semantic search.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}

    def ingest_document(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        doc = Document(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            content=content,
            metadata=metadata or {},
        )
        self._documents[doc.id] = doc
        return doc.id

    def search_knowledge(
        self,
        tenant_id: str,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        query_lower = query.lower()
        results: list[SearchResult] = []

        for doc in self._documents.values():
            if doc.tenant_id != tenant_id:
                continue
            if doc.knowledge_base_id != knowledge_base_id:
                continue
            # Simple keyword overlap score
            words = set(query_lower.split())
            doc_words = set(doc.content.lower().split())
            overlap = len(words & doc_words)
            if overlap > 0:
                score = overlap / max(len(words), 1)
                results.append(
                    SearchResult(
                        document_id=doc.id,
                        content=doc.content,
                        score=score,
                        metadata=doc.metadata,
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete_knowledge_base(self, tenant_id: str, knowledge_base_id: str) -> bool:
        to_delete = [
            doc_id
            for doc_id, doc in self._documents.items()
            if doc.tenant_id == tenant_id and doc.knowledge_base_id == knowledge_base_id
        ]
        for doc_id in to_delete:
            del self._documents[doc_id]
        return True
