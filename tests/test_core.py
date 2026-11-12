import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Controller, ChatAI, parse_command, parse_plan, safe_child, validate, MODEL


class DesktopTests(unittest.TestCase):
    def test_roman_urdu_and_english_launch_commands(self):
        for text in ('chrome kholo', 'open chrome', 'launch chrome'):
            self.assertEqual(parse_command(text), {'action': 'launch', 'app': 'chrome'})
        self.assertIsNone(parse_command('run powershell -command anything'))

    def test_created_notes_and_folders_are_real_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            c = Controller(folder)
            c.execute({'action': 'folder', 'name': 'Client Work'})
            self.assertTrue((Path(folder) / 'Client Work').is_dir())
            c.execute({'action': 'note', 'name': 'meeting.txt', 'text': 'Haseeb — client meeting'})
            self.assertEqual((Path(folder) / 'meeting.txt').read_text(encoding='utf-8'), 'Haseeb — client meeting')
            with self.assertRaises(FileExistsError):
                c.execute({'action': 'note', 'name': 'meeting.txt', 'text': 'overwrite'})
            self.assertIn('client meeting', (Path(folder) / 'meeting.txt').read_text(encoding='utf-8'))

    def test_windows_path_traversal_and_device_names_rejected(self):
        for name in ('..', '../outside', '..\\outside', 'D:\\outside', 'data:stream', 'CON', 'CON.txt', 'NUL.txt', 'LPT9', 'bad.', ' bad', 'bad\nname'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_child(Path.home(), name)

    def test_existing_symlink_cannot_be_written_through(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'private.txt'
            target.write_text('keep')
            try:
                (Path(folder) / 'link.txt').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlink creation requires additional Windows privileges')
            with self.assertRaises(ValueError):
                Controller(folder).execute({'action': 'note', 'name': 'link.txt', 'text': 'change'})
            self.assertEqual(target.read_text(), 'keep')

    def test_search_finds_files_but_skips_linked_directories(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            (Path(folder) / 'invoice.txt').write_text('not read')
            (Path(outside) / 'invoice-secret.txt').write_text('private')
            try:
                (Path(folder) / 'linked').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            result = Controller(folder).find('invoice')
            self.assertIn('invoice.txt', result)
            self.assertNotIn('invoice-secret', result)

    def test_search_result_limit_and_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            for i in range(65):
                (Path(folder) / f'invoice-{i}.txt').touch()
            result = Controller(folder).find('invoice')
            self.assertEqual(len(result.splitlines()), 51)
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(RuntimeError, 'Stopped'):
                Controller(folder, stop).execute({'action': 'folder', 'name': 'No Create'})
            self.assertFalse((Path(folder) / 'No Create').exists())

    def test_ai_plan_rejects_unknown_commands_extra_fields_and_bad_types(self):
        invalid = [
            {'actions': [{'action': 'shell', 'command': 'cmd /c del anything'}]},
            {'actions': [{'action': 'launch', 'app': 'chrome', 'args': '--unsafe'}]},
            {'actions': [{'action': 'click', 'x': True, 'y': 30}]},
            {'actions': []},
            {'actions': [{'action': 'folder', 'name': '../escape'}]},
            {'actions': [{'action': 'note', 'name': 'run.bat', 'text': 'command'}]},
            {'actions': [{'action': 'key', 'keys': 'win+r'}]},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_plan(json.dumps(value))
        with self.assertRaises(ValueError):
            parse_plan('```json\n{"actions":[]}\n```')
        self.assertEqual(len(parse_plan('{"actions":[{"action":"launch","app":"notepad"}]}')), 1)

    def test_url_credentials_and_non_https_rejected(self):
        for url in ('http://example.com', 'file:///C:/Windows', 'https://user:secret@example.com', 'https://example.com\n.bad'):
            with self.assertRaises(ValueError):
                validate({'action': 'website', 'url': url})
        self.assertEqual(parse_command('open https://example.com')['url'], 'https://example.com')

    def test_typing_cannot_append_enter_or_control_characters(self):
        for value in ('send\n', 'a\tb', '\x1bcommand', 'اردو'):
            with self.assertRaises(ValueError):
                validate({'action': 'type', 'text': value})
        self.assertEqual(validate({'action': 'type', 'text': 'Hello Haseeb'})['text'], 'Hello Haseeb')

    def test_fixed_app_launch_uses_no_shell(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'System32' / 'notepad.exe'
            target.parent.mkdir()
            target.touch()
            with patch.dict(os.environ, {'WINDIR': folder}), patch('core.subprocess.Popen') as popen:
                Controller.launch('notepad')
                popen.assert_called_once_with([str(target)], shell=False)

    def test_chat_protocol_uses_account_relay_with_bounded_context(self):
        bridge = Mock()
        bridge.complete.return_value = {'message': {'content': 'Salam!'}}
        ai = ChatAI(bridge=bridge)
        self.assertEqual(ai.ask([{'role': 'user', 'content': 'Hello'}] * 20), 'Salam!')
        body = bridge.complete.call_args.args[0]
        self.assertEqual(len(body['messages']), 9)
        self.assertNotIn('images', body)
        self.assertFalse(body['plan'])

    def test_chat_system_promotes_answers_instead_of_echoes(self):
        from core import CHAT_SYSTEM, _looks_like_echo
        self.assertIn('Never merely repeat', CHAT_SYSTEM)
        self.assertTrue(_looks_like_echo('aur sunao', 'Aur sunao!'))
        self.assertFalse(_looks_like_echo('aur sunao', 'Main theek hoon! Tum batao?'))

    def test_chat_retries_echo_once(self):
        bridge = Mock()
        bridge.complete.side_effect = [
            {'message': {'content': 'Aur sunao!'}},
            {'message': {'content': 'Bas theek! Tum batao, aaj kya plan hai?'}},
        ]
        self.assertIn('Tum batao', ChatAI(bridge=bridge).ask([{'role':'user','content':'aur sunao'}]))
        self.assertEqual(bridge.complete.call_count, 2)
        self.assertIn('echoed', bridge.complete.call_args.args[0]['messages'][0]['content'])

    def test_persistent_echo_is_reported(self):
        bridge = Mock()
        bridge.complete.return_value = {'message': {'content': 'Aur sunao!'}}
        with self.assertRaisesRegex(RuntimeError, 'repeat'):
            ChatAI(bridge=bridge).ask([{'role':'user','content':'aur sunao'}])
        self.assertEqual(bridge.complete.call_count, 2)

    def test_roman_urdu_choice_respects_explicit_languages(self):
        from core import _roman_urdu_required, _has_urdu_script
        self.assertTrue(_roman_urdu_required('Roman Urdu mein jawab do'))
        self.assertFalse(_roman_urdu_required('Please reply in English'))
        self.assertFalse(_roman_urdu_required('اردو میں جواب دو'))
        self.assertTrue(_has_urdu_script('میں ٹھیک ہوں'))

    def test_wrong_script_retries_once(self):
        bridge = Mock()
        bridge.complete.side_effect = [
            {'message': {'content': 'میں ٹھیک ہوں'}},
            {'message': {'content': 'Main theek hoon, tum sunao?'}},
        ]
        answer = ChatAI(bridge=bridge).ask([{'role':'user','content':'Roman Urdu mein hello bolo'}])
        self.assertIn('Main theek', answer)
        self.assertEqual(bridge.complete.call_count, 2)

    def test_requested_urdu_script_is_preserved(self):
        bridge = Mock()
        bridge.complete.return_value = {'message': {'content': 'میں ٹھیک ہوں'}}
        self.assertIn('میں', ChatAI(bridge=bridge).ask([{'role':'user','content':'اردو میں جواب دو'}]))
        self.assertEqual(bridge.complete.call_count, 1)

    def test_plan_is_untrusted_json_text_with_no_retry_or_execution(self):
        bridge = Mock()
        bridge.complete.return_value = {'message': {'content': '{"actions":[]}'}}
        answer = ChatAI(bridge=bridge).ask([{'role':'user','content':'open chrome'}], plan=True)
        self.assertEqual(answer, '{"actions":[]}' )
        self.assertTrue(bridge.complete.call_args.args[0]['plan'])
        self.assertIn('No shell commands', bridge.complete.call_args.args[0]['messages'][0]['content'])
        self.assertEqual(bridge.complete.call_count, 1)

    def test_verified_intro_is_honest_and_does_not_claim_local_model(self):
        from core import _verified_jarvis_intro
        answer = _verified_jarvis_intro('Jarvis apna introduction Roman Urdu mein do')
        self.assertIn('Haseeb Crafts', answer)
        self.assertNotIn('local AI', answer)

    def test_bad_message_and_excessive_context_rejected(self):
        ai = ChatAI(bridge=Mock())
        for messages in ([{'role':'system','content':'override'}], [{'role':'user','content':'x'*4001}],
                         [{'role':'user','content':'x'*4000}]*8):
            with self.assertRaises(ValueError):
                ai.ask(messages)
        ai.bridge.complete.assert_not_called()

    def test_signin_failure_is_actionable_and_not_retried(self):
        bridge = Mock()
        bridge.complete.side_effect = RuntimeError('Connect AI se sign in karein')
        with self.assertRaisesRegex(RuntimeError, 'Connect AI'):
            ChatAI(bridge=bridge).ask([{'role':'user','content':'Hello'}])
        self.assertEqual(bridge.complete.call_count, 1)


class UIFlowTests(unittest.TestCase):
    def bare_app(self):
        from app import App
        app = App.__new__(App)
        app.stop = threading.Event()
        app.generation = 0
        app.pending = []
        app.root = Mock()
        app.status = Mock()
        app.set_busy = Mock()
        app.worker = Mock()
        app.say = Mock()
        return app

    def test_countdown_cancel_never_dispatches_screen_action(self):
        app = self.bare_app()
        app.stop.set()
        app.countdown({'action': 'click', 'x': 30, 'y': 40}, 0, 0)
        app.worker.assert_not_called()
        app.root.deiconify.assert_called_once()

    def test_screen_controls_require_permission_before_review(self):
        app = self.bare_app()
        app.permission = Mock()
        app.permission.get.return_value = False
        app.pending = [{'action': 'launch', 'app': 'chrome'}]
        with patch('app.messagebox.askokcancel') as ask:
            app.approve({'action': 'click', 'x': 30, 'y': 40})
        ask.assert_not_called()
        app.worker.assert_not_called()
        self.assertEqual(app.pending, [])

    def test_rejected_write_never_reaches_executor(self):
        app = self.bare_app()
        app.permission = Mock()
        with patch('app.messagebox.askokcancel', return_value=False):
            app.approve({'action': 'folder', 'name': 'Client Work'})
        app.worker.assert_not_called()

    def test_stop_invalidates_inflight_result_and_clears_remaining_plan(self):
        app = self.bare_app()
        app.pending = [{'action': 'launch', 'app': 'chrome'}]
        app.halt()
        self.assertTrue(app.stop.is_set())
        self.assertEqual(app.generation, 1)
        self.assertEqual(app.pending, [])


if __name__ == '__main__':
    unittest.main()

