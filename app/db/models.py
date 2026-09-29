from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


JsonType = JSONB
EMBEDDING_DIMENSION = 384


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list[ResumeSession]] = relationship(back_populates="user")


class ResumeSession(Base):
    __tablename__ = "resume_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL")
    )
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    asked_deficiencies: Mapped[list[str]] = mapped_column(JsonType, default=list)
    asked_deficiency_codes: Mapped[list[str]] = mapped_column(JsonType, default=list)
    next_question: Mapped[str | None] = mapped_column(Text)
    conversation_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    suppressed_facts: Mapped[list[str]] = mapped_column(JsonType, default=list)
    operation_history: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="sessions")
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    questions: Mapped[list[ResumeQuestion]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    entities: Mapped[list[ResumeEntity]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_sessions.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[ResumeSession] = relationship(back_populates="messages")


class ResumeQuestion(Base):
    __tablename__ = "resume_questions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_sessions.id", ondelete="CASCADE")
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_code: Mapped[str | None] = mapped_column(String(200))
    embedding: Mapped[list[float] | None] = mapped_column(JsonType)
    answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[ResumeSession] = relationship(back_populates="questions")


class ResumeEntity(Base):
    __tablename__ = "resume_entities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_sessions.id", ondelete="CASCADE")
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    session: Mapped[ResumeSession] = relationship(back_populates="entities")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_sessions.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    resume_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    analysis_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[ResumeSession] = relationship(back_populates="versions")
    graph_nodes: Mapped[list[ResumeGraphNode]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class ResumeGraphNode(Base):
    __tablename__ = "resume_graph_nodes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("resume_versions.id", ondelete="CASCADE")
    )
    node_key: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    filled_fields: Mapped[int] = mapped_column(Integer, nullable=False)
    total_fields: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_fields: Mapped[list[str]] = mapped_column(JsonType, default=list)
    node_data: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    version: Mapped[ResumeVersion] = relationship(back_populates="graph_nodes")
