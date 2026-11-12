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

    def test_default_repair_does_not_download_unneeded_models(self):
        """GPT-Live-1 uses Cloud inference; base install must not download models."""
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        completed = Mock(returncode=0, stdout=b'installed', stderr=b'')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.run', return_value=completed) as runner, \
             patch.object(lk, 'preflight_runtime', return_value=True) as preflight:
            message = lk.install_optional()
        self.assertIn('No extra model download needed', message)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args_list[0].args[0][-3:], ['-m', 'pip', '--version'])
        command = runner.call_args_list[1].args[0]
        self.assertEqual(command[1:4], ['-m', 'pip', '--disable-pip-version-check'])
        self.assertNotIn('download-files', command)
        self.assertNotIn('ai-coustics', ' '.join(command))
        preflight.assert_called_once_with(noise_enhancement=False)

    def test_base_install_failure_has_specific_stage_and_local_diagnostic(self):
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        failed = Mock(returncode=1, stdout=b'', stderr=b'No matching distribution found')
        healthy_pip = Mock(returncode=0, stdout=b'pip installed', stderr=b'')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.run', side_effect=[healthy_pip, failed]), \
             patch.object(lk, 'preflight_runtime') as preflight:
            with self.assertRaisesRegex(lk.LiveKitSetupError, 'pip install'):
                lk.install_optional()
            preflight.assert_not_called()
        self.assertIn('No matching distribution found', lk.safe_log_tail())
        self.assertIn('pip install', lk.safe_log_tail())

    def test_optional_model_download_only_if_noise_selected(self):
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        completed = Mock(returncode=0, stdout=b'', stderr=b'')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.run', return_value=completed) as runner, \
             patch.object(lk, 'preflight_runtime', return_value=True) as preflight:
            result = lk.install_optional(noise_enhancement=True)
        self.assertIn('optional AI-Coustics', result)
        self.assertEqual(runner.call_count, 4)
        cmds = [call.args[0] for call in runner.call_args_list]
        self.assertIn('livekit-plugins-ai-coustics~=0.2', cmds[2])
        self.assertIn('download-files', cmds[3])
        preflight.assert_called_once_with(noise_enhancement=True)

    def test_repair_does_not_access_cloud_keys_or_start_metered_session(self):
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        lk.create_credentials_template().write_text(
            'LIVEKIT_URL=wss://local.livekit.cloud\n'
            'LIVEKIT_API_KEY=private-key\n'
            'LIVEKIT_API_SECRET=private-secret\n', encoding='utf-8')
        completed = Mock(returncode=0, stdout=b'', stderr=b'')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.run', return_value=completed) as runner, \
             patch('livekit_bridge.subprocess.Popen') as launch, \
             patch.object(lk, 'preflight_runtime', return_value=True):
            lk.install_optional()
            launch.assert_not_called()
            self.assertEqual(runner.call_count, 2)
            self.assertNotIn('private-key', repr(runner.call_args))
            self.assertNotIn('private-secret', repr(runner.call_args))

    def test_existing_venv_with_missing_pip_is_bootstrapped_before_install(self):
        """User's exact error: venv python exists, but -m pip is missing."""
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        missing = Mock(returncode=1, stdout=b'',
                       stderr=b'No module named pip')
        ok = Mock(returncode=0, stdout=b'', stderr=b'')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.run',
                   side_effect=[missing, ok, ok, ok]) as runner, \
             patch.object(lk, 'preflight_runtime', return_value=True) as preflight:
            result = lk.install_optional()
        commands = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(len(commands), 4)
        self.assertEqual(commands[0][-3:], ['-m', 'pip', '--version'])
        self.assertEqual(commands[1][-4:],
                         ['-m', 'ensurepip', '--upgrade', '--default-pip'])
        self.assertEqual(commands[2][-3:], ['-m', 'pip', '--version'])
        self.assertIn('install', commands[3])
        self.assertNotIn('download-files', ' '.join(map(str, commands)))
        self.assertIn('installed and verified', result)
        preflight.assert_called_once_with(noise_enhancement=False)

    def test_missing_ensurepip_fails_safely_and_preserves_credentials(self):
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        credentials = lk.create_credentials_template()
        secret = ('LIVEKIT_URL=wss://example.livekit.cloud\n'
                  'LIVEKIT_API_KEY=test-private-key\n'
                  'LIVEKIT_API_SECRET=test-private-secret\n')
        credentials.write_text(secret, encoding='utf-8')
        missing_pip = Mock(returncode=1, stdout=b'',
                           stderr=b'No module named pip')
        missing_ensurepip = Mock(returncode=1, stdout=b'',
                                stderr=b'No module named ensurepip')
        with patch.object(lk.os, 'name', 'nt'), \
             patch('livekit_bridge.subprocess.run',
                   side_effect=[missing_pip, missing_ensurepip]) as runner, \
             patch('livekit_bridge.subprocess.Popen') as launch:
            with self.assertRaisesRegex(lk.LiveKitSetupError,
                                        'Python 3.12 installer'):
                lk.install_optional()
            launch.assert_not_called()
        self.assertEqual(runner.call_count, 2)
        self.assertIn('No module named ensurepip', lk.safe_log_tail())
        self.assertEqual(credentials.read_text(encoding='utf-8'), secret)

    def test_existing_pip_is_not_bootstrapped_again(self):
        healthy = Mock(returncode=0, stdout=b'pip 24.0', stderr=b'')
        with patch('livekit_bridge.subprocess.run', return_value=healthy) as run:
            self.assertFalse(lk.ensure_venv_pip())
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-3:],
                         ['-m', 'pip', '--version'])

    def test_recognizes_app_control_blocked_native_blingfire(self):
        message = (
            b'ImportError: DLL load failed while importing _native: '
            b'An Application Control policy has blocked this file.'
        )
        self.assertTrue(lk.is_windows_app_control_block(message))
        self.assertFalse(lk.is_windows_app_control_block(b'No module named pip'))
        self.assertFalse(lk.is_windows_app_control_block(b'Connection timeout'))
        self.assertIn('Windows security OFF na karo',
                      lk.application_control_guidance())

    def test_blocked_native_sdk_preflight_shows_browser_recovery_not_repair(self):
        python = lk.environment_python()
        python.parent.mkdir(parents=True, exist_ok=True)
        python.touch()
        blocked = Mock(
            returncode=1, stdout=b'',
            stderr=b'ImportError: DLL load failed while importing _native: '
                   b'An Application Control policy has blocked this file.',
        )
        with patch('livekit_bridge.subprocess.run', return_value=blocked), \
             patch('livekit_bridge.subprocess.Popen') as launched:
            for noise in (False, True):
                with self.assertRaisesRegex(lk.LiveKitSetupError,
                                            'Application Control'):
                    lk.preflight_runtime(noise_enhancement=noise)
            launched.assert_not_called()
        self.assertIn('Application Control', lk.safe_log_tail())

    def test_native_download_failure_reports_blocked_dll(self):
        blocked = Mock(
            returncode=1, stdout=b'',
            stderr=b'ImportError: DLL load failed while importing _native: '
                   b'An Application Control policy has blocked this file.',
        )
        with patch('livekit_bridge.subprocess.run', return_value=blocked):
            with self.assertRaisesRegex(lk.LiveKitSetupError, 'Application Control'):
                lk._install_command(['python', '-m', 'some-command'],
                                    self.root, 'optional AI-Coustics model download')
        self.assertIn('optional AI-Coustics', lk.safe_log_tail())
        self.assertIn('blocked this file', lk.safe_log_tail())

    def _browser_voice_stub(self):
        from livekit_window import LiveKitVoiceWindow
        from queue import Queue
        host = LiveKitVoiceWindow.__new__(LiveKitVoiceWindow)
        host.closed = False
        host.busy = False
        host.console = Mock()
        host.console.is_running.return_value = False
        host.browser_opened = False
        host.direct_service = None
        host.tool_requests = Queue()
        host.window = Mock()
        host.status = Mock()
        host.refresh = Mock()
        host._launch_direct_browser = Mock(return_value=True)
        return host

    def test_direct_webrtc_requires_local_cloud_keys_but_not_native_dll(self):
        from livekit_bridge import LiveKitSetupError
        window = self._browser_voice_stub()
        self.assertFalse(lk.configured())
        self.assertFalse(lk.environment_python().is_file())
        with patch("direct_livekit.get_project_settings",
                   side_effect=LiveKitSetupError("Project credentials missing")), \
             patch("livekit_window.messagebox.showinfo") as info, \
             patch("livekit_window.preflight_runtime") as preflight:
            self.assertFalse(window.start())
            info.assert_called_once()
            preflight.assert_not_called()
        window._launch_direct_browser.assert_not_called()

    def test_direct_webrtc_launch_needs_approval_and_no_native_python(self):
        window = self._browser_voice_stub()
        server = Mock()
        server.start.return_value = "http://127.0.0.1:48123/#random"
        server.status.return_value = {"active":False}
        with patch("direct_livekit.get_project_settings", return_value={
                "LIVEKIT_URL":"wss://example.livekit.cloud",
                "LIVEKIT_API_KEY":"key",
                "LIVEKIT_API_SECRET":"secretsecret",
             }), \
             patch("livekit_window.messagebox.askyesno", return_value=True), \
             patch("direct_livekit.DirectVoiceService", return_value=server), \
             patch("livekit_window.preflight_runtime") as preflight:
            self.assertTrue(window.start())
        window._launch_direct_browser.assert_called_once_with(
            "http://127.0.0.1:48123/#random~auto")
        self.assertTrue(window.browser_opened)
        window.window.withdraw.assert_called_once()
        preflight.assert_not_called()
        window.console.start.assert_not_called()

    def test_direct_webrtc_cancel_never_opens_or_starts_voice(self):
        window = self._browser_voice_stub()
        with patch("direct_livekit.get_project_settings",
                   return_value={"LIVEKIT_URL":"wss://ok.livekit.cloud"}), \
             patch("livekit_window.messagebox.askyesno", return_value=False):
            self.assertFalse(window.start())
        self.assertFalse(window.browser_opened)
        window._launch_direct_browser.assert_not_called()

    def test_direct_webrtc_launch_failure_never_claims_active_session(self):
        window = self._browser_voice_stub()
        window._launch_direct_browser.return_value = False
        server = Mock()
        server.start.return_value = "http://127.0.0.1:48123/#random"
        with patch("direct_livekit.get_project_settings", return_value={
                "LIVEKIT_URL":"wss://example.livekit.cloud",
                "LIVEKIT_API_KEY":"key",
                "LIVEKIT_API_SECRET":"secretsecret",
             }), \
             patch("livekit_window.messagebox.askyesno", return_value=True), \
             patch("direct_livekit.DirectVoiceService", return_value=server), \
             patch("livekit_window.messagebox.showerror") as notice:
            self.assertFalse(window.start())
        notice.assert_called_once()
        self.assertFalse(window.browser_opened)
        window.window.withdraw.assert_not_called()

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
