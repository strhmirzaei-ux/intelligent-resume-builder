from __future__ import annotations

from typing import Any

import httpx


class LLMClientError(Exception):
    pass


class InferXClient:
    """Small OpenAI-compatible client for the configured InferX endpoint."""

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
                detail = response.text[:1000].replace("\n", " ")
                raise LLMClientError(
                    f"InferX returned HTTP {response.status_code}: {detail}"
                )
            data: dict[str, Any] = response.json()
            content = data["choices"][0]["message"]["content"]
            return str(content)
        except LLMClientError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMClientError(f"InferX request failed: {error}") from error
