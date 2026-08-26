from __future__ import annotations

from typing import Any, Callable

from app.modules.gap_analysis.rules import NODE_LABELS, NODE_WEIGHTS
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
            if (
                education.institution_name
                and education.institution_name.casefold() not in source
            ):
                issues.append(
                    f"نام مؤسسه یا دانشگاه «{education.institution_name}» در متن اولیه "
                    "پیدا نشد و باید تأیید شود."
                )
        return issues

    @staticmethod
    def _has(value: Any) -> bool:
        if value is None or value is False:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict, set)):
            return bool(value)
        return True

    def _node_gaps(
        self,
        node_key: str,
        checks: list[tuple[str, str, Callable[[], bool]]],
    ) -> tuple[dict[str, Any], list[str]]:
        missing = [message for _, message, check in checks if not check()]
        filled = len(checks) - len(missing)
        score = round((filled / len(checks)) * 100, 2) if checks else 100.0
        return (
            {
                "label": NODE_LABELS[node_key],
                "weight": NODE_WEIGHTS[node_key],
                "score": score,
                "filled_fields": filled,
                "total_fields": len(checks),
                "missing_fields": missing,
            },
            missing,
        )

    def _graph_analysis(self) -> tuple[dict[str, Any], list[str]]:
        if self.resume is None:
            return {}, ["رزومه‌ای برای بررسی ارائه نشده است."]
        resume = self.resume
        personal_checks = [
            (
                "name",
                "نام و نام خانوادگی کامل نیست.",
                lambda: self._has(resume.personal_info.full_name)
                or (
                    self._has(resume.personal_info.first_name)
                    and self._has(resume.personal_info.last_name)
                ),
            ),
            (
                "location",
                "محل سکونت مشخص نشده است.",
                lambda: self._has(
                    resume.contact_info.city or resume.contact_info.country
                ),
            ),
            (
                "contact",
                "حداقل یکی از ایمیل یا شماره تلفن لازم است.",
                lambda: self._has(resume.contact_info.email)
                or self._has(resume.contact_info.phone),
            ),
            (
                "links",
                "لینک LinkedIn، GitHub یا وب‌سایت مشخص نشده است.",
                lambda: self._has(resume.contact_info.linkedin)
                or self._has(resume.contact_info.github)
                or self._has(resume.contact_info.website),
            ),
            (
                "summary",
                "خلاصه حرفه‌ای، نقاط قوت یا هدف شغلی وارد نشده است.",
                lambda: self._has(resume.professional_summary)
                or self._has(resume.key_strengths)
                or self._has(resume.career_objective),
            ),
            (
                "additional",
                "اطلاعات تکمیلی مانند زبان‌ها، گواهی‌نامه‌ها یا علایق وارد نشده است.",
                lambda: self._has(resume.languages)
                or self._has(resume.certificates)
                or self._has(resume.interests),
            ),
        ]
        education_checks = [
            (
                "degrees",
                "مدرک تحصیلی، رشته و نام دانشگاه یا مؤسسه آموزشی مشخص نشده است.",
                lambda: any(
                    self._has(item.institution_name) and self._has(item.degree)
                    for item in resume.educations
                ),
            ),
            (
                "courses",
                "دوره‌های مرتبط یا دروس مهم وارد نشده است.",
                lambda: any(item.relevant_courses for item in resume.educations),
            ),
            (
                "academic_projects",
                "پروژه‌های دانشگاهی یا دستاوردهای آموزشی وارد نشده است.",
                lambda: any(
                    item.academic_projects or item.achievements
                    for item in resume.educations
                ),
            ),
        ]
        work_checks = [
            (
                "experiences",
                "حداقل یک سابقه کاری با نام شرکت و عنوان شغلی لازم است.",
                lambda: any(
                    self._has(item.company_name) and self._has(item.job_title)
                    for item in resume.work_experiences
                )
                or any(
                    self._has(item.company_name) and self._has(item.role)
                    for item in resume.internships
                ),
            ),
            (
                "duration",
                "تاریخ یا مدت هر سابقه کاری مشخص نشده است.",
                lambda: any(
                    item.start_date
                    or item.start_date_raw
                    or item.end_date
                    or item.end_date_raw
                    for item in resume.work_experiences
                )
                or any(self._has(item.duration) for item in resume.internships),
            ),
            (
                "responsibilities",
                "مسئولیت‌ها و وظایف سابقه کاری وارد نشده است.",
                lambda: any(
                    item.description or item.key_responsibilities
                    for item in resume.work_experiences
                )
                or any(item.responsibilities for item in resume.internships),
            ),
            (
                "achievements",
                "دستاوردهای قابل اندازه‌گیری سابقه کاری وارد نشده است.",
                lambda: any(item.achievements for item in resume.work_experiences)
                or any(item.key_learnings for item in resume.internships),
            ),
        ]
        project_checks = [
            (
                "projects",
                "حداقل یک پروژه یا نمونه‌کار با عنوان لازم است.",
                lambda: any(self._has(item.name) for item in resume.projects),
            ),
            (
                "details",
                "مسئله، نقش، فناوری‌ها یا قابلیت‌های پروژه‌ها مشخص نشده است.",
                lambda: any(
                    item.problem_statement
                    or item.role
                    or item.tech_stack
                    or item.key_features
                    for item in resume.projects
                ),
            ),
            (
                "outcomes",
                "نتایج پروژه یا لینک GitHub و Demo وارد نشده است.",
                lambda: any(item.outcomes or item.url for item in resume.projects),
            ),
            (
                "other_projects",
                "پروژه‌های شخصی، متن‌باز یا کوچک‌تر وارد نشده است.",
                lambda: self._has(resume.other_projects),
            ),
        ]
        skill_checks = [
            (
                "technical",
                "مهارت‌های فنی و تخصصی وارد نشده است.",
                lambda: self._has(resume.skills),
            ),
            (
                "levels",
                "سطح تسلط مهارت‌های فنی مشخص نشده است.",
                lambda: bool(resume.skills)
                and all(self._has(item.level) for item in resume.skills),
            ),
            (
                "tools",
                "ابزارها و پلتفرم‌های مورد استفاده وارد نشده‌اند.",
                lambda: self._has(resume.tools_platforms),
            ),
            (
                "languages",
                "زبان‌های برنامه‌نویسی، فریم‌ورک‌ها یا کتابخانه‌های تخصصی مشخص نشده‌اند.",
                lambda: self._has(resume.tools_platforms) or len(resume.skills) >= 2,
            ),
        ]
        nodes: dict[str, dict[str, Any]] = {}
        all_missing: list[str] = []
        for node_key, checks in (
            ("personal_info", personal_checks),
            ("education", education_checks),
            ("work_experience", work_checks),
            ("projects", project_checks),
            ("interactive_skills", skill_checks),
        ):
            node, missing = self._node_gaps(node_key, checks)
            nodes[node_key] = node
            all_missing.extend(missing)

        total_weight = sum(NODE_WEIGHTS.values())
        weighted_score = sum(
            node["score"] * NODE_WEIGHTS[key] for key, node in nodes.items()
        ) / (100 * total_weight) * 100
        graph = {
            "nodes": nodes,
            "weights": NODE_WEIGHTS,
            "weighted_score": round(weighted_score, 2),
            "structure": resume.to_graph().model_dump(mode="json"),
        }
        return graph, list(dict.fromkeys(all_missing))

    def identify_missing_fields(self) -> list[str]:
        _, missing = self._graph_analysis()
        return missing

    def calculate_coverage_score(self) -> float:
        graph, _ = self._graph_analysis()
        return float(graph.get("weighted_score", 0.0))

    def run_analysis(self) -> dict[str, object]:
        hallucinations = self.check_hallucination()
        graph, missing = self._graph_analysis()
        self.deficiencies = list(dict.fromkeys(hallucinations + missing))
        return {
            "coverage_score": float(graph.get("weighted_score", 0.0)),
            "is_valid": not hallucinations,
            "deficiencies": self.deficiencies,
            "suggestions": [
                f"لطفاً تکمیل یا بررسی کنید: {item}" for item in self.deficiencies
            ],
            "graph": graph,
        }

    def analyze(
        self,
        resume: ResumeSchema | dict | None = None,
        original_text: str | None = None,
    ) -> dict[str, object]:
        if resume is not None:
            self.resume = (
                resume
                if isinstance(resume, ResumeSchema)
                else ResumeSchema.model_validate(resume)
            )
        if original_text is not None:
            self.original_text = original_text
        return self.run_analysis()
