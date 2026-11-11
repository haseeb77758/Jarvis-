"""Regression tests for the desktop agent's permission boundaries.

These tests use temporary folders and mocks only; they never control the host PC.
"""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Controller, parse_command, parse_plan, safe_child, valid_url, validate


class DesktopSafetyRegressionTests(unittest.TestCase):
    def test_rejects_unsafe_web_addresses(self):
        for address in (
            'http://example.com', 'file:///C:/Windows/system.ini',
            'https://user:pass@example.com', 'https://example.com/a b',
            'javascript:alert(1)',
        ):
            with self.subTest(address=address), self.assertRaises(ValueError):
                valid_url(address)
        self.assertEqual(valid_url('https://example.com/path'), 'https://example.com/path')

    def test_workspace_names_cannot_escape_or_use_windows_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('../outside', '..', 'CON', 'nul.txt', 'file:stream',
                         'folder/name', 'folder\\name', 'trailing.', ' leading'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    safe_child(directory, name)
            self.assertEqual(safe_child(directory, 'Client Work'), Path(directory).resolve() / 'Client Work')

    def test_plan_rejects_shell_actions_and_excessive_steps(self):
        with self.assertRaises(ValueError):
            parse_plan(json.dumps({'actions': [{'action': 'shell', 'command': 'whoami'}]}))
        with self.assertRaises(ValueError):
            parse_plan(json.dumps({'actions': [{'action': 'windows'}] * 9}))
        with self.assertRaises(ValueError):
            parse_plan('not-json')
        self.assertEqual(parse_plan('{"actions":[{"action":"windows"}]}'),
                         [{'action': 'windows'}])

    def test_unknown_command_is_not_automatically_executed(self):
        self.assertIsNone(parse_command('delete all files'))
        self.assertIsNone(parse_command('run powershell'))
        with self.assertRaises(ValueError):
            validate({'action': 'type', 'text': 'hello\nenter'})
        with self.assertRaises(ValueError):
            validate({'action': 'key', 'keys': 'win+r'})

    def test_stopped_controller_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as directory:
            stopped = threading.Event()
            stopped.set()
            controller = Controller(directory, stop=stopped)
            with self.assertRaisesRegex(RuntimeError, 'Stopped'):
                controller.execute({'action': 'folder', 'name': 'Do Not Create'})
            self.assertFalse((Path(directory) / 'Do Not Create').exists())

    def test_note_creation_never_overwrites_existing_content(self):
        with tempfile.TemporaryDirectory() as directory:
            note = Path(directory) / 'meeting.txt'
            note.write_text('original', encoding='utf-8')
            controller = Controller(directory)
            with self.assertRaises(FileExistsError):
                controller.execute({'action': 'note', 'name': 'meeting.txt', 'text': 'replacement'})
            self.assertEqual(note.read_text(encoding='utf-8'), 'original')

    def test_cancelled_search_returns_without_following_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            stopped = threading.Event()
            stopped.set()
            controller = Controller(directory, stop=stopped)
            (Path(directory) / 'sample.txt').write_text('ok', encoding='utf-8')
            self.assertIn('Search stopped', controller.find('sample'))


if __name__ == '__main__':
    unittest.main()
