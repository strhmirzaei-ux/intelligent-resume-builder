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
    assert b'"response_format":{"type":"json_object"}' in captured["json"]


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


def test_openai_compatible_client_accepts_completion_endpoint_base_url():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleClient(
        api_key="secret",
        base_url="https://example.test/v1/chat/completions",
        model="model",
        http_client=client,
    )

    assert adapter.invoke("hello") == "ok"
    assert captured["url"] == "https://example.test/v1/chat/completions"


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


def test_openai_compatible_client_explains_unavailable_model():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503,
                json={"error": {"message": "new_model_not_found"}},
            )
        )
    )
    adapter = OpenAICompatibleClient("secret", "https://example.test/v1", "mimo-v2.5", http_client=client)
    with pytest.raises(LLMClientError, match="برای این API Key در دسترس نیست"):
        adapter.invoke("hello")


def test_openai_compatible_client_retries_network_errors():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.RemoteProtocolError("unexpected EOF")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OpenAICompatibleClient(
        "secret", "https://example.test/v1", "model", max_network_retries=1, http_client=client
    )
    assert adapter.invoke("hello") == "ok"
    assert attempts == 2
