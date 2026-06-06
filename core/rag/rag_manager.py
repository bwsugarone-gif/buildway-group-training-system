# -*- coding: utf-8 -*-
"""
core/rag/rag_manager.py
Buildway AI Core — RAG Lite Document Processing Layer

Local JSON index only. No OCR, no Qdrant, no vector database.
Industry-neutral: categories and labels are configurable per vertical.
"""

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


_BASE_DIR = Path(__file__).parent.parent.parent
RAG_DIR = _BASE_DIR / "data" / "rag_documents"
INDEX_FILE = _BASE_DIR / "data" / "rag_index.json"

# Default categories — verticals can override
DEFAULT_CATEGORIES = [
    "regulations",
    "codes_of_practice",
    "guidelines",
    "company_sop",
    "project_docs",
    "reference",
]

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt"}
PRIMARY_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
CHUNK_MIN = 800
CHUNK_TARGET = 1000
CHUNK_MAX = 1200


def _load_index(index_file: Path | None = None) -> dict:
    """Load the RAG index from JSON. Returns empty index on error."""
    path = index_file or INDEX_FILE
    if not path.exists():
        return {"documents": [], "last_updated": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"documents": [], "last_updated": None}
        return data
    except Exception:
        return {"documents": [], "last_updated": None}


def _save_index(index: dict, index_file: Path | None = None) -> None:
    path = index_file or INDEX_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _chunk_text(text: str) -> list[str]:
    """Split text into chunks of roughly CHUNK_TARGET characters."""
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) > CHUNK_MAX and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para)
        if current_len >= CHUNK_TARGET:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("\n\n".join(current))

    return [c for c in chunks if len(c) >= CHUNK_MIN] or [text[:CHUNK_MAX]]


def _simple_score(query: str, chunk: str) -> float:
    """Simple keyword overlap score (no embeddings)."""
    query_words = set(re.findall(r"\w+", query.lower()))
    chunk_words = set(re.findall(r"\w+", chunk.lower()))
    if not query_words:
        return 0.0
    overlap = query_words & chunk_words
    return len(overlap) / math.sqrt(len(query_words) * max(len(chunk_words), 1))


def index_document(
    file_path: Path,
    text: str,
    category: str = "project_docs",
    metadata: dict | None = None,
    index_file: Path | None = None,
) -> str:
    """
    Add a document to the RAG index.

    Args:
        file_path: Path to the source file.
        text: Extracted text content.
        category: Document category.
        metadata: Optional extra metadata dict.
        index_file: Override index file path.

    Returns:
        Document ID string.
    """
    index = _load_index(index_file)
    documents = index.get("documents", [])

    doc_id = f"DOC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{Path(file_path).stem[:8]}"
    chunks = _chunk_text(text)

    doc_entry = {
        "doc_id": doc_id,
        "file_name": Path(file_path).name,
        "file_path": str(file_path),
        "category": category,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "metadata": metadata or {},
    }

    # Remove existing entry for same file
    documents = [d for d in documents if d.get("file_name") != Path(file_path).name]
    documents.append(doc_entry)

    index["documents"] = documents
    index["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_index(index, index_file)
    return doc_id


def search(
    query: str,
    top_k: int = 5,
    category: str | None = None,
    index_file: Path | None = None,
) -> list[dict]:
    """
    Search the RAG index for relevant chunks.

    Args:
        query: Search query string.
        top_k: Number of top results to return.
        category: Optional category filter.
        index_file: Override index file path.

    Returns:
        List of dicts with keys: doc_id, file_name, category, chunk, score.
    """
    index = _load_index(index_file)
    documents = index.get("documents", [])

    if category:
        documents = [d for d in documents if d.get("category") == category]

    results = []
    for doc in documents:
        for chunk in doc.get("chunks", []):
            score = _simple_score(query, chunk)
            if score > 0:
                results.append({
                    "doc_id": doc["doc_id"],
                    "file_name": doc["file_name"],
                    "category": doc.get("category", ""),
                    "chunk": chunk,
                    "score": round(score, 4),
                    "metadata": doc.get("metadata", {}),
                })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def list_documents(category: str | None = None, index_file: Path | None = None) -> list[dict]:
    """List all indexed documents, optionally filtered by category."""
    index = _load_index(index_file)
    documents = index.get("documents", [])
    if category:
        documents = [d for d in documents if d.get("category") == category]
    return [
        {
            "doc_id": d["doc_id"],
            "file_name": d["file_name"],
            "category": d.get("category", ""),
            "chunk_count": d.get("chunk_count", 0),
            "indexed_at": d.get("indexed_at", ""),
        }
        for d in documents
    ]


def remove_document(file_name: str, index_file: Path | None = None) -> bool:
    """Remove a document from the index by file name. Returns True if removed."""
    index = _load_index(index_file)
    documents = index.get("documents", [])
    new_docs = [d for d in documents if d.get("file_name") != file_name]
    if len(new_docs) == len(documents):
        return False
    index["documents"] = new_docs
    index["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_index(index, index_file)
    return True
