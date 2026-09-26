from app.rendering.resume_content import (
    date_range,
    date_text,
    full_name,
    has_value,
    is_ltr_text,
    project_items,
    record_title,
    section_items,
    text,
)


def test_text_filters_empty_list_values():
    assert text([None, "", "Python", [], " "]) == "Python"


def test_text_reads_raw_date_and_preserves_jalali_value():
    assert date_text({"raw_value": "۱۴۰۲/۰۱/۰۱", "calendar": "jalali"}) == "۱۴۰۲/۰۱/۰۱"
    assert date_text({"raw_value": "۱۴۰۲", "is_approximate": True}) == "۱۴۰۲ (تقریبی)"


def test_has_value_ignores_metadata_only_evidence():
    assert not has_value({"status": "confirmed", "confidence": 0.9, "evidence": []})
    assert has_value({"status": "confirmed", "evidence": [], "name": "Python"})


def test_section_items_removes_empty_records():
    resume = {"skills": [{"status": "missing", "evidence": []}, {"name": "Python"}]}
    assert section_items(resume, "skills") == [{"name": "Python"}]


def test_project_items_combines_both_project_sections():
    resume = {"projects": [{"name": "Main"}], "other_projects": [{"name": "Side"}]}
    assert [item["name"] for item in project_items(resume)] == ["Main", "Side"]


def test_date_range_keeps_duration_and_precise_jalali_range():
    item = {
        "duration": "دو سال",
        "start_date_raw": {"raw_value": "۱۴۰۱/۰۱/۰۱", "calendar": "jalali"},
        "end_date_raw": {"raw_value": "۱۴۰۳/۰۱/۰۱", "calendar": "jalali"},
    }
    result = date_range(item)
    assert result == "دو سال | ۱۴۰۱/۰۱/۰۱ - ۱۴۰۳/۰۱/۰۱"


def test_full_name_ignores_whitespace_only_parts():
    assert full_name({"personal_info": {"first_name": " علی ", "last_name": "   "}}) == "علی"
    assert full_name({"personal_info": {"first_name": " ", "last_name": " احمدی "}}) == "احمدی"
    assert full_name({"personal_info": {"first_name": " ", "last_name": " "}}) == "رزومه"


def test_shared_title_and_ltr_detection_helpers():
    assert record_title([None, "", "Backend", "Engineer"]) == "Backend | Engineer"
    assert is_ltr_text("https://example.com")
    assert is_ltr_text("ali@example.com")
    assert is_ltr_text("Python")
    assert is_ltr_text("09121234567")
    assert not is_ltr_text("برنامه‌نویس")
