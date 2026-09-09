from pathlib import Path

from app.schemas.resume import ResumeSchema
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore


class SequenceExtractor:
    def __init__(self, resumes):
        self.resumes = iter(resumes)

    def extract(self, text):
        return ResumeSchema.model_validate(next(self.resumes))


def test_legacy_work_question_is_not_repeated(tmp_path: Path):
    extractor = SequenceExtractor(
        [
            {"work_experiences": [{"company_name": "شرکت نمونه", "job_title": "مدیر"}]},
            {"work_experiences": [{"company_name": "شرکت نمونه", "job_title": "مدیر"}]},
        ]
    )
    store = JsonStore(str(tmp_path))
    service = ResumePipelineService(extractor, store)
    first = service.process("در شرکت نمونه مدیر بودم")
    first["next_question"] = "لطفاً وظایف، مسئولیت‌ها و مهم‌ترین دستاوردهای این سابقه کاری را توضیح دهید."
    first["asked_deficiency_codes"] = []
    store.put(first["resume_id"], first)

    second = service.process("هماهنگی تیم و توسعه فرایندها را انجام می‌دادم", first["resume_id"])
    assert "مسئولیت" not in (second["next_question"] or "")


def test_database_style_missing_codes_do_not_repeat_question(tmp_path: Path):
    extractor = SequenceExtractor(
        [
            {"work_experiences": [{"company_name": "شرکت نمونه", "job_title": "مدیر"}]},
            {"work_experiences": [{"company_name": "شرکت نمونه", "job_title": "مدیر"}]},
        ]
    )
    store = JsonStore(str(tmp_path))
    service = ResumePipelineService(extractor, store)
    first = service.process("در شرکت نمونه مدیر بودم")
    first["next_question"] = "لطفاً وظایف، مسئولیت‌ها و مهم‌ترین دستاوردهای این سابقه کاری را توضیح دهید."
    first.pop("asked_deficiency_codes", None)
    store.put(first["resume_id"], first)

    second = service.process("هماهنگی تیم را انجام می‌دادم", first["resume_id"])
    assert "مسئولیت" not in (second["next_question"] or "")
