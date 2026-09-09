from __future__ import annotations

from collections.abc import Iterable
from typing import Any

LABELS = {
    "summary": "خلاصه حرفه‌ای",
    "objective": "هدف شغلی",
    "experience": "سوابق کاری",
    "internship": "کارآموزی",
    "education": "تحصیلات",
    "skills": "مهارت‌ها",
    "tools": "ابزارها و پلتفرم‌ها",
    "languages": "زبان‌ها",
    "projects": "پروژه‌ها",
    "certificates": "گواهینامه‌ها",
    "interests": "علایق",
    "contact": "اطلاعات تماس",
}


def text(value: Any) -> str:
    return "" if value is None else str(value)


def full_name(resume: dict[str, Any]) -> str:
    personal = resume.get("personal_info") or {}
    return (
        text(personal.get("full_name"))
        or " ".join(
            value for value in (personal.get("first_name"), personal.get("last_name")) if value
        )
        or "رزومه"
    )


def non_empty(values: Iterable[Any]) -> list[str]:
    return [text(value) for value in values if value not in (None, "", [])]


def contact_lines(resume: dict[str, Any]) -> list[str]:
    contact = resume.get("contact_info") or {}
    result = non_empty(
        [
            contact.get("email"),
            contact.get("phone"),
            "، ".join(non_empty([contact.get("city"), contact.get("country")])),
            contact.get("linkedin"),
            contact.get("github"),
            contact.get("website"),
        ]
    )
    return result


def date_range(item: dict[str, Any]) -> str:
    if item.get("duration"):
        return text(item["duration"])
    start = text(item.get("start_date"))
    end = "اکنون" if item.get("is_current") else text(item.get("end_date"))
    return " - ".join(part for part in (start, end) if part)
