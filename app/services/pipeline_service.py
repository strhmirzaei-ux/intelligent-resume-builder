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
            resume = self._apply_answer_fallback(resume, previous, normalized)
        conversation_text = normalized
        if previous:
            previous_messages = previous.get("messages", [])
            conversation_text = "\n".join(
                [
                    str(message.get("content", ""))
                    for message in previous_messages
                    if message.get("role") == "user"
                ]
                + [normalized]
            )
        analysis = GapAnalyzer(resume, conversation_text).run_analysis()
        resume_id = resume_id or str(uuid4())
        previously_asked = list(previous.get("asked_deficiencies", [])) if previous else []
        deficiency_codes = list(analysis.get("deficiency_codes", []))
        previous_codes = list(previous.get("asked_deficiency_codes", [])) if previous else []
        if previous and not previous_codes:
            previous_codes = self._infer_asked_codes(previous.get("next_question"))
        available_deficiencies = [
            item for index, item in enumerate(analysis.get("deficiencies", []))
            if index >= len(deficiency_codes) or deficiency_codes[index] not in previous_codes
        ]
        generated_questions = QuestionGenerator().generate(available_deficiencies)
        next_question = generated_questions[0] if generated_questions else None
        asked_deficiencies = previously_asked + (
            [next_question["source_deficiency"]] if next_question else []
        )
        asked_deficiency_codes = previous_codes + (
            [deficiency_codes[analysis["deficiencies"].index(next_question["source_deficiency"])] ]
            if next_question and next_question["source_deficiency"] in analysis["deficiencies"]
            else []
        )
        record = {
            "resume_id": resume_id,
            "raw_text": text,
            "normalized_text": normalized,
            "resume": resume.model_dump(mode="json"),
            "analysis": analysis,
            "asked_deficiencies": asked_deficiencies,
            "asked_deficiency_codes": asked_deficiency_codes,
            "next_question": next_question["text"] if next_question else None,
            "messages": (
                list(previous.get("messages", [])) if previous else []
            ) + [{"role": "user", "content": text}],
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
            if key in {"work_experiences", "internships"} and isinstance(value, list):
                merged[key] = ResumePipelineService._merge_experience_lists(
                    merged.get(key, []), value
                )
            elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ResumePipelineService.merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _merge_experience_lists(old: list[Any], new: list[Any]) -> list[Any]:
        result = [dict(item) for item in old if isinstance(item, dict)]
        for incoming in new:
            if not isinstance(incoming, dict):
                continue
            candidates = [
                index
                for index, existing in enumerate(result)
                if (
                    incoming.get("company_name")
                    and existing.get("company_name")
                    and incoming["company_name"].casefold()
                    == existing["company_name"].casefold()
                )
                or (
                    incoming.get("job_title")
                    and existing.get("job_title")
                    and incoming["job_title"].casefold()
                    == existing["job_title"].casefold()
                )
            ]
            index = candidates[0] if candidates else (
                len(result) - 1 if len(result) == 1 else None
            )
            if index is None:
                result.append(dict(incoming))
            else:
                result[index] = ResumePipelineService.merge(result[index], incoming)
        return result

    @staticmethod
    def _apply_answer_fallback(
        resume: ResumeSchema, previous: dict[str, Any], answer: str
    ) -> ResumeSchema:
        """Keep a direct answer when the model returns no structured work details."""
        previous_analysis = previous.get("analysis", {})
        previous_deficiencies = previous_analysis.get("deficiency_codes", [])
        work_gap_codes = {
            "work_experience.responsibilities",
            "work_experience.achievements",
        }
        question = str(previous.get("next_question") or "")
        is_work_details_question = any(
            term in question for term in ("وظایف", "مسئولیت", "دستاورد")
        )
        if not work_gap_codes.intersection(previous_deficiencies) and not is_work_details_question:
            return resume
        if not resume.work_experiences:
            return resume
        updated = resume.model_dump(mode="json")
        target = updated["work_experiences"][-1]
        if "دستاورد" in question or "دستاورد" in answer:
            target.setdefault("achievements", [])
            if answer not in target["achievements"]:
                target["achievements"].append(answer)
        else:
            target["description"] = target.get("description") or answer
            target.setdefault("key_responsibilities", [])
            if answer not in target["key_responsibilities"]:
                target["key_responsibilities"].append(answer)
        target.setdefault("evidence", []).append({"source_text": answer})
        return ResumeSchema.model_validate(updated)

    @staticmethod
    def _infer_asked_codes(question: Any) -> list[str]:
        text = str(question or "")
        if any(term in text for term in ("وظایف", "مسئولیت")):
            return ["work_experience.responsibilities"]
        if "دستاورد" in text:
            return ["work_experience.achievements"]
        if any(term in text for term in ("نام شرکت", "عنوان شغلی")):
            return ["work_experience.experiences"]
        if any(term in text for term in ("مدت", "تاریخ شروع")):
            return ["work_experience.duration"]
        return []
