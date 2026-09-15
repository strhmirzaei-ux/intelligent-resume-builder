from pathlib import Path

from app.integrations.embedding_service import EmbeddingService
from app.schemas.resume import ResumeSchema
from app.services.pipeline_service import ResumePipelineService
from app.storage.json_store import JsonStore


class SequenceExtractor:
    def __init__(self, resumes):
        self.resumes = iter(resumes)

    def extract(self, text):
        return ResumeSchema.model_validate(next(self.resumes))


class SemanticStub:
    """Deterministic local substitute for scenario tests without model downloads."""

    def embed(self, text):
        lowered = text.casefold()
        if any(term in lowered for term in ("python", "api", "backend", "پایتون", "api")):
            return [1.0, 0.0]
        if any(term in lowered for term in ("design", "mobile", "طراحی")):
            return [0.0, 1.0]
        return [0.5, 0.5] if text else None

    @staticmethod
    def cosine_similarity(left, right):
        return EmbeddingService.cosine_similarity(None, left, right)


def service(tmp_path: Path, resumes, embedding=None):
    return ResumePipelineService(
        extractor=SequenceExtractor(resumes),
        store=JsonStore(str(tmp_path)),
        embedding_service=embedding or SemanticStub(),
    )


def test_different_wording_for_responsibilities_merges_into_same_entity(tmp_path: Path):
    pipeline = service(
        tmp_path,
        [
            {"work_experiences": [{"company_name": "Acme", "job_title": "Backend Engineer"}]},
            {
                "work_experiences": [
                    {
                        "company_name": "Acme Labs",
                        "description": "I built APIs and maintained backend services.",
                    }
                ]
            },
        ],
    )

    first = pipeline.process("I worked at Acme as a backend engineer.")
    second = pipeline.process("I handled backend API development.", first["resume_id"])

    experiences = second["resume"]["work_experiences"]
    assert len(experiences) == 1
    assert experiences[0]["company_name"] == "Acme"
    assert "backend" in experiences[0]["description"].casefold()


def test_achievement_without_company_attaches_to_latest_entity(tmp_path: Path):
    pipeline = service(
        tmp_path,
        [
            {
                "work_experiences": [
                    {"company_name": "Acme", "job_title": "Engineer"},
                    {"company_name": "Beta", "job_title": "Developer"},
                ]
            },
            {"work_experiences": [{"achievements": ["Reduced API latency by 40 percent"]}]},
        ],
    )

    first = pipeline.process("I worked at Acme and then Beta.")
    second = pipeline.process("I reduced API latency by 40 percent.", first["resume_id"])

    experiences = second["resume"]["work_experiences"]
    assert len(experiences) == 2
    assert experiences[0]["achievements"] == []
    assert experiences[1]["achievements"] == ["Reduced API latency by 40 percent"]


def test_similar_work_experiences_do_not_merge_without_matching_identity(tmp_path: Path):
    pipeline = service(
        tmp_path,
        [
            {
                "work_experiences": [
                    {"company_name": "Acme", "job_title": "Backend Engineer"},
                    {"company_name": "Beta", "job_title": "Backend Engineer"},
                ]
            },
            {"work_experiences": [{"company_name": "Gamma", "job_title": "Data Analyst"}]},
        ],
    )

    first = pipeline.process("I worked at Acme and Beta as a backend engineer.")
    second = pipeline.process("I also worked at Gamma as a data analyst.", first["resume_id"])

    assert len(second["resume"]["work_experiences"]) == 3


def test_mixed_persian_and_english_identity_is_resolved(tmp_path: Path):
    pipeline = service(
        tmp_path,
        [
            {"work_experiences": [{"company_name": "شرکت Acme", "job_title": "Backend Engineer"}]},
            {"work_experiences": [{"company_name": "شرکت Acme", "job_title": "مهندس Backend"}]},
        ],
    )

    first = pipeline.process("در شرکت Acme به عنوان Backend Engineer کار کردم.")
    second = pipeline.process("در شرکت Acme به عنوان مهندس Backend بودم.", first["resume_id"])

    assert len(second["resume"]["work_experiences"]) == 1


def test_repeated_answer_does_not_create_repeated_question(tmp_path: Path, monkeypatch):
    from app.services import pipeline_service

    class FixedAnalyzer:
        def __init__(self, resume, conversation_text):
            pass

        def run_analysis(self):
            return {
                "deficiencies": ["work experience responsibilities are missing"],
                "deficiency_codes": ["work_experience.responsibilities"],
                "coverage_score": 0.5,
            }

    class FixedQuestions:
        def generate(self, deficiencies):
            return [
                {
                    "text": "Describe your work responsibilities.",
                    "priority": "medium",
                    "source_deficiency": deficiencies[0],
                }
            ] if deficiencies else []

    monkeypatch.setattr(pipeline_service, "GapAnalyzer", FixedAnalyzer)
    pipeline = ResumePipelineService(
        extractor=SequenceExtractor([{}, {}]),
        store=JsonStore(str(tmp_path)),
        question_generator=FixedQuestions(),
        embedding_service=EmbeddingService(enabled=False),
    )

    first = pipeline.process("I managed backend APIs.")
    second = pipeline.process("I managed backend APIs.", first["resume_id"])

    assert first["next_question"] == "Describe your work responsibilities."
    assert second["next_question"] is None
    assert len(second["questions"]) == 1


def test_json_session_survives_service_restart(tmp_path: Path):
    first_pipeline = service(tmp_path, [{"work_experiences": [{"company_name": "Acme"}]}])
    first = first_pipeline.process("I worked at Acme.")

    restarted_pipeline = service(tmp_path, [{"work_experiences": [{"job_title": "Backend Engineer"}]}])
    second = restarted_pipeline.process("My title was Backend Engineer.", first["resume_id"])

    assert second["resume_id"] == first["resume_id"]
    assert len(second["resume"]["work_experiences"]) == 1
    assert second["resume"]["work_experiences"][0]["company_name"] == "Acme"
    assert second["resume"]["work_experiences"][0]["job_title"] == "Backend Engineer"
    persisted = JsonStore(str(tmp_path)).get(first["resume_id"])
    assert persisted is not None
    assert len(persisted["messages"]) >= 2
