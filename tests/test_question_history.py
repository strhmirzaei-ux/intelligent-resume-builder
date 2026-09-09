from pathlib import Path

from app.integrations.embedding_service import EmbeddingService
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore


class AlwaysSimilarEmbedding:
    def embed(self, text):
        return [1.0, 0.0] if text else None

    @staticmethod
    def cosine_similarity(left, right):
        return EmbeddingService.cosine_similarity(None, left, right)


def build_service(tmp_path: Path, embedding=None):
    return ResumePipelineService(
        extractor=object(),
        store=JsonStore(str(tmp_path)),
        embedding_service=embedding or EmbeddingService(enabled=False),
    )


def test_question_record_contains_required_fields(tmp_path: Path):
    service = build_service(tmp_path)

    record = service._question_record(
        {"text": "Please describe your responsibilities.", "source_deficiency": "work"},
        "work_experience.responsibilities",
    )

    assert record == {
        "text": "Please describe your responsibilities.",
        "question_text": "Please describe your responsibilities.",
        "question_code": "work_experience.responsibilities",
        "embedding": None,
        "answered": False,
    }


def test_semantically_similar_question_is_filtered(tmp_path: Path):
    service = build_service(tmp_path, AlwaysSimilarEmbedding())
    history = [
        {
            "text": "Describe your work responsibilities.",
            "question_text": "Describe your work responsibilities.",
            "question_code": "work_experience.responsibilities",
            "embedding": [1.0, 0.0],
            "answered": False,
        }
    ]

    assert service._is_duplicate_question(
        "Tell me about your responsibilities at work.",
        "work_experience.achievements",
        history,
    )


def test_answered_question_is_marked_when_deficiency_disappears(tmp_path: Path):
    service = build_service(tmp_path)
    history = [
        {
            "text": "What were your responsibilities?",
            "question_text": "What were your responsibilities?",
            "question_code": "work_experience.responsibilities",
            "embedding": None,
            "answered": False,
        }
    ]

    service._update_question_answers(
        history,
        {"next_question": "What were your responsibilities?"},
        {"deficiency_codes": []},
        "I managed the backend team.",
    )

    assert history[0]["answered"] is True


def test_related_answer_marks_question_answered_with_embedding(tmp_path: Path):
    service = build_service(tmp_path, AlwaysSimilarEmbedding())
    history = [
        {
            "text": "Describe your responsibilities.",
            "question_text": "Describe your responsibilities.",
            "question_code": "work_experience.responsibilities",
            "embedding": [1.0, 0.0],
            "answered": False,
        }
    ]

    service._update_question_answers(
        history,
        {"next_question": "Describe your responsibilities."},
        {"deficiency_codes": ["work_experience.responsibilities"]},
        "I managed the backend team.",
    )

    assert history[0]["answered"] is True
