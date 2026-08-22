from __future__ import annotations

import re

from hazm import Normalizer as HazmNormalizer
from hazm import sent_tokenize

_CONTACT_PATTERN = re.compile(
    r"(?P<email>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})|"
    r"(?P<url>https?://\S+)|"
    r"(?P<phone>\+?\d[\d\s()-]{7,}\d)"
)
_ALLOWED_PATTERN = re.compile(
    r"[^\u0600-\u06FF\u0020\u000A\u000D\u200C\u200F0-9A-Za-z"
    r"\.,;\u060C\u061B\u061F!?:?\(\)\[\]\{\}\-_\/\\@%+#]"
)
_MULTI_SPACE_PATTERN = re.compile(r"[ \t]+")
_SPACE_BEFORE_PUNCT_PATTERN = re.compile(r"\s+([.,;\u060C\u061B\u061F!?:?\)\]}])")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")
_INFORMAL_PREFIX = re.compile(r"\b(\u0645\u06cc|\u0646\u0645\u06cc)\s+(?=[\u0600-\u06FF])")


def _token(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    suffix = ""
    value = index
    while True:
        suffix = alphabet[value % 26] + suffix
        value = value // 26 - 1
        if value < 0:
            return f"ZXQPROTECTED{suffix}"


class PersianTextNormalizer:
    def __init__(self) -> None:
        self._hazm = HazmNormalizer()

    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        protected: dict[str, str] = {}

        def protect(match: re.Match[str]) -> str:
            token = _token(len(protected))
            protected[token] = match.group(0)
            return token

        normalized = self._hazm.normalize(_CONTACT_PATTERN.sub(protect, text))
        normalized = normalized.translate(_ARABIC_DIGITS)
        normalized = normalized.replace("\u200e", "").replace("\u200d", "")
        normalized = _INFORMAL_PREFIX.sub(
            lambda match: f"{match.group(1)}\u200c",
            normalized,
        )
        for token, value in protected.items():
            normalized = normalized.replace(token, value)
        return normalized

    def remove_noise(self, text: str) -> str:
        normalized = self.normalize(text)
        protected: dict[str, str] = {}

        def protect(match: re.Match[str]) -> str:
            token = _token(len(protected))
            protected[token] = match.group(0)
            return token

        cleaned = _CONTACT_PATTERN.sub(protect, normalized)
        cleaned = _ALLOWED_PATTERN.sub(" ", cleaned.replace("*", " "))
        cleaned = _MULTI_SPACE_PATTERN.sub(" ", cleaned)
        cleaned = _SPACE_BEFORE_PUNCT_PATTERN.sub(r"\1", cleaned)
        for token, value in protected.items():
            cleaned = cleaned.replace(token, value)
        return cleaned.strip()

    def split_sentences(self, text: str) -> list[str]:
        return [
            sentence.strip()
            for sentence in sent_tokenize(self.remove_noise(text))
            if sentence.strip()
        ]

    def clean_text(self, text: str) -> str:
        return self.remove_noise(text)


Normalizer = PersianTextNormalizer
