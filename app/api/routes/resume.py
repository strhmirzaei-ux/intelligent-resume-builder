from copy import deepcopy

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.rendering.docx_renderer import DocxResumeRenderer
from app.rendering.pdf_renderer import PdfResumeRenderer
from app.rendering.resume_content import normalize_profile_url
from app.schemas.chat import AnalysisResponse, ResumeCreateRequest
from app.storage.store_factory import build_store

router = APIRouter(prefix="/resumes", tags=["resumes"])
settings = get_settings()
store = build_store(settings)
pdf_renderer = PdfResumeRenderer()
docx_renderer = DocxResumeRenderer()


@router.get("/{resume_id}")
def get_resume(resume_id: str) -> dict:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return record


@router.get("/{resume_id}/json")
def export_resume_json(resume_id: str) -> JSONResponse:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    resume = deepcopy(record["resume"])
    contact = resume.get("contact_info") or {}
    for field, platform in (("linkedin", "linkedin"), ("github", "github")):
        if contact.get(field):
            contact[field] = normalize_profile_url(contact[field], platform)
    payload = {
        "resume_id": resume_id,
        "resume": resume,
        "analysis": record.get("analysis", {}),
        "graph": record.get("analysis", {}).get("graph"),
    }
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": f'attachment; filename="resume-{resume_id}-latest.json"',
            "Cache-Control": "no-store, max-age=0",
        },
    )


@router.post("/{resume_id}/analyze", response_model=AnalysisResponse)
def analyze_resume(resume_id: str) -> AnalysisResponse:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    analysis = record["analysis"]
    return AnalysisResponse(resume_id=resume_id, **analysis)


@router.get("/{resume_id}/pdf")
def export_resume_pdf(resume_id: str) -> Response:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return Response(
        content=pdf_renderer.render(record["resume"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="resume-{resume_id}-latest.pdf"',
            "Cache-Control": "no-store, max-age=0",
        },
    )


@router.get("/{resume_id}/docx")
def export_resume_docx(resume_id: str) -> Response:
    record = store.get(resume_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return Response(
        content=docx_renderer.render(record["resume"]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="resume-{resume_id}-latest.docx"',
            "Cache-Control": "no-store, max-age=0",
        },
    )


@router.post("", status_code=201)
def create_resume(payload: ResumeCreateRequest) -> dict:
    # Creation is intentionally routed through the same pipeline as chat.
    from app.api.routes.chat import pipeline

    return pipeline.process(payload.text)
