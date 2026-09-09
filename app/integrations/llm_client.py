from __future__ import annotations

from typing import Any
import time

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
        max_network_retries: int = 2,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.max_network_retries = max(0, max_network_retries)
        self._client = http_client

    @property
    def completion_url(self) -> str:
        """Return the chat-completions URL for either URL configuration style."""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def invoke(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": self.max_output_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = self._post_with_retry(headers, payload)
            if response.is_error:
                detail = self._format_error_detail(response)
                if response.status_code == 524:
                    raise LLMClientError(
                        "LLM provider timed out before returning a response (HTTP 524). "
                        "Try a faster model or reduce the requested output size."
                    )
                if response.status_code == 503 and self._looks_like_model_unavailable(detail):
                    raise LLMClientError(
                        f"مدل «{self.model}» برای این API Key در دسترس نیست. "
                        "مدل‌های مجاز کلید را از GET /v1/models بررسی کنید و مقدار LLM_MODEL را تغییر دهید."
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
        except httpx.TransportError as error:
            raise LLMClientError(
                "ارتباط امن با سرویس LLM برقرار نشد. اتصال اینترنت، VPN یا proxy را بررسی کنید."
            ) from error
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMClientError(f"LLM request failed: {error}") from error

    def _post_with_retry(
        self, headers: dict[str, str], payload: dict[str, Any]
    ) -> httpx.Response:
        last_error: httpx.TransportError | None = None
        for attempt in range(self.max_network_retries + 1):
            try:
                if self._client is not None:
                    return self._client.post(
                        self.completion_url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout,
                    )
                with httpx.Client(timeout=self.timeout) as client:
                    return client.post(
                        self.completion_url,
                        headers=headers,
                        json=payload,
                    )
            except httpx.TransportError as error:
                last_error = error
                if attempt < self.max_network_retries:
                    time.sleep(0.5 * (attempt + 1))
        assert last_error is not None
        raise last_error

    @staticmethod
    def _format_error_detail(response: httpx.Response) -> str:
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type:
            return "The provider returned an HTML error page."
        return response.text[:1000].replace("\n", " ")

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
