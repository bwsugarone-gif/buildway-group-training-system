# -*- coding: utf-8 -*-
"""
verticals/crm/customer_rag.py
Buildway AI Core — CRM Vertical: Customer RAG

Extends core RAG with CRM-specific document categories.
Customer documents: contracts, proposals, emails, meeting notes, etc.
"""

from pathlib import Path
from core.rag.rag_manager import (
    index_document,
    search,
    list_documents,
    remove_document,
)

# CRM-specific document categories
CRM_CATEGORIES = [
    "contracts",
    "proposals",
    "emails",
    "meeting_notes",
    "support_tickets",
    "product_docs",
    "customer_sop",
]

CRM_CATEGORY_LABELS = {
    "contracts": "Contracts",
    "proposals": "Proposals",
    "emails": "Email Correspondence",
    "meeting_notes": "Meeting Notes",
    "support_tickets": "Support Tickets",
    "product_docs": "Product Documentation",
    "customer_sop": "Customer SOP",
}

# Default CRM RAG index location
_CRM_INDEX = Path(__file__).parent.parent.parent / "data" / "crm_rag_index.json"


def index_customer_document(
    file_path: Path,
    text: str,
    customer_id: str,
    category: str = "customer_sop",
    metadata: dict | None = None,
) -> str:
    """
    Index a customer document into the CRM RAG index.

    Args:
        file_path: Path to the source file.
        text: Extracted text content.
        customer_id: Customer ID to associate with this document.
        category: CRM document category.
        metadata: Optional extra metadata.

    Returns:
        Document ID string.
    """
    meta = metadata or {}
    meta["customer_id"] = customer_id
    meta["crm_category"] = category
    return index_document(
        file_path=file_path,
        text=text,
        category=category,
        metadata=meta,
        index_file=_CRM_INDEX,
    )


def search_customer_docs(
    query: str,
    customer_id: str | None = None,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Search CRM documents.

    Args:
        query: Search query.
        customer_id: Optional filter by customer ID.
        category: Optional filter by category.
        top_k: Number of results.

    Returns:
        List of matching chunks with scores.
    """
    results = search(
        query=query,
        top_k=top_k * 3,  # Over-fetch then filter
        category=category,
        index_file=_CRM_INDEX,
    )
    if customer_id:
        results = [
            r for r in results
            if r.get("metadata", {}).get("customer_id") == customer_id
        ]
    return results[:top_k]


def list_customer_documents(customer_id: str | None = None) -> list[dict]:
    """List all CRM documents, optionally filtered by customer."""
    docs = list_documents(index_file=_CRM_INDEX)
    if customer_id:
        # Filter by metadata — requires loading full index
        from core.rag.rag_manager import _load_index
        index = _load_index(_CRM_INDEX)
        docs = [
            {
                "doc_id": d["doc_id"],
                "file_name": d["file_name"],
                "category": d.get("category", ""),
                "chunk_count": d.get("chunk_count", 0),
                "indexed_at": d.get("indexed_at", ""),
                "customer_id": d.get("metadata", {}).get("customer_id", ""),
            }
            for d in index.get("documents", [])
            if d.get("metadata", {}).get("customer_id") == customer_id
        ]
    return docs
