from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator


class DataStatus(str, Enum):
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=1)
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    evidence_type: str = "explicit"


class SectionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DataStatus = DataStatus.UNVERIFIED
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)


class RawDate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_value: str
    normalized_value: date | None = None
    precision: str = "unknown"
    calendar: str = "unknown"
    is_approximate: bool = False


class PersonalInfo(SectionBase):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    birth_date: date | None = None
    birth_date_raw: RawDate | None = None
    gender: str | None = Field(default=None, max_length=50)


class ContactInfo(SectionBase):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    linkedin: HttpUrl | None = None
    github: HttpUrl | None = None
    website: HttpUrl | None = None


class WorkExperience(SectionBase):
    company_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    start_date_raw: RawDate | None = None
    end_date_raw: RawDate | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=4000)
    achievements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_date_range(self) -> WorkExperience:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class Education(SectionBase):
    institution_name: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=150)
    field_of_study: str | None = Field(default=None, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    start_date_raw: RawDate | None = None
    end_date_raw: RawDate | None = None


class Skill(SectionBase):
    name: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=50)


class LanguageSkill(SectionBase):
    name: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=50)


class Project(SectionBase):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    role: str | None = Field(default=None, max_length=150)
    url: HttpUrl | None = None
    start_date: date | None = None
    end_date: date | None = None


class Certificate(SectionBase):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    issue_date: date | None = None
    url: HttpUrl | None = None


class ResumeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    professional_summary: str | None = Field(default=None, max_length=4000)
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    educations: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[LanguageSkill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certificates: list[Certificate] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)

    @property
    def education(self) -> list[Education]:
        return self.educations

    def evidence_texts(self) -> list[str]:
        sections: list[Any] = [
            self.personal_info,
            self.contact_info,
            *self.work_experiences,
            *self.educations,
            *self.skills,
            *self.languages,
            *self.projects,
            *self.certificates,
        ]
        return [
            evidence.source_text
            for section in sections
            for evidence in section.evidence
        ]
