# -*- coding: utf-8 -*-
"""
core/rag/retriever.py
Unified RAG retrieval interface integrating loader, chunker, embedder, and vector store.
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone

from .loader import load_document, is_supported_format
from .chunker import chunk_text
from .embedder import create_embedder, PROVIDER_LOCAL
from .vector_store import VectorStore


# Source Priority Weighting System
SOURCE_PRIORITY = {
    "faq": 1.5,
    "product": 1.3,
    "catalog": 1.3,
    "price": 1.2,
    "shipping": 1.2,
    "template": 1.1,
    "reply": 1.1,
    "notes": 0.7,
    "random": 0.5,
    "garbage": 0.3,
    "test": 0.5,
}


class RAGRetriever:
    """
    Unified RAG retrieval system.
    Handles document ingestion, embedding, storage, and retrieval.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_provider: str = PROVIDER_LOCAL,
        embedding_api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
    ):
        """
        Initialize RAG retriever.
        
        Args:
            vector_store: VectorStore instance (creates default if None).
            embedding_provider: Embedding provider name.
            embedding_api_key: API key for embedding provider.
            embedding_model: Embedding model name.
            embedding_base_url: Base URL for OpenAI-Compatible embeddings.
        """
        self.vector_store = vector_store or VectorStore()
        self.embedder = create_embedder(
            provider=embedding_provider,
            api_key=embedding_api_key,
            model=embedding_model,
            base_url=embedding_base_url,
        )
    
    def index_document(
        self,
        file_path: Path,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Index a document: load, chunk, embed, and store.
        
        Args:
            file_path: Path to the document file.
            metadata: Optional metadata to attach to chunks.
        
        Returns:
            Dict with keys: file_name, chunk_count, indexed_at, chunk_ids.
        
        Raises:
            ValueError: If file format is not supported.
            FileNotFoundError: If file does not exist.
        """
        if not is_supported_format(file_path):
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Load document
        text = load_document(file_path)
        
        # Chunk text
        chunks = chunk_text(text)
        
        if not chunks:
            return {
                "file_name": file_path.name,
                "chunk_count": 0,
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "chunk_ids": [],
            }
        
        # Generate embeddings
        embeddings = self.embedder.embed_batch(chunks)
        
        # Prepare metadata
        base_metadata = metadata or {}
        base_metadata.update({
            "file_name": file_path.name,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        })
        
        metadatas = [
            {**base_metadata, "chunk_index": i}
            for i in range(len(chunks))
        ]
        
        # Store in vector database
        chunk_ids = self.vector_store.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        
        return {
            "file_name": file_path.name,
            "chunk_count": len(chunks),
            "indexed_at": base_metadata["indexed_at"],
            "chunk_ids": chunk_ids,
        }
    
    def _get_source_weight(self, filename: str) -> float:
        """
        Determine source weight based on filename.
        
        Args:
            filename: Name of the source file.
        
        Returns:
            Weight multiplier (higher = more important).
        """
        filename_lower = filename.lower()
        for keyword, weight in SOURCE_PRIORITY.items():
            if keyword in filename_lower:
                return weight
        return 1.0  # default weight for unrecognized sources
    
    def _apply_source_weighting(self, results: List[Dict]) -> List[Dict]:
        """
        Apply source priority weighting and re-sort results.
        
        Args:
            results: Raw search results from vector store.
        
        Returns:
            Results with added weight fields, sorted by weighted_score.
        """
        for result in results:
            filename = result['metadata'].get('file_name', '')
            source_weight = self._get_source_weight(filename)
            
            # Convert distance to similarity (lower distance = higher similarity)
            # ChromaDB uses cosine distance: range [0, 2], lower is better
            distance = result.get('distance', 0.0)
            similarity = 1.0 - (distance / 2.0)  # normalize to [0, 1]
            
            # Calculate weighted score
            weighted_score = similarity * source_weight
            
            result['source_weight'] = source_weight
            result['similarity'] = similarity
            result['weighted_score'] = weighted_score
        
        # Re-sort by weighted_score (descending)
        results.sort(key=lambda x: x.get('weighted_score', 0.0), reverse=True)
        return results
    
    def calculate_confidence(self, results: List[Dict]) -> str:
        """
        Calculate confidence level based on top result similarity.
        
        Args:
            results: Search results (should already have similarity scores).
        
        Returns:
            "HIGH", "MEDIUM", or "LOW"
        """
        if not results:
            return "LOW"
        
        top_similarity = results[0].get('similarity', 0.0)
        
        if top_similarity >= 0.85:
            return "HIGH"
        elif top_similarity >= 0.65:
            return "MEDIUM"
        else:
            return "LOW"
    
    def detect_conflicts(self, results: List[Dict], query: str) -> Optional[str]:
        """
        Detect if retrieved chunks contain conflicting information.
        
        Args:
            results: Search results.
            query: Original query string.
        
        Returns:
            Warning message if conflict detected, None otherwise.
        """
        if len(results) < 2:
            return None
        
        # Keywords that often have specific values that might conflict
        conflict_keywords = {
            "moq": "MOQ",
            "minimum order": "MOQ",
            "price": "pricing",
            "cost": "pricing",
            "shipping": "shipping terms",
            "delivery": "delivery time",
            "payment": "payment terms",
            "lead time": "lead time",
        }
        
        query_lower = query.lower()
        detected_keyword = None
        detected_label = None
        
        for keyword, label in conflict_keywords.items():
            if keyword in query_lower:
                detected_keyword = keyword
                detected_label = label
                break
        
        if not detected_keyword:
            return None
        
        # Check if multiple top results mention the keyword
        top_texts = [r['text'].lower() for r in results[:3]]
        keyword_mentions = sum(1 for text in top_texts if detected_keyword in text)
        
        if keyword_mentions >= 2:
            # Check if they're from different sources
            sources = set(r['metadata'].get('file_name', '') for r in results[:3])
            if len(sources) > 1:
                return f"⚠️ Knowledge base contains multiple {detected_label} values from different sources. Please verify which applies to your specific case."
        
        return None
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Search for relevant chunks with source weighting applied.
        
        Args:
            query: Search query string.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filter.
        
        Returns:
            List of dicts with keys: id, text, metadata, distance, similarity, 
            source_weight, weighted_score.
        """
        if not query or not query.strip():
            return []
        
        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)
        
        # Search vector store
        results = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata,
        )
        
        # Apply source weighting and re-sort
        if results:
            results = self._apply_source_weighting(results)
        
        return results
    
    def delete_document(self, file_name: str) -> int:
        """
        Delete all chunks for a document by file name.
        
        Args:
            file_name: Name of the file to delete.
        
        Returns:
            Number of chunks deleted.
        """
        return self.vector_store.delete_by_metadata({"file_name": file_name})
    
    def get_stats(self) -> Dict:
        """
        Get retriever statistics.
        
        Returns:
            Dict with keys: total_chunks, embedding_provider.
        """
        return {
            "total_chunks": self.vector_store.count(),
            "embedding_provider": self.embedder.__class__.__name__,
        }
    
    def list_documents(self) -> List[Dict]:
        """
        List all indexed documents with summary info.
        
        Returns:
            List of dicts with keys: file_name, chunk_count, indexed_at, file_type.
        """
        try:
            all_docs = self.vector_store.get_all_documents()
            if not all_docs:
                return []
            
            # Group by filename
            file_groups = {}
            for doc in all_docs:
                metadata = doc.get("metadata", {})
                filename = metadata.get("file_name", "unknown")
                
                if filename not in file_groups:
                    file_groups[filename] = {
                        "file_name": filename,
                        "chunk_count": 0,
                        "indexed_at": metadata.get("indexed_at", ""),
                        "file_type": Path(filename).suffix.lower() if filename != "unknown" else "",
                    }
                file_groups[filename]["chunk_count"] += 1
            
            return list(file_groups.values())
        except Exception:
            return []
    
    def re_index_document(
        self,
        file_path: Path,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Re-index a document: delete old chunks and index new version.
        
        Args:
            file_path: Path to the document file.
            metadata: Optional metadata to attach to chunks.
        
        Returns:
            Dict with keys: file_name, chunk_count, indexed_at, chunk_ids, status.
        
        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file format is not supported.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Delete old chunks
        deleted_count = self.delete_document(file_path.name)
        
        # Index new version
        result = self.index_document(file_path, metadata)
        result["status"] = f"Re-indexed (deleted {deleted_count} old chunks)"
        
        return result
    
    def clear_all(self) -> None:
        """Clear all documents from the vector store."""
        self.vector_store.clear()
