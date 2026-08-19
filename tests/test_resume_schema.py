from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.resume import DataStatus, ResumeSchema, WorkExperience


def test_resume_accepts_valid_data():
    resume = ResumeSchema(
        personal_info={"first_name": "محمد", "status": "complete"},
        contact_info={"email": "mohsen@example.com"},
        work_experiences=[
            {
                "company_name": "Nova AI",
                "job_title": "Backend Developer",
                "start_date": "2020-01-01",
                "end_date": "2022-01-01",
            }
        ],
        skills=[{"name": "Python"}],
    )
    assert str(resume.contact_info.email) == "mohsen@example.com"
    assert resume.skills[0].status == DataStatus.UNVERIFIED


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        ResumeSchema(contact_info={"email": "not-an-email"})


def test_reversed_work_dates_are_rejected():
    with pytest.raises(ValidationError):
        WorkExperience(
            company_name="X",
            start_date=date(2022, 1, 1),
            end_date=date(2020, 1, 1),
        )


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        ResumeSchema(whatever_extra="field")
