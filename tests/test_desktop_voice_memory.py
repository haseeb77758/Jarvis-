import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop
from core import parse_command, validate
from memory import PreferenceStore
from voice import normalize_command


class MemoryTests(unittest.TestCase):
    def test_preferences_and_validated_shortcuts_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PreferenceStore(directory)
            store.remember('Roman Urdu mein short jawab do')
            store.shortcut('work', [{'action': 'launch', 'app': 'notepad'}, {'action': 'wait_window', 'title': 'Notepad'}])
            restored = PreferenceStore(directory)
            self.assertEqual(restored.facts, ['Roman Urdu mein short jawab do'])
            self.assertEqual(len(restored.shortcuts['work']), 2)

    def test_memory_cannot_load_unvalidated_shell_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'preferences.json'
            p.write_text(json.dumps({'facts': ['Preference'], 'shortcuts': {'bad': [{'action': 'shell', 'command': 'cmd.exe'}]}}))
            store = PreferenceStore(directory)
            self.assertEqual(store.shortcuts, {})
            self.assertEqual(store.facts, [])

    def test_explicit_app_registration_has_no_command_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'Demo App.exe'
            exe.touch()
            store = PreferenceStore(Path(directory) / 'data')
            store.register_app('demo', exe)
            self.assertEqual(PreferenceStore(Path(directory) / 'data').apps['demo'], str(exe.resolve()))
            with self.assertRaises(ValueError):
                store.register_app('shell --command', Path(directory) / 'script.bat')
            with self.assertRaises(ValueError):
                validate({'action': 'launch_custom', 'alias': 'demo', 'args': ['dangerous']})

    def test_memory_size_limit_prevents_invalid_persisted_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PreferenceStore(directory)
            with self.assertRaises(ValueError):
                store.remember('x' * 501)
            self.assertFalse(store.path.exists())


class VoiceTests(unittest.TestCase):
    def test_urdu_and_punctuated_english_voice_commands_normalize(self):
        self.assertEqual(normalize_command('Open calculator.'), 'calculator kholo')
        self.assertEqual(normalize_command('کروم کھول دو۔'), 'chrome kholo')
        self.assertEqual(normalize_command('رک جاؤ!'), 'stop')
        self.assertEqual(normalize_command('Jarvis, stop!'), 'stop')
        self.assertEqual(normalize_command('Do not open chrome'), 'Do not open chrome')

    def test_cancelled_microphone_never_starts_capture(self):
        # Stub imports: no actual microphone/device is accessed in this test.
        from voice import listen
        stop = threading.Event()
        stop.set()
        audio = Mock()
        with patch.dict(sys.modules, {'sounddevice': audio, 'numpy': Mock()}):
            with self.assertRaisesRegex(RuntimeError, 'Stopped'):
                listen(stop)
        audio.rec.assert_not_called()


class DesktopTests(unittest.TestCase):
    def test_desktop_commands_require_named_targets(self):
        self.assertEqual(parse_command('focus: Calculator'), {'action': 'focus', 'title': 'Calculator'})
        self.assertEqual(parse_command('button: Calculator | Nine'), {'action': 'invoke', 'title': 'Calculator', 'name': 'Nine'})
        self.assertEqual(parse_command('write: Notepad | Hello')['action'], 'type_window')
        with self.assertRaises(ValueError):
            parse_command('button: unlabeled')
        with self.assertRaises(ValueError):
            validate({'action': 'type_window', 'title': 'Notepad', 'text': 'hello\nsubmit'})

    def window(self, title):
        window = Mock()
        window.window_text.return_value = title
        return window

    def test_ambiguous_window_refuses_to_choose(self):
        fake = Mock()
        fake.windows.return_value = [self.window('Project A - Notepad'), self.window('Project B - Notepad')]
        with patch('desktop.desktop', return_value=fake):
            with self.assertRaisesRegex(RuntimeError, 'Ek se zyada'):
                desktop.match_window('Notepad')
        for window in fake.windows.return_value:
            window.set_focus.assert_not_called()

    def test_exact_window_preferred_over_substring_match(self):
        target = self.window('Notepad')
        fake = Mock()
        fake.windows.return_value = [self.window('Other - Notepad'), target]
        with patch('desktop.desktop', return_value=fake):
            self.assertIs(desktop.match_window('Notepad'), target)

    def test_inspect_does_not_read_edit_values(self):
        target = self.window('Demo')
        entry = Mock()
        entry.element_info.control_type = 'Edit'
        entry.window_text.side_effect = AssertionError('Must not read edit text')
        button = self.window('Save')
        button.element_info.control_type = 'Button'
        button.element_info.is_password = False
        button.children.return_value = []
        target.children.return_value = [entry, button]
        with patch('desktop.match_window', return_value=target):
            text = desktop.inspect('Demo')
        self.assertIn('Button: Save', text)
        entry.window_text.assert_not_called()

    def test_ambiguous_button_never_invokes_or_guesses_coordinates(self):
        target = self.window('Demo')
        controls = [Mock(), Mock()]
        for control in controls:
            control.is_visible.return_value = True
            control.is_enabled.return_value = True
        target.descendants.return_value = controls
        with patch('desktop.match_window', return_value=target):
            with self.assertRaises(RuntimeError):
                desktop.invoke('Demo', 'Save')
        for control in controls:
            control.invoke.assert_not_called()
            control.click_input.assert_not_called()

    def test_cancelled_wait_stops_before_ui_access(self):
        stop = threading.Event()
        stop.set()
        with patch('desktop.match_window') as match:
            with self.assertRaisesRegex(RuntimeError, 'Stopped'):
                desktop.wait_window('Demo', stop)
        match.assert_not_called()


if __name__ == '__main__':
    unittest.main()
