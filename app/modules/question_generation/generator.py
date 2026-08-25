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
        seen: set[str] = set()
        for deficiency in deficiencies:
            if deficiency in seen:
                continue
            seen.add(deficiency)
            question = self._build_rule_based_question(deficiency)
            if self.llm is not None:
                question = self._polish_question_with_llm(question, deficiency)
            questions.append(
                GeneratedQuestion(
                    text=question,
                    priority=self._classify_priority(deficiency),
                    source_deficiency=deficiency,
                )
            )

        order = {
            QuestionPriority.HIGH: 0,
            QuestionPriority.MEDIUM: 1,
            QuestionPriority.LOW: 2,
        }
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
        high_terms = (
            "نام",
            "تماس",
            "شرکت",
            "سازمان",
            "دانشگاه",
            "مؤسسه",
            "تاریخ",
            "سابقه کاری",
            "تحصیلات",
            "full name",
            "contact",
        )
        medium_terms = (
            "مهارت",
            "سطح",
            "توضیحات",
            "دستاورد",
            "پروژه",
            "نمونه‌کار",
            "زبان",
            "گواهی",
            "خلاصه",
            "هدف شغلی",
            "description",
            "achievement",
            "project",
        )
        if any(term.casefold() in text for term in high_terms):
            return QuestionPriority.HIGH
        if any(term.casefold() in text for term in medium_terms):
            return QuestionPriority.MEDIUM
        return QuestionPriority.LOW

    def _build_rule_based_question(self, deficiency: str) -> str:
        text = deficiency.strip().casefold()
        if "نام و نام خانوادگی" in text or "full name" in text:
            return "لطفاً نام و نام خانوادگی خود را اعلام کنید."
        if "راه‌های تماس" in text or "تماس" in text or "contact" in text:
            return "لطفاً حداقل یکی از ایمیل یا شماره تلفن خود را اعلام کنید."
        if "سابقه کاری وارد نشده" in text:
            return "لطفاً سابقه‌های کاری خود را با نام شرکت، عنوان شغلی و مدت همکاری معرفی کنید."
        if "نام شرکت" in text or "شرکت" in text or "organization" in text:
            return "لطفاً نام شرکت یا سازمان و عنوان شغلی خود را اعلام کنید."
        if "تاریخ شروع" in text or "start date" in text:
            return "لطفاً تاریخ شروع این سابقه کاری را اعلام کنید؛ اگر هنوز ادامه دارد، بگویید «اکنون»."
        if "توضیحات" in text or "دستاورد" in text or "description" in text:
            return "لطفاً وظایف، مسئولیت‌ها و مهم‌ترین دستاوردهای این سابقه کاری را توضیح دهید."
        if "تحصیلات" in text or "مدارک دانشگاهی" in text or "مؤسسه آموزشی" in text:
            return "لطفاً مقطع تحصیلی، رشته و نام دانشگاه یا مؤسسه آموزشی خود را اعلام کنید."
        if "زبان‌های خارجی" in text or "زبان" in text:
            return "لطفاً زبان‌هایی را که می‌دانید و سطح تسلط خود بر هرکدام را اعلام کنید."
        if "پروژه‌ها" in text or "نمونه‌کار" in text:
            return "لطفاً مهم‌ترین پروژه‌ها یا نمونه‌کارهای خود را همراه با نقش و توضیح کوتاه معرفی کنید."
        if "گواهی‌نامه" in text or "دوره‌های تخصصی" in text:
            return "لطفاً گواهی‌نامه‌ها و دوره‌های تخصصی خود را همراه با نام صادرکننده اعلام کنید."
        if "خلاصه حرفه‌ای" in text or "هدف شغلی" in text:
            return "لطفاً درباره تخصص، نقاط قوت و هدف شغلی خود یک خلاصه کوتاه بنویسید."
        if "سطح تسلط" in text:
            return "لطفاً سطح تسلط خود بر این مهارت را مقدماتی، متوسط یا حرفه‌ای اعلام کنید."
        return "لطفاً اطلاعات مربوط به این بخش از رزومه را تکمیل یا بررسی کنید."

    def _polish_question_with_llm(self, question: str, deficiency: str) -> str:
        prompt = f"""این سؤال تکمیلی رزومه را به فارسی روان بازنویسی کن.
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
