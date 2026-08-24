from app.modules.gap_analysis.analyzer import GapAnalyzer
from app.schemas.resume import ResumeSchema


def test_gap_analyzer_uses_schema_field_names():
    resume = ResumeSchema(
        personal_info=[{
            "first_name" : "علی"
           } ],
        work_experiences=[{
                "company_name": "شرکت الف",
                "job_title": "برنامه‌نویس",
                "description": "توسعه سامانه داخلی",
                         }],
        skills=[{
                "name": "Python"
                }],
    )
    result = GapAnalyzer(resume, "علی در شرکت الف کار می‌کند").run_analysis()
    assert result["coverage_score"] == 20
    assert any("تاریخ شروع" in item for item in result["deficiencies"])
    assert any("سطح تسلط" in item for item in result["deficiencies"])


def test_gap_analyzer_flags_unverified_company():
    resume = ResumeSchema(
        work_experiences=[{
            "company_name": "شرکت خیالی", "job_title": "مدیر"
        }]
    )
    result = GapAnalyzer(resume, "من مدیر هستم").run_analysis()
    assert result["is_valid"] is False
    assert any("شرکت خیالی" in item for item in result["deficiencies"])
