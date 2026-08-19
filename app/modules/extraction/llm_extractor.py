from __future__ import annotations

import json
import re
from typing import Optional, Type

from pydantic import ValidationError

# اگر مدل Pydantic شما جای دیگری است، import را اصلاح کن
from app.schemas.resume import ResumeSchema


class LLMExtractionError(Exception):
    """خطای کلی استخراج با LLM."""


class LLMInvalidJSONError(LLMExtractionError):
    """وقتی خروجی مدل JSON معتبر نیست."""


class LLMSchemaValidationError(LLMExtractionError):
    """وقتی JSON معتبر است اما با Pydantic سازگار نیست."""


class ResumeLLMExtractor:
    """
    استخراج اطلاعات رزومه از متن نرمال‌شده با LLM.
    خروجی نهایی باید یک ResumeSchema معتبر باشد.
    """

    def __init__(
        self,
        llm,
        schema_model: Type[ResumeSchema] = ResumeSchema,
        max_retries: int = 2,
    ) -> None:
        """
        llm:
            هر آبجکتی که متد invoke(prompt) داشته باشد
            (مثلاً LangChain chat model یا wrapper سفارشی)
        """
        self.llm = llm
        self.schema_model = schema_model
        self.max_retries = max_retries

    def build_prompt(self, text: str) -> str:
        """
        پرامپت ضد توهم:
        - فقط از اطلاعات موجود در متن استفاده کن
        - چیزی را حدس نزن
        - اگر فیلدی موجود نبود null بگذار یا خالی بگذار
        - فقط JSON خروجی بده
        """

        return f"""
You are a strict information extraction engine for Persian resumes.

TASK:
Extract structured resume data from the input text and return ONLY valid JSON.

CRITICAL RULES:
1. Do NOT invent, guess, infer, or complete missing information.
2. Use ONLY facts explicitly present in the text.
3. If a field is not present, set it to null, empty string, empty list, or omit it only if the schema allows.
4. Never add explanations, markdown, code fences, or comments.
5. Output must be a single JSON object and nothing else.
6. Preserve source text fragments when possible in source_text fields.
7. If dates are unclear, keep them as strings exactly as written instead of converting them.
8. If a value is ambiguous, prefer null over hallucination.
9. Do not normalize or rewrite facts beyond basic structuring.

EXPECTED OUTPUT:
A JSON object compatible with the ResumeSchema structure.

INPUT TEXT:
{text}
""".strip()

    def _extract_json_block(self, raw_output: str) -> str:
        """
        اگر مدل به‌جای JSON خالص، متن اضافه یا code fence برگرداند،
        سعی می‌کنیم JSON را از آن جدا کنیم.
        """
        raw_output = raw_output.strip()

        # حذف code fence
        raw_output = re.sub(r"^ ```json\s*", "", raw_output, flags=re.IGNORECASE)
        raw_output = re.sub(r"^ ```\s*", "", raw_output)
        raw_output = re.sub(r"\s* ```$", "", raw_output)

        # اگر کل خروجی JSON نبود، اولین آبجکت JSON را پیدا کن
        start = raw_output.find("{")
        end = raw_output.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise LLMInvalidJSONError("No JSON object found in model output.")

        return raw_output[start : end + 1]

    def _parse_json(self, raw_output: str) -> dict:
        json_text = self._extract_json_block(raw_output)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise LLMInvalidJSONError(f"Invalid JSON output: {e}") from e

    def _validate_schema(self, data: dict) -> ResumeSchema:
        try:
            return self.schema_model.model_validate(data)
        except ValidationError as e:
            raise LLMSchemaValidationError(f"Schema validation failed: {e}") from e

    def _call_llm(self, prompt: str) -> str:
        """
        انتظار می‌رود llm خروجی متنی بدهد.
        برای LangChain معمولاً invoke(prompt) یا invoke(messages) استفاده می‌شود.
        """
        response = self.llm.invoke(prompt)

# سازگاری با LangChain message objects
        if hasattr(response, "content"):
            return response.content

        return str(response)

    def extract(self, text: str) -> ResumeSchema:
        """
        متن را به ResumeSchema تبدیل می‌کند.
        در صورت خطای JSON یا validation، retry انجام می‌شود.
        """
        prompt = self.build_prompt(text)
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                raw_output = self._call_llm(prompt)
                data = self._parse_json(raw_output)
                return self._validate_schema(data)

            except (LLMInvalidJSONError, LLMSchemaValidationError, ValidationError) as e:
                last_error = e

# در retry، پرامپت سخت‌گیرانه‌تر می‌شود
        prompt = self._build_retry_prompt(text, str(e))

        raise LLMExtractionError(
        f"Failed to extract resume after {self.max_retries + 1} attempts: {last_error}"
        )

    def _build_retry_prompt(self, text: str, error_message: str) -> str:
        """
        پرامپت اصلاحی برای retry.
        به مدل می‌گوییم خروجی قبلی نامعتبر بوده و فقط JSON درست بدهد.
        """
        return f"""
            Your previous response was invalid.

        ERROR:
        {error_message}

        You must now return ONLY valid JSON that matches the schema.

        STRICT RULES:
        - No markdown
        - No explanation
        - No code fences
        - No hallucination
        - Use only facts from the text
        - If unsure, use null or empty values

        INPUT TEXT:
        {text}
        """.strip()
