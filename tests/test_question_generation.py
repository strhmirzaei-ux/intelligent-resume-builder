from app.modules.question_generation.generator import QuestionGenerator


def test_questions_are_persian_and_priority_sorted():
    questions = QuestionGenerator().generate(["توضیحات پروژه ناقص است", "نام شرکت مشخص نیست"])
    assert questions[0]["priority"] == "high"
    assert "شرکت" in questions[0]["text"]
    assert all("Ø" not in question["text"] for question in questions)
