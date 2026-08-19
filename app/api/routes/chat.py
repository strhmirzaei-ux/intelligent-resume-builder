from __future__ import annotations

from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.preprocessing.normalizer import PersianTextNormalizer
from app.modules.extraction.llm_extractor import ResumeLLMExtractor
from app.modules.gap_analysis.analyzer import GapAnalyzer
from app.modules.question_generation.generator import QuestionGenerator

router = APIRouter(prefix="/chat", tags=["chat"])


# -----------------------------
# In-memory session store
# -----------------------------
SESSION_STORE: Dict[str, Dict[str, Any]] = {}


# -----------------------------
# Request / Response Schemas
# -----------------------------
class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None,
        description="شناسه نشست گفتگو. اگر ارسال نشود، یک session جدید ساخته می‌شود.",
    )
    message: str = Field(..., min_length=1, description="پیام کاربر")


class ChatResponse(BaseModel):
    session_id: str
    status: str
    normalized_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    deficiencies: List[str] = []
    next_question: Optional[str] = None
    coverage_score: Optional[float] = None


# -----------------------------
# Dependencies / services
# -----------------------------
normalizer = PersianTextNormalizer()
extractor = ResumeLLMExtractor()
gap_analyzer = GapAnalyzer()
question_generator = QuestionGenerator()


# -----------------------------
# Helper functions
# -----------------------------
def get_or_create_session(session_id: Optional[str]) -> str:
    if session_id and session_id in SESSION_STORE:
        return session_id

    new_session_id = session_id or str(uuid4())
    SESSION_STORE[new_session_id] = {
        "messages": [],
        "current_data": {},
        "last_normalized_text": None,
        "last_deficiencies": [],
        "status": "collecting",
    }
    return new_session_id


def merge_extracted_data(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ادغام ساده داده‌های جدید با داده‌های قبلی.
    قانون:
    - مقدار جدید اگر None یا خالی نباشد، جایگزین مقدار قبلی شود
    """
    merged = dict(old_data)

    for key, value in new_data.items():
        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        if isinstance(value, list) and len(value) == 0:
            continue

        if isinstance(value, dict):
            old_value = merged.get(key, {})
            if isinstance(old_value, dict):
                merged[key] = merge_extracted_data(old_value, value)
            else:
                merged[key] = value
        else:
            merged[key] = value

    return merged


def evaluate_resume_completeness(extracted_data: Dict[str, Any], deficiencies: List[str]) -> bool:
    """
    معیار ساده برای کامل بودن رزومه:
    اگر هیچ نقصی باقی نمانده باشد، داده کامل فرض می‌شود.
    """
    return len(deficiencies) == 0


# -----------------------------
# Route
# -----------------------------
@router.post("/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest) -> ChatResponse:
    session_id = get_or_create_session(payload.session_id)
    session = SESSION_STORE[session_id]

    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    # 1) ذخیره پیام خام
    session["messages"].append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    # 2) Normalization
    normalized_text = normalizer.normalize(user_message)
    session["last_normalized_text"] = normalized_text

    # 3) Extraction
    # فرض: extractor خروجی ساختاریافته در قالب dict یا مدل pydantic برمی‌گرداند
    extracted_result = extractor.extract(normalized_text)

    if hasattr(extracted_result, "model_dump"):
        extracted_data = extracted_result.model_dump()
    elif isinstance(extracted_result, dict):
        extracted_data = extracted_result
    else:
        raise HTTPException(status_code=500, detail="Extractor returned invalid output")

    # 4) Merge with session memory
    session["current_data"] = merge_extracted_data(
        session.get("current_data", {}),
        extracted_data,
    )

    # 5) Gap analysis
    analysis = gap_analyzer.analyze(
        session["current_data"],
        original_text=normalized_text,
    )

    # انتظار می‌رود analyzer یک dict با deficiencies و coverage_score بدهد
    deficiencies = analysis.get("deficiencies", [])
    coverage_score = analysis.get("coverage_score", None)

    session["last_deficiencies"] = deficiencies

    # 6) Decide next step
    if evaluate_resume_completeness(session["current_data"], deficiencies):
        session["status"] = "completed"
        response = ChatResponse(
            session_id=session_id,
            status="completed",
            normalized_text=normalized_text,
            extracted_data=session["current_data"],
            deficiencies=[],
            next_question=None,
            coverage_score=coverage_score,
        )
        session["messages"].append(
            {
                "role": "assistant",
                "content": "رزومه شما با موفقیت تکمیل شد.",
            }
        )
        return response

    # 7) Generate next question
    questions = question_generator.generate(deficiencies)
    next_question = questions[0]["text"] if questions else "لطفاً اطلاعات بیشتری ارسال کنید."

    session["status"] = "collecting"
    session["messages"].append(
        {
            "role": "assistant",
            "content": next_question,
        }
    )

    return ChatResponse(
        session_id=session_id,
        status="collecting",
        normalized_text=normalized_text,
        extracted_data=session["current_data"],
        deficiencies=deficiencies,
        next_question=next_question,
        coverage_score=coverage_score,
    )
