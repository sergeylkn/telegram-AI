import pytest

from app.domain.state_machine import (
    ChatEvent,
    ChatMode,
    ChatStateMachine,
    InvalidTransitionError,
)


def test_new_chat_defaults_to_ai_active() -> None:
    sm = ChatStateMachine()
    assert sm.mode_for("chat-1") == ChatMode.AI_ACTIVE
    assert sm.transition_log == []


def test_manager_first_message_forces_manual_active() -> None:
    sm = ChatStateMachine()
    mode = sm.handle_event("chat-1", ChatEvent.MANAGER_FIRST_MESSAGE)

    assert mode == ChatMode.MANUAL_ACTIVE
    assert sm.transition_log[-1].from_mode == ChatMode.AI_ACTIVE
    assert sm.transition_log[-1].to_mode == ChatMode.MANUAL_ACTIVE


def test_user_messages_do_not_leave_manual_mode() -> None:
    sm = ChatStateMachine()
    sm.handle_event("chat-1", ChatEvent.MANAGER_TAKEOVER)

    mode = sm.handle_event("chat-1", ChatEvent.USER_MESSAGE)

    assert mode == ChatMode.MANUAL_ACTIVE
    assert len(sm.transition_log) == 1


def test_explicit_safe_transition_back_to_ai_only_via_operator_event() -> None:
    sm = ChatStateMachine()
    sm.handle_event("chat-1", ChatEvent.MANAGER_TAKEOVER)
    sm.handle_event("chat-1", ChatEvent.MANAGER_RELEASE)

    # User activity alone cannot switch back to AI.
    still_return = sm.handle_event("chat-1", ChatEvent.USER_MESSAGE)
    assert still_return == ChatMode.RETURN_TO_AI

    # Explicit admin action returns AI control.
    ai_mode = sm.handle_event(
        "chat-1", ChatEvent.ADMIN_MODE_SWITCH, target_mode=ChatMode.AI_ACTIVE
    )
    assert ai_mode == ChatMode.AI_ACTIVE


def test_admin_switch_requires_target_mode() -> None:
    sm = ChatStateMachine()

    with pytest.raises(InvalidTransitionError):
        sm.handle_event("chat-1", ChatEvent.ADMIN_MODE_SWITCH)


def test_transition_log_records_each_mode_change_only() -> None:
    sm = ChatStateMachine()
    sm.handle_event("chat-1", ChatEvent.USER_MESSAGE)  # no mode change
    sm.handle_event("chat-1", ChatEvent.MANAGER_TAKEOVER)
    sm.handle_event("chat-1", ChatEvent.MANAGER_FIRST_MESSAGE)  # no mode change
    sm.handle_event("chat-1", ChatEvent.MANAGER_RELEASE)

    records = sm.transition_log
    assert [(r.from_mode, r.to_mode) for r in records] == [
        (ChatMode.AI_ACTIVE, ChatMode.MANUAL_ACTIVE),
        (ChatMode.MANUAL_ACTIVE, ChatMode.RETURN_TO_AI),
    ]


def test_multi_chat_isolation() -> None:
    sm = ChatStateMachine()

    sm.handle_event("chat-a", ChatEvent.MANAGER_TAKEOVER)
    sm.handle_event("chat-b", ChatEvent.USER_MESSAGE)

    assert sm.mode_for("chat-a") == ChatMode.MANUAL_ACTIVE
    assert sm.mode_for("chat-b") == ChatMode.AI_ACTIVE

    assert [record.chat_id for record in sm.transition_log] == ["chat-a"]
