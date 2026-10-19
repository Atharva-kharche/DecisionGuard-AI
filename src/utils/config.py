"""
Configuration management for DecisionGuard AI.

Configuration is loaded securely from environment variables or Streamlit secrets.
API keys are NEVER hardcoded or printed. See .env.example for required variables.
"""

from __future__ import annotations

import os
from typing import Any
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()


def _get_setting(key: str, default: str = "") -> str:
    """Safely retrieve configuration from environment variables or Streamlit secrets.

    Checks os.environ first (e.g. from local .env), then falls back to Streamlit
    secrets (st.secrets) if running within Streamlit Community Cloud.
    """
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            secret_val = st.secrets[key]
            if secret_val is not None:
                return str(secret_val)
    except Exception:
        pass
    return default


class _ConfigMeta(type):
    """Metaclass allowing dynamic, secure property access for Config attributes."""

    @property
    def NEBIUS_API_KEY(cls) -> str:
        return _get_setting("NEBIUS_API_KEY", "")

    @property
    def NEBIUS_BASE_URL(cls) -> str:
        return _get_setting("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")

    @property
    def NEBIUS_MODEL(cls) -> str:
        return _get_setting("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning")

    @property
    def PINECONE_API_KEY(cls) -> str:
        return _get_setting("PINECONE_API_KEY", "")

    @property
    def PINECONE_INDEX_NAME(cls) -> str:
        return _get_setting("PINECONE_INDEX_NAME", "decisionguard")

    @property
    def EMBEDDING_MODEL(cls) -> str:
        return _get_setting("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    @property
    def CHUNK_SIZE(cls) -> int:
        val = _get_setting("CHUNK_SIZE", "1000")
        try:
            return int(val)
        except ValueError:
            return 1000

    @property
    def CHUNK_OVERLAP(cls) -> int:
        val = _get_setting("CHUNK_OVERLAP", "150")
        try:
            return int(val)
        except ValueError:
            return 150


class Config(metaclass=_ConfigMeta):
    """Central configuration for DecisionGuard AI."""

    # ── Application Metadata ───────────────────────────────────────
    APP_NAME: str = "DecisionGuard AI"
    APP_DESCRIPTION: str = "Evidence-Based Decision Review Agent"
    APP_VERSION: str = "0.2.0"

    def __getattr__(self, name: str) -> Any:
        return getattr(type(self), name)

    @classmethod
    def is_nebius_configured(cls) -> bool:
        """Check whether the Nebius API key has been provided."""
        return bool(cls.NEBIUS_API_KEY)

    @classmethod
    def is_pinecone_configured(cls) -> bool:
        """Check whether Pinecone is fully configured."""
        return bool(cls.PINECONE_API_KEY)

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration.

        Returns:
            A list of human-readable error strings.
            An empty list means all required configuration is present.
        """
        errors = []
        if not cls.NEBIUS_API_KEY:
            errors.append(
                "NEBIUS_API_KEY is not set. "
                "Please add it to your .env file (for local development) "
                "or Streamlit Cloud Secrets (under App Settings -> Secrets)."
            )
        return errors
