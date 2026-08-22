import httpx

from app.integrations.llm_client import InferXClient, LLMClientError


def test_inferx_client_sends_openai_compatible_request():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["json"] = request.read()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    inferx = InferXClient(
        api_key="secret",
        base_url="https://example.test/v1",
        model="test-model",
        http_client=client,
    )
    assert inferx.invoke("hello") == '{"ok": true}'
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert b'"model":"test-model"' in captured["json"]


def test_inferx_client_raises_on_http_error():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(401))
    )
    inferx = InferXClient("secret", "https://example.test/v1", "model", http_client=client)
    try:
        inferx.invoke("hello")
    except LLMClientError as error:
        assert "InferX request failed" in str(error)
    else:
        raise AssertionError("Expected InferXClient error")
