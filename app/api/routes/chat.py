from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.integrations.llm_client import InferXClient, LLMClientError
from app.modules.extraction.llm_extractor import LLMExtractionError, ResumeLLMExtractor
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()

llm = (
    InferXClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
    )
    if settings.llm_api_key
    else None
)
pipeline = ResumePipelineService(
    extractor=ResumeLLMExtractor(llm=llm),
    store=JsonStore(settings.storage_path),
)


@router.post("/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest) -> ChatResponse:
    if len(payload.message) > settings.max_input_length:
        raise HTTPException(
            status_code=413,
            detail=f"Input exceeds the {settings.max_input_length} character limit.",
        )
    try:
        record = pipeline.process(payload.message, payload.session_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LLMExtractionError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LLMClientError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    analysis = record["analysis"]
    deficiencies = list(analysis.get("deficiencies", []))
    questions = pipeline.questions_for(record)
    return ChatResponse(
        session_id=record["resume_id"],
        status="completed" if not deficiencies else "collecting",
        normalized_text=record["normalized_text"],
        extracted_data=record["resume"],
        deficiencies=deficiencies,
        next_question=questions[0]["text"] if questions else None,
        coverage_score=float(analysis["coverage_score"]),
    )
