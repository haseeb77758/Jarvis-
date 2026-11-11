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
from core import Controller, LocalAI, parse_command, parse_plan, safe_child, validate, ollama_status, MODEL


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

    def test_ollama_status_detects_installed_local_model(self):
        def client(models):
            fake = Mock()
            fake.__enter__ = Mock(return_value=io.BytesIO(json.dumps({'models': models}).encode()))
            fake.__exit__ = Mock(return_value=False)
            transport = Mock()
            transport.open.return_value = fake
            return transport
        ready = client([{'name': MODEL}])
        self.assertEqual(ollama_status(opener=ready, executable="ollama.exe"), 'ready')
        request = ready.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/tags')
        self.assertEqual(ready.open.call_args.kwargs['timeout'], 3)
        self.assertEqual(ollama_status(opener=client([{'name': 'other:latest'}]), executable="ollama.exe"), 'model_missing')
        self.assertEqual(ollama_status(opener=client([{'model': MODEL}]), executable="ollama.exe"), 'ready')

    def test_ollama_status_handles_missing_and_stopped_server(self):
        self.assertEqual(ollama_status(executable=""), 'missing')
        transport = Mock()
        transport.open.side_effect = ConnectionError("refused")
        self.assertEqual(ollama_status(opener=transport, executable="ollama.exe"), 'stopped')

    def test_local_ai_protocol_has_fixed_local_url_and_bounded_context(self):
        ai = LocalAI()
        fake = Mock()
        fake.__enter__ = Mock(return_value=io.BytesIO(json.dumps({'message': {'content': 'Salam!'}}).encode()))
        fake.__exit__ = Mock(return_value=False)
        ai.opener = Mock()
        ai.opener.open.return_value = fake
        value = ai.ask([{'role': 'user', 'content': 'Hello'}] * 20)
        self.assertEqual(value, 'Salam!')
        req = ai.opener.open.call_args.args[0]
        self.assertEqual(req.full_url, 'http://127.0.0.1:11434/api/chat')
        body = json.loads(req.data)
        self.assertFalse(body['stream'])
        self.assertEqual(len(body['messages']), 9)
        self.assertEqual(body['options']['num_ctx'], 2048)
        self.assertNotIn('images', body)

    def test_chat_system_promotes_actual_answers_not_echoes(self):
        from core import CHAT_SYSTEM, _looks_like_echo
        self.assertIn("Never merely repeat", CHAT_SYSTEM)
        self.assertTrue(_looks_like_echo("aur sunao", "Aur sunao!"))
        self.assertTrue(_looks_like_echo("assalam ua alaikum", "Assalam u Alaikum!"))
        self.assertFalse(_looks_like_echo("aur sunao", "Main theek hoon! Tum sunao, aaj kya plan hai?"))
        self.assertFalse(_looks_like_echo("computer kholo", "Computer kholne ka tarika yeh hai:"))

    def test_chat_retries_echo_and_returns_new_conversational_reply(self):
        ai = LocalAI()
        responses = [
            {"message": {"content": "Aur sunao!"}},
            {"message": {"content": "Bas theek! Tum batao, aaj kya naya chal raha hai?"}},
        ]
        ai.opener = Mock()
        def responder(*_args, **_kwargs):
            value = responses.pop(0)
            fake = Mock()
            fake.__enter__ = Mock(return_value=io.BytesIO(json.dumps(value).encode()))
            fake.__exit__ = Mock(return_value=False)
            return fake
        ai.opener.open.side_effect = responder
        answer = ai.ask([{"role": "user", "content": "aur sunao"}])
        self.assertIn("Tum batao", answer)
        self.assertEqual(ai.opener.open.call_count, 2)
        first = json.loads(ai.opener.open.call_args_list[0].args[0].data)
        second = json.loads(ai.opener.open.call_args_list[1].args[0].data)
        self.assertGreater(second["options"]["temperature"], first["options"]["temperature"])
        self.assertIn("echoed", second["messages"][0]["content"])

    def test_chat_never_displays_repeated_echo_as_success(self):
        ai = LocalAI()
        ai.opener = Mock()
        fake = Mock()
        fake.__enter__ = Mock(return_value=io.BytesIO(
            json.dumps({"message": {"content": "Aur sunao!"}}).encode()
        ))
        fake.__exit__ = Mock(return_value=False)
        ai.opener.open.return_value = fake
        with self.assertRaisesRegex(RuntimeError, "repeat"):
            ai.ask([{"role": "user", "content": "aur sunao"}])
        self.assertEqual(ai.opener.open.call_count, 2)

    def test_local_ai_connection_failure_is_actionable(self):
        ai = LocalAI()
        ai.opener = Mock()
        ai.opener.open.side_effect = ConnectionError('refused')
        with self.assertRaisesRegex(RuntimeError, 'SETUP-LOCAL-AI'):
            ai.ask([{'role': 'user', 'content': 'Hello'}])


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
