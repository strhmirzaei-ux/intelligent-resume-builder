from io import BytesIO
from zipfile import ZipFile

from app.rendering.docx_renderer import DocxResumeRenderer
from app.rendering.pdf_renderer import PdfResumeRenderer


def sample_resume() -> dict:
    return {
        "personal_info": {"full_name": "علی احمدی"},
        "contact_info": {"email": "ali@example.com", "city": "تهران"},
        "professional_summary": "برنامه‌نویس پایتون با تجربه توسعه سامانه‌های وب.",
        "work_experiences": [
            {
                "job_title": "توسعه‌دهنده بک‌اند",
                "company_name": "شرکت نمونه",
                "duration": "۱۴۰۱ تا اکنون",
                "description": "طراحی و توسعه API",
                "key_responsibilities": ["توسعه سرویس‌های FastAPI"],
                "achievements": [],
            }
        ],
        "skills": [{"name": "Python", "level": "پیشرفته"}],
    }


def test_pdf_renderer_returns_valid_pdf_with_persian_text():
    output = PdfResumeRenderer().render(sample_resume())
    assert output.startswith(b"%PDF")
    assert len(output) > 1_000


def test_docx_renderer_returns_valid_openxml_document():
    output = DocxResumeRenderer().render(sample_resume())
    assert output.startswith(b"PK")
    with ZipFile(BytesIO(output)) as archive:
        document_xml = archive.read("word/document.xml")
        assert "علی".encode() in document_xml
        assert b"w:bidi" in document_xml
        assert b'w:jc w:val="right"' in document_xml
        assert b'w:right="360"' not in document_xml


def test_export_endpoints_return_downloadable_files(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.routes import resume as resume_route
    from app.main import app

    monkeypatch.setattr(
        resume_route.store,
        "get",
        lambda resume_id: {"resume": sample_resume(), "analysis": {}},
    )
    client = TestClient(app)
    json_response = client.get("/api/v1/resumes/demo/json")
    pdf = client.get("/api/v1/resumes/demo/pdf")
    docx = client.get("/api/v1/resumes/demo/docx")
    assert json_response.status_code == 200
    assert json_response.headers["content-type"].startswith("application/json")
    assert json_response.headers["content-disposition"].endswith("resume-demo-latest.json\"")
    assert json_response.json()["resume"] == sample_resume()
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["cache-control"] == "no-store, max-age=0"
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert docx.content.startswith(b"PK")
    assert docx.headers["cache-control"] == "no-store, max-age=0"
