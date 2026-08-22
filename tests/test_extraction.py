from app.modules.extraction.validators import validate_extracted_resume
from app.schemas.resume import Evidence, ResumeSchema


def test_evidence_must_exist_in_source_text():
    resume = ResumeSchema(
        skills=[
            {
                "name": "Python",
                "evidence": [Evidence(source_text="Java")],
            }
        ]
    )
    violations = validate_extracted_resume(resume, "من Python بلدم")
    assert violations
