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
def test_parser_accepts_thinking_fence_and_trailing_comma():
    output = (
        '<think>I should return only the extracted fields.</think>\n'
        '```json\n{"personal_info":{"full_name":"Ali",},}\n```'
    )
    result = ResumeLLMExtractor(FakeLLM(output), max_retries=0).extract("Ali")
    assert result.personal_info.full_name == "Ali"


def test_parser_accepts_bare_keys_from_python_style_output():
    output = '{"personal_info": {full_name: "Ali"}}'
    result = ResumeLLMExtractor(FakeLLM(output), max_retries=0).extract("Ali")
    assert result.personal_info.full_name == "Ali"


def test_normalizes_flat_skill_object():
    output = (
        '{"name":"Python","level":null,"status":"unverified",'
        '"confidence":null,"evidence":["Python"]}'
    )
    result = ResumeLLMExtractor(FakeLLM(output), max_retries=0).extract("Python")
    assert result.skills[0].name == "Python"
    assert result.skills[0].evidence[0].source_text == "Python"


def test_normalizes_model_status_evidence_and_raw_dates():
    output = {
        "personal_info": {
            "full_name": "Ali",
            "status": "verified",
            "evidence": ["Ali"],
        },
        "contact_info": "شماره تماس 09120000000",
        "work_experiences": [
            {
                "company_name": "Example",
                "start_date_raw": "سه سال کار کردم",
                "status": "verified",
                "evidence": ["سه سال کار کردم"],
            }
        ],
    }
    import json

    result = ResumeLLMExtractor(
        FakeLLM(json.dumps(output, ensure_ascii=False)),
        max_retries=0,
    ).extract("Ali")
    assert result.personal_info.status.value == "confirmed"
    assert result.personal_info.evidence[0].source_text == "Ali"
    assert result.contact_info.evidence[0].source_text == "شماره تماس 09120000000"
    assert result.work_experiences[0].start_date_raw.raw_value == "سه سال کار کردم"
