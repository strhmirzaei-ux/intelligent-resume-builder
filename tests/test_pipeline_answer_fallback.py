from pathlib import Path

from app.schemas.resume import ResumeSchema
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore


class SequenceExtractor:
    def __init__(self, resumes):
        self.resumes = iter(resumes)

    def extract(self, text):
        return ResumeSchema.model_validate(next(self.resumes))


def test_answer_to_work_details_is_attached_when_model_returns_no_details(tmp_path: Path):
    extractor = SequenceExtractor(
        [
            {"work_experiences": [{"company_name": "شرکت نمونه", "duration": "سه سال", "job_title": "مدیر"}]},
            {"work_experiences": [{"company_name": "شرکت نمونه", "duration": "سه سال", "job_title": "مدیر"}]},
        ]
    )
    service = ResumePipelineService(extractor, JsonStore(str(tmp_path)))
    first = service.process("سه سال در شرکت نمونه به عنوان مدیر کار کردم")
    second = service.process("هماهنگی تیم و توسعه فرایندها را انجام می‌دادم", first["resume_id"])
    work = second["resume"]["work_experiences"][0]
    assert work["key_responsibilities"] == ["هماهنگی تیم و توسعه فرایندها را انجام می‌دادم"]
    assert not any("مسئولیت" in item for item in second["analysis"]["deficiencies"])
