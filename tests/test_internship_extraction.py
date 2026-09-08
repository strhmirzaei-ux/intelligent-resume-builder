from app.modules.extraction.llm_extractor import ResumeLLMExtractor


class FakeLLM:
    def invoke(self, prompt):
        return (
            '{"internships":[{"company_name":"شرکت نمونه",'
            '"key_responsibilities":"هماهنگی تیم",'
            '"accomplishments":"یادگیری فرایندها"}]}'
        )


def test_internship_aliases_use_internship_schema_fields():
    result = ResumeLLMExtractor(FakeLLM(), max_retries=0).extract("شرکت نمونه")
    internship = result.internships[0]
    assert internship.responsibilities == ["هماهنگی تیم"]
    assert internship.key_learnings == ["یادگیری فرایندها"]
