from app.modules.gap_analysis.analyzer import GapAnalyzer
from app.modules.gap_analysis.rules import NODE_WEIGHTS
from app.schemas.resume import ResumeSchema


def test_gap_analysis_uses_weighted_five_node_graph():
    resume = ResumeSchema(
        personal_info={"full_name": "علی احمدی"},
        contact_info={"email": "ali@example.com"},
        work_experiences=[
            {"company_name": "شرکت الف", "job_title": "برنامه‌نویس"}
        ],
        skills=[{"name": "Python"}],
    )
    result = GapAnalyzer(
        resume, "علی احمدی در شرکت الف کار می‌کند"
    ).run_analysis()
    assert 0 < result["coverage_score"] < 100
    assert result["graph"]["weights"] == NODE_WEIGHTS
    assert set(result["graph"]["nodes"]) == {
        "personal_info",
        "interactive_skills",
        "projects",
        "education",
        "work_experience",
    }
    assert any("مدت" in item or "تاریخ" in item for item in result["deficiencies"])
    assert result["is_valid"] is True


def test_graph_contains_all_requested_sections():
    resume = ResumeSchema(
        personal_info={"full_name": "علی احمدی"},
        contact_info={"city": "تهران", "phone": "09120000000"},
        professional_summary="توسعه‌دهنده",
        skills=[{"name": "Python", "level": "senior"}],
        tools_platforms=["Docker"],
        educations=[
            {
                "institution_name": "دانشگاه تهران",
                "degree": "لیسانس",
                "relevant_courses": ["داده"],
                "academic_projects": ["سامانه"],
            }
        ],
        projects=[
            {
                "name": "سامانه",
                "problem_statement": "حل مشکل",
                "tech_stack": ["Python"],
                "outcomes": ["استقرار"],
            }
        ],
    )
    analysis = GapAnalyzer(resume, "علی احمدی").run_analysis()
    graph = analysis["graph"]["structure"]
    assert set(graph) == {
        "personal_info",
        "education",
        "work_experience",
        "projects",
        "interactive_skills",
    }
    assert analysis["graph"]["nodes"]["interactive_skills"]["weight"] == 4


def test_gap_analysis_detects_unverified_company():
    resume = ResumeSchema(
        work_experiences=[{"company_name": "شرکت خیالی", "job_title": "مدیر"}]
    )
    result = GapAnalyzer(resume, "من مدیر هستم").run_analysis()
    assert result["is_valid"] is False
    assert any("شرکت خیالی" in item for item in result["deficiencies"])
