from app import ChatStateStore, Mode, assemble_context


def test_ai_default_active():
    store = ChatStateStore()
    should_trigger = store.ingest_message(chat_id=1, sender_role="user", text="hello")

    assert should_trigger is True
    assert store.get(1).mode == Mode.AI


def test_manager_takeover_flow():
    store = ChatStateStore()

    store.manager_takeover(chat_id=10, manager_id=77)

    state = store.get(10)
    assert state.mode == Mode.MANUAL
    assert state.manager_id == 77


def test_first_manager_message_disables_ai():
    store = ChatStateStore()

    # starts in AI
    assert store.get(1).mode == Mode.AI

    should_trigger = store.ingest_message(
        chat_id=1,
        sender_role="assistant",
        text="I'm taking over",
        sender_id=99,
        from_manager=True,
    )

    assert should_trigger is False
    assert store.get(1).mode == Mode.MANUAL
    assert store.get(1).manager_id == 99


def test_user_messages_in_manual_mode_do_not_trigger_ai():
    store = ChatStateStore()
    store.manager_takeover(chat_id=5, manager_id=1001)

    should_trigger = store.ingest_message(chat_id=5, sender_role="user", text="are you there?")

    assert should_trigger is False


def test_switch_back_to_ai():
    store = ChatStateStore()
    store.manager_takeover(chat_id=7, manager_id=222)
    store.switch_to_ai(chat_id=7)

    assert store.get(7).mode == Mode.AI
    should_trigger = store.ingest_message(chat_id=7, sender_role="user", text="welcome back")
    assert should_trigger is True


def test_multi_chat_state_isolation():
    store = ChatStateStore()

    store.manager_takeover(chat_id=1, manager_id=1)
    store.ingest_message(chat_id=2, sender_role="user", text="hi")

    assert store.get(1).mode == Mode.MANUAL
    assert store.get(2).mode == Mode.AI


def test_context_assembly_behavior_summary_and_recent_window():
    store = ChatStateStore()
    state = store.get(3)
    state.summary = "User asked about pricing; promised follow-up."
    for idx in range(10):
        state.messages.append({"role": "user" if idx % 2 == 0 else "assistant", "text": f"m{idx}"})

    context = assemble_context(state, recent_window=4)

    assert context[0]["role"] == "system"
    assert "Summary:" in context[0]["text"]
    assert [m["text"] for m in context[1:]] == ["m6", "m7", "m8", "m9"]
