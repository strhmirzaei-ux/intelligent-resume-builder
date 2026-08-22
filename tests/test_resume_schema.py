from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.resume import DataStatus, ResumeSchema, WorkExperience


def test_resume_schema_supports_core_sections():
    resume = ResumeSchema(
        personal_info={"full_name": "محمد رضایی"},
        contact_info={"email": "mohsen@example.com"},
        professional_summary="توسعه‌دهنده بک‌اند",
        skills=[{"name": "Python", "level": "پیشرفته"}],
        languages=[{"name": "انگلیسی", "level": "B2"}],
    )
    assert str(resume.contact_info.email) == "mohsen@example.com"
    assert resume.skills[0].status == DataStatus.UNVERIFIED


def test_invalid_email_and_date_are_rejected():
    with pytest.raises(ValidationError):
        ResumeSchema(contact_info={"email": "not-an-email"})
    with pytest.raises(ValidationError):
        WorkExperience(
            company_name="X",
            start_date=date(2022, 1, 1),
            end_date=date(2020, 1, 1),
        )


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        ResumeSchema(unknown="value")
