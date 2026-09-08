from app.modules.extraction.llm_extractor import ResumeLLMExtractor


class FakeLLM:
    def __init__(self, output):
        self.output = output

    def invoke(self, prompt):
        return self.output


def test_work_responsibility_and_accomplishment_aliases_are_normalized():
    output = (
        '{"work_experiences":[{"company_name":"Example",'
        '"responsibilities":"مدیریت تیم",'
        '"accomplishments":"افزایش بهره‌وری"}]}'
    )
    result = ResumeLLMExtractor(FakeLLM(output), max_retries=0).extract("Example")
    work = result.work_experiences[0]
    assert work.key_responsibilities == ["مدیریت تیم"]
    assert work.achievements == ["افزایش بهره‌وری"]
