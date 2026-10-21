"""
Nebius Token Factory client for DecisionGuard AI.

Communicates with NVIDIA Nemotron via the Nebius Token Factory
using the OpenAI-compatible API format.

The API key is NEVER hardcoded — it is read from the environment
through the Config module.
"""

from __future__ import annotations

import time
import re
import json
from openai import (
    OpenAI,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    BadRequestError,
    PermissionDeniedError,
    NotFoundError,
    InternalServerError,
    APIStatusError,
)

from utils.config import Config


class NebiusClient:
    """Client for NVIDIA Nemotron through Nebius Token Factory.

    Usage:
        client = NebiusClient()
        reply = client.chat(messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": "Hello!"},
        ])
    """

    DEFAULT_TIMEOUT: float = 60.0
    HEALTH_CHECK_TIMEOUT: float = 8.0
    MAX_RETRIES: int = 3
    INITIAL_RETRY_DELAY: float = 1.0

    def __init__(self, client: OpenAI | None = None) -> None:
        """Initialise the client.

        Args:
            client: Optional injected OpenAI client (useful for testing/mocking).

        Raises:
            ValueError: If ``NEBIUS_API_KEY`` is not configured.
        """
        if not Config.is_nebius_configured() and client is None:
            raise ValueError(
                "NEBIUS_API_KEY is not set. "
                "Please add it to your .env file or Streamlit Cloud Secrets. "
                "See .env.example for reference."
            )

        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(
                base_url=Config.NEBIUS_BASE_URL,
                api_key=Config.NEBIUS_API_KEY,
                timeout=self.DEFAULT_TIMEOUT,
            )
        self._model: str = Config.NEBIUS_MODEL

    # ── Public properties ──────────────────────────────────────────

    @property
    def model_name(self) -> str:
        """Return the name of the configured Nemotron model."""
        return self._model

    # ── Internal Sanitization ──────────────────────────────────────

    @staticmethod
    def _sanitize_error(error_msg: str) -> str:
        """Scrub API keys and bearer tokens from error strings."""
        if not error_msg:
            return ""
        sanitized = error_msg
        key = Config.NEBIUS_API_KEY
        if key and len(key) > 5 and key in sanitized:
            sanitized = sanitized.replace(key, "[REDACTED_API_KEY]")
        # Redact bearer token patterns
        sanitized = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [REDACTED]', sanitized)
        return sanitized

    # ── Chat ───────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
        timeout: float | None = None,
    ) -> str | dict:
        """Send a conversation to Nemotron and return the response.

        Retries bounded transient errors (429 rate limits, 5xx server errors, timeouts)
        with exponential backoff up to MAX_RETRIES. Fails fast on authentication or
        client errors.

        Args:
            messages:    List of message dicts (``role`` + ``content``).
                         The caller is responsible for including the
                         system prompt.
            temperature: Sampling temperature (lower → more precise).
            max_tokens:  Maximum tokens in the response.
            json_mode:   Whether to enforce JSON parsing of the response.
            timeout:     Optional request timeout in seconds (defaults to DEFAULT_TIMEOUT).

        Returns:
            The assistant's reply as a plain string or a parsed JSON dict.

        Raises:
            ConnectionError: If the Nebius API is unreachable.
            RuntimeError:    If the model request fails permanently or retries are exhausted.
            ValueError:      If json_mode is True and parsing fails.
        """
        req_timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        content = ""
        attempt = 0

        while attempt < self.MAX_RETRIES:
            attempt += 1
            try:
                kwargs = {
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": req_timeout,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                break

            except AuthenticationError as exc:
                raise RuntimeError(
                    "Authentication failed with Nebius Token Factory. "
                    "Please verify your NEBIUS_API_KEY is correct."
                ) from exc

            except (BadRequestError, PermissionDeniedError, NotFoundError) as exc:
                clean_msg = self._sanitize_error(str(exc))
                raise RuntimeError(f"Nemotron request rejected: {clean_msg}") from exc

            except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError, APIStatusError) as exc:
                # Check if APIStatusError is a non-retryable 4xx error (other than 429)
                is_transient = True
                if isinstance(exc, APIStatusError) and getattr(exc, 'status_code', 0) not in (429, 500, 502, 503, 504):
                    is_transient = False

                if not is_transient or attempt >= self.MAX_RETRIES:
                    if isinstance(exc, RateLimitError):
                        raise RuntimeError(
                            "Nebius Token Factory rate limit exceeded. Please wait a few moments and try again."
                        ) from exc
                    elif isinstance(exc, (APITimeoutError, APIConnectionError)):
                        raise ConnectionError(
                            "Could not reach Nebius Token Factory after multiple attempts. "
                            "Please check your internet connection."
                        ) from exc
                    else:
                        clean_msg = self._sanitize_error(str(exc))
                        raise RuntimeError(f"Nemotron request failed: {clean_msg}") from exc

                # Exponential backoff delay
                delay = self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)

            except Exception as exc:
                clean_msg = self._sanitize_error(str(exc))
                raise RuntimeError(f"Nemotron request failed: {clean_msg}") from exc

        if json_mode:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON if wrapped in markdown
                if "```json" in content:
                    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if match:
                        try:
                            return json.loads(match.group(1))
                        except json.JSONDecodeError:
                            pass

                # Try to extract from the first { to the last }
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(content[start:end+1])
                    except json.JSONDecodeError:
                        pass

                # Try finding the actual schema start
                idx = content.find('"decision":')
                if idx != -1:
                    start_idx = content.rfind('{', 0, idx)
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        try:
                            return json.loads(content[start_idx:end_idx+1])
                        except json.JSONDecodeError:
                            pass

                # If all parsing attempts fail
                try:
                    with open("failed_output.txt", "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception:
                    pass
                raise ValueError(f"Failed to parse JSON response: {content[:200]}...")

        return content

    # ── Health check ───────────────────────────────────────────────

    def health_check(self) -> bool:
        """Send a minimal request to verify the API is reachable.

        Returns:
            ``True`` if the API responded successfully.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "Respond with: OK"}],
                max_tokens=5,
                timeout=self.HEALTH_CHECK_TIMEOUT,
            )
            return bool(response.choices[0].message.content)
        except Exception:
            return False
