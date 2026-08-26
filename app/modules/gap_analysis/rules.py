NODE_WEIGHTS: dict[str, int] = {
    "personal_info": 1,
    "interactive_skills": 4,
    "projects": 3,
    "education": 2,
    "work_experience": 3,
}

NODE_LABELS: dict[str, str] = {
    "personal_info": "اطلاعات فردی",
    "interactive_skills": "مهارت‌ها و تعامل",
    "projects": "پروژه‌ها",
    "education": "تحصیلات",
    "work_experience": "سابقه کاری",
}

REQUIRED_GAPS = (
    "personal_info",
    "interactive_skills",
    "projects",
    "education",
    "work_experience",
)
