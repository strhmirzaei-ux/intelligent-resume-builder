from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=20_000)


class ChatResponse(BaseModel):
    session_id: str
    status: str
    normalized_text: str | None = None
    extracted_data: dict[str, Any] | None = None
    deficiencies: list[str] = Field(default_factory=list)
    next_question: str | None = None
    coverage_score: float | None = None
    coverage_graph: dict[str, Any] | None = None


class ResumeCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


class AnalysisResponse(BaseModel):
    resume_id: str
    coverage_score: float
    is_valid: bool
    deficiencies: list[str]
    suggestions: list[str]
