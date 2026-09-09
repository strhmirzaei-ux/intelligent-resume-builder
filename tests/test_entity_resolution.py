from app.integrations.embedding_service import EmbeddingService
from app.services.entity_resolution import EntityResolver


class KeywordEmbedding:
    def __init__(self):
        self.vectors = {
            "acme python api": [1.0, 0.0],
            "acme backend python api": [1.0, 0.0],
            "other design mobile": [0.0, 1.0],
        }

    def embed(self, text):
        if "python" in text.lower() or "api" in text.lower():
            return [1.0, 0.0]
        return self.vectors.get(text)

    @staticmethod
    def cosine_similarity(left, right):
        return EmbeddingService.cosine_similarity(self=None, left=left, right=right)


def test_entity_resolver_prefers_exact_company_or_title():
    resolver = EntityResolver(KeywordEmbedding(), threshold=0.7)
    result = resolver.find_work_experience_match(
        [{"company_name": "Acme", "job_title": "Backend Engineer"}],
        {"company_name": "Acme", "description": "ساخت API"},
    )

    assert result.index == 0
    assert result.reason.startswith("exact:")


def test_entity_resolver_uses_embedding_for_paraphrased_details():
    resolver = EntityResolver(KeywordEmbedding(), threshold=0.7)
    result = resolver.find_work_experience_match(
        [{"company_name": "Acme", "job_title": "Backend", "description": "python api"}],
        {"company_name": "Acme Labs", "job_title": "Backend Python", "description": "api"},
    )

    assert result.index == 0


def test_named_unrelated_experience_is_not_attached_to_latest():
    resolver = EntityResolver(KeywordEmbedding(), threshold=0.7)
    result = resolver.find_work_experience_match(
        [{"company_name": "Acme", "job_title": "Engineer"}],
        {"company_name": "Other", "job_title": "Designer"},
    )

    assert result.index is None


def test_detail_only_experience_attaches_to_latest():
    resolver = EntityResolver(KeywordEmbedding(), threshold=0.7)
    result = resolver.find_work_experience_match(
        [{"company_name": "First"}, {"company_name": "Latest"}],
        {"achievements": ["افزایش سرعت"]},
    )

    assert result.index == 1
