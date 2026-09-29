from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.extraction.llm_extractor import LLMExtractionError, ResumeLLMExtractor


@dataclass
class UnifiedAgentResult:
    extracted_resume: dict[str, Any] = field(default_factory=dict)
    operations: list[dict[str, Any]] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)
    next_question: str | None = None
    memory_summary: str = ""
    intent: str = "answer"


class UnifiedResumeAgent:
    """One structured LLM request for extraction, edits and questioning."""

    def __init__(self, llm: Any = None, max_retries: int = 1) -> None:
        self.llm = llm
        self.max_retries = max(0, max_retries)

    def invoke(self, *, user_message: str, current_resume: dict[str, Any],
               conversation_summary: str = "",
               recent_messages: list[dict[str, Any]] | None = None,
               previous_questions: list[dict[str, Any]] | None = None,
               deficiencies: list[str] | None = None,
               suppressed_facts: list[str] | None = None) -> UnifiedAgentResult:
        if self.llm is None:
            raise LLMExtractionError("An LLM client is required for unified resume processing.")
        prompt = self.build_prompt(
            user_message=user_message,
            current_resume=current_resume,
            conversation_summary=conversation_summary,
            recent_messages=recent_messages or [],
            previous_questions=previous_questions or [],
            deficiencies=deficiencies or [],
            suppressed_facts=suppressed_facts or [],
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                raw = self.llm.invoke(prompt)
                content = getattr(raw, "content", raw)
                return self._parse_result(self._parse_json(str(content)))
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                last_error = error
                if attempt < self.max_retries:
                    prompt += "\nپاسخ قبلی معتبر نبود. فقط JSON مطابق قرارداد خروجی بده."
        raise LLMExtractionError(f"Unified LLM response was invalid: {last_error}") from last_error

    @classmethod
    def build_prompt(cls, *, user_message: str, current_resume: dict[str, Any],
                     conversation_summary: str, recent_messages: list[dict[str, Any]],
                     previous_questions: list[dict[str, Any]],
                     deficiencies: list[str], suppressed_facts: list[str]) -> str:
        contract = {
            "intent": "answer|add|edit|remove|clarify",
            "extracted_resume": {"personal_info": {}, "contact_info": {},
                "professional_summary": None, "key_strengths": [], "career_objective": None,
                "work_experiences": [], "internships": [], "educations": [], "skills": [],
                "tools_platforms": [], "languages": [], "projects": [], "other_projects": [],
                "certificates": [], "interests": []},
            "operations": [{"op": "add|replace|remove|merge", "path": "/json/pointer", "value": None}],
            "analysis": {"deficiencies": [], "deficiency_codes": [], "coverage_score": 0},
            "next_question": None, "memory_summary": "",
        }
        sections = [
            "تو دستیار ساخت رزومه حرفه‌ای فارسی هستی. فقط یک JSON معتبر مطابق قرارداد زیر برگردان.",
            "",
            "قواعد قطعی:",
            "1. فقط بر اساس فکت‌هایی که کاربر صریحاً گفته عمل کن؛ هیچ نام، مهارت، سابقه، عدد یا دستاوردی را حدس نزن.",
            "2. از فکت‌های فعلی و جدید برای نوشتن professional_summary استفاده کن. خلاصه باید حرفه‌ای و معرفی‌کننده باشد، اما کاملاً وفادار به فکت‌ها بماند. اگر کاربر گفت مهندسی کامپیوتر خوانده‌ام، می‌توانی او را مهندس کامپیوتر معرفی کنی؛ سابقه یا مهارتی که گفته نشده اضافه نکن.",
            "3. برای اطلاعات جدید extracted_resume را به‌صورت داده‌های استخراج‌شده برگردان و اطلاعات قبلی را بدون دلیل حذف نکن.",
            "4. برای ویرایش یا حذف اطلاعات موجود از operations استفاده کن. حذف مبهم ممنوع است؛ در ابهام intent را clarify کن.",
            "5. اگر سؤال بعدی لازم است، فقط یک سؤال کوتاه فارسی در next_question بنویس و سؤال تکراری تولید نکن.",
            "6. خلاصه مکالمه را کوتاه و factual در memory_summary به‌روزرسانی کن.",
            "",
            "قرارداد JSON:", json.dumps(contract, ensure_ascii=False),
            "رزومه فعلی:", json.dumps(current_resume, ensure_ascii=False),
            "خلاصه مکالمه:", conversation_summary,
            "پیام‌های اخیر:", json.dumps(recent_messages, ensure_ascii=False),
            "سؤال‌های قبلی:", json.dumps(previous_questions, ensure_ascii=False),
            "کمبودهای فعلی:", json.dumps(deficiencies, ensure_ascii=False),
            "فکت‌ها یا بخش‌هایی که کاربر حذف کرده و نباید دوباره اضافه شوند:",
            json.dumps(suppressed_facts, ensure_ascii=False),
            "پیام جدید کاربر:", user_message,
        ]
        return "\n".join(sections)

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        text = re.sub(r"<think\b[^>]*>.*?</think\s*>", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()
        text = re.sub(r"\x60\x60\x60(?:json)?", "", text, flags=re.IGNORECASE).replace("\x60\x60\x60", "").strip()
        start = text.find("{")
        if start < 0:
            raise ValueError("No JSON object found in unified response")
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    value = json.loads(text[start:index + 1])
                    if not isinstance(value, dict):
                        raise ValueError("Unified response must be an object")
                    return value
        raise ValueError("Incomplete JSON object in unified response")

    @staticmethod
    def _parse_result(data: dict[str, Any]) -> UnifiedAgentResult:
        data = UnifiedResumeAgent._unwrap_payload(data)
        operations = data.get("operations") or []
        if not isinstance(operations, list):
            raise TypeError("operations must be a list")
        extracted = data.get("extracted_resume")
        if extracted is None:
            extracted = data.get("resume")
        if extracted is None and UnifiedResumeAgent._looks_like_resume(data):
            extracted = data
        extracted = extracted or {}
        if not isinstance(extracted, dict):
            raise TypeError("extracted_resume must be an object")
        analysis = data.get("analysis") or {}
        if not isinstance(analysis, dict):
            analysis = {}
        return UnifiedAgentResult(
            extracted_resume=UnifiedResumeAgent._normalize_resume_payload(extracted),
            operations=[item for item in operations if isinstance(item, dict)],
            analysis=analysis,
            next_question=str(data["next_question"]).strip() if data.get("next_question") else None,
            memory_summary=str(data.get("memory_summary") or "").strip(),
            intent=str(data.get("intent") or "answer"),
        )

    @staticmethod
    def _unwrap_payload(data: dict[str, Any]) -> dict[str, Any]:
        """Accept provider wrappers such as {"json": {...}} or {"resume": {...}}."""
        value = data
        for key in ("json", "result", "response"):
            nested = value.get(key)
            if isinstance(nested, dict) and len(value) <= 3:
                value = nested
        return value

    @staticmethod
    def _looks_like_resume(data: dict[str, Any]) -> bool:
        return bool(
            set(data)
            & {
                "personal_info", "contact_info", "professional_summary",
                "work_experiences", "educations", "skills", "projects",
            }
        )

    @staticmethod
    def _normalize_resume_payload(data: dict[str, Any]) -> dict[str, Any]:
        """Map common model aliases and loose values to ResumeSchema's contract."""
        top_level = {
            "personal_info", "contact_info", "professional_summary", "key_strengths",
            "career_objective", "work_experiences", "internships", "educations", "skills",
            "tools_platforms", "languages", "projects", "other_projects", "certificates", "interests",
        }
        result = {key: value for key, value in data.items() if key in top_level}
        result = dict(ResumeLLMExtractor._normalize_common_model_shape(result))
        if isinstance(result.get("personal_info"), dict):
            result["personal_info"] = UnifiedResumeAgent._normalize_item(
                result["personal_info"],
                {"first_name", "last_name", "full_name", "birth_date", "birth_date_raw", "gender", "status", "confidence", "evidence"},
                {},
            )
        if isinstance(result.get("contact_info"), dict):
            result["contact_info"] = UnifiedResumeAgent._normalize_item(
                result["contact_info"],
                {"email", "phone", "city", "country", "linkedin", "github", "website", "status", "confidence", "evidence"},
                {},
            )
        result["work_experiences"] = [
            UnifiedResumeAgent._normalize_item(
                item,
                {"company_name", "job_title", "duration", "start_date", "end_date", "start_date_raw",
                 "end_date_raw", "is_current", "description", "key_responsibilities", "achievements",
                 "status", "confidence", "evidence"},
                {"company": "company_name", "title": "job_title"},
            )
            for item in result.get("work_experiences", [])
            if isinstance(item, dict)
        ]
        result["educations"] = [
            UnifiedResumeAgent._normalize_item(
                item,
                {"institution_name", "degree", "field_of_study", "start_date", "end_date", "start_date_raw",
                 "end_date_raw", "relevant_courses", "academic_projects", "achievements", "status",
                 "confidence", "evidence"},
                {"institution": "institution_name", "university": "institution_name"},
            )
            for item in result.get("educations", [])
            if isinstance(item, dict)
        ]
        result["internships"] = [
            UnifiedResumeAgent._normalize_item(
                item,
                {"role", "company_name", "duration", "responsibilities", "key_learnings", "status", "confidence", "evidence"},
                {"company": "company_name"},
            )
            for item in result.get("internships", [])
            if isinstance(item, dict)
        ]
        project_allowed = {"name", "description", "role", "problem_statement", "tech_stack", "key_features", "outcomes", "url", "start_date", "end_date", "start_date_raw", "end_date_raw", "status", "confidence", "evidence"}
        for section in ("projects", "other_projects"):
            result[section] = [
                UnifiedResumeAgent._normalize_project(item, project_allowed)
                for item in result.get(section, [])
                if isinstance(item, dict)
            ]
        result["certificates"] = [
            UnifiedResumeAgent._normalize_item(
                item,
                {"name", "issuer", "issue_date", "url", "status", "confidence", "evidence"},
                {},
            )
            for item in result.get("certificates", [])
            if isinstance(item, dict)
        ]
        result["skills"] = [
            UnifiedResumeAgent._normalize_skill(item)
            for item in result.get("skills", [])
        ]
        result["languages"] = [
            UnifiedResumeAgent._normalize_skill(item, {"language": "name", "proficiency": "level"})
            for item in result.get("languages", [])
        ]
        return result

    @staticmethod
    def _normalize_item(item: dict[str, Any], allowed: set[str], aliases: dict[str, str]) -> dict[str, Any]:
        value = dict(item)
        for source, target in aliases.items():
            if target not in value and source in value:
                value[target] = value[source]
        for date_field in ("start_date", "end_date", "birth_date", "issue_date"):
            raw = value.get(date_field)
            if raw is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(raw)):
                if date_field in {"start_date", "end_date", "birth_date"}:
                    value[date_field + "_raw"] = {"raw_value": str(raw)}
                value.pop(date_field, None)
                if date_field == "end_date" and str(raw).strip() in {"اکنون", "حال", "present", "current"}:
                    value["is_current"] = True
        if isinstance(value.get("evidence"), list):
            value["evidence"] = [UnifiedResumeAgent._normalize_evidence(entry) for entry in value["evidence"]]
        return {key: value[key] for key in allowed if key in value}

    @staticmethod
    def _normalize_project(item: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
        value = dict(item)
        for source, target in {
            "title": "name",
            "project_name": "name",
            "technologies": "tech_stack",
            "technology_stack": "tech_stack",
            "link": "url",
        }.items():
            if target not in value and source in value:
                value[target] = value[source]
        if not value.get("name") and value.get("description"):
            description = " ".join(str(value["description"]).split())
            value["name"] = description[:200].rstrip()
        return UnifiedResumeAgent._normalize_item(value, allowed, {})

    @staticmethod
    def _normalize_skill(item: Any, aliases: dict[str, str] | None = None) -> dict[str, Any]:
        if isinstance(item, str):
            return {"name": item}
        if not isinstance(item, dict):
            return {}
        value = dict(item)
        for source, target in (aliases or {}).items():
            if target not in value and source in value:
                value[target] = value[source]
        if not value.get("name"):
            evidence = value.get("evidence") or []
            if evidence and isinstance(evidence[0], dict):
                value["name"] = evidence[0].get("source_text")
        allowed = {"name", "level", "status", "confidence", "evidence"}
        if isinstance(value.get("evidence"), list):
            value["evidence"] = [UnifiedResumeAgent._normalize_evidence(entry) for entry in value["evidence"]]
        return {key: value[key] for key in allowed if key in value and value[key] is not None}

    @staticmethod
    def _normalize_evidence(entry: Any) -> dict[str, Any]:
        if isinstance(entry, str):
            return {"source_text": entry}
        if not isinstance(entry, dict):
            return {}
        value = dict(entry)
        if "evidence_type" not in value and "source_type" in value:
            value["evidence_type"] = value["source_type"]
        allowed = {"source_text", "source_start", "source_end", "evidence_type"}
        return {key: value[key] for key in allowed if key in value}

