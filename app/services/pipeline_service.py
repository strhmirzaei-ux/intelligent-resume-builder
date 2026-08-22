from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.modules.extraction.llm_extractor import ResumeLLMExtractor
from app.modules.gap_analysis.analyzer import GapAnalyzer
from app.modules.preprocessing.normalizer import PersianTextNormalizer
from app.modules.question_generation.generator import QuestionGenerator
from app.schemas.resume import ResumeSchema
from app.storage.json_store import JsonStore


class ResumePipelineService:
    def __init__(
        self,
        extractor: ResumeLLMExtractor,
        store: JsonStore,
        normalizer: PersianTextNormalizer | None = None,
        question_generator: QuestionGenerator | None = None,
    ) -> None:
        self.extractor = extractor
        self.store = store
        self.normalizer = normalizer or PersianTextNormalizer()
        self.questions = question_generator or QuestionGenerator()
        self.settings = get_settings()

    def process(self, text: str, resume_id: str | None = None) -> dict[str, Any]:
        normalized = self.normalizer.clean_text(text)
        resume = self.extractor.extract(normalized)
        previous = (
            self.store.get(resume_id, max_age_seconds=self.settings.session_ttl_seconds)
            if resume_id
            else None
        )
        if previous:
            old_resume = ResumeSchema.model_validate(previous["resume"])
            merged_resume = self.merge(
                old_resume.model_dump(mode="json"),
                resume.model_dump(mode="json"),
            )
            resume = ResumeSchema.model_validate(merged_resume)
        analysis = GapAnalyzer(resume, normalized).run_analysis()
        resume_id = resume_id or str(uuid4())
        record = {
            "resume_id": resume_id,
            "raw_text": text,
            "normalized_text": normalized,
            "resume": resume.model_dump(mode="json"),
            "analysis": analysis,
        }
        self.store.put(resume_id, record)
        return record

    def get(self, resume_id: str) -> dict[str, Any] | None:
        return self.store.get(resume_id)

    @staticmethod
    def questions_for(record: dict[str, Any]) -> list[dict[str, Any]]:
        return QuestionGenerator().generate(record["analysis"].get("deficiencies", []))

    @staticmethod
    def merge(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        merged = dict(old)
        for key, value in new.items():
            if value is None or value == "" or value == []:
                continue
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ResumePipelineService.merge(merged[key], value)
            else:
                merged[key] = value
        return merged
