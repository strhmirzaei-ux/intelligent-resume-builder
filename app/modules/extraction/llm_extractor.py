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
        return (
            "You extract Persian resume data. Return ONLY one valid JSON object.\n"
            "Use only facts explicitly present in INPUT. Never invent or infer.\n"
            "Use null for unknown scalar values and [] for unknown lists.\n"
            "Dates must be ISO format YYYY-MM-DD when exact; otherwise use the raw date field.\n"
            "Do not include markdown, comments, explanations, or extra keys.\n"
            "JSON contract:\n"
            '{"personal_info":{"first_name":null,"last_name":null,"full_name":null,'
            '"birth_date":null,"birth_date_raw":null,"gender":null,"status":"unverified",'
            '"confidence":null,"evidence":[]},'
            '"contact_info":{"email":null,"phone":null,"city":null,"country":null,'
            '"linkedin":null,"github":null,"website":null,"status":"unverified",'
            '"confidence":null,"evidence":[]},'
            '"professional_summary":null,'
            '"work_experiences":[{"company_name":null,"job_title":null,"start_date":null,'
            '"end_date":null,"start_date_raw":null,"end_date_raw":null,"is_current":false,'
            '"description":null,"achievements":[],"status":"unverified","confidence":null,'
            '"evidence":[]}],'
            '"educations":[],"skills":[{"name":"...","level":null,"status":"unverified",'
            '"confidence":null,"evidence":[]}],"languages":[],"projects":[],"certificates":[],'
            '"interests":[]}\n'
            f"INPUT:\n{text}"
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
