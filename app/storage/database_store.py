from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.db.models import ChatMessage, ResumeGraphNode, ResumeSession, ResumeVersion
from app.db.session import Database


class DatabaseStore:
    """Database-backed equivalent of JsonStore.

    The public get/put contract intentionally matches JsonStore so the pipeline
    can switch storage backends without changing API behavior.
    """

    def __init__(self, url: str, auto_create: bool = False) -> None:
        self.database = Database(url, auto_create=auto_create)

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
                "next_question": resume_session.next_question,
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
            resume_session.next_question = value.get("next_question")

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
                        )
                    )
            session.commit()

    def delete(self, key: str) -> None:
        with self.database.session() as session:
            resume_session = session.get(ResumeSession, key)
            if resume_session is not None:
                session.delete(resume_session)
                session.commit()
