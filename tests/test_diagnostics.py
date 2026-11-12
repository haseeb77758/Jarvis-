"""Readiness failures and voice setup state must not masquerade as AI readiness."""
import queue
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import diagnostics
from app import App


class ReadinessTests(unittest.TestCase):
    def test_ai_missing_model_has_actionable_setup_without_generation(self):
        with patch.object(diagnostics, 'ollama_status', return_value='model_missing') as status:
            result = diagnostics.check_ai('qwen2.5:1.5b')
        status.assert_called_once_with('qwen2.5:1.5b')
        self.assertEqual(result.state, 'Setup needed')
        self.assertIn('Setup AI', result.detail)

    def test_microphone_probe_does_not_record_or_play(self):
        sd = Mock()
        sd.query_devices.return_value = {'name': 'Test mic', 'max_input_channels': 1}
        with patch.dict(sys.modules, {'sounddevice': sd}):
            result = diagnostics.check_microphone()
        self.assertEqual(result.state, 'Device found')
        sd.rec.assert_not_called()
        sd.play.assert_not_called()
        sd.check_input_settings.assert_called_once_with(channels=1, samplerate=16000, dtype='float32')

    def test_device_error_is_actionable_not_ready(self):
        sd = Mock()
        sd.query_devices.side_effect = RuntimeError('No audio device')
        with patch.dict(sys.modules, {'sounddevice': sd}):
            result = diagnostics.check_microphone()
        self.assertEqual(result.state, 'Check settings')
        self.assertIn('permissions', result.detail)

    def test_voice_cache_is_local_only_and_incomplete_files_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            hub = Mock()
            hub.snapshot_download.return_value = directory
            with patch.dict(sys.modules, {'faster_whisper': Mock(), 'huggingface_hub': hub}), \
                 patch.object(diagnostics, 'bundled_model', return_value=None):
                self.assertEqual(diagnostics.check_voice_model().state, 'Setup needed')
                for name in ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.json'):
                    (model / name).touch()
                self.assertEqual(diagnostics.check_voice_model().state, 'Files found')
            self.assertTrue(all(call.kwargs['local_files_only'] for call in hub.snapshot_download.call_args_list))

    def test_one_probe_failure_does_not_hide_other_results(self):
        with patch.object(diagnostics, 'check_ai', side_effect=RuntimeError('service failed')), \
             patch.object(diagnostics, 'check_microphone', return_value=diagnostics.Check('Microphone', 'Device found', 'test')), \
             patch.object(diagnostics, 'check_voice_model', return_value=diagnostics.Check('Voice', 'Files found', 'test')), \
             patch.object(diagnostics, 'check_speaker', return_value=diagnostics.Check('Speaker', 'Voice found', 'test')):
            results = diagnostics.collect_checks('test')
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].state, 'Unavailable')
        self.assertEqual(results[1].state, 'Device found')

    def test_voice_setup_completion_preserves_chat_mode_and_ai_status(self):
        host = SimpleNamespace(events=queue.Queue(), generation=3, stop=threading.Event(),
                               root=Mock(), poll=Mock(), set_busy=Mock(), say=Mock(),
                               ai_status=Mock(), mode=Mock(), status=Mock(), pending=[], busy=False)
        host.events.put((3, 'voice_setup', 'Voice model ready', '', None))
        App.poll(host)
        host.ai_status.set.assert_not_called()
        host.mode.set.assert_not_called()
        host.say.assert_called_once_with('VOICE SETUP', 'Voice model ready')
        host.status.set.assert_called_once_with('Voice model ready · press Mic to test')

    def test_cancelled_voice_setup_does_not_claim_readiness(self):
        host = SimpleNamespace(events=queue.Queue(), generation=4, stop=threading.Event(),
                               root=Mock(), poll=Mock(), set_busy=Mock(), say=Mock(),
                               ai_status=Mock(), mode=Mock(), status=Mock(), pending=[], busy=False)
        host.events.put((3, 'voice_setup', 'Voice model ready', '', None))
        App.poll(host)
        host.ai_status.set.assert_not_called()
        host.status.set.assert_not_called()

    def test_native_readiness_window_shows_results_and_closes_cleanly(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest('No display for native Tk check: ' + str(exc))
        self.addCleanup(root.destroy)
        host = SimpleNamespace(root=root, ai=SimpleNamespace(model='test'),
                               setup_ai=Mock(), setup_voice=Mock(), test_voice=Mock(), check_ollama=Mock())
        checks = [diagnostics.Check(name, 'Setup needed', 'Open setup to continue')
                  for name in ('AI', 'Mic', 'Model', 'Speaker')]
        with patch.object(diagnostics, 'collect_checks', return_value=checks), \
             patch.object(diagnostics.threading, 'Thread', side_effect=lambda target, **kw: SimpleNamespace(start=target)):
            panel = diagnostics.DiagnosticsWindow(host)
            root.update()
            self.assertEqual(panel.rows[0][0].get(), 'AI · Setup needed')
            self.assertFalse(panel.running)
            self.assertEqual(str(panel.refresh_button['state']), 'normal')
            panel.refresh_button.invoke()
            panel.poll()
            self.assertEqual(host.check_ollama.call_count, 2)
            panel.close()
            root.update()
            self.assertTrue(panel.closed)

    def test_readiness_window_does_not_touch_widgets_after_close(self):
        panel = diagnostics.DiagnosticsWindow.__new__(diagnostics.DiagnosticsWindow)
        panel.closed = True
        panel.window = Mock()
        panel.results = Mock()
        panel.poll()
        panel.results.get_nowait.assert_not_called()
        panel.window.after.assert_not_called()


if __name__ == '__main__':
    unittest.main()
