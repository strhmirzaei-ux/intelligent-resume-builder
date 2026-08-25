from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.rendering.html_renderer import HtmlResumeRenderer
from app.schemas.chat import AnalysisResponse, ResumeCreateRequest
from app.storage.json_store import JsonStore

router = APIRouter(prefix="/resumes", tags=["resumes"])
settings = get_settings()
store = JsonStore(settings.storage_path)
renderer = HtmlResumeRenderer()


@router.get("/{resume_id}")
def get_resume(resume_id: str) -> dict:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return record


@router.get("/{resume_id}/json")
def export_resume_json(resume_id: str) -> dict:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {
        "resume_id": resume_id,
        "resume": record["resume"],
        "analysis": record["analysis"],
    }


@router.post("/{resume_id}/analyze", response_model=AnalysisResponse)
def analyze_resume(resume_id: str) -> AnalysisResponse:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    analysis = record["analysis"]
    return AnalysisResponse(resume_id=resume_id, **analysis)


@router.get("/{resume_id}/html", response_class=HTMLResponse)
def render_resume(resume_id: str) -> HTMLResponse:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return HTMLResponse(renderer.render(record["resume"]))


@router.post("", status_code=201)
def create_resume(payload: ResumeCreateRequest) -> dict:
    # Creation is intentionally routed through the same pipeline as chat.
    from app.api.routes.chat import pipeline

    return pipeline.process(payload.text)
