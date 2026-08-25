from app.modules.question_generation.generator import QuestionGenerator


def test_english_gap_is_never_shown_to_user():
    questions = QuestionGenerator().generate(
        ["Description or achievements are missing for 'work experience'."]
    )
    text = questions[0]["text"]
    assert "لطفاً" in text
    assert "Description" not in text
    assert "work experience" not in text


def test_persian_gap_asks_for_work_details():
    questions = QuestionGenerator().generate(["توضیحات یا دستاوردهای این سابقه کاری مشخص نیست."])
    assert "وظایف" in questions[0]["text"]
    assert "دستاوردها" in questions[0]["text"]
