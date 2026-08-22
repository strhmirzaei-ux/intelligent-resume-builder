from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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
    """تولید سؤال‌های تکمیلی هدفمند از روی کمبودهای رزومه."""

    def __init__(self, llm=None) -> None:
        self.llm = llm

    def generate(self, deficiencies: list[str]) -> list[dict[str, Any]]:
        questions: list[GeneratedQuestion] = []
        for deficiency in deficiencies:
            priority = self._classify_priority(deficiency)
            question = self._build_rule_based_question(deficiency)
            if self.llm is not None:
                question = self._polish_question_with_llm(question, deficiency)
            questions.append(GeneratedQuestion(question, priority, deficiency))

        order = {QuestionPriority.HIGH: 0, QuestionPriority.MEDIUM: 1, QuestionPriority.LOW: 2}
        return [
            {
                "text": item.text,
                "priority": item.priority.value,
                "source_deficiency": item.source_deficiency,
            }
            for item in sorted(questions, key=lambda item: order[item.priority])
        ]

    def _classify_priority(self, deficiency: str) -> QuestionPriority:
        text = deficiency.lower()
        high_keywords = (
            "نام",
            "نام خانوادگی",
            "شرکت",
            "سازمان",
            "تاریخ",
            "start_date",
            "end_date",
            "دانشگاه",
            "مقطع",
            "عنوان شغلی",
        )
        medium_keywords = ("مهارت", "سطح", "توضیحات", "project", "پروژه")
        if any(keyword.lower() in text for keyword in high_keywords):
            return QuestionPriority.HIGH
        if any(keyword.lower() in text for keyword in medium_keywords):
            return QuestionPriority.MEDIUM
        return QuestionPriority.LOW

    def _build_rule_based_question(self, deficiency: str) -> str:
        text = deficiency.strip()
        if "شرکت" in text or "سازمان" in text:
            return "لطفاً نام شرکت یا سازمان را اعلام کنید."
        if "دانشگاه" in text:
            return "لطفاً نام دانشگاه را اعلام کنید."
        if "تاریخ شروع" in text or "start_date" in text:
            return "لطفاً تاریخ شروع این بخش را اعلام کنید."
        if "تاریخ پایان" in text or "end_date" in text:
            return "لطفاً تاریخ پایان این بخش را اعلام کنید."
        if "سطح تسلط" in text or "مهارت" in text:
            return "لطفاً سطح تسلط خود بر این مهارت را مشخص کنید."
        if "نام و نام خانوادگی" in text or "نام خانوادگی" in text:
            return "لطفاً نام و نام خانوادگی خود را تکمیل کنید."
        return f"لطفاً این مورد را تکمیل کنید: {text}"

    def _polish_question_with_llm(self, question: str, deficiency: str) -> str:
        prompt = f"""Rewrite this Persian resume follow-up question professionally.
Do not add information. Return only the question.
Deficiency: {deficiency}
Question: {question}"""
        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return self._clean_llm_output(text) or question

    @staticmethod
    def _clean_llm_output(text: str) -> str:
        return text.strip().strip('"').strip("'")
