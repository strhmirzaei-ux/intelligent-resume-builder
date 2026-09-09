import math

from app.integrations.embedding_service import EmbeddingService


class FakeModel:
    def encode(self, text, convert_to_numpy=False):
        assert convert_to_numpy is False
        return [3.0, 4.0]


def test_embedding_service_is_disabled_by_default():
    service = EmbeddingService()

    assert service.available is False
    assert service.embed("متن فارسی") is None


def test_embedding_is_normalized():
    service = EmbeddingService(enabled=True, model=FakeModel())

    vector = service.embed("English and فارسی")

    assert vector == [0.6, 0.8]
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)


def test_cosine_similarity_accepts_non_normalized_vectors():
    service = EmbeddingService()

    assert service.cosine_similarity([3, 4], [6, 8]) == 1.0
    assert service.cosine_similarity([1, 0], [0, 1]) == 0.0
    assert service.cosine_similarity([0, 0], [1, 0]) is None
    assert service.cosine_similarity([1], [1, 2]) is None


def test_missing_sentence_transformers_does_not_break_service(monkeypatch):
    service = EmbeddingService(enabled=True)

    monkeypatch.setattr(service, "_ensure_model", lambda: False)

    assert service.embed("some text") is None
    assert service.last_error is None
