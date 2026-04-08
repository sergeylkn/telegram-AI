from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError


logger = logging.getLogger("telegram_webhook")


class TelegramMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: int
    date: int
    text: str | None = None


class TelegramChat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    type: str


class TelegramUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    is_bot: bool
    first_name: str | None = None
    username: str | None = None


class IncomingMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: int
    date: int
    chat: TelegramChat
    from_user: TelegramUser = Field(alias="from")
    text: str | None = None


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_id: int
    message: IncomingMessage | None = None


class Orchestrator(Protocol):
    def handle_inbound(self, update: TelegramUpdate, correlation_id: str) -> list[str]:
        """Return outbound messages to send."""


class TelegramClient(Protocol):
    def send_message(self, chat_id: int, text: str, idempotency_key: str) -> str:
        """Send message and return provider message id."""


@dataclass
class WebhookDeps:
    db: sqlite3.Connection
    orchestrator: Orchestrator
    telegram_client: TelegramClient


class EchoOrchestrator:
    def handle_inbound(self, update: TelegramUpdate, correlation_id: str) -> list[str]:
        message = update.message
        if not message or not message.text:
            return []
        return [f"Echo: {message.text}"]


class NoopTelegramClient:
    def send_message(self, chat_id: int, text: str, idempotency_key: str) -> str:
        return f"noop:{chat_id}:{idempotency_key}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_updates (
            update_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            correlation_id TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 1,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS inbound_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_id INTEGER NOT NULL UNIQUE,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT,
            payload_json TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(update_id) REFERENCES processed_updates(update_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS outbound_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            provider_message_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            UNIQUE(update_id, text),
            FOREIGN KEY(update_id) REFERENCES processed_updates(update_id)
        )
        """
    )
    connection.commit()


@contextmanager
def tx_immediate(connection: sqlite3.Connection):
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def mark_failed(connection: sqlite3.Connection, update_id: int, error: str) -> None:
    with tx_immediate(connection):
        connection.execute(
            """
            UPDATE processed_updates
            SET status='failed', last_error=?, updated_at=?
            WHERE update_id=?
            """,
            (error[:2000], now_iso(), update_id),
        )


def claim_or_skip(connection: sqlite3.Connection, update: TelegramUpdate, correlation_id: str) -> tuple[bool, str]:
    chat_id = update.message.chat.id if update.message else None
    with tx_immediate(connection):
        row = connection.execute(
            "SELECT status, correlation_id, attempts FROM processed_updates WHERE update_id=?",
            (update.update_id,),
        ).fetchone()
        if row:
            status, existing_correlation_id, attempts = row
            if status == "completed":
                return False, existing_correlation_id
            if status == "processing":
                return False, existing_correlation_id
            connection.execute(
                """
                UPDATE processed_updates
                SET status='processing', attempts=?, correlation_id=?, updated_at=?, last_error=NULL
                WHERE update_id=?
                """,
                (attempts + 1, correlation_id, now_iso(), update.update_id),
            )
        else:
            connection.execute(
                """
                INSERT INTO processed_updates(update_id, chat_id, correlation_id, status, created_at, updated_at)
                VALUES(?, ?, ?, 'processing', ?, ?)
                """,
                (update.update_id, chat_id, correlation_id, now_iso(), now_iso()),
            )

        if update.message:
            connection.execute(
                """
                INSERT OR IGNORE INTO inbound_messages(update_id, chat_id, user_id, text, payload_json, correlation_id, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    update.update_id,
                    update.message.chat.id,
                    update.message.from_user.id,
                    update.message.text,
                    update.model_dump_json(by_alias=True),
                    correlation_id,
                    now_iso(),
                ),
            )
    return True, correlation_id


def send_outbound_once(
    connection: sqlite3.Connection,
    telegram_client: TelegramClient,
    update: TelegramUpdate,
    outbound_text: str,
    correlation_id: str,
) -> None:
    if not update.message:
        return
    chat_id = update.message.chat.id
    idempotency_key = f"update:{update.update_id}:text:{hash(outbound_text)}"

    with tx_immediate(connection):
        existing = connection.execute(
            "SELECT 1 FROM outbound_messages WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return

    provider_message_id = telegram_client.send_message(
        chat_id=chat_id,
        text=outbound_text,
        idempotency_key=idempotency_key,
    )

    with tx_immediate(connection):
        connection.execute(
            """
            INSERT OR IGNORE INTO outbound_messages(update_id, chat_id, text, correlation_id, provider_message_id, idempotency_key, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update.update_id,
                chat_id,
                outbound_text,
                correlation_id,
                provider_message_id,
                idempotency_key,
                now_iso(),
            ),
        )


def complete_update(connection: sqlite3.Connection, update_id: int) -> None:
    with tx_immediate(connection):
        connection.execute(
            """
            UPDATE processed_updates
            SET status='completed', updated_at=?, last_error=NULL
            WHERE update_id=?
            """,
            (now_iso(), update_id),
        )


async def handle_update(request: Request, deps: WebhookDeps) -> dict[str, Any]:
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    try:
        raw_payload = await request.json()
        update = TelegramUpdate.model_validate(raw_payload)
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.warning(
            "invalid_telegram_payload",
            extra={"correlation_id": correlation_id, "error": str(exc)},
        )
        raise HTTPException(status_code=400, detail={"error": "Invalid payload", "correlation_id": correlation_id})

    chat_id = update.message.chat.id if update.message else None
    logger.info(
        "webhook_received",
        extra={"correlation_id": correlation_id, "update_id": update.update_id, "chat_id": chat_id},
    )

    claimed, owner_correlation_id = claim_or_skip(deps.db, update, correlation_id)
    if not claimed:
        return {
            "ok": True,
            "skipped": True,
            "reason": "already_processed_or_inflight",
            "correlation_id": owner_correlation_id,
            "update_id": update.update_id,
            "chat_id": chat_id,
        }

    try:
        outbound = deps.orchestrator.handle_inbound(update, correlation_id)
        for message in outbound:
            send_outbound_once(deps.db, deps.telegram_client, update, message, correlation_id)
        complete_update(deps.db, update.update_id)
    except Exception as exc:
        mark_failed(deps.db, update.update_id, str(exc))
        logger.exception(
            "webhook_processing_failed",
            extra={"correlation_id": correlation_id, "update_id": update.update_id, "chat_id": chat_id},
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "Processing failed", "correlation_id": correlation_id, "update_id": update.update_id},
        ) from exc

    return {
        "ok": True,
        "skipped": False,
        "correlation_id": correlation_id,
        "update_id": update.update_id,
        "chat_id": chat_id,
    }


def create_app(deps: WebhookDeps) -> FastAPI:
    app = FastAPI()

    @app.post("/webhook/telegram")
    async def telegram_webhook(request: Request):
        return await handle_update(request, deps)

    return app


default_connection = sqlite3.connect("telegram_ai.db", check_same_thread=False)
init_db(default_connection)
default_deps = WebhookDeps(
    db=default_connection,
    orchestrator=EchoOrchestrator(),
    telegram_client=NoopTelegramClient(),
)
app = create_app(default_deps)
