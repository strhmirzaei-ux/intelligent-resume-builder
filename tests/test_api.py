from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_web_app_is_served():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "رزومه" in response.text


def test_expected_routes_are_in_openapi():
    paths = app.openapi()["paths"]
    assert "/api/v1/chat/message" in paths
    assert "/api/v1/resumes/{resume_id}/html" in paths


def test_chat_returns_service_unavailable_when_llm_fails(monkeypatch):
    from app.api.routes import chat as chat_route
    from app.modules.extraction.llm_extractor import LLMExtractionError

    def fail_process(*args, **kwargs):
        raise LLMExtractionError("model unavailable")

    monkeypatch.setattr(chat_route.pipeline, "process", fail_process)
    response = TestClient(app).post(
        "/api/v1/chat/message",
        json={"message": "من برنامه‌نویس هستم"},
    )
    assert response.status_code == 503


def test_chat_rejects_oversized_input():
    response = TestClient(app).post(
        "/api/v1/chat/message",
        json={"message": "x" * 20_001},
    )
    assert response.status_code == 422
