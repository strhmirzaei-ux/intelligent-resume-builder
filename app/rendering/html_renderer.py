from __future__ import annotations

from html import escape
from typing import Any


class HtmlResumeRenderer:
    def render(self, resume: dict[str, Any]) -> str:
        personal = resume.get("personal_info", {})
        name = escape(
            personal.get("full_name")
            or " ".join(
                value for value in [personal.get("first_name"), personal.get("last_name")]
                if value
            )
            or "Resume"
        )
        summary = escape(resume.get("professional_summary") or "")
        skills = "".join(
            f"<li>{escape(str(skill.get('name', '')))}"
            f"{' — ' + escape(str(skill.get('level'))) if skill.get('level') else ''}</li>"
            for skill in resume.get("skills", [])
        )
        experiences = "".join(
            "<article>"
            f"<h3>{escape(str(item.get('job_title') or ''))}</h3>"
            f"<p>{escape(str(item.get('company_name') or ''))}</p>"
            f"<p>{escape(str(item.get('description') or ''))}</p>"
            "</article>"
            for item in resume.get("work_experiences", [])
        )
        return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><title>{name}</title>
<style>
body {{ font-family: Vazirmatn, Tahoma, sans-serif; max-width: 900px; margin: 2rem auto; line-height: 1.8; }}
h1 {{ color: #17324d; }} h2 {{ border-bottom: 1px solid #ddd; padding-bottom: .3rem; }}
article {{ margin-bottom: 1rem; }} li {{ margin: .25rem 0; }}
</style></head>
<body><h1>{name}</h1>
<section><h2>خلاصه حرفه‌ای</h2><p>{summary}</p></section>
<section><h2>مهارت‌ها</h2><ul>{skills}</ul></section>
<section><h2>سوابق کاری</h2>{experiences}</section>
</body></html>"""
