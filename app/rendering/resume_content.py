from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import re
from urllib.parse import unquote, urlsplit, urlunsplit

LABELS = {
    "summary": "درباره من",
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


def normalize_profile_url(value: Any, platform: str) -> str:
    """Clean common URL encoding and duplicated-domain artifacts in profile links."""
    raw = unquote(text(value)).strip()
    if not raw:
        return ""
    raw = re.sub(r"\s+", "", raw)
    if raw.startswith("www."):
        raw = "https://" + raw
    elif not re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.IGNORECASE):
        raw = "https://" + raw

    parsed = urlsplit(raw)
    path = parsed.path
    if platform == "linkedin" and (parsed.hostname or "").lower().endswith("linkedin.com"):
        path = re.sub(r"^/(?:in/)?linkedin\.com/(?:in/)?", "/in/", path, flags=re.IGNORECASE)
    elif platform == "github" and (parsed.hostname or "").lower().endswith("github.com"):
        path = re.sub(r"^/github\.com/", "/", path, flags=re.IGNORECASE)
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def contact_lines(resume: dict[str, Any]) -> list[str]:
    contact = resume.get("contact_info") or {}
    result = non_empty(
        [
            contact.get("email"),
            contact.get("phone"),
            "، ".join(non_empty([contact.get("city"), contact.get("country")])),
            normalize_profile_url(contact.get("linkedin"), "linkedin"),
            normalize_profile_url(contact.get("github"), "github"),
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
