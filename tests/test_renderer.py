from app.rendering.html_renderer import HtmlResumeRenderer


def test_html_renderer_escapes_user_content_and_sets_rtl():
    html = HtmlResumeRenderer().render(
        {
            "personal_info": {"full_name": "<Ali>"},
            "professional_summary": "Summary",
            "skills": [{"name": "Python", "level": "advanced"}],
        }
    )
    assert 'dir="rtl"' in html
    assert "&lt;Ali&gt;" in html
    assert "<Ali>" not in html
