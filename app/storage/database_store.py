from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.models import (
    ChatMessage,
    ResumeEntity,
    ResumeGraphNode,
    ResumeQuestion,
    ResumeSession,
    ResumeVersion,
)
from app.db.session import Database
from app.integrations.embedding_service import EmbeddingService
from app.integrations.faiss_search import search_rows


class DatabaseStore:
    """Database-backed equivalent of JsonStore.

    The public get/put contract intentionally matches JsonStore so the pipeline
    can switch storage backends without changing API behavior.
    """

    def __init__(
        self,
        url: str,
        auto_create: bool = False,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.database = Database(url, auto_create=auto_create)
        settings = get_settings()
        self.embedding_service = embedding_service or EmbeddingService(
            enabled=settings.embedding_enabled,
            model_name=settings.embedding_model_name,
        )

    def get(self, key: str, max_age_seconds: int | None = None) -> dict[str, Any] | None:
        with self.database.session() as session:
            resume_session = session.get(ResumeSession, key)
            if resume_session is None:
                return None
            updated_at = resume_session.updated_at
            if (
                max_age_seconds is not None
                and updated_at is not None
                and (datetime.now(UTC) - updated_at).total_seconds() > max_age_seconds
            ):
                session.delete(resume_session)
                session.commit()
                return None

            version = session.scalars(
                select(ResumeVersion)
                .where(ResumeVersion.session_id == key)
                .order_by(ResumeVersion.version_number.desc())
                .limit(1)
            ).first()
            if version is None:
                return None
            messages = session.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == key)
                .order_by(ChatMessage.created_at)
            ).all()
            return {
                "resume_id": key,
                "raw_text": resume_session.raw_text,
                "normalized_text": resume_session.normalized_text,
                "resume": version.resume_data,
                "analysis": version.analysis_data,
                "asked_deficiencies": resume_session.asked_deficiencies or [],
                "asked_deficiency_codes": resume_session.asked_deficiency_codes or [],
                "next_question": resume_session.next_question,
                "conversation_summary": resume_session.conversation_summary or "",
                "suppressed_facts": resume_session.suppressed_facts or [],
                "operation_history": resume_session.operation_history or [],
                "questions": [
                    {
                        "text": question.question_text,
                        "question_text": question.question_text,
                        "question_code": question.question_code,
                        "embedding": question.embedding,
                        "answered": question.answered,
                    }
                    for question in session.scalars(
                        select(ResumeQuestion)
                        .where(ResumeQuestion.session_id == key)
                        .order_by(ResumeQuestion.created_at)
                    ).all()
                ],
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in messages
                ],
                "updated_at": updated_at.isoformat() if updated_at else None,
            }

    def put(self, key: str, value: dict[str, Any]) -> None:
        with self.database.session() as session:
            resume_session = session.get(ResumeSession, key)
            if resume_session is None:
                resume_session = ResumeSession(id=key)
                session.add(resume_session)
            resume_session.raw_text = value.get("raw_text", "")
            resume_session.normalized_text = value.get("normalized_text", "")
            resume_session.asked_deficiencies = value.get("asked_deficiencies", [])
            resume_session.asked_deficiency_codes = value.get("asked_deficiency_codes", [])
            resume_session.next_question = value.get("next_question")
            resume_session.conversation_summary = value.get("conversation_summary", "")
            resume_session.suppressed_facts = value.get("suppressed_facts", [])
            resume_session.operation_history = value.get("operation_history", [])

            version_number = (
                session.scalar(
                    select(ResumeVersion.version_number)
                    .where(ResumeVersion.session_id == key)
                    .order_by(ResumeVersion.version_number.desc())
                    .limit(1)
                )
                or 0
            ) + 1
            analysis = value.get("analysis", {})
            version = ResumeVersion(
                session_id=key,
                version_number=version_number,
                resume_data=value.get("resume", {}),
                analysis_data=analysis,
                coverage_score=float(analysis.get("coverage_score", 0.0)),
            )
            session.add(version)
            session.flush()
            graph = analysis.get("graph", {})
            for node_key, node_data in graph.get("nodes", {}).items():
                session.add(
                    ResumeGraphNode(
                        version_id=version.id,
                        node_key=node_key,
                        label=node_data.get("label", node_key),
                        weight=int(node_data.get("weight", 0)),
                        score=float(node_data.get("score", 0.0)),
                        filled_fields=int(node_data.get("filled_fields", 0)),
                        total_fields=int(node_data.get("total_fields", 0)),
                        missing_fields=node_data.get("missing_fields", []),
                        node_data=graph.get("structure", {}).get(node_key, {}),
                    )
                )

            existing_messages = {
                (message.role, message.content)
                for message in resume_session.messages
            }
            for message in value.get("messages", []):
                pair = (message.get("role", "user"), message.get("content", ""))
                if pair not in existing_messages and pair[1]:
                    session.add(
                        ChatMessage(
                            session_id=key,
                            role=pair[0],
                            content=pair[1],
                            embedding=self.embedding_service.embed(pair[1]),
                        )
                    )

            session.execute(delete(ResumeQuestion).where(ResumeQuestion.session_id == key))
            for question in value.get("questions", []):
                question_text = question.get("question_text") or question.get("text")
                if not question_text:
                    continue
                session.add(
                    ResumeQuestion(
                        session_id=key,
                        question_text=question_text,
                        question_code=question.get("question_code"),
                        embedding=question.get("embedding")
                        or self.embedding_service.embed(question_text),
                        answered=bool(question.get("answered", False)),
                    )
                )

            session.execute(delete(ResumeEntity).where(ResumeEntity.session_id == key))
            for entity_type, entities in self._resume_entities(value.get("resume", {})):
                for index, entity in enumerate(entities):
                    if not isinstance(entity, dict):
                        continue
                    entity_text = self._entity_text(entity)
                    session.add(
                        ResumeEntity(
                            session_id=key,
                            entity_type=entity_type,
                            entity_key=self._entity_key(entity_type, entity, index),
                            entity_data=entity,
                            embedding=self.embedding_service.embed(entity_text),
                        )
                    )
            session.commit()

    @staticmethod
    def _resume_entities(resume: dict[str, Any]):
        for entity_type in ("work_experience", "internship", "education", "project"):
            field = {
                "work_experience": "work_experiences",
                "internship": "internships",
                "education": "educations",
                "project": "projects",
            }[entity_type]
            yield entity_type, resume.get(field, [])

    @staticmethod
    def _entity_text(entity: dict[str, Any]) -> str:
        values: list[str] = []
        for value in entity.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(item) for item in value if isinstance(item, str))
        return " ".join(values)

    @staticmethod
    def _entity_key(entity_type: str, entity: dict[str, Any], index: int) -> str:
        identity = entity.get("company_name") or entity.get("institution_name")
        identity = identity or entity.get("name") or entity.get("role")
        return f"{entity_type}:{identity or index}"

    def delete(self, key: str) -> None:
        with self.database.session() as session:
            resume_session = session.get(ResumeSession, key)
            if resume_session is not None:
                session.delete(resume_session)
                session.commit()

    def search_questions(
        self,
        embedding: list[float],
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find the nearest stored questions using the FAISS adapter."""
        with self.database.session() as session:
            query = select(ResumeQuestion).where(ResumeQuestion.embedding.is_not(None))
            if session_id:
                query = query.where(ResumeQuestion.session_id == session_id)
            rows = session.scalars(query).all()
            ranked = search_rows(rows, embedding, limit)
            return [
                {
                    "question_text": row.question_text,
                    "question_code": row.question_code,
                    "embedding": row.embedding,
                    "answered": row.answered,
                }
                for row, _score in ranked
            ]

    def search_entities(
        self,
        embedding: list[float],
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find stored resume entities nearest to an embedding."""
        with self.database.session() as session:
            query = select(ResumeEntity).where(ResumeEntity.embedding.is_not(None))
            if session_id:
                query = query.where(ResumeEntity.session_id == session_id)
            rows = session.scalars(query).all()
            ranked = search_rows(rows, embedding, limit)
            return [
                {
                    "entity_type": row.entity_type,
                    "entity_key": row.entity_key,
                    "entity_data": row.entity_data,
                    "embedding": row.embedding,
                }
                for row, _score in ranked
            ]

    def search_messages(
        self,
        embedding: list[float],
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find stored chat messages nearest to an embedding."""
        with self.database.session() as session:
            query = select(ChatMessage).where(ChatMessage.embedding.is_not(None))
            if session_id:
                query = query.where(ChatMessage.session_id == session_id)
            rows = session.scalars(query).all()
            ranked = search_rows(rows, embedding, limit)
            return [
                {
                    "role": row.role,
                    "content": row.content,
                    "embedding": row.embedding,
                }
                for row, _score in ranked
            ]
