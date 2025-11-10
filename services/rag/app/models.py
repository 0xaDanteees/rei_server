from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class MessageRole(str, Enum):
    human = "human"
    ai = "ai"
    system = "system"


class ChatSession(Base):
    __tablename__ = "rag_chat_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    partner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), index=True)

    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    messages: Mapped[list[ChatMessage]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    memories: Mapped[list[ChatMemory]] = relationship("ChatMemory", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_rag_chat_sessions_user_partner", "user_id", "partner_id"),
    )


class ChatMessage(Base):
    __tablename__ = "rag_chat_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("rag_chat_sessions.id", ondelete="CASCADE"), index=True)

    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_rag_chat_messages_session_role", "session_id", "role"),
    )


class ChatMemory(Base):
    __tablename__ = "rag_chat_memories"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("rag_chat_sessions.id", ondelete="CASCADE"), index=True)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="memories")
