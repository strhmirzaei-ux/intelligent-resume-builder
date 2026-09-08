from pathlib import Path

from app.schemas.resume import ResumeSchema
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore


class SequenceExtractor:
    def __init__(self, resumes):
        self.resumes = iter(resumes)

    def extract(self, text):
        return ResumeSchema.model_validate(next(self.resumes))


def test_work_experience_is_completed_across_messages(tmp_path: Path):
    extractor = SequenceExtractor(
        [
            {"work_experiences": [{"company_name": "شرکت نمونه", "duration": "سه سال"}]},
            {"work_experiences": [{"job_title": "برنامه‌نویس پایتون"}]},
        ]
    )
    service = ResumePipelineService(extractor, JsonStore(str(tmp_path)))

    first = service.process("سه سال در شرکت نمونه کار کردم")
    second = service.process("عنوان شغلی من برنامه‌نویس پایتون بود", first["resume_id"])

    work = second["resume"]["work_experiences"]
    assert len(work) == 1
    assert work[0]["company_name"] == "شرکت نمونه"
    assert work[0]["duration"] == "سه سال"
    assert work[0]["job_title"] == "برنامه‌نویس پایتون"
    assert not any("نام شرکت" in item or "مدت" in item for item in second["analysis"]["deficiencies"])


def test_merge_does_not_overwrite_previous_experience_fields():
    merged = ResumePipelineService.merge(
        {"work_experiences": [{"company_name": "A", "duration": "2 years"}]},
        {"work_experiences": [{"job_title": "Engineer"}]},
    )
    assert merged == {
        "work_experiences": [
            {"company_name": "A", "duration": "2 years", "job_title": "Engineer"}
        ]
    }
