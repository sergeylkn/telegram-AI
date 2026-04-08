"""create telegram core tables

Revision ID: 0001_create_telegram_core_tables
Revises:
Create Date: 2026-04-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_create_telegram_core_tables"
down_revision = None
branch_labels = None
depends_on = None


sender_type_enum = sa.Enum("user", "ai", "manager", "system", name="sender_type_enum", native_enum=False)
message_status_enum = sa.Enum(
    "received", "processed", "failed", name="message_status_enum", native_enum=False
)
mode_actor_type_enum = sa.Enum(
    "user", "ai", "manager", "system", name="mode_actor_type_enum", native_enum=False
)
handoff_action_enum = sa.Enum("takeover", "release", name="handoff_action_enum", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "managers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_managers_email", "managers", ["email"], unique=False)

    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("current_mode", sa.String(length=64), nullable=False),
        sa.Column("assigned_manager_id", sa.Integer(), sa.ForeignKey("managers.id"), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chats_telegram_chat_id", "chats", ["telegram_chat_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_type", sender_type_enum, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", message_status_enum, nullable=False, server_default="received"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_messages_chat_id_created_at", "messages", ["chat_id", "created_at"], unique=False)

    op.create_table(
        "mode_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_mode", sa.String(length=64), nullable=False),
        sa.Column("to_mode", sa.String(length=64), nullable=False),
        sa.Column("actor_type", mode_actor_type_enum, nullable=False),
        sa.Column("actor_manager_id", sa.Integer(), sa.ForeignKey("managers.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "handoff_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", handoff_action_enum, nullable=False),
        sa.Column("actor_manager_id", sa.Integer(), sa.ForeignKey("managers.id"), nullable=True),
        sa.Column("target_manager_id", sa.Integer(), sa.ForeignKey("managers.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "memory_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("chat_id", "version", name="uq_memory_snapshots_chat_version"),
    )

    op.create_table(
        "processed_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("update_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_processed_updates_update_id", "processed_updates", ["update_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_processed_updates_update_id", table_name="processed_updates")
    op.drop_table("processed_updates")
    op.drop_table("memory_snapshots")
    op.drop_table("handoff_events")
    op.drop_table("mode_events")
    op.drop_index("ix_messages_chat_id_created_at", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_chats_telegram_chat_id", table_name="chats")
    op.drop_table("chats")
    op.drop_index("ix_managers_email", table_name="managers")
    op.drop_table("managers")

    handoff_action_enum.drop(op.get_bind(), checkfirst=True)
    mode_actor_type_enum.drop(op.get_bind(), checkfirst=True)
    message_status_enum.drop(op.get_bind(), checkfirst=True)
    sender_type_enum.drop(op.get_bind(), checkfirst=True)
