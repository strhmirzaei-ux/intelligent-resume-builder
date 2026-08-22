from __future__ import annotations

from app.schemas.resume import ResumeSchema


def validate_extracted_resume(
    resume: ResumeSchema,
    source_text: str,
) -> list[str]:
    """Return provenance violations instead of silently accepting fabricated facts."""
    source = source_text.casefold()
    violations: list[str] = []
    for section in [
        *resume.work_experiences,
        *resume.educations,
        *resume.skills,
        *resume.languages,
        *resume.projects,
        *resume.certificates,
    ]:
        for evidence in section.evidence:
            if evidence.source_text.casefold() not in source:
                violations.append("Evidence text was not found in the source.")
    return violations
