from pathlib import Path

from app.schemas.resume import ResumeSchema
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore


class RecordingNormalizer:
    def __init__(self, calls):
        self.calls = calls

    def clean_text(self, text):
        self.calls.append("normalize")
        return f"normalized:{text}"


class RecordingExtractor:
    def __init__(self, calls):
        self.calls = calls

    def extract(self, text):
        self.calls.append(("extract", text))
        return ResumeSchema()


class RecordingQuestions:
    def __init__(self, calls):
        self.calls = calls

    def generate(self, deficiencies):
        self.calls.append(("questions", deficiencies))
        return []


def test_pipeline_runs_normalize_extract_analyze_question_and_store(
    tmp_path: Path, monkeypatch
):
    calls = []
    from app.services import pipeline_service

    class RecordingAnalyzer:
        def __init__(self, resume, conversation_text):
            calls.append(("analyze", conversation_text))

        def run_analysis(self):
            return {"deficiencies": [], "deficiency_codes": [], "coverage_score": 1.0}

    monkeypatch.setattr(pipeline_service, "GapAnalyzer", RecordingAnalyzer)
    service = ResumePipelineService(
        extractor=RecordingExtractor(calls),
        store=JsonStore(str(tmp_path)),
        normalizer=RecordingNormalizer(calls),
        question_generator=RecordingQuestions(calls),
    )

    record = service.process("raw user message")
    stored = service.get(record["resume_id"])

    assert calls == [
        "normalize",
        ("extract", "normalized:raw user message"),
        ("analyze", "normalized:raw user message"),
        ("questions", []),
    ]
    assert stored is not None
    assert stored["normalized_text"] == "normalized:raw user message"
    assert stored["raw_text"] == "raw user message"
    assert stored["questions"] == []
