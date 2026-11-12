"""Tests for the integrated Jarvis chat user experience.

No Tk display or Ollama server required for these behavioral tests.
"""
import sys
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import App
from chat_ui import ChatComposer, on_return, preset_prompt
from tools.package_source import source_files


class LocalChatTests(unittest.TestCase):
    def create_app(self, mode="AI chat"):
        app = App.__new__(App)
        app.busy = False
        app.sleeping = False
        app.stop = threading.Event()
        app.history = [{'role': 'user', 'content': 'Pehla sawal'},
                       {'role': 'assistant', 'content': 'Pehla jawab'}]
        app.mode = Mock()
        app.mode.get.return_value = mode
        app.entry = Mock()
        app.entry.get.return_value = 'calculator kholo'
        app.say = Mock()
        app.worker = Mock()
        app.ai = Mock()
        app.store = Mock()
        app.store.facts = []
        app.store.apps = {}
        app.pending = []
        return app

    def test_chat_message_never_executes_matching_desktop_command(self):
        app = self.create_app()
        with patch('app.parse_command') as parser:
            app.submit()
            parser.assert_not_called()
        app.worker.assert_called_once()
        callback, kind, query = app.worker.call_args.args
        self.assertEqual((kind, query), ('ai', 'calculator kholo'))
        app.ai.ask.return_value = 'Yeh ek AI response hai.'
        self.assertEqual(callback(), 'Yeh ek AI response hai.')
        sent = app.ai.ask.call_args.args[0]
        self.assertEqual(sent[-1], {'role': 'user', 'content': 'calculator kholo'})
        self.assertEqual(len(sent), 3)

    def test_desktop_mode_keeps_existing_command_behavior(self):
        app = self.create_app('Computer commands')
        app.last_plan = []
        app.approve = Mock()
        app.submit()
        app.approve.assert_called_once_with({'action': 'launch', 'app': 'calculator'})
        app.worker.assert_not_called()

    def test_too_long_message_does_not_queue_or_clear_composer(self):
        app = self.create_app()
        app.entry.get.return_value = 'x' * 4001
        app.submit()
        app.worker.assert_not_called()
        app.entry.delete.assert_not_called()

    def test_sleep_mode_blocks_chat_but_wake_command_resumes(self):
        app = self.create_app()
        app.sleeping = True
        app.toggle_sleep_mode = Mock(side_effect=lambda: setattr(app, 'sleeping', False))
        app.submit()
        app.worker.assert_not_called()
        app.say.assert_any_call('SLEEP', unittest.mock.ANY)
        app.entry.get.return_value = 'wake up jarvis'
        app.submit()
        app.toggle_sleep_mode.assert_called_once()
        self.assertFalse(app.sleeping)

    def test_chat_source_is_in_windows_install_bundle(self):
        self.assertIn('chat_ui.py', [p.as_posix() for p in source_files(ROOT)])

    def test_enter_sends_and_shift_enter_inserts_newline(self):
        send = Mock()
        event = Mock(state=0)
        self.assertEqual(on_return(event, send), 'break')
        send.assert_called_once()
        send.reset_mock()
        event.state = 1
        self.assertIsNone(on_return(event, send))
        send.assert_not_called()

    def test_preset_prompt_populates_but_does_not_send(self):
        entry = Mock()
        preset_prompt(entry, 'Salam')
        entry.delete.assert_called_once_with(0, 'end')
        entry.insert.assert_called_once_with(0, 'Salam')
        entry.focus_set.assert_called_once()


if __name__ == '__main__':
    unittest.main()

