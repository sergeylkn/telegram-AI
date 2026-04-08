import sqlite3

from fastapi.testclient import TestClient

from src.webhook import TelegramUpdate, WebhookDeps, create_app, init_db


class StubOrchestrator:
    def __init__(self):
        self.calls = 0

    def handle_inbound(self, update: TelegramUpdate, correlation_id: str):
        self.calls += 1
        if update.message and update.message.text:
            return [f"AI:{update.message.text}"]
        return []


class StubTelegramClient:
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id: int, text: str, idempotency_key: str):
        self.sent.append((chat_id, text, idempotency_key))
        return f"msg-{len(self.sent)}"


def setup_client():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(db)
    orchestrator = StubOrchestrator()
    tg_client = StubTelegramClient()
    deps = WebhookDeps(db=db, orchestrator=orchestrator, telegram_client=tg_client)
    app = create_app(deps)
    return TestClient(app), db, orchestrator, tg_client


def test_process_once_and_skip_duplicates():
    client, db, orchestrator, tg = setup_client()
    payload = {
        "update_id": 123,
        "message": {
            "message_id": 1,
            "date": 100,
            "text": "hello",
            "chat": {"id": 42, "type": "private"},
            "from": {"id": 7, "is_bot": False, "first_name": "A"},
        },
    }

    first = client.post("/webhook/telegram", json=payload)
    assert first.status_code == 200
    assert first.json()["skipped"] is False

    second = client.post("/webhook/telegram", json=payload)
    assert second.status_code == 200
    assert second.json()["skipped"] is True

    status = db.execute("SELECT status FROM processed_updates WHERE update_id=123").fetchone()[0]
    assert status == "completed"
    inbound_count = db.execute("SELECT COUNT(*) FROM inbound_messages WHERE update_id=123").fetchone()[0]
    outbound_count = db.execute("SELECT COUNT(*) FROM outbound_messages WHERE update_id=123").fetchone()[0]

    assert inbound_count == 1
    assert outbound_count == 1
    assert orchestrator.calls == 1
    assert len(tg.sent) == 1


def test_invalid_payload_validation_error():
    client, *_ = setup_client()
    resp = client.post("/webhook/telegram", json={"foo": "bar"})
    assert resp.status_code == 400
    body = resp.json()["detail"]
    assert body["error"] == "Invalid payload"
    assert "correlation_id" in body
