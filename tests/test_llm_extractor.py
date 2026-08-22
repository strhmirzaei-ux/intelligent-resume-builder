import pytest

from app.modules.extraction.llm_extractor import LLMExtractionError, ResumeLLMExtractor


class FakeLLM:
    def __init__(self, outputs):
        self.outputs = iter(outputs if isinstance(outputs, list) else [outputs])

    def invoke(self, prompt):
        return next(self.outputs)


def test_valid_json_is_validated():
    result = ResumeLLMExtractor(
        FakeLLM('{"personal_info":{"full_name":"علی احمدی"}}'),
        max_retries=0,
    ).extract("من علی احمدی هستم")
    assert result.personal_info.full_name == "علی احمدی"


def test_invalid_json_and_empty_input_fail_safely():
    with pytest.raises(LLMExtractionError):
        ResumeLLMExtractor(FakeLLM("not json"), max_retries=0).extract("متن")
    with pytest.raises(ValueError):
        ResumeLLMExtractor(FakeLLM("{}")).extract(" ")


def test_retry_recovers_from_invalid_first_response():
    result = ResumeLLMExtractor(
        FakeLLM(["not json", '{"personal_info":{"full_name":"علی احمدی"}}']),
        max_retries=1,
    ).extract("من علی احمدی هستم")
    assert result.personal_info.full_name == "علی احمدی"
