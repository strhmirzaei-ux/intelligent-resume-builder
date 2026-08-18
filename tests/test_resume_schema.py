from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.resume import (
    ContactInfo,
    DataStatus,
    ResumeSchema,
    WorkExperience,
)


def test_کامل_رزومه():
    """یک رزومه کامل باید بدون خطا ساخته شود."""
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
    assert resume.contact_info.email == "mohsen@example.com"
    assert resume.skills[0].status == DataStatus.UNVERIFIED


def test_ایمیل_اشتباه_خطا_می_دهد():
    with pytest.raises(ValidationError):
        ResumeSchema(contact_info={"email": "not-an-email"})


def test_تاریخ_معکوس_خطا_می_دهد():
    with pytest.raises(ValidationError):
        WorkExperience(
            company_name="X",
            start_date=date(2022, 1, 1),
            end_date=date(2020, 1, 1),
        )


def test_فیلد_اضافی_رد_می_شود():
    with pytest.raises(ValidationError):
        ResumeSchema(whatever_extra="field")


def test_رزومه_خالی_مجاز_است():
    resume = ResumeSchema()
    assert resume.work_experiences == []
    assert resume.personal_info.status == DataStatus.UNVERIFIED
