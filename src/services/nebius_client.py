"""
Nebius Token Factory client for DecisionGuard AI.

Communicates with NVIDIA Nemotron via the Nebius Token Factory
using the OpenAI-compatible API format.

The API key is NEVER hardcoded — it is read from the environment
through the Config module.
"""

from __future__ import annotations

from openai import OpenAI, APIConnectionError, AuthenticationError

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

    def __init__(self) -> None:
        """Initialise the client.

        Raises:
            ValueError: If ``NEBIUS_API_KEY`` is not configured.
        """
        if not Config.is_nebius_configured():
            raise ValueError(
                "NEBIUS_API_KEY is not set. "
                "Please add it to your .env file. "
                "See .env.example for reference."
            )

        self._client = OpenAI(
            base_url=Config.NEBIUS_BASE_URL,
            api_key=Config.NEBIUS_API_KEY,
        )
        self._model: str = Config.NEBIUS_MODEL

    # ── Public properties ──────────────────────────────────────────

    @property
    def model_name(self) -> str:
        """Return the name of the configured Nemotron model."""
        return self._model

    # ── Chat ───────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str | dict:
        """Send a conversation to Nemotron and return the response.

        Args:
            messages:    List of message dicts (``role`` + ``content``).
                         The caller is responsible for including the
                         system prompt.
            temperature: Sampling temperature (lower → more precise).
            max_tokens:  Maximum tokens in the response.
            json_mode:   Whether to enforce JSON parsing of the response.

        Returns:
            The assistant's reply as a plain string or a parsed JSON dict.

        Raises:
            ConnectionError: If the Nebius API is unreachable.
            RuntimeError:    If the model request fails for any reason.
            ValueError:      If json_mode is True and parsing fails.
        """
        try:
            # Note: Depending on the specific Nemotron endpoint, 
            # response_format={"type": "json_object"} might be supported.
            # We explicitly ask the model to produce JSON in the prompt as well.
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            
            if json_mode:
                import json
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON if there's markdown wrapping
                    if "```json" in content:
                        import re
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
                            
                    # If all else fails
                    with open("failed_output.txt", "w", encoding="utf-8") as f:
                        f.write(content)
                    raise ValueError(f"Failed to parse JSON response: {content[:200]}...")
            
            return content

        except APIConnectionError as exc:
            raise ConnectionError(
                "Could not reach Nebius Token Factory. "
                "Please check your internet connection and the API URL."
            ) from exc

        except AuthenticationError:
            raise RuntimeError(
                "Authentication failed with Nebius Token Factory. "
                "Please verify your NEBIUS_API_KEY is correct."
            )

        except Exception as exc:
            error_msg = str(exc)
            # Scrub the API key from any error message
            if Config.NEBIUS_API_KEY and Config.NEBIUS_API_KEY in error_msg:
                error_msg = (
                    "Authentication error with Nebius Token Factory. "
                    "Please check your API key."
                )
            raise RuntimeError(
                f"Nemotron request failed: {error_msg}"
            ) from exc

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
            )
            return bool(response.choices[0].message.content)
        except Exception:
            return False
