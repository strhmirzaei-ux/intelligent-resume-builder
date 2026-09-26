from __future__ import annotations

from typing import Any

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


class LLMClientError(Exception):
    pass


class GeminiAIStudioClient:
    """Google Gen AI SDK client for Gemini Developer API (AI Studio)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 45.0,
        max_output_tokens: int = 3_000,
        client: Any = None,
    ) -> None:
        from google import genai
        from google.genai import types

        self.model = model
        self.max_output_tokens = max_output_tokens
        self._types = types
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=self.max_output_tokens,
                    response_mime_type="application/json",
                ),
            )
            return response.text or ""
        except Exception as error:
            # Keep provider-specific SDK errors behind the app's stable interface.
            raise LLMClientError(f"Gemini AI Studio request failed: {error}") from error


class OpenAICompatibleClient:
    """OpenAI SDK client for OpenAI-compatible chat-completions endpoints."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout: float = 45.0,
        max_output_tokens: int = 3_000,
        max_network_retries: int = 2,
        http_client: httpx.Client | None = None,
        openai_client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.base_url = base_url.rstrip("/")
        self._client = openai_client or OpenAI(
            api_key=api_key or "unused",
            base_url=self.base_url,
            timeout=timeout,
            max_retries=max(0, max_network_retries),
            http_client=http_client,
        )

    @property
    def completion_url(self) -> str:
        """Return the chat-completions URL for either URL configuration style."""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def invoke(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=self.max_output_tokens,
                stream=False,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""
        except APIStatusError as error:
            detail = self._format_error_detail(error)
            if error.status_code == 524:
                raise LLMClientError(
                    "LLM provider timed out before returning a response (HTTP 524). "
                    "Try a faster model or reduce the requested output size."
                ) from error
            if error.status_code == 503 and self._looks_like_model_unavailable(detail):
                raise LLMClientError(
                    f"Model '{self.model}' is unavailable for this API key. "
                    "Check the provider's model list and update LLM_MODEL."
                ) from error
            raise LLMClientError(
                f"LLM provider returned HTTP {error.status_code}: {detail}"
            ) from error
        except (APITimeoutError, httpx.TimeoutException) as error:
            raise LLMClientError(
                "LLM request timed out. Try a faster model or reduce the requested output size."
            ) from error
        except (APIConnectionError, httpx.TransportError) as error:
            raise LLMClientError(
                "Could not connect securely to the LLM service. Check internet, VPN, or proxy settings."
            ) from error
        except (httpx.HTTPError, IndexError, TypeError, ValueError) as error:
            raise LLMClientError(f"LLM request failed: {error}") from error

    @staticmethod
    def _format_error_detail(error: APIStatusError) -> str:
        body: Any = error.body
        if isinstance(body, dict):
            return str(body)[:1000].replace("\n", " ")
        return str(body or error.message)[:1000].replace("\n", " ")

    @staticmethod
    def _looks_like_model_unavailable(detail: str) -> bool:
        text = detail.casefold()
        return any(
            marker in text
            for marker in (
                "model unavailable",
                "model not found",
                "模型不可用",
                "模型不存在",
                "new_model_not_found",
            )
        )
