from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.integrations.llm_client import GeminiAIStudioClient, LLMClientError, OpenAICompatibleClient
from app.modules.extraction.llm_extractor import LLMExtractionError, ResumeLLMExtractor
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.pipeline_service import ResumePipelineService
from app.storage.store_factory import build_store

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()

if settings.llm_api_key and settings.llm_base_url:
    llm = OpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        max_output_tokens=settings.llm_max_output_tokens,
        max_network_retries=settings.llm_network_retries,
    )
elif settings.llm_api_key:
    llm = GeminiAIStudioClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        max_output_tokens=settings.llm_max_output_tokens,
    )
else:
    llm = None

pipeline = ResumePipelineService(
    extractor=ResumeLLMExtractor(llm=llm),
    store=build_store(settings),
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
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="ارتباط با پایگاه‌داده برقرار نشد. تنظیمات PostgreSQL را بررسی کنید.",
        ) from error

    analysis = record["analysis"]
    deficiencies = list(analysis.get("deficiencies", []))
    return ChatResponse(
        session_id=record["resume_id"],
        status="collecting" if record.get("next_question") else "completed",
        normalized_text=record["normalized_text"],
        extracted_data=record["resume"],
        deficiencies=deficiencies,
        next_question=record.get("next_question"),
        coverage_score=float(analysis["coverage_score"]),
        coverage_graph=analysis.get("graph"),
    )
