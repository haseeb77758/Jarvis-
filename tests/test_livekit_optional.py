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
                patch.object(lk, 'agent_path', return_value=Path(__file__).resolve().parents[1] / 'livekit_voice' / 'agent.py'), \
                patch('livekit_bridge.subprocess.Popen', return_value=process) as launch:
            session = lk.LiveKitConsole()
            session.start(consent=True)
            call_args = launch.call_args.args[0]
            self.assertEqual(call_args[-1], 'console')
            self.assertIn('agent.py', str(call_args[1]))
            self.assertNotIn('super-secret-example', str(call_args))
            self.assertNotIn('private-example', str(call_args))
            self.assertEqual(launch.call_args.kwargs['env']['JARVIS_LIVEKIT_ENV_FILE'], str(creds))
            self.assertTrue(session.is_running())
            session.stop()
            process.terminate.assert_called_once()

    def test_billing_cannot_be_started_by_background_import(self):
        source = Path(__file__).resolve().parents[1] / 'livekit_voice' / 'agent.py'
        self.assertTrue(source.is_file())
        ast.parse(source.read_text(encoding='utf-8'))
        with patch('livekit_bridge.subprocess.Popen') as launched:
            lk.LiveKitConsole()
        launched.assert_not_called()

    def test_packaging_includes_agent_and_ui_but_never_keys(self):
        from tools.package_source import source_files, ROOT
        files = {p.as_posix() for p in source_files(ROOT)}
        for entry in ('livekit_bridge.py', 'livekit_window.py',
                      'livekit_voice/agent.py', 'livekit_voice/requirements.txt'):
            self.assertIn(entry, files)
        self.assertNotIn('.env.local', files)
        self.assertFalse(any('.venv' in p for p in files))


if __name__ == '__main__':
    unittest.main()
