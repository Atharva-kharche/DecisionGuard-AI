"""
RAG Engine for DecisionGuard AI.

Orchestrates document parsing, chunking, and vector storage.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
from rag.loaders import extract_text_from_bytes
from rag.chunker import chunk_document
from rag.vector_store import DocumentStore


class RAGEngine:
    """Retrieval-Augmented Generation engine for document analysis."""

    def __init__(self, embeddings: Any = None) -> None:
        self.embeddings = embeddings
        self.clear()

    def clear(self) -> None:
        self.store = DocumentStore(embeddings=self.embeddings)
        self._document_names = set()
        self._chunk_count = 0
        self._all_chunks = []

    @property
    def is_ready(self) -> bool:
        """Whether at least one document has been ingested."""
        return len(self._document_names) > 0

    @property
    def document_count(self) -> int:
        """Number of unique documents ingested."""
        return len(self._document_names)

    @property
    def chunk_count(self) -> int:
        """Total number of chunks stored."""
        return self._chunk_count
        
    @property
    def document_names(self) -> List[str]:
        """List of ingested filenames."""
        return list(self._document_names)

    def ingest_bytes(self, file_bytes: bytes, filename: str) -> Tuple[bool, str]:
        """Ingest a file from its raw bytes.

        Args:
            file_bytes: Raw file content.
            filename: Original filename.

        Returns:
            Tuple of (success_bool, message_str)
        """
        try:
            # 1. Extract text
            raw_text = extract_text_from_bytes(file_bytes, filename)
            if not raw_text.strip():
                return False, f"Document {filename} is empty or unreadable."

            # 2. Chunk text
            documents = chunk_document(raw_text, filename)
            if not documents:
                return False, f"Failed to chunk {filename}."

            # 3. Store in Vector Database
            self.store.add_documents(documents)
            
            # 4. Update stats
            self._document_names.add(filename)
            self._chunk_count += len(documents)
            
            if not hasattr(self, '_all_chunks'):
                self._all_chunks = []
            
            for doc in documents:
                self._all_chunks.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
            
            return True, f"Successfully ingested {filename} ({len(documents)} chunks)."
            
        except Exception as e:
            return False, str(e)

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Retrieve all ingested chunks for a comprehensive decision review."""
        if not hasattr(self, '_all_chunks'):
            return []
        return self._all_chunks

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the most relevant document chunks for *query*.

        Args:
            query: The natural-language search query.
            top_k: Maximum number of chunks to return.

        Returns:
            List of dicts, each with ``content`` (str) and ``metadata`` (dict).
        """
        if not self.is_ready:
            return []
            
        docs = self.store.similarity_search(query, k=top_k)
        
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
            
        return results
