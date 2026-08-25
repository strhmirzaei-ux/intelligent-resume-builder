from __future__ import annotations

from app.schemas.resume import ResumeSchema


class GapAnalyzer:
    def __init__(self, resume: ResumeSchema | None = None, original_text: str = ""):
        self.resume = resume
        self.original_text = original_text
        self.deficiencies: list[str] = []

    def check_hallucination(self) -> list[str]:
        if self.resume is None:
            return ["رزومه‌ای برای بررسی ارائه نشده است."]
        source = self.original_text.casefold()
        issues: list[str] = []
        for job in self.resume.work_experiences:
            if job.company_name and job.company_name.casefold() not in source:
                issues.append(
                    f"نام شرکت «{job.company_name}» در متن اولیه پیدا نشد و باید تأیید شود."
                )
        for education in self.resume.educations:
            if education.institution_name and education.institution_name.casefold() not in source:
                issues.append(
                    f"نام مؤسسه یا دانشگاه «{education.institution_name}» در متن اولیه پیدا نشد "
                    "و باید تأیید شود."
                )
        return issues

    def identify_missing_fields(self) -> list[str]:
        if self.resume is None:
            return ["رزومه‌ای برای بررسی ارائه نشده است."]
        missing: list[str] = []
        if not (
            self.resume.personal_info.full_name
            or (
                self.resume.personal_info.first_name
                and self.resume.personal_info.last_name
            )
        ):
            missing.append("نام و نام خانوادگی کامل نیست.")
        for job in self.resume.work_experiences:
            title = job.job_title or "این سابقه کاری"
            if not job.start_date and not job.start_date_raw:
                missing.append(f"تاریخ شروع «{title}» مشخص نشده است.")
            if not job.description and not job.achievements:
                missing.append(f"توضیحات یا دستاوردهای «{title}» مشخص نشده است.")
        for skill in self.resume.skills:
            if not skill.level:
                missing.append(f"سطح تسلط بر مهارت «{skill.name}» مشخص نشده است.")
        if self.resume.contact_info.email is None and self.resume.contact_info.phone is None:
            missing.append("حداقل یکی از راه‌های تماس، مانند ایمیل یا شماره تلفن، لازم است.")
        return missing

    def calculate_coverage_score(self) -> float:
        if self.resume is None:
            return 0.0
        checks = [
            (10, bool(self.resume.personal_info.full_name or self.resume.personal_info.first_name)),
            (15, bool(self.resume.contact_info.email or self.resume.contact_info.phone)),
            (
                30,
                any(
                    j.company_name
                    and j.job_title
                    and (j.start_date or j.start_date_raw)
                    for j in self.resume.work_experiences
                ),
            ),
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
            "suggestions": [f"لطفاً تکمیل یا بررسی کنید: {item}" for item in self.deficiencies],
        }

    def analyze(
        self,
        resume: ResumeSchema | dict | None = None,
        original_text: str | None = None,
    ) -> dict[str, object]:
        if resume is not None:
            self.resume = (
                resume if isinstance(resume, ResumeSchema) else ResumeSchema.model_validate(resume)
            )
        if original_text is not None:
            self.original_text = original_text
        return self.run_analysis()
