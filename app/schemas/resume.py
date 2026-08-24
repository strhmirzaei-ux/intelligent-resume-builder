"""Schemaهای رزومه برای سامانه هوشمند تولید رزومه.

این ماژول شامل مدل‌های Pydantic برای تمام بخش‌های رزومه است.
هر بخش علاوه بر داده‌ها، وضعیت تکمیل (status) و منبع استخراج (source_text)
را نگه می‌دارد تا بتوان نقص‌ها و ابهام‌ها را ردیابی کرد.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    model_validator,
)


# ─────────────────────────────────────────────────────
# ۱. Enum وضعیت داده — برای ردیابی نقص هر بخش
# ─────────────────────────────────────────────────────
class DataStatus(str, Enum):
    """وضعیت تکمیل و اعتبار یک بخش از رزومه."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    UNVERIFIED = "unverified"
    CONFIRMED = "confirmed"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    INFERRED = "inferred"
    REJECTED = "rejected"


# ─────────────────────────────────────────────────────
# ۲. مدل پایه مشترک — هر بخش آن را ارث می‌برد
# ─────────────────────────────────────────────────────
class SectionBase(BaseModel):
    """فیلدهای مشترک بین همه بخش‌های رزومه."""

    model_config = ConfigDict(extra="forbid")

    status: DataStatus = Field(
        default=DataStatus.UNVERIFIED,
        description="وضعیت تکمیل این بخش",
    )
    source_text: Optional[str] = Field(
        default=None,
        description="متن/بخشی از متن اصلی که این داده از آن استخراج شده",
    )
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


# ─────────────────────────────────────────────────────
# ۳. اطلاعات فردی
# ─────────────────────────────────────────────────────
class PersonalInfo(SectionBase):
    """اطلاعات هویتی فرد."""

    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)
    birth_date: Optional[date] = Field(default=None)
    gender: Optional[str] = Field(default=None, max_length=50)


# ─────────────────────────────────────────────────────
# ۴. اطلاعات تماس
# ─────────────────────────────────────────────────────
class ContactInfo(SectionBase):
    """راه‌های ارتباطی."""

    email: Optional[EmailStr] = Field(default=None)
    phone: Optional[str] = Field(default=None, max_length=30)
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    linkedin: Optional[HttpUrl] = Field(default=None)
    github: Optional[HttpUrl] = Field(default=None)
    website: Optional[HttpUrl] = Field(default=None)


# ─────────────────────────────────────────────────────
# ۵. سوابق شغلی
# ─────────────────────────────────────────────────────
class WorkExperience(SectionBase):
    """یک تجربه کاری."""

    company_name: Optional[str] = Field(default=None, max_length=200)
    job_title: Optional[str] = Field(default=None, max_length=200)
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    is_current: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_date_range(self) -> "WorkExperience":
        """اطمینان از اینکه end_date بعد از start_date است."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError(
                "end_date نمی‌تواند زودتر از start_date باشد."
            )
        return self


# ─────────────────────────────────────────────────────
# ۶. سوابق تحصیلی
# ─────────────────────────────────────────────────────
class Education(SectionBase):
    """یک سابقه تحصیلی."""

    institution_name: Optional[str] = Field(default=None, max_length=200)
    degree: Optional[str] = Field(default=None, max_length=150)
    field_of_study: Optional[str] = Field(default=None, max_length=150)
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)


# ─────────────────────────────────────────────────────
# ۷. مهارت
# ─────────────────────────────────────────────────────
class Skill(SectionBase):
    """یک مهارت."""

    name: str = Field(..., max_length=100)
    level: Optional[str] = Field(default=None, max_length=50)


# ─────────────────────────────────────────────────────
# ۸. پروژه
# ─────────────────────────────────────────────────────
class Project(SectionBase):
    """یک پروژه."""

    name: str = Field(..., max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    role: Optional[str] = Field(default=None, max_length=150)
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    url: Optional[HttpUrl] = Field(default=None)


# ─────────────────────────────────────────────────────
# ۹. مدل ریشه — کل رزومه
# ─────────────────────────────────────────────────────
class ResumeSchema(BaseModel):
    """نمای کامل یک رزومه استخراج‌شده."""

    model_config = ConfigDict(extra="forbid")

    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    work_experiences: List[WorkExperience] = Field(default_factory=list)
    educations: List[Education] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @property
    def education(self) -> List[Education]:
        """Compatibility alias for older integrations."""
        return self.educations

    def evidence_texts(self) -> List[str]:
        values: List[str] = []
        sections = [self.personal_info, self.contact_info, *self.work_experiences,
                    *self.educations, *self.skills, *self.projects]
        for section in sections:
            if section.source_text:
                values.append(section.source_text)
        return values
