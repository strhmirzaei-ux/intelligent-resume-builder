import pytest

from app.modules.extraction.llm_extractor import ResumeLLMExtractor


class FakeLLM:
    def __init__(self, output):
        self.output = output

    def invoke(self, prompt):
        return self.output


    def test_extract_valid_json():
        llm = FakeLLM("""
        {
        "personal_info": {
        "first_name": "علی",
        "last_name": "احمدی"}
        }
        """)
        extractor = ResumeLLMExtractor(llm=llm, max_retries=0)
        result = extractor.extract("متن نمونه")
        assert result is not None


    def test_extract_invalid_json_raises():
        llm = FakeLLM("not json")
        extractor = ResumeLLMExtractor(llm=llm, max_retries=0)

        with pytest.raises(Exception):
            extractor.extract("متن نمونه")
