"""
Vector Store interface for DecisionGuard AI.

Supports Pinecone (primary) and FAISS (local fallback).
"""

from __future__ import annotations
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from utils.config import Config


class DocumentStore:
    """Manages the underlying vector store and embeddings."""

    def __init__(self) -> None:
        """Initialize embeddings and the vector store backend."""
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL)
        
        self.use_pinecone = Config.is_pinecone_configured()
        self.store = None
        
        # Local fallback mode uses FAISS in-memory
        self.local_faiss = None
        
    def _init_store(self, first_docs: List[Document] = None):
        """Lazy initialization of the vector store."""
        if self.use_pinecone:
            if self.store is None:
                try:
                    from langchain_pinecone import PineconeVectorStore
                except ImportError as exc:
                    raise ImportError(
                        "Pinecone is configured but 'langchain-pinecone' is not installed. "
                        "Please install 'pinecone' and 'langchain-pinecone' to use Pinecone."
                    ) from exc
                self.store = PineconeVectorStore(
                    index_name=Config.PINECONE_INDEX_NAME, 
                    embedding=self.embeddings
                )
        else:
            if self.local_faiss is None:
                if not first_docs:
                    # Initialize empty FAISS requires at least one dimension or doc in older langchain, 
                    # but we'll only initialize when we have the first docs.
                    return
                self.local_faiss = FAISS.from_documents(first_docs, self.embeddings)

    def add_documents(self, documents: List[Document]) -> None:
        """Add chunked documents to the vector store."""
        if not documents:
            return
            
        if self.use_pinecone:
            self._init_store()
            self.store.add_documents(documents)
        else:
            if self.local_faiss is None:
                self._init_store(first_docs=documents)
            else:
                self.local_faiss.add_documents(documents)

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Retrieve most relevant document chunks for the query."""
        if self.use_pinecone:
            if self.store is None:
                self._init_store()
            return self.store.similarity_search(query, k=k)
        else:
            if self.local_faiss is None:
                return []
            return self.local_faiss.similarity_search(query, k=k)
            
    def get_document_count(self) -> int:
        """Approximate count of chunks."""
        # For simplicity in local dev, we just track this externally in engine, 
        # but FAISS exposes index.ntotal
        if self.use_pinecone:
            # Requires pinecone client direct access for stats
            return 0
        else:
            if self.local_faiss is None:
                return 0
            return self.local_faiss.index.ntotal
