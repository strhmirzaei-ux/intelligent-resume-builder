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
            "The keys name, level, status, confidence, and evidence are allowed ONLY "
            "inside an item in the skills or languages array. Never put them at the "
            "top level of the resume object.\n"
            "Capture these graph fields when explicitly present: key_strengths, "
            "career_objective, tools_platforms, other_projects; work items may include "
            "key_responsibilities; education items may include relevant_courses, "
            "academic_projects, and achievements; project items may include "
            "problem_statement, tech_stack, key_features, and outcomes; internships "
            "may include role, company_name, duration, responsibilities, and key_learnings.\n"
            "JSON contract:\n"
            '{"personal_info":{"first_name":null,"last_name":null,"full_name":null,'
            '"birth_date":null,"birth_date_raw":null,"gender":null,"status":"unverified",'
            '"confidence":null,"evidence":[]},'
            '"contact_info":{"email":null,"phone":null,"city":null,"country":null,'
            '"linkedin":null,"github":null,"website":null,"status":"unverified",'
            '"confidence":null,"evidence":[]},'
            '"professional_summary":null,'
            '"key_strengths":[],"career_objective":null,'
            '"work_experiences":[],"internships":[],'
            '"educations":[{"institution_name":null,"degree":null,"field_of_study":null,'
            '"relevant_courses":[],"academic_projects":[],"achievements":[],"status":"unverified",'
            '"confidence":null,"evidence":[]}],'
            '"skills":[{"name":"...","level":null,"status":"unverified",'
            '"confidence":null,"evidence":[]}],"tools_platforms":[],"languages":[],'
            '"projects":[{"name":"...","problem_statement":null,"role":null,"tech_stack":[],'
            '"key_features":[],"outcomes":[],"description":null,"url":null,'
            '"status":"unverified","confidence":null,"evidence":[]}],'
            '"other_projects":[],"certificates":[],'
            '"interests":[]}\n'
            f"INPUT:\n{text}"
        )

    @staticmethod
    def _extract_json_block(raw_output: str) -> str:
        text = re.sub(
            r"<think\b[^>]*>.*?</think\s*>",
            "",
            raw_output,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "")
        start = text.find("{")
        if start < 0:
            raise LLMInvalidJSONError("No JSON object found in model output.")

        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]

        raise LLMInvalidJSONError("Incomplete JSON object in model output.")

    @staticmethod
    def _repair_common_json_errors(json_block: str) -> str:
        repaired = re.sub(r",(\s*[}\]])", r"\1", json_block)
        return re.sub(
            r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:',
            r'\1"\2":',
            repaired,
        )

    def _parse_json(self, raw_output: str) -> dict[str, Any]:
        json_block = self._extract_json_block(raw_output)
        try:
            value = json.loads(json_block)
        except json.JSONDecodeError as error:
            try:
                value = json.loads(self._repair_common_json_errors(json_block))
            except json.JSONDecodeError:
                raise LLMInvalidJSONError(str(error)) from error
        if not isinstance(value, dict):
            raise LLMInvalidJSONError("Model output must be a JSON object.")
        return value

    @staticmethod
    def _normalize_common_model_shape(data: dict[str, Any]) -> dict[str, Any]:
        """Handle a common small-model mistake without inventing resume facts."""
        valid_statuses = {
            "confirmed",
            "partial",
            "missing",
            "ambiguous",
            "conflicting",
            "inferred",
            "unverified",
            "rejected",
        }
        top_level_keys = {
            "personal_info",
            "contact_info",
            "professional_summary",
            "work_experiences",
            "educations",
            "skills",
            "languages",
            "projects",
            "certificates",
            "interests",
        }
        skill_keys = {"name", "level", "status", "confidence", "evidence"}
        if (
            "name" in data
            and not (set(data) & top_level_keys)
            and set(data) <= skill_keys
        ):
            data = {"skills": [data]}

        section_names = (
            "personal_info",
            "contact_info",
            "work_experiences",
            "internships",
            "educations",
            "skills",
            "languages",
            "projects",
            "certificates",
        )

        def normalize_section(section: Any) -> dict[str, Any]:
            if isinstance(section, str):
                return {
                    "status": "unverified",
                    "evidence": [{"source_text": section}],
                }
            if not isinstance(section, dict):
                return {}
            normalized = dict(section)
            if normalized.get("status") == "verified":
                normalized["status"] = "confirmed"
            if isinstance(normalized.get("evidence"), list):
                normalized["evidence"] = [
                    {"source_text": evidence}
                    if isinstance(evidence, str) and evidence.strip()
                    else evidence
                    for evidence in normalized["evidence"]
                ]
            if normalized.get("status") not in valid_statuses:
                normalized["status"] = "unverified"
            for raw_date_key in ("birth_date_raw", "start_date_raw", "end_date_raw"):
                raw_date = normalized.get(raw_date_key)
                if isinstance(raw_date, str) and raw_date.strip():
                    normalized[raw_date_key] = {"raw_value": raw_date}
            return normalized

        for section_name in section_names:
            value = data.get(section_name)
            if isinstance(value, list):
                data[section_name] = [
                    normalize_section(item) for item in value
                ]
            elif section_name in data:
                data[section_name] = normalize_section(value)
        return data

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
                data = self._normalize_common_model_shape(data)
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
                        "Your previous response was invalid. "
                        f"Parser error: {last_error}. "
                        "Return the corrected JSON object only; do not include "
                        "thinking, markdown, comments, or trailing commas."
                    )
        raise LLMExtractionError(
            f"Extraction failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error


LLMExtractor = ResumeLLMExtractor
