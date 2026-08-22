from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.resume import ResumeSchema


class LLMExtractionError(Exception):
    pass


class LLMInvalidJSONError(LLMExtractionError):
    pass


class LLMSchemaValidationError(LLMExtractionError):
    pass


class ResumeLLMExtractor:
    def __init__(
        self,
        llm: Any = None,
        schema_model: type[ResumeSchema] = ResumeSchema,
        max_retries: int = 2,
    ) -> None:
        self.llm = llm
        self.schema_model = schema_model
        self.max_retries = max(0, max_retries)

    def build_prompt(self, text: str) -> str:
        schema = json.dumps(
            self.schema_model.model_json_schema(),
            ensure_ascii=False,
        )
        return (
            "You are a strict Persian resume information extraction engine.\n"
            "Return only one JSON object matching the supplied schema.\n"
            "Use only explicit facts from INPUT. Never invent, infer, or complete facts.\n"
            "For missing or ambiguous values use null or an empty list.\n"
            "Every extracted section should include evidence when possible.\n"
            f"SCHEMA:\n{schema}\nINPUT:\n{text}"
        )

    @staticmethod
    def _extract_json_block(raw_output: str) -> str:
        text = raw_output.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise LLMInvalidJSONError("No JSON object found in model output.")
        return text[start : end + 1]

    def _parse_json(self, raw_output: str) -> dict[str, Any]:
        try:
            value = json.loads(self._extract_json_block(raw_output))
        except json.JSONDecodeError as error:
            raise LLMInvalidJSONError(str(error)) from error
        if not isinstance(value, dict):
            raise LLMInvalidJSONError("Model output must be a JSON object.")
        return value

    def _call_llm(self, prompt: str) -> str:
        if self.llm is None:
            raise LLMExtractionError("No LLM client has been configured.")
        response = self.llm.invoke(prompt)
        content = getattr(response, "content", response)
        return str(content)

    def extract(self, text: str) -> ResumeSchema:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must not be empty")
        prompt = self.build_prompt(text)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                data = self._parse_json(self._call_llm(prompt))
                return self.schema_model.model_validate(data)
            except (LLMExtractionError, ValidationError) as error:
                last_error = (
                    LLMSchemaValidationError(str(error))
                    if isinstance(error, ValidationError)
                    else error
                )
                if attempt < self.max_retries:
                    prompt = (
                        f"{self.build_prompt(text)}\n"
                        f"Previous response was invalid: {last_error}"
                    )
        raise LLMExtractionError(
            f"Extraction failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error


LLMExtractor = ResumeLLMExtractor
