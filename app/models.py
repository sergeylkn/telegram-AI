from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SenderType(str, enum.Enum):
    USER = "user"
    AI = "ai"
    MANAGER = "manager"
    SYSTEM = "system"


class MessageStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class ModeActorType(str, enum.Enum):
    USER = "user"
    AI = "ai"
    MANAGER = "manager"
    SYSTEM = "system"


class HandoffAction(str, enum.Enum):
    TAKEOVER = "takeover"
    RELEASE = "release"


class Manager(Base):
    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    chats: Mapped[list[Chat]] = relationship(back_populates="assigned_manager")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    current_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    assigned_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    assigned_manager: Mapped[Manager | None] = relationship(back_populates="chats")
    messages: Mapped[list[Message]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    mode_events: Mapped[list[ModeEvent]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    handoff_events: Mapped[list[HandoffEvent]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    memory_snapshots: Mapped[list[MemorySnapshot]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_type: Mapped[SenderType] = mapped_column(
        Enum(SenderType, name="sender_type_enum", native_enum=False), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status_enum", native_enum=False),
        nullable=False,
        default=MessageStatus.RECEIVED,
        server_default=MessageStatus.RECEIVED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    chat: Mapped[Chat] = relationship(back_populates="messages")


class ModeEvent(Base):
    __tablename__ = "mode_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    from_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    to_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[ModeActorType] = mapped_column(
        Enum(ModeActorType, name="mode_actor_type_enum", native_enum=False), nullable=False
    )
    actor_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chat: Mapped[Chat] = relationship(back_populates="mode_events")


class HandoffEvent(Base):
    __tablename__ = "handoff_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[HandoffAction] = mapped_column(
        Enum(HandoffAction, name="handoff_action_enum", native_enum=False), nullable=False
    )
    actor_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"), nullable=True)
    target_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chat: Mapped[Chat] = relationship(back_populates="handoff_events")


class MemorySnapshot(Base):
    __tablename__ = "memory_snapshots"
    __table_args__ = (UniqueConstraint("chat_id", "version", name="uq_memory_snapshots_chat_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chat: Mapped[Chat] = relationship(back_populates="memory_snapshots")


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    update_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


Index("ix_chats_telegram_chat_id", Chat.telegram_chat_id)
Index("ix_processed_updates_update_id", ProcessedUpdate.update_id)
