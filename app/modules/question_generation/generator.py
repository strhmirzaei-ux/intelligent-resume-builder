
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any


class QuestionPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class GeneratedQuestion:
    text: str
    priority: QuestionPriority
    source_deficiency: str


class QuestionGenerator:
    """Generate completion questions directly with the configured LLM."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    def generate(self, deficiencies: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        if self.llm is None:
            raise RuntimeError("An LLM client is required for question generation.")
        allowed = kwargs.get("llm_deficiencies") or set(deficiencies)
        limit = int(kwargs.get("llm_question_limit", 1))
        context = kwargs.get("resume_context") or {}
        previous = kwargs.get("previous_questions") or []
        conversation = kwargs.get("conversation_context", "")
        questions: list[GeneratedQuestion] = []
        for deficiency in deficiencies:
            if deficiency not in allowed or len(questions) >= limit:
                continue
            prompt = f"""برای تکمیل رزومه، فقط یک سؤال کوتاه و روشن به فارسی بنویس.
کمبود اطلاعات: {deficiency}
اطلاعات فعلی رزومه: {context}
سؤال‌های قبلی: {previous}
متن گفت‌وگو: {conversation}
اطلاعات جدید جعل نکن و فقط متن سؤال را برگردان."""
            response = self.llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            text = self._clean_question_text(text)
            if not text:
                raise RuntimeError("LLM returned an empty completion question.")
            questions.append(GeneratedQuestion(text, self._priority(deficiency), deficiency))
        order = {QuestionPriority.HIGH: 0, QuestionPriority.MEDIUM: 1, QuestionPriority.LOW: 2}
        return [{"text": q.text, "priority": q.priority.value, "source_deficiency": q.source_deficiency}
                for q in sorted(questions, key=lambda q: order[q.priority])]

    @staticmethod
    def _priority(deficiency: str) -> QuestionPriority:
        text = deficiency.casefold()
        if any(term in text for term in ("full name", "contact", "نام", "تماس", "تاریخ")):
            return QuestionPriority.HIGH
        if any(term in text for term in ("description", "achievement", "project", "مهارت", "تحصیلات")):
            return QuestionPriority.MEDIUM
        return QuestionPriority.LOW

    @classmethod
    def _clean_question_text(cls, value: Any) -> str:
        """Turn the model's response into the plain question shown to the user.

        Some providers honor ``response_format=json_object`` even though the
        prompt asks for plain text and return ``{"question": "..."}``.  Keep
        that provider detail out of the chat history and UI.
        """
        if isinstance(value, dict):
            value = value.get("question", value.get("text", ""))
        elif isinstance(value, list):
            value = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in value
            )

        text = str(value or "").strip()
        text = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        if not text:
            return ""

        # First handle valid JSON responses, including a JSON string or object.
        try:
            parsed = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, (dict, list)):
            cleaned = cls._clean_question_text(parsed)
            if cleaned:
                return cleaned
        if isinstance(parsed, str):
            text = parsed.strip()

        # Recover the field when the provider added commentary around JSON.
        match = re.search(r'"question"\s*:\s*("(?:\\.|[^"\\])*")', text, flags=re.DOTALL)
        if match:
            try:
                return str(json.loads(match.group(1))).strip()
            except json.JSONDecodeError:
                pass

        # A plain quoted answer is also common with text-only providers.
        return text.strip().strip('"').strip("'").strip()
