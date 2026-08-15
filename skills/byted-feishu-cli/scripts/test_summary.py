#!/usr/bin/env python3
"""Offline tests for unread classification helpers."""

from __future__ import annotations

import unittest

from summary import (
    extract_text,
    is_from_me,
    is_related_to_me,
    related_reasons,
    render_markdown,
)


ME = {"ou_me"}


def _msg(**kwargs):
    message = {
        "message_id": kwargs.get("message_id", "om_1"),
        "msg_type": "text",
        "create_time": "1710000000000",
        "sender": {"id": kwargs.get("sender", "ou_other"), "sender_type": "user"},
        "body": {"content": kwargs.get("content", '{"text":"hello"}')},
        "mentions": kwargs.get("mentions", []),
        "parent_id": kwargs.get("parent_id"),
        "root_id": kwargs.get("root_id"),
        "deleted": False,
    }
    return message


class SummaryTests(unittest.TestCase):
    def test_extract_text(self):
        self.assertEqual(extract_text(_msg(content='{"text":"你好"}')), "你好")

    def test_p2p_is_related(self):
        msg = _msg()
        self.assertTrue(
            is_related_to_me(msg, me_ids=ME, chat_mode="p2p", my_message_ids=set())
        )
        self.assertEqual(
            related_reasons(msg, me_ids=ME, chat_mode="p2p", my_message_ids=set()),
            ["p2p"],
        )

    def test_mention_is_related(self):
        msg = _msg(mentions=[{"id": "ou_me", "name": "me"}])
        self.assertTrue(
            is_related_to_me(msg, me_ids=ME, chat_mode="group", my_message_ids=set())
        )

    def test_reply_to_me_is_related(self):
        msg = _msg(parent_id="om_mine")
        self.assertTrue(
            is_related_to_me(
                msg, me_ids=ME, chat_mode="group", my_message_ids={"om_mine"}
            )
        )

    def test_plain_group_is_other(self):
        msg = _msg()
        self.assertFalse(
            is_related_to_me(msg, me_ids=ME, chat_mode="group", my_message_ids=set())
        )

    def test_self_message(self):
        self.assertTrue(is_from_me(_msg(sender="ou_me"), ME))
        self.assertFalse(is_from_me(_msg(sender="ou_other"), ME))

    def test_markdown_sections(self):
        text = render_markdown(
            {
                "window": {
                    "hours": 24,
                    "start_time_text": "a",
                    "end_time_text": "b",
                },
                "chats_scanned": 1,
                "related": [
                    {
                        "chat_id": "oc_1",
                        "chat_name": "测试组",
                        "chat_mode": "group",
                        "create_time_text": "12:00",
                        "text": "@我看一下",
                        "reasons": ["mention"],
                    }
                ],
                "others": [],
                "note": "note",
            }
        )
        self.assertIn("与我相关", text)
        self.assertIn("测试组", text)
        self.assertIn("其他消息", text)


if __name__ == "__main__":
    unittest.main()
