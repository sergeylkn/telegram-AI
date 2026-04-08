from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuthError(PermissionError):
    """Raised when an internal admin request is unauthenticated."""


class NotFoundError(LookupError):
    """Raised when a chat cannot be found."""


@dataclass(frozen=True)
class AdminContext:
    operator_id: str
    auth_token: str


class AdminAPI:
    """Authenticated internal admin operations for chat supervision and handoff."""

    def __init__(self, db_path: str = ":memory:", internal_token: str = "internal-admin-token") -> None:
        self._db = sqlite3.connect(db_path)
        self._db.row_factory = sqlite3.Row
        self._internal_token = internal_token
        self._bootstrap()

    def _bootstrap(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS chats (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL DEFAULT 'active',
              current_mode TEXT NOT NULL DEFAULT 'ai',
              assigned_manager_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id TEXT NOT NULL,
              sender_type TEXT NOT NULL,
              sender_id TEXT,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(chat_id) REFERENCES chats(id)
            );

            CREATE TABLE IF NOT EXISTS mode_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id TEXT NOT NULL,
              from_mode TEXT,
              to_mode TEXT NOT NULL,
              operator_id TEXT NOT NULL,
              reason TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(chat_id) REFERENCES chats(id)
            );

            CREATE TABLE IF NOT EXISTS handoff_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              manager_id TEXT,
              operator_id TEXT NOT NULL,
              metadata TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(chat_id) REFERENCES chats(id)
            );
            """
        )
        self._db.commit()

    def create_chat(self, chat_id: str, status: str = "active") -> None:
        now = _utc_now_iso()
        self._db.execute(
            """
            INSERT INTO chats (id, status, current_mode, assigned_manager_id, created_at, updated_at)
            VALUES (?, ?, 'ai', NULL, ?, ?)
            """,
            (chat_id, status, now, now),
        )
        self._db.commit()

    def add_message(self, chat_id: str, sender_type: str, content: str, sender_id: str | None = None) -> int:
        self._ensure_chat(chat_id)
        cur = self._db.execute(
            """
            INSERT INTO messages (chat_id, sender_type, sender_id, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, sender_type, sender_id, content, _utc_now_iso()),
        )
        self._db.commit()
        return int(cur.lastrowid)

    def _authenticated(method: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(method)
        def wrapper(self: "AdminAPI", ctx: AdminContext, *args: Any, **kwargs: Any) -> Any:
            if ctx.auth_token != self._internal_token:
                raise AuthError("Invalid internal admin token")
            return method(self, ctx, *args, **kwargs)

        return wrapper

    def _ensure_chat(self, chat_id: str) -> sqlite3.Row:
        row = self._db.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Chat '{chat_id}' not found")
        return row

    def _log_mode_event(self, chat_id: str, from_mode: str | None, to_mode: str, operator_id: str, reason: str) -> None:
        self._db.execute(
            """
            INSERT INTO mode_events (chat_id, from_mode, to_mode, operator_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, from_mode, to_mode, operator_id, reason, _utc_now_iso()),
        )

    def _log_handoff_event(
        self, chat_id: str, event_type: str, manager_id: str | None, operator_id: str, metadata: str | None
    ) -> None:
        self._db.execute(
            """
            INSERT INTO handoff_events (chat_id, event_type, manager_id, operator_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, event_type, manager_id, operator_id, metadata, _utc_now_iso()),
        )

    @_authenticated
    def list_active_chats(self, ctx: AdminContext) -> list[dict[str, Any]]:
        rows = self._db.execute(
            """
            SELECT id, current_mode, assigned_manager_id, updated_at
            FROM chats
            WHERE status = 'active'
            ORDER BY updated_at DESC, id ASC
            """
        ).fetchall()
        return [
            {
                "chat_id": row["id"],
                "mode": row["current_mode"],
                "assigned_manager_id": row["assigned_manager_id"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    @_authenticated
    def get_chat_details(self, ctx: AdminContext, chat_id: str, history_limit: int = 20) -> dict[str, Any]:
        chat = self._ensure_chat(chat_id)
        history = self._db.execute(
            """
            SELECT id, sender_type, sender_id, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, history_limit),
        ).fetchall()
        return {
            "chat_id": chat["id"],
            "status": chat["status"],
            "mode": chat["current_mode"],
            "assigned_manager_id": chat["assigned_manager_id"],
            "history": [
                {
                    "message_id": row["id"],
                    "sender_type": row["sender_type"],
                    "sender_id": row["sender_id"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in history
            ],
        }

    @_authenticated
    def switch_chat_to_manual_mode(self, ctx: AdminContext, chat_id: str, reason: str = "operator_override") -> dict[str, Any]:
        chat = self._ensure_chat(chat_id)
        from_mode = chat["current_mode"]
        if from_mode != "manual":
            self._db.execute(
                "UPDATE chats SET current_mode = 'manual', updated_at = ? WHERE id = ?",
                (_utc_now_iso(), chat_id),
            )
            self._log_mode_event(chat_id, from_mode, "manual", ctx.operator_id, reason)
            self._db.commit()
        return {"chat_id": chat_id, "mode": "manual"}

    @_authenticated
    def return_chat_to_ai_mode(self, ctx: AdminContext, chat_id: str, reason: str = "operator_release") -> dict[str, Any]:
        chat = self._ensure_chat(chat_id)
        from_mode = chat["current_mode"]
        if from_mode != "ai":
            self._db.execute(
                "UPDATE chats SET current_mode = 'ai', updated_at = ? WHERE id = ?",
                (_utc_now_iso(), chat_id),
            )
            self._log_mode_event(chat_id, from_mode, "ai", ctx.operator_id, reason)
            self._db.commit()
        return {"chat_id": chat_id, "mode": "ai"}

    @_authenticated
    def assign_manager(self, ctx: AdminContext, chat_id: str, manager_id: str) -> dict[str, Any]:
        self._ensure_chat(chat_id)
        self._db.execute(
            "UPDATE chats SET assigned_manager_id = ?, updated_at = ? WHERE id = ?",
            (manager_id, _utc_now_iso(), chat_id),
        )
        self._log_handoff_event(chat_id, "manager_assigned", manager_id, ctx.operator_id, None)
        self._db.commit()
        return {"chat_id": chat_id, "assigned_manager_id": manager_id}

    @_authenticated
    def unassign_manager(self, ctx: AdminContext, chat_id: str) -> dict[str, Any]:
        chat = self._ensure_chat(chat_id)
        manager_id = chat["assigned_manager_id"]
        self._db.execute(
            "UPDATE chats SET assigned_manager_id = NULL, updated_at = ? WHERE id = ?",
            (_utc_now_iso(), chat_id),
        )
        self._log_handoff_event(chat_id, "manager_unassigned", manager_id, ctx.operator_id, None)
        self._db.commit()
        return {"chat_id": chat_id, "assigned_manager_id": None}

    @_authenticated
    def post_manager_message(self, ctx: AdminContext, chat_id: str, manager_id: str, content: str) -> dict[str, Any]:
        chat = self._ensure_chat(chat_id)
        from_mode = chat["current_mode"]
        if from_mode != "manual":
            self._db.execute(
                "UPDATE chats SET current_mode = 'manual', assigned_manager_id = ?, updated_at = ? WHERE id = ?",
                (manager_id, _utc_now_iso(), chat_id),
            )
            self._log_mode_event(chat_id, from_mode, "manual", ctx.operator_id, "manager_first_message_takeover")
            self._log_handoff_event(chat_id, "manager_takeover", manager_id, ctx.operator_id, "first_message")
        message_id = self.add_message(chat_id, "manager", content, sender_id=manager_id)
        self._log_handoff_event(chat_id, "manager_message_sent", manager_id, ctx.operator_id, f"message_id={message_id}")
        self._db.commit()
        return {
            "chat_id": chat_id,
            "mode": "manual",
            "assigned_manager_id": manager_id,
            "message_id": message_id,
        }

    @_authenticated
    def get_mode_events(self, ctx: AdminContext, chat_id: str) -> list[dict[str, Any]]:
        self._ensure_chat(chat_id)
        rows = self._db.execute(
            "SELECT * FROM mode_events WHERE chat_id = ? ORDER BY id ASC", (chat_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    @_authenticated
    def get_handoff_events(self, ctx: AdminContext, chat_id: str) -> list[dict[str, Any]]:
        self._ensure_chat(chat_id)
        rows = self._db.execute(
            "SELECT * FROM handoff_events WHERE chat_id = ? ORDER BY id ASC", (chat_id,)
        ).fetchall()
        return [dict(row) for row in rows]
