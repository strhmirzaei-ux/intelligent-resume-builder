import httpx
import pytest

from app.integrations.llm_client import LLMClientError, OpenAICompatibleClient


def test_openai_compatible_client_sends_request():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["json"] = request.read()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    client_adapter = OpenAICompatibleClient(
        api_key="secret",
        base_url="https://example.test/v1",
        model="test-model",
        http_client=client,
    )
    assert client_adapter.invoke("hello") == '{"ok": true}'
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert b'"model":"test-model"' in captured["json"]
    assert b'"stream":false' in captured["json"]


def test_openai_compatible_client_raises_on_http_error():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(401))
    )
    client_adapter = OpenAICompatibleClient("secret", "https://example.test/v1", "model", http_client=client)
    try:
        client_adapter.invoke("hello")
    except LLMClientError as error:
        assert "LLM provider returned HTTP 401" in str(error)
    else:
        raise AssertionError("Expected OpenAICompatibleClient error")


def test_openai_compatible_client_supports_local_server_without_api_key():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    client_adapter = OpenAICompatibleClient(
        api_key=None,
        base_url="http://localhost:11434/v1",
        model="qwen-local:latest",
        http_client=client,
    )

    assert client_adapter.invoke("hello") == "ok"
    assert "authorization" not in captured["headers"]


def test_openai_compatible_client_reports_provider_timeout_without_html():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                524,
                headers={"content-type": "text/html"},
                text="<html><title>524 timeout</title></html>",
            )
        )
    )
    adapter = OpenAICompatibleClient("secret", "https://example.test/v1", "model", http_client=client)
    with pytest.raises(LLMClientError, match="timed out.*HTTP 524"):
        adapter.invoke("hello")
