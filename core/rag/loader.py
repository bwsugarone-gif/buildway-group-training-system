# -*- coding: utf-8 -*-
"""
core/rag/loader.py
Document loader for RAG system — extracts text from various file formats.
"""

from pathlib import Path
from typing import Optional


def load_text_file(file_path: Path) -> str:
    """Load plain text or markdown file."""
    return file_path.read_text(encoding="utf-8", errors="replace")


def load_pdf_file(file_path: Path) -> str:
    """Load PDF file using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF loading. Install: pip install pypdf")
    
    reader = PdfReader(str(file_path))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def load_docx_file(file_path: Path) -> str:
    """Load DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for DOCX loading. Install: pip install python-docx")
    
    doc = Document(str(file_path))
    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text)
    return "\n\n".join(text_parts)


def load_csv_file(file_path: Path) -> str:
    """
    Load CSV file using pandas and convert to text format.
    Each row is converted to "column_name: value" format.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for CSV loading. Install: pip install pandas")
    
    try:
        # Try UTF-8 first, then fallback to other encodings
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="gbk", errors="replace")
    except pd.errors.EmptyDataError:
        raise ValueError(f"CSV file is empty: {file_path}")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {e}")
    
    if df.empty:
        raise ValueError(f"CSV file contains no data: {file_path}")
    
    # Convert each row to text format
    text_parts = []
    for idx, row in df.iterrows():
        row_text_parts = []
        for col_name, value in row.items():
            # Skip NaN values
            if pd.notna(value):
                row_text_parts.append(f"{col_name}: {value}")
        if row_text_parts:
            text_parts.append("\n".join(row_text_parts))
    
    return "\n\n---\n\n".join(text_parts)


def load_document(file_path: Path) -> str:
    """
    Load document and extract text based on file extension.
    
    Args:
        file_path: Path to the document file.
    
    Returns:
        Extracted text content.
    
    Raises:
        ValueError: If file format is not supported.
        FileNotFoundError: If file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = file_path.suffix.lower()
    
    if ext in {".txt", ".md"}:
        return load_text_file(file_path)
    elif ext == ".pdf":
        return load_pdf_file(file_path)
    elif ext == ".docx":
        return load_docx_file(file_path)
    elif ext == ".csv":
        return load_csv_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def is_supported_format(file_path: Path) -> bool:
    """Check if file format is supported."""
    return file_path.suffix.lower() in {".txt", ".md", ".pdf", ".docx", ".csv"}
