import unittest

from admin_api import AdminAPI, AdminContext, AuthError


class AdminAPITest(unittest.TestCase):
    def setUp(self) -> None:
        self.api = AdminAPI(internal_token="secret")
        self.ctx = AdminContext(operator_id="op-1", auth_token="secret")
        self.api.create_chat("chat-1")
        self.api.add_message("chat-1", "user", "hello")

    def test_list_active_chats(self) -> None:
        chats = self.api.list_active_chats(self.ctx)
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0]["chat_id"], "chat-1")
        self.assertEqual(chats[0]["mode"], "ai")

    def test_switch_modes_and_log_mode_events(self) -> None:
        self.api.switch_chat_to_manual_mode(self.ctx, "chat-1")
        self.api.return_chat_to_ai_mode(self.ctx, "chat-1")

        events = self.api.get_mode_events(self.ctx, "chat-1")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["to_mode"], "manual")
        self.assertEqual(events[1]["to_mode"], "ai")

    def test_assign_unassign_manager_logs_handoff(self) -> None:
        self.api.assign_manager(self.ctx, "chat-1", "mgr-7")
        self.api.unassign_manager(self.ctx, "chat-1")

        events = self.api.get_handoff_events(self.ctx, "chat-1")
        self.assertEqual(events[0]["event_type"], "manager_assigned")
        self.assertEqual(events[1]["event_type"], "manager_unassigned")

    def test_post_manager_message_triggers_takeover(self) -> None:
        response = self.api.post_manager_message(self.ctx, "chat-1", "mgr-9", "I can help you")

        self.assertEqual(response["mode"], "manual")
        details = self.api.get_chat_details(self.ctx, "chat-1")
        self.assertEqual(details["assigned_manager_id"], "mgr-9")
        self.assertEqual(details["history"][0]["sender_type"], "manager")

        mode_events = self.api.get_mode_events(self.ctx, "chat-1")
        self.assertEqual(mode_events[0]["reason"], "manager_first_message_takeover")

    def test_auth_is_required(self) -> None:
        bad_ctx = AdminContext(operator_id="op-2", auth_token="wrong")
        with self.assertRaises(AuthError):
            self.api.list_active_chats(bad_ctx)


if __name__ == "__main__":
    unittest.main()
