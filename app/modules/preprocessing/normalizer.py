"""ماژول نرمال‌سازی متن فارسی برای پیش‌پردازش رزومه‌ها.

این ماژول وظایف زیر را انجام می‌دهد:
- نرمال‌سازی متن با hazm (اصلاح ی/ک، نیم‌فاصله، اعراب و ...)
- حذف نویزها و کاراکترهای غیرمجاز
- تفکیک متن به جملات
"""

from __future__ import annotations

import re
from typing import List

from hazm import Normalizer as HazmNormalizer, sent_tokenize

_PROTECTED_PATTERN = re.compile(
    r"(?P<email>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})|"
    r"(?P<url>https?://\S+)|"
    r"(?P<phone>\+?\d[\d\s()-]{7,}\d)"
)
_ALLOWED_CHARS_PATTERN = re.compile(
    r"[^\u0600-\u06FF\u0020\u000A\u000D\u200C\u200F0-9A-Za-z"
    r"\.\,\;\:\!\?\؟\(\)\[\]\{\}\-\_\/\\@%+#]"
)
_MULTI_SPACE_PATTERN = re.compile(r"[ \t]+")
_SPACE_BEFORE_PUNCT_PATTERN = re.compile(r"\s+([.,;:!?؟)\]}])")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")
_INFORMAL_PREFIX_SPACE = re.compile(r"\b(می|نمی)\s+(?=[\u0600-\u06FF])")


def _placeholder(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    value = index
    suffix = ""
    while True:
        suffix = alphabet[value % len(alphabet)] + suffix
        value = value // len(alphabet) - 1
        if value < 0:
            return f"ZXQPROTECTED{suffix}"


class PersianTextNormalizer:
    """Normalize Persian text without destroying contact data or source meaning."""

    def __init__(self) -> None:
        self._normalizer = HazmNormalizer()

    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        protected: dict[str, str] = {}

        def protect(match: re.Match[str]) -> str:
            token = _placeholder(len(protected))
            protected[token] = match.group(0)
            return token

        text_with_protected_contacts = _PROTECTED_PATTERN.sub(protect, text)
        normalized = self._normalizer.normalize(text_with_protected_contacts)
        normalized = normalized.translate(_ARABIC_DIGITS)
        normalized = normalized.replace("\u200e", "").replace("\u200d", "")
        normalized = _INFORMAL_PREFIX_SPACE.sub(r"\1‌", normalized)
        for token, value in protected.items():
            normalized = normalized.replace(token, value)
        return normalized

    def remove_noise(self, text: str) -> str:
        normalized = self.normalize(text)
        protected: dict[str, str] = {}

        def protect(match: re.Match[str]) -> str:
            token = _placeholder(len(protected))
            protected[token] = match.group(0)
            return token

        cleaned = _PROTECTED_PATTERN.sub(protect, normalized)
        cleaned = cleaned.replace("*", " ")
        cleaned = _ALLOWED_CHARS_PATTERN.sub(" ", cleaned)
        cleaned = _MULTI_SPACE_PATTERN.sub(" ", cleaned)
        cleaned = _SPACE_BEFORE_PUNCT_PATTERN.sub(r"\1", cleaned)
        for token, value in protected.items():
            cleaned = cleaned.replace(token, value)
        return cleaned.strip()

    def split_sentences(self, text: str) -> List[str]:
        cleaned = self.remove_noise(text)
        return [sentence.strip() for sentence in sent_tokenize(cleaned) if sentence.strip()]

    def clean_text(self, text: str) -> str:
        return self.remove_noise(text)


# Backward-compatible public name used by the API.
Normalizer = PersianTextNormalizer
