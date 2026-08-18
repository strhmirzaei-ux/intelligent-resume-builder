"""ماژول نرمال‌سازی متن فارسی برای پیش‌پردازش رزومه‌ها.

این ماژول وظایف زیر را انجام می‌دهد:
- نرمال‌سازی متن با hazm (اصلاح ی/ک، نیم‌فاصله، اعراب و ...)
- حذف نویزها و کاراکترهای غیرمجاز
- تفکیک متن به جملات
"""

from __future__ import annotations

import re
from typing import List

from hazm import Normalizer, sent_tokenize

# ─────────────────────────────────────────────
# پیکربندی
# ─────────────────────────────────────────────
# کاراکترهای مجاز: حروف فارسی، ارقام، فاصله و علائم نگارشی پایه
_ALLOWED_CHARS_PATTERN = re.compile(
    r"[^\u0600-\u06FF\u0020\u200C\u200F"
    r"0-9A-Za-z"
    r"\.\,\;\:\!\?\؟\(\）\[\]\{\}\-\_\/\\\u0660-\u0669]"
)

# چند فاصله‌ی پشت‌سرهم → یک فاصله
_MULTI_SPACE_PATTERN = re.compile(r"[ \t]+")

# فاصله‌ی قبل از علائم نگارشی → حذف
_SPACE_BEFORE_PUNCT_PATTERN = re.compile(r"\s+([\.,;:!?؟\)\]}])")


class PersianTextNormalizer:
    """کلاس سرویس نرمال‌سازی متون فارسی."""

    def __init__(self) -> None:
        self._normalizer = Normalizer()

    # ── ۱. نرمال‌سازی پایه (hazm) ─────────────────────
    def normalize(self, text: str) -> str:
        """نرمال‌سازی پایه: اصلاح ی/ک، نیم‌فاصله‌ها، اعراب و ..."""
        return self._normalizer.normalize(text)

    # ── ۲. حذف نویز و کاراکترهای غیرمجاز ──────────────
    def remove_noise(self, text: str) -> str:
        """حذف نویز، کاراکترهای غیرمجاز و فاصله‌های اضافی."""
        # نرمال‌سازی ابتدایی
        text = self.normalize(text)
        # حذف کاراکترهای غیرمجاز
        text = _ALLOWED_CHARS_PATTERN.sub(" ", text)
        # حذف چند فاصله‌ی متوالی
        text = _MULTI_SPACE_PATTERN.sub(" ", text)
        # حذف فاصله‌ی قبل از علائم نگارشی
        text = _SPACE_BEFORE_PUNCT_PATTERN.sub(r"\1", text)
        return text.strip()

    # ── ۳. تفکیک جملات ────────────────────────────────
    def split_sentences(self, text: str) -> List[str]:
        """تفکیک متن به جملات برای تحلیل‌های بعدی."""
        cleaned = self.remove_noise(text)
        sentences = sent_tokenize(cleaned)
        # حذف جمله‌های خالی
        return [s.strip() for s in sentences if s.strip()]

    # ── متد ترکیبی ────────────────────────────────────
    def clean_text(self, text: str) -> str:
        """رابط اصلی: نرمال‌سازی + حذف نویز در یک قدم."""
        return self.remove_noise(text)
