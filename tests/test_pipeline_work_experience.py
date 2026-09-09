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


def test_merge_attaches_anonymous_followup_to_latest_experience():
    merged = ResumePipelineService.merge(
        {
            "work_experiences": [
                {"company_name": "شرکت اول", "job_title": "برنامه‌نویس"},
                {"company_name": "شرکت دوم", "job_title": "کارآموز"},
            ]
        },
        {"work_experiences": [{"achievements": ["افزایش سرعت سامانه"]}]},
    )
    assert len(merged["work_experiences"]) == 2
    assert merged["work_experiences"][-1]["achievements"] == ["افزایش سرعت سامانه"]


def test_session_keeps_one_id_and_records_user_and_assistant_messages(tmp_path: Path):
    extractor = SequenceExtractor(
        [{"work_experiences": [{"company_name": "شرکت نمونه", "job_title": "مدیر"}]}]
    )
    service = ResumePipelineService(extractor, JsonStore(str(tmp_path)))
    record = service.process("در شرکت نمونه مدیر بودم")
    stored = JsonStore(str(tmp_path)).get(record["resume_id"])

    assert stored is not None
    assert stored["resume_id"] == record["resume_id"]
    assert [message["role"] for message in stored["messages"]] == ["user", "assistant"]
    assert stored["messages"][0]["content"] == "در شرکت نمونه مدیر بودم"
    assert stored["messages"][1]["content"] == stored["next_question"]
