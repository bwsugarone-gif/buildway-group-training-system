# -*- coding: utf-8 -*-
"""
core/rag/chunker.py
Intelligent text chunking for RAG system.
Preserves paragraphs, bullet points, and headings.
"""

import re
from typing import List


CHUNK_SIZE = 800
OVERLAP = 120


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks while preserving structure.
    
    Args:
        text: Input text to chunk.
        chunk_size: Target size for each chunk (characters).
        overlap: Number of characters to overlap between chunks.
    
    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []
    
    # Split by paragraphs (double newline or more)
    paragraphs = re.split(r'\n\s*\n', text.strip())
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        para_size = len(para)
        
        # If single paragraph exceeds chunk_size, split it
        if para_size > chunk_size * 1.5:
            # Save current chunk if exists
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split long paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            temp_chunk = []
            temp_size = 0
            
            for sent in sentences:
                sent_size = len(sent)
                if temp_size + sent_size > chunk_size and temp_chunk:
                    chunks.append(' '.join(temp_chunk))
                    # Keep overlap
                    overlap_text = ' '.join(temp_chunk[-2:]) if len(temp_chunk) >= 2 else temp_chunk[-1] if temp_chunk else ''
                    temp_chunk = [overlap_text, sent] if overlap_text else [sent]
                    temp_size = len(overlap_text) + sent_size
                else:
                    temp_chunk.append(sent)
                    temp_size += sent_size
            
            if temp_chunk:
                chunks.append(' '.join(temp_chunk))
            continue
        
        # Check if adding this paragraph exceeds chunk_size
        if current_size + para_size > chunk_size and current_chunk:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk))
            
            # Start new chunk with overlap
            if overlap > 0 and current_chunk:
                # Keep last paragraph as overlap if it fits
                last_para = current_chunk[-1]
                if len(last_para) <= overlap:
                    current_chunk = [last_para, para]
                    current_size = len(last_para) + para_size
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk = [para]
                current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size
    
    # Add remaining chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


def chunk_document(text: str, metadata: dict = None) -> List[dict]:
    """
    Chunk document and return structured chunks with metadata.
    
    Args:
        text: Input text to chunk.
        metadata: Optional metadata to attach to each chunk.
    
    Returns:
        List of dicts with keys: text, chunk_id, metadata.
    """
    chunks = chunk_text(text)
    metadata = metadata or {}
    
    return [
        {
            "text": chunk,
            "chunk_id": f"chunk_{i:04d}",
            "metadata": metadata,
        }
        for i, chunk in enumerate(chunks)
    ]
