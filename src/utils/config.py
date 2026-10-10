"""
Configuration management for DecisionGuard AI.

All configuration is loaded from environment variables.
API keys are NEVER hardcoded. See .env.example for required variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()


class Config:
    """Central configuration for DecisionGuard AI."""

    # ── Nebius Token Factory / NVIDIA Nemotron ──────────────────────
    NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
    NEBIUS_BASE_URL: str = "https://api.tokenfactory.nebius.com/v1/"
    NEBIUS_MODEL: str = os.getenv("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning")

    # ── RAG Vector Store Configuration ─────────────────────────────
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "decisionguard")

    # ── RAG Embedding & Chunking Configuration ─────────────────────
    # Standard sentence-transformers model for dense embeddings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    # ── Application Metadata ───────────────────────────────────────
    APP_NAME: str = "DecisionGuard AI"
    APP_DESCRIPTION: str = "Evidence-Based Decision Review Agent"
    APP_VERSION: str = "0.2.0"

    @classmethod
    def is_nebius_configured(cls) -> bool:
        """Check whether the Nebius API key has been provided."""
        return bool(cls.NEBIUS_API_KEY)

    @classmethod
    def is_pinecone_configured(cls) -> bool:
        """Check whether Pinecone is fully configured."""
        return bool(cls.PINECONE_API_KEY)

    @classmethod
    def validate(cls) -> list:
        """Validate required configuration.

        Returns:
            A list of human-readable error strings.
            An empty list means all required configuration is present.
        """
        errors = []
        if not cls.NEBIUS_API_KEY:
            errors.append(
                "NEBIUS_API_KEY is not set. "
                "Please add it to your .env file. "
                "See .env.example for reference."
            )
        return errors
