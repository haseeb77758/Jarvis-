"""Offline checks: sandbox is conversational, bounded, and not a desktop executor."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox_chat import SandboxSession, sandbox_reply
from tools.package_source import source_files
from tools.update_windows import REQUIRED, LOCAL_TESTS


class SandboxTests(unittest.TestCase):
    def test_session_uses_conversation_history(self):
        chat = SandboxSession(max_messages=4)
        chat.commit("Salam", "Wa alaikum salam")
        messages = chat.conversation_for("Kaise ho?")
        self.assertEqual(messages, [
            {"role": "user", "content": "Salam"},
            {"role": "assistant", "content": "Wa alaikum salam"},
            {"role": "user", "content": "Kaise ho?"},
        ])

    def test_bounded_and_clearable(self):
        chat = SandboxSession(max_messages=4)
        for n in range(4):
            chat.commit(f"Q{n}", f"A{n}")
        self.assertEqual(len(chat.history), 4)
        self.assertEqual(chat.history[0]["content"], "Q2")
        chat.clear()
        self.assertEqual(chat.history, [])

    def test_limits_and_empty_replies(self):
        chat = SandboxSession()
        for invalid in ("", "    ", "X" * 4001):
            with self.assertRaises(ValueError):
                chat.conversation_for(invalid)
        with self.assertRaises(ValueError):
            chat.commit("Hello", "")

    def test_desktop_command_is_only_chat_text(self):
        ai = Mock()
        ai.ask.return_value = "Main computer control nahi karta."
        session = SandboxSession()
        answer = sandbox_reply(ai, session, "calculator kholo")
        self.assertIn("control", answer)
        args, kwargs = ai.ask.call_args
        self.assertEqual(args[0], [{"role": "user", "content": "calculator kholo"}])
        self.assertFalse(kwargs["plan"])
        self.assertEqual(session.history, [])

    def test_installer_and_updater_include_sandbox(self):
        paths = [p.as_posix() for p in source_files(ROOT)]
        self.assertIn("sandbox_chat.py", paths)
        self.assertIn("sandbox_chat.py", REQUIRED)
        self.assertIn("test_sandbox_chat.py", LOCAL_TESTS)


if __name__ == "__main__":
    unittest.main()
