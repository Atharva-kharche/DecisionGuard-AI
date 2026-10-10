"""
Text chunking module for DecisionGuard AI.

Splits large documents into smaller chunks while preserving metadata.
"""

from __future__ import annotations
import os
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.config import Config


def chunk_document(text: str, filename: str) -> List[Document]:
    """Split a document into manageable chunks with metadata.
    
    Args:
        text: The raw text extracted from the document.
        filename: The original filename (used for metadata).
        
    Returns:
        A list of LangChain Document objects.
    """
    ext = os.path.splitext(filename)[1].lower().replace('.', '')
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    
    documents = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "source": filename,
            "document_type": ext,
            "chunk_index": i
        }
        documents.append(Document(page_content=chunk, metadata=metadata))
        
    return documents
