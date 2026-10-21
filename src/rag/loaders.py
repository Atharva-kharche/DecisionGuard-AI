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
        ValueError: If the file extension is not supported, empty, corrupted, or parsing fails.
    """
    if not file_bytes or len(file_bytes.strip()) == 0:
        raise ValueError(f"Document '{filename}' is empty (0 bytes).")

    ext = os.path.splitext(filename)[1].lower()
    
    try:
        if ext == '.pdf':
            return _extract_from_pdf(file_bytes, filename)
        elif ext == '.docx':
            return _extract_from_docx(file_bytes, filename)
        elif ext in ('.txt', '.md', '.markdown'):
            return _extract_from_txt(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file type: {ext}. Supported formats are PDF, DOCX, TXT, MD.")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Failed to parse '{filename}': {str(exc)}") from exc


def _extract_from_pdf(file_bytes: bytes, filename: str = "") -> str:
    """Parse text from a PDF."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Invalid or corrupted PDF file '{filename}': {exc}") from exc

    if getattr(reader, 'is_encrypted', False):
        raise ValueError(f"PDF '{filename}' is password-protected or encrypted. Please provide an unencrypted document.")

    text_chunks = []
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
        except Exception:
            continue

    extracted = "\n".join(text_chunks).strip()
    if not extracted:
        raise ValueError(f"No readable text could be extracted from PDF '{filename}'. Scanned images or OCR-only PDFs are not supported.")
    return extracted


def _extract_from_docx(file_bytes: bytes, filename: str = "") -> str:
    """Parse text from a Word document."""
    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Invalid or corrupted DOCX file '{filename}': {exc}") from exc

    text_chunks = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
    extracted = "\n".join(text_chunks).strip()
    if not extracted:
        raise ValueError(f"DOCX '{filename}' contains no readable paragraph text.")
    return extracted


def _extract_from_txt(file_bytes: bytes, filename: str = "") -> str:
    """Parse text from a plain text or Markdown document."""
    try:
        text = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = file_bytes.decode('latin-1', errors='replace')
    if not text.strip():
        raise ValueError(f"Text document '{filename}' is empty.")
    return text
