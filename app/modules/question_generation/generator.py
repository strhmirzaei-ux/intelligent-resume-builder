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
    """تولید سؤال‌های تکمیلی فارسی از روی کمبودهای رزومه."""

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
        text = deficiency.casefold()
        high_keywords = (
            "نام",
            "شرکت",
            "سازمان",
            "دانشگاه",
            "مؤسسه",
            "تاریخ",
            "start date",
            "end date",
            "full name",
            "contact",
            "راه تماس",
        )
        medium_keywords = (
            "مهارت",
            "سطح",
            "توضیحات",
            "دستاورد",
            "description",
            "achievement",
            "proficiency",
            "project",
            "پروژه",
        )
        if any(keyword.casefold() in text for keyword in high_keywords):
            return QuestionPriority.HIGH
        if any(keyword.casefold() in text for keyword in medium_keywords):
            return QuestionPriority.MEDIUM
        return QuestionPriority.LOW

    def _build_rule_based_question(self, deficiency: str) -> str:
        text = deficiency.strip()
        normalized = text.casefold()

        if any(term in normalized for term in ("نام شرکت", "شرکت", "company", "organization")):
            return "لطفاً نام شرکت یا سازمان و عنوان شغلی خود را اعلام کنید."
        if any(term in normalized for term in ("دانشگاه", "مؤسسه", "institution", "university")):
            return "لطفاً نام دانشگاه یا مؤسسه آموزشی را اعلام کنید."
        if "start date" in normalized or "تاریخ شروع" in text:
            return "لطفاً تاریخ شروع این سابقه کاری را اعلام کنید."
        if "end date" in normalized or "تاریخ پایان" in text:
            return "لطفاً تاریخ پایان این سابقه کاری را اعلام کنید؛ اگر هنوز ادامه دارد، بگویید «اکنون»."
        if any(term in normalized for term in ("description", "achievement", "توضیحات", "دستاورد")):
            return "لطفاً وظایف، مسئولیت‌ها و دستاوردهای این سابقه کاری را توضیح دهید."
        if any(term in normalized for term in ("proficiency", "سطح تسلط", "مهارت")):
            return "لطفاً سطح تسلط خود بر این مهارت را مشخص کنید؛ مثلاً مقدماتی، متوسط یا حرفه‌ای."
        if "full name" in normalized or "نام و نام خانوادگی" in text:
            return "لطفاً نام و نام خانوادگی خود را اعلام کنید."
        if "contact" in normalized or "راه تماس" in text:
            return "لطفاً حداقل یکی از ایمیل یا شماره تلفن خود را اعلام کنید."

        # Never expose raw schema names or English model output to the user.
        return "لطفاً اطلاعات مربوط به این بخش از رزومه را تکمیل یا بررسی کنید."

    def _polish_question_with_llm(self, question: str, deficiency: str) -> str:
        prompt = f"""این سؤال تکمیلی رزومه را به فارسی روان و محترمانه بازنویسی کن.
معنا را تغییر نده و اطلاعات جدید اضافه نکن.
فقط متن سؤال را برگردان.
کمبود: {deficiency}
سؤال: {question}"""
        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return self._clean_llm_output(text) or question

    @staticmethod
    def _clean_llm_output(text: str) -> str:
        return text.strip().strip('"').strip("'")
