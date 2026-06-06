# -*- coding: utf-8 -*-
"""
core/rag/embedder.py
Embedding abstraction layer supporting multiple providers.
"""

from typing import List, Optional
import sys
from pathlib import Path


# Embedding providers
PROVIDER_OPENAI = "OpenAI"
PROVIDER_OPENAI_COMPATIBLE = "OpenAI-Compatible"
PROVIDER_LOCAL = "Local"

DEFAULT_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"


class EmbeddingProvider:
    """Base class for embedding providers."""
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        raise NotImplementedError
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed_text(text) for text in texts]


class LocalEmbedder(EmbeddingProvider):
    """Local sentence-transformers embedder."""
    
    def __init__(self, model_name: str = DEFAULT_LOCAL_MODEL):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install: pip install sentence-transformers"
            )
        self.model = SentenceTransformer(model_name)
    
    def embed_text(self, text: str) -> List[float]:
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


class OpenAIEmbedder(EmbeddingProvider):
    """OpenAI embeddings provider."""
    
    def __init__(self, api_key: str, model: str = DEFAULT_OPENAI_MODEL):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai is required. Install: pip install openai")
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]


class OpenAICompatibleEmbedder(EmbeddingProvider):
    """OpenAI-Compatible embeddings provider (e.g., OpenRouter, local LLM)."""
    
    def __init__(self, base_url: str, api_key: str, model: str):
        import json
        from urllib import request, error
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._request = request
        self._json = json
    
    def _normalize_endpoint(self) -> str:
        """Normalize base URL to include /v1 if needed."""
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/embeddings"
        return f"{self.base_url}/v1/embeddings"
    
    def embed_text(self, text: str) -> List[float]:
        endpoint = self._normalize_endpoint()
        payload = {
            "model": self.model,
            "input": text,
        }
        
        req = self._request.Request(
            endpoint,
            data=self._json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        
        with self._request.urlopen(req, timeout=30) as response:
            raw_body = response.read().decode("utf-8")
        
        parsed = self._json.loads(raw_body)
        return parsed["data"][0]["embedding"]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        endpoint = self._normalize_endpoint()
        payload = {
            "model": self.model,
            "input": texts,
        }
        
        req = self._request.Request(
            endpoint,
            data=self._json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        
        with self._request.urlopen(req, timeout=30) as response:
            raw_body = response.read().decode("utf-8")
        
        parsed = self._json.loads(raw_body)
        return [item["embedding"] for item in parsed["data"]]


def create_embedder(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> EmbeddingProvider:
    """
    Factory function to create an embedder based on provider.
    
    Args:
        provider: One of PROVIDER_OPENAI, PROVIDER_OPENAI_COMPATIBLE, PROVIDER_LOCAL.
        api_key: API key for OpenAI or OpenAI-Compatible providers.
        model: Model name (optional, uses defaults if not provided).
        base_url: Base URL for OpenAI-Compatible provider.
    
    Returns:
        EmbeddingProvider instance.
    
    Raises:
        ValueError: If required parameters are missing.
    """
    if provider == PROVIDER_LOCAL:
        model = model or DEFAULT_LOCAL_MODEL
        return LocalEmbedder(model_name=model)
    
    elif provider == PROVIDER_OPENAI:
        if not api_key:
            raise ValueError("API key is required for OpenAI embeddings")
        model = model or DEFAULT_OPENAI_MODEL
        return OpenAIEmbedder(api_key=api_key, model=model)
    
    elif provider == PROVIDER_OPENAI_COMPATIBLE:
        if not api_key:
            raise ValueError("API key is required for OpenAI-Compatible embeddings")
        if not base_url:
            raise ValueError("Base URL is required for OpenAI-Compatible embeddings")
        if not model:
            raise ValueError("Model name is required for OpenAI-Compatible embeddings")
        return OpenAICompatibleEmbedder(base_url=base_url, api_key=api_key, model=model)
    
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
