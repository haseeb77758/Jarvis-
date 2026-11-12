"""LiveKit integration smoke tests with no cloud requests, secrets, or audio."""
import ast
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import livekit_bridge as lk


class LiveKitOptionalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        patcher = patch.object(lk, 'app_data_root', return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_creds_file_not_in_repository_and_not_overwritten(self):
        path = lk.create_credentials_template()
        self.assertFalse(lk.configured())
        self.assertEqual(path.parent, self.root)
        self.assertEqual(path.name, '.env.local')
        self.assertEqual(set(line.split('=')[0] for line in path.read_text().splitlines()),
                         set(lk.ENV_KEYS))
        path.write_text('LIVEKIT_API_KEY=keep-private\n')
        self.assertEqual(lk.create_credentials_template().read_text(),
                         'LIVEKIT_API_KEY=keep-private\n')

    def test_missing_blank_and_partial_credentials_cannot_start(self):
        client = lk.LiveKitConsole()
        with patch.object(lk.os, 'name', 'nt'):
            with self.assertRaisesRegex(lk.LiveKitSetupError, 'consent'):
                client.start()
            with self.assertRaisesRegex(lk.LiveKitSetupError, 'credentials'):
                client.start(consent=True)

    def test_valid_credentials_are_not_exposed_in_process_arguments(self):
        creds = lk.create_credentials_template()
        creds.write_text(
            'LIVEKIT_URL=wss://example.livekit.cloud\n'
            'LIVEKIT_API_KEY=private-example\n'
            'LIVEKIT_API_SECRET=super-secret-example\n',
            encoding='utf-8',
        )
        self.assertTrue(lk.configured())
        # Inject a mock venv Python without installing or launching anything.
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        process = Mock()
        process.poll.return_value = None
        with patch.object(lk.os, 'name', 'nt'), \
                patch.object(lk, 'agent_path', return_value=Path(__file__).resolve().parents[1] / 'livekit_agent.py'), \
                patch('livekit_bridge.subprocess.Popen', return_value=process) as launch:
            session = lk.LiveKitConsole()
            session.start(consent=True)
            call_args = launch.call_args.args[0]
            self.assertEqual(call_args[-1], 'console')
            self.assertIn('agent.py', str(call_args[1]))
            self.assertNotIn('super-secret-example', str(call_args))
            self.assertNotIn('private-example', str(call_args))
            self.assertEqual(launch.call_args.kwargs['env']['JARVIS_LIVEKIT_ENV_FILE'], str(creds))
            self.assertEqual(launch.call_args.kwargs['env']['JARVIS_LIVEKIT_AI_COUSTICS'], '0')
            self.assertTrue(session.is_running())
            session.stop()
            process.terminate.assert_called_once()

    def test_voice_session_has_hard_user_selected_time_limit(self):
        creds = lk.create_credentials_template()
        creds.write_text(
            'LIVEKIT_URL=wss://example.livekit.cloud\n'
            'LIVEKIT_API_KEY=private-example\n'
            'LIVEKIT_API_SECRET=private-secret\n',
            encoding='utf-8',
        )
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        process = Mock()
        process.poll.return_value = None
        timer = Mock()
        with patch.object(lk.os, 'name', 'nt'), \
                patch.object(lk, 'agent_path',
                             return_value=Path(__file__).resolve().parents[1] / 'livekit_agent.py'), \
                patch('livekit_bridge.subprocess.Popen', return_value=process), \
                patch('livekit_bridge.threading.Timer', return_value=timer) as create_timer:
            session = lk.LiveKitConsole()
            session.start(consent=True, max_minutes=5)
            create_timer.assert_called_once_with(300, session.stop)
            timer.start.assert_called_once()
            self.assertGreater(session.remaining_seconds(), 0)
            session.stop()
            timer.cancel.assert_called_once()
            process.terminate.assert_called_once()
            self.assertEqual(session.remaining_seconds(), 0)

    def test_invalid_maximum_minutes_does_not_launch_cloud(self):
        with patch.object(lk.os, 'name', 'nt'), \
                patch('livekit_bridge.subprocess.Popen') as launch:
            for value in (0, 20, True, '10'):
                with self.assertRaises(lk.LiveKitSetupError):
                    lk.LiveKitConsole().start(consent=True, max_minutes=value)
            launch.assert_not_called()

    def test_no_auto_cloud_start_and_primary_handler_stops_running_session(self):
        from app import App
        instance = App.__new__(App)
        instance.livekit_window = Mock()
        instance.livekit_window.closed = False
        instance.livekit_window.console.is_running.return_value = True
        instance.open_livekit_voice = Mock()
        App.toggle_livekit_voice(instance)
        instance.livekit_window.stop.assert_called_once()
        instance.open_livekit_voice.assert_not_called()

    def test_billing_cannot_be_started_by_background_import(self):
        source = Path(__file__).resolve().parents[1] / 'livekit_agent.py'
        self.assertTrue(source.is_file())
        ast.parse(source.read_text(encoding='utf-8'))
        with patch('livekit_bridge.subprocess.Popen') as launched:
            lk.LiveKitConsole()
        launched.assert_not_called()

    def test_invalid_cloud_url_is_rejected_before_start(self):
        file = lk.create_credentials_template()
        file.write_text('LIVEKIT_URL=https://cloud.livekit.io/projects/test\n'
                        'LIVEKIT_API_KEY=secret-key\n'
                        'LIVEKIT_API_SECRET=secret-value\n', encoding='utf-8')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.Popen') as launched:
            with self.assertRaisesRegex(lk.LiveKitSetupError, 'wss://'):
                lk.LiveKitConsole().start(consent=True)
            launched.assert_not_called()

    def test_crashed_console_reports_exit_instead_of_ready(self):
        process = Mock()
        process.poll.return_value = 1
        timer = Mock()
        session = lk.LiveKitConsole()
        session.process = process
        session.started_at = lk.time.monotonic() - 3
        session.max_minutes = 10
        session._stop_timer = timer
        self.assertFalse(session.is_running())
        self.assertEqual(session.last_exit_code, 1)
        self.assertIn('unexpectedly', session.last_error)
        self.assertIn('exit code 1', session.last_error)
        self.assertIsNone(session.process)
        timer.cancel.assert_called_once()
        self.assertFalse(session.is_running())

    def test_failure_log_scrubs_known_cloud_keys(self):
        credentials = lk.create_credentials_template()
        credentials.write_text('LIVEKIT_URL=wss://valid.livekit.cloud\n'
                               'LIVEKIT_API_KEY=sample-private-key\n'
                               'LIVEKIT_API_SECRET=sample-private-secret\n',
                               encoding='utf-8')
        lk.session_log_path().write_text(
            'LiveKit HTTP auth failed: sample-private-key sample-private-secret '
            'wss://valid.livekit.cloud', encoding='utf-8')
        tail = lk.safe_log_tail()
        self.assertIn('[REDACTED]', tail)
        self.assertNotIn('sample-private-key', tail)
        self.assertNotIn('sample-private-secret', tail)
        self.assertNotIn('valid.livekit.cloud', tail)

    def test_preflight_is_offline_and_does_not_start_a_session(self):
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        completed = Mock(returncode=0)
        with patch('livekit_bridge.subprocess.run', return_value=completed) as run, \
             patch('livekit_bridge.subprocess.Popen') as launch:
            self.assertTrue(lk.preflight_runtime())
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[1], '-c')
            self.assertIn('livekit.agents', cmd[2])
            self.assertNotIn('LIVEKIT_API_SECRET', repr(cmd))
            launch.assert_not_called()

    def test_packaging_includes_agent_and_ui_but_never_keys(self):
        from tools.package_source import source_files, ROOT
        files = {p.as_posix() for p in source_files(ROOT)}
        for entry in ('livekit_bridge.py', 'livekit_window.py',
                      'livekit_agent.py', 'livekit_requirements.txt'):
            self.assertIn(entry, files)
        self.assertNotIn('.env.local', files)
        self.assertFalse(any('.venv' in p for p in files))


if __name__ == '__main__':
    unittest.main()
