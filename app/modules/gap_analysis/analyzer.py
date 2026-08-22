from __future__ import annotations

from app.schemas.resume import ResumeSchema


class GapAnalyzer:
    def __init__(self, resume: ResumeSchema | None = None, original_text: str = ""):
        self.resume = resume
        self.original_text = original_text
        self.deficiencies: list[str] = []

    def check_hallucination(self) -> list[str]:
        if self.resume is None:
            return ["No resume was provided."]
        source = self.original_text.casefold()
        issues: list[str] = []
        for job in self.resume.work_experiences:
            if job.company_name and job.company_name.casefold() not in source:
                issues.append(f"Company '{job.company_name}' was not found in source text.")
        for education in self.resume.educations:
            if (
                education.institution_name
                and education.institution_name.casefold() not in source
            ):
                issues.append(
                    f"Institution '{education.institution_name}' was not found in source text."
                )
        return issues

    def identify_missing_fields(self) -> list[str]:
        if self.resume is None:
            return ["No resume was provided."]
        missing: list[str] = []
        if not (
            self.resume.personal_info.full_name
            or (
                self.resume.personal_info.first_name
                and self.resume.personal_info.last_name
            )
        ):
            missing.append("Full name is incomplete.")
        for job in self.resume.work_experiences:
            if not job.start_date and not job.start_date_raw:
                missing.append(f"Start date is missing for '{job.job_title or 'work experience'}'.")
            if not job.description and not job.achievements:
                missing.append(f"Description or achievements are missing for '{job.job_title or 'work experience'}'.")
        for skill in self.resume.skills:
            if not skill.level:
                missing.append(f"Proficiency level is missing for skill '{skill.name}'.")
        if self.resume.contact_info.email is None and self.resume.contact_info.phone is None:
            missing.append("At least one contact method is missing.")
        return missing

    def calculate_coverage_score(self) -> float:
        if self.resume is None:
            return 0.0
        checks = [
            (10, bool(self.resume.personal_info.full_name or self.resume.personal_info.first_name)),
            (15, bool(self.resume.contact_info.email or self.resume.contact_info.phone)),
            (30, any(j.company_name and j.job_title and (j.start_date or j.start_date_raw) for j in self.resume.work_experiences)),
            (15, bool(self.resume.educations)),
            (15, bool(self.resume.skills)),
            (10, bool(self.resume.professional_summary)),
            (5, bool(self.resume.projects or self.resume.certificates)),
        ]
        return float(sum(weight for weight, present in checks if present))

    def run_analysis(self) -> dict[str, object]:
        hallucinations = self.check_hallucination()
        missing = self.identify_missing_fields()
        self.deficiencies = hallucinations + missing
        return {
            "coverage_score": self.calculate_coverage_score(),
            "is_valid": not hallucinations,
            "deficiencies": self.deficiencies,
            "suggestions": [f"Complete or verify: {item}" for item in self.deficiencies],
        }

    def analyze(
        self,
        resume: ResumeSchema | dict | None = None,
        original_text: str | None = None,
    ) -> dict[str, object]:
        if resume is not None:
            self.resume = resume if isinstance(resume, ResumeSchema) else ResumeSchema.model_validate(resume)
        if original_text is not None:
            self.original_text = original_text
        return self.run_analysis()
