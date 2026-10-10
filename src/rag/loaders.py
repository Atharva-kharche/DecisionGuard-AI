"""
Document ingestion loaders for DecisionGuard AI.

Supports parsing PDF, DOCX, TXT, and Markdown files.
"""

from __future__ import annotations
import io
import os
from pypdf import PdfReader
from docx import Document


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from a file's byte stream based on its extension.
    
    Args:
        file_bytes: The raw byte content of the file.
        filename: The name of the file (used to determine extension).
        
    Returns:
        The extracted plain text.
        
    Raises:
        ValueError: If the file extension is not supported or parsing fails.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        if ext == '.pdf':
            return _extract_from_pdf(file_bytes)
        elif ext == '.docx':
            return _extract_from_docx(file_bytes)
        elif ext in ('.txt', '.md', '.markdown'):
            return _extract_from_txt(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Failed to parse {filename}: {str(exc)}") from exc


def _extract_from_pdf(file_bytes: bytes) -> str:
    """Parse text from a PDF."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text_chunks = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_chunks.append(page_text)
    return "\n".join(text_chunks)


def _extract_from_docx(file_bytes: bytes) -> str:
    """Parse text from a Word document."""
    doc = Document(io.BytesIO(file_bytes))
    text_chunks = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
    return "\n".join(text_chunks)


def _extract_from_txt(file_bytes: bytes) -> str:
    """Parse text from a plain text or Markdown document."""
    # Attempt UTF-8 first, fallback to latin-1
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1', errors='replace')
