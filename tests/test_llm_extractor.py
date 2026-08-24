import pytest

from app.modules.extraction.llm_extractor import (
    LLMExtractionError,
    ResumeLLMExtractor,
)


class FakeLLM:
    def __init__(self, outputs):
        self.outputs = iter(outputs if isinstance(outputs, list) else [outputs])

    def invoke(self, prompt):
        return next(self.outputs)


def test_extract_valid_json():
    llm = FakeLLM(
        '{"personal_info":{"first_name":"علی","last_name":"احمدی"}}'
    )
    result = ResumeLLMExtractor(llm=llm, max_retries=0).extract("متن نمونه")
    assert result.personal_info.first_name == "علی"


def test_extract_invalid_json_raises():
    extractor = ResumeLLMExtractor(llm=FakeLLM("not json"), max_retries=0)
    with pytest.raises(LLMExtractionError):
        extractor.extract("متن نمونه")


def test_extract_retries_after_invalid_response():
    llm = FakeLLM(
        [
            "not json",
            '{"personal_info":{"full_name":"علی احمدی"}}',
        ]
    )
    result = ResumeLLMExtractor(llm=llm, max_retries=1).extract("متن نمونه")
    assert result.personal_info.full_name == "علی احمدی"


def test_extractor_rejects_empty_input():
    with pytest.raises(ValueError):
        ResumeLLMExtractor(llm=FakeLLM("{}")).extract(" ")
