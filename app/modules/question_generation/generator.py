from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


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
    """
    تولید سوالات تکمیلی از روی نواقص استخراج‌شده از رزومه.
    - اول rule-based سوال می‌سازد
    - سپس اگر LLM در دسترس باشد، لحن را حرفه‌ای و طبیعی می‌کند
    """

    def __init__(self, llm=None) -> None:
        """
        llm:
            آبجکتی اختیاری با متد invoke(prompt)
            اگر ندهی، سوال‌ها به‌صورت rule-based تولید می‌شوند.
        """
        self.llm = llm

    def generate(self, deficiencies: List[str]) -> List[Dict[str, Any]]:
        """
        ورودی:
            deficiencies: لیست نواقص از GapAnalyzer

        خروجی:
            لیست سوالات مرتب‌شده بر اساس priority
        """
        questions: List[GeneratedQuestion] = []

        for deficiency in deficiencies:
            priority = self._classify_priority(deficiency)
            raw_question = self._build_rule_based_question(deficiency)

            if self.llm is not None:
                polished_question = self._polish_question_with_llm(raw_question, deficiency)
            else:
                polished_question = raw_question

            questions.append(
                GeneratedQuestion(
                    text=polished_question,
                    priority=priority,
                    source_deficiency=deficiency,
                )
            )

        questions = self._sort_questions(questions)

        return [
            {
                "text": q.text,
                "priority": q.priority.value,
                "source_deficiency": q.source_deficiency,
            }
            for q in questions
        ]

    def _classify_priority(self, deficiency: str) -> QuestionPriority:
        """
        اولویت‌بندی ساده:
        - فیلدهای هویتی و شغلی: high
        - تاریخ‌ها و ابهام‌های ساختاری: high
        - مهارت‌ها و جزئیات: medium
        - موارد کم‌اهمیت‌تر: low
        """
        d = deficiency.lower()

        high_keywords = [
            "نام",
            "نام‌خانوادگی",
            "شرکت",
            "سازمان",
            "تاریخ",
            "start_date",
            "end_date",
            "دانشگاه",
            "مقطع",
            "عنوان شغلی",
        ]
        medium_keywords = [
            "مهارت",
            "سطح",
            "توضیحات",
            "project",
            "پروژه",
        ]

        if any(k.lower() in d for k in high_keywords):
            return QuestionPriority.HIGH
        if any(k.lower() in d for k in medium_keywords):
            return QuestionPriority.MEDIUM
        return QuestionPriority.LOW

    def _build_rule_based_question(self, deficiency: str) -> str:
        """
        تبدیل نقص به سوال مستقیم و هدفمند.
        """
        d = deficiency.strip()

        if "شرکت" in d:
            return "شما نام شرکت را ذکر نکرده‌اید. لطفاً نام شرکت را بفرمایید."
        if "دانشگاه" in d:
            return "نام دانشگاه در رزومه مشخص نیست. لطفاً نام دانشگاه را بگویید."
        if "تاریخ شروع" in d or "start_date" in d:
            return "تاریخ شروع این بخش مشخص نیست. لطفاً تاریخ شروع را اعلام کنید."
        if "تاریخ پایان" in d or "end_date" in d:
            return "تاریخ پایان این بخش مشخص نیست. لطفاً تاریخ پایان را اعلام کنید."
        if "سطح تسلط" in d or "مهارت" in d:
            return "سطح تسلط این مهارت مشخص نیست. لطفاً سطح خود را بیان کنید."
        if "نام و نام‌خانوادگی" in d or "نام خانوادگی" in d:
            return "اطلاعات نام و نام‌خانوادگی کامل نیست. لطفاً آن را تکمیل کنید."

        return f"لطفاً این مورد را تکمیل کنید: {deficiency}"

    def _polish_question_with_llm(self, question: str, deficiency: str) -> str:
        """
        استفاده از LLM برای حرفه‌ای و روان کردن سوال.
        خروجی باید فقط یک سوال کوتاه، محترمانه و شفاف باشد.
        """
        prompt = f"""
You are a Persian assistant that rewrites follow-up questions for resume filling.

GOAL:
Rewrite the question in a friendly, professional, concise Persian tone.

RULES:
- Do not change the meaning.
- Do not add new information.
- Keep the question short and natural.
- Return only the rewritten question.
- No bullet points, no explanation, no quotes.

DEFICIENCY:
{deficiency}

QUESTION:
{question}
""".strip()

        response = self.llm.invoke(prompt)
        if hasattr(response, "content"):
            text = response.content.strip()
        else:
            text = str(response).strip()

        return self._clean_llm_output(text) or question

    def _clean_llm_output(self, text: str) -> str:
        """
        پاکسازی خروجی LLM از موارد اضافی.
        """
        text = text.strip()
        text = text.strip('"').strip("'")
        return text

    def _sort_questions(self, questions: List[GeneratedQuestion]) -> List[GeneratedQuestion]:
        """
        مرتب‌سازی:
        high -> medium -> low
        """
        order = {
            QuestionPriority.HIGH: 0,
            QuestionPriority.MEDIUM: 1,
            QuestionPriority.LOW: 2,
        }
        return sorted(questions, key=lambda q: order[q.priority])
