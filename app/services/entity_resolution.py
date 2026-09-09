from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.integrations.embedding_service import EmbeddingService


@dataclass(frozen=True)
class EntityMatch:
    index: int | None
    score: float
    reason: str


class EntityResolver:
    """Resolve incoming work experience data to an existing resume entity."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        threshold: float = 0.72,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.threshold = threshold

    def find_work_experience_match(
        self, existing: list[dict[str, Any]], incoming: dict[str, Any]
    ) -> EntityMatch:
        if not existing:
            return EntityMatch(None, 0.0, "no_existing_entities")

        incoming_company = self._normalize(incoming.get("company_name"))
        incoming_title = self._normalize(incoming.get("job_title"))
        has_identity = bool(incoming_company or incoming_title)
        best = EntityMatch(None, 0.0, "no_match")

        for index, candidate in enumerate(existing):
            company_exact = bool(
                incoming_company
                and incoming_company == self._normalize(candidate.get("company_name"))
            )
            title_exact = bool(
                incoming_title
                and incoming_title == self._normalize(candidate.get("job_title"))
            )
            if company_exact or title_exact:
                exact_fields = []
                if company_exact:
                    exact_fields.append("company_name")
                if title_exact:
                    exact_fields.append("job_title")
                return EntityMatch(index, 1.0, "exact:" + ",".join(exact_fields))

            score = self._score(incoming, candidate)
            if score > best.score:
                best = EntityMatch(index, score, "embedding_and_text")

        if not has_identity and existing:
            # Detail-only follow-ups are intentionally attached to the latest
            # entity, preserving the existing conversational behavior.
            return EntityMatch(len(existing) - 1, 1.0, "latest_for_detail_only")
        if (
            len(existing) == 1
            and bool(incoming_title)
            and not incoming_company
            and not best.index
        ):
            # A single existing experience plus a title-only extraction is a
            # common follow-up answer. With multiple experiences we require a
            # real match to avoid attaching it to the wrong entity.
            return EntityMatch(0, 0.65, "single_entity_partial_identity")
        if best.index is not None and best.score >= self.threshold:
            return best
        return EntityMatch(None, best.score, best.reason)

    def _score(self, incoming: dict[str, Any], candidate: dict[str, Any]) -> float:
        scores: list[float] = []
        incoming_company = self._normalize(incoming.get("company_name"))
        candidate_company = self._normalize(candidate.get("company_name"))
        incoming_title = self._normalize(incoming.get("job_title"))
        candidate_title = self._normalize(candidate.get("job_title"))
        if incoming_company and candidate_company:
            scores.append(self._field_similarity(incoming_company, candidate_company))
        if incoming_title and candidate_title:
            scores.append(self._field_similarity(incoming_title, candidate_title))

        incoming_text = self._experience_text(incoming)
        candidate_text = self._experience_text(candidate)
        semantic = self.embedding_service.cosine_similarity(
            self.embedding_service.embed(incoming_text),
            self.embedding_service.embed(candidate_text),
        )
        if semantic is not None:
            scores.append(max(0.0, semantic))
        return max(scores, default=0.0)

    def _field_similarity(self, left: str, right: str) -> float:
        if left == right:
            return 1.0
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    @staticmethod
    def _experience_text(value: dict[str, Any]) -> str:
        parts = [value.get("company_name"), value.get("job_title"), value.get("description")]
        for key in ("key_responsibilities", "achievements"):
            items = value.get(key) or []
            if isinstance(items, list):
                parts.extend(items)
        return " ".join(str(part) for part in parts if part).strip()

    @staticmethod
    def _normalize(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return re.sub(r"\s+", " ", value.strip().casefold())
