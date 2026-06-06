# -*- coding: utf-8 -*-
"""
core/rag/vector_store.py
ChromaDB wrapper for vector storage and similarity search.
"""

from pathlib import Path
from typing import List, Dict, Optional
import uuid


class VectorStore:
    """ChromaDB-based vector store for document embeddings."""
    
    def __init__(self, persist_directory: str = "data/vector_db", collection_name: str = "kb_documents"):
        """
        Initialize vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data.
            collection_name: Name of the collection to use.
        """
        try:
            import chromadb
        except ImportError:
            raise ImportError("chromadb is required. Install: pip install chromadb")
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            texts: List of text chunks.
            embeddings: List of embedding vectors.
            metadatas: Optional list of metadata dicts.
            ids: Optional list of document IDs (auto-generated if not provided).
        
        Returns:
            List of document IDs.
        """
        if not texts or not embeddings:
            return []
        
        if len(texts) != len(embeddings):
            raise ValueError("texts and embeddings must have the same length")
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        
        return ids
    
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filter.
        
        Returns:
            List of dicts with keys: id, text, metadata, distance.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
        )
        
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        
        documents = []
        for i in range(len(results["ids"][0])):
            documents.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })
        
        return documents
    
    def delete_by_metadata(self, filter_metadata: Dict) -> int:
        """
        Delete documents by metadata filter.
        
        Args:
            filter_metadata: Metadata filter dict.
        
        Returns:
            Number of documents deleted.
        """
        results = self.collection.get(where=filter_metadata)
        if not results or not results["ids"]:
            return 0
        
        ids_to_delete = results["ids"]
        self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    
    def delete_by_ids(self, ids: List[str]) -> None:
        """Delete documents by IDs."""
        if ids:
            self.collection.delete(ids=ids)
    
    def count(self) -> int:
        """Get total number of documents in the collection."""
        return self.collection.count()
    
    def get_all_documents(self) -> List[Dict]:
        """
        Get all documents with metadata.
        
        Returns:
            List of dicts with keys: id, text, metadata.
        """
        try:
            results = self.collection.get()
            if not results or not results["ids"]:
                return []
            
            documents = []
            for i in range(len(results["ids"])):
                documents.append({
                    "id": results["ids"][i],
                    "text": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
            return documents
        except Exception:
            return []
    
    def get_documents_by_filename(self, filename: str) -> List[Dict]:
        """
        Get all chunks for a specific filename.
        
        Args:
            filename: Name of the file.
        
        Returns:
            List of document dicts.
        """
        try:
            results = self.collection.get(where={"file_name": filename})
            if not results or not results["ids"]:
                return []
            
            documents = []
            for i in range(len(results["ids"])):
                documents.append({
                    "id": results["ids"][i],
                    "text": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
            return documents
        except Exception:
            return []
    
    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection(name=self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"}
        )
