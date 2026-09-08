from __future__ import annotations

from typing import Any

import httpx


class LLMClientError(Exception):
    pass


class OpenAICompatibleClient:
    """Minimal client for any OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout: float = 45.0,
        max_output_tokens: int = 3_000,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self._client = http_client

    def invoke(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": self.max_output_tokens,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            if self._client is not None:
                response = self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            if response.is_error:
                detail = self._format_error_detail(response)
                if response.status_code == 524:
                    raise LLMClientError(
                        "LLM provider timed out before returning a response (HTTP 524). "
                        "Try a faster model or reduce the requested output size."
                    )
                raise LLMClientError(
                    f"LLM provider returned HTTP {response.status_code}: {detail}"
                )
            data: dict[str, Any] = response.json()
            content = data["choices"][0]["message"]["content"]
            return str(content)
        except LLMClientError:
            raise
        except httpx.TimeoutException as error:
            raise LLMClientError(
                "LLM request timed out. Try a faster model or reduce the requested output size."
            ) from error
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMClientError(f"LLM request failed: {error}") from error

    @staticmethod
    def _format_error_detail(response: httpx.Response) -> str:
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            return "The provider returned an HTML error page."
        return response.text[:1000].replace("\n", " ")
