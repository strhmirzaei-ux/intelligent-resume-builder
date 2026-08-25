from app.modules.gap_analysis.analyzer import GapAnalyzer
from app.schemas.resume import ResumeSchema


def test_gap_analysis_and_weighted_coverage():
    resume = ResumeSchema(
        personal_info={"full_name": "علی احمدی"},
        contact_info={"email": "ali@example.com"},
        work_experiences=[
            {"company_name": "شرکت الف", "job_title": "برنامه‌نویس"}
        ],
        skills=[{"name": "Python"}],
    )
    result = GapAnalyzer(resume, "علی احمدی در شرکت الف کار می‌کند").run_analysis()
    assert result["coverage_score"] == 40
    assert any("تاریخ شروع" in item for item in result["deficiencies"])
    assert result["is_valid"] is True


def test_gap_analysis_detects_unverified_company():
    resume = ResumeSchema(
        work_experiences=[{"company_name": "شرکت خیالی", "job_title": "مدیر"}]
    )
    result = GapAnalyzer(resume, "من مدیر هستم").run_analysis()
    assert result["is_valid"] is False
    assert any("شرکت خیالی" in item for item in result["deficiencies"])
