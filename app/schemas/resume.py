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
    duration: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    start_date_raw: RawDate | None = None
    end_date_raw: RawDate | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=4000)
    key_responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_date_range(self) -> WorkExperience:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


class Internship(SectionBase):
    role: str | None = Field(default=None, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    duration: str | None = Field(default=None, max_length=100)
    responsibilities: list[str] = Field(default_factory=list)
    key_learnings: list[str] = Field(default_factory=list)


class Education(SectionBase):
    institution_name: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=150)
    field_of_study: str | None = Field(default=None, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    start_date_raw: RawDate | None = None
    end_date_raw: RawDate | None = None
    relevant_courses: list[str] = Field(default_factory=list)
    academic_projects: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


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
    problem_statement: str | None = Field(default=None, max_length=4000)
    tech_stack: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
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
    key_strengths: list[str] = Field(default_factory=list)
    career_objective: str | None = Field(default=None, max_length=2000)
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    educations: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    tools_platforms: list[str] = Field(default_factory=list)
    languages: list[LanguageSkill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    other_projects: list[Project] = Field(default_factory=list)
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
            *self.internships,
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

    def to_graph(self) -> "ResumeGraph":
        return ResumeGraph.from_resume(self)


class PersonalInfoGraph(BaseModel):
    basic_details: dict[str, Any]
    summary: dict[str, Any]
    core_skills: dict[str, Any]
    additional_info: dict[str, Any]


class EducationGraph(BaseModel):
    degrees: list[Education]
    relevant_courses: list[str]
    academic_projects: list[str]
    achievements: list[str]


class WorkExperienceGraph(BaseModel):
    experiences: list[WorkExperience]
    internships: list[Internship]


class ProjectsGraph(BaseModel):
    projects: list[Project]
    other_projects: list[Project]


class InteractiveSkillsGraph(BaseModel):
    technical_skills: list[Skill]
    tools_platforms: list[str]
    key_questions: list[str]
    live_interaction: list[str]


class ResumeGraph(BaseModel):
    """Five-node view of the resume used by scoring and future persistence."""

    personal_info: PersonalInfoGraph
    education: EducationGraph
    work_experience: WorkExperienceGraph
    projects: ProjectsGraph
    interactive_skills: InteractiveSkillsGraph

    @classmethod
    def from_resume(cls, resume: ResumeSchema) -> "ResumeGraph":
        courses = [
            course
            for education in resume.educations
            for course in education.relevant_courses
        ]
        academic_projects = [
            project
            for education in resume.educations
            for project in education.academic_projects
        ]
        achievements = [
            achievement
            for education in resume.educations
            for achievement in education.achievements
        ]
        return cls(
            personal_info=PersonalInfoGraph(
                basic_details={
                    "full_name": resume.personal_info.full_name,
                    "first_name": resume.personal_info.first_name,
                    "last_name": resume.personal_info.last_name,
                    "location": resume.contact_info.city or resume.contact_info.country,
                    "phone": resume.contact_info.phone,
                    "email": str(resume.contact_info.email)
                    if resume.contact_info.email
                    else None,
                    "linkedin": str(resume.contact_info.linkedin)
                    if resume.contact_info.linkedin
                    else None,
                    "github": str(resume.contact_info.github)
                    if resume.contact_info.github
                    else None,
                },
                summary={
                    "professional_summary": resume.professional_summary,
                    "key_strengths": resume.key_strengths,
                    "career_objective": resume.career_objective,
                },
                core_skills={
                    "skills": resume.skills,
                    "tools_platforms": resume.tools_platforms,
                },
                additional_info={
                    "languages": resume.languages,
                    "certificates": resume.certificates,
                    "interests": resume.interests,
                },
            ),
            education=EducationGraph(
                degrees=resume.educations,
                relevant_courses=courses,
                academic_projects=academic_projects,
                achievements=achievements,
            ),
            work_experience=WorkExperienceGraph(
                experiences=resume.work_experiences,
                internships=resume.internships,
            ),
            projects=ProjectsGraph(
                projects=resume.projects,
                other_projects=resume.other_projects,
            ),
            interactive_skills=InteractiveSkillsGraph(
                technical_skills=resume.skills,
                tools_platforms=resume.tools_platforms,
                key_questions=[
                    "خودتان را معرفی کنید.",
                    "چرا برای این نقش مناسب هستید؟",
                    "نقاط قوت و ضعف شما چیست؟",
                    "چطور مسئله‌ها را حل می‌کنید؟",
                    "پروژه عمیق یا مهم شما کدام است؟",
                ],
                live_interaction=[
                    "مصاحبه آزمایشی هوش مصنوعی",
                    "پرسش و پاسخ رزومه",
                    "پیشنهادهای بهبود",
                    "بهبود تعاملی رزومه",
                ],
            ),
        )
