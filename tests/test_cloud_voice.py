"""No real API credentials, credit spending, recording, or audible playback."""
import io
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import cloud_voice as cv
from voice import Speaker
from app import App
from diagnostics import check_cloud_speaker


def config():
    return dict(provider='ElevenLabs', voice_id=cv.VOICE_ID, language='ur', api_key='fake-unit-test-key')


class CloudVoiceTests(unittest.TestCase):
    def test_official_request_uses_urdu_v3_pcm_and_only_spoken_text(self):
        response = io.BytesIO(b'\x01\x02' * 100)
        opener = Mock()
        opener.open.return_value = response
        result = cv.generate_pcm('السلام علیکم', config(), threading.Event(), opener)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.elevenlabs.io/v1/text-to-speech/' + cv.VOICE_ID + '?output_format=pcm_24000')
        payload = json.loads(request.data)
        self.assertEqual(payload, dict(text='السلام علیکم', model_id='eleven_v3', language_code='ur'))
        self.assertEqual(request.get_header('Xi-api-key'), 'fake-unit-test-key')
        self.assertEqual(len(result), 200)
        self.assertEqual(opener.open.call_count, 1)

    def test_cancel_before_request_does_not_spend_credits(self):
        stop = threading.Event()
        stop.set()
        opener = Mock()
        self.assertEqual(cv.generate_pcm('hello', config(), stop, opener), b'')
        opener.open.assert_not_called()

    def test_cancel_during_response_discards_audio(self):
        stop = threading.Event()
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        def read(_size):
            stop.set()
            return b'\0\0'
        response.read.side_effect = read
        opener = Mock()
        opener.open.return_value = response
        self.assertEqual(cv.generate_pcm('hello', config(), stop, opener), b'')

    def test_text_bounded_and_auto_language_omitted(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'\0\0')
        selected = config()
        selected['language'] = 'auto'
        cv.generate_pcm('x' * 4000, selected, threading.Event(), opener)
        data = json.loads(opener.open.call_args.args[0].data)
        self.assertEqual(len(data['text']), 1800)
        self.assertNotIn('language_code', data)

    def test_quota_auth_and_network_errors_are_sanitized_and_not_retried(self):
        for issue in (HTTPError('https://example.test/fake-unit-test-key', 401, 'SECRET', {}, None),
                      HTTPError('https://example.test', 429, 'SECRET', {}, None),
                      URLError('fake-unit-test-key')):
            opener = Mock()
            opener.open.side_effect = issue
            with self.assertRaises(cv.VoiceError) as caught:
                cv.generate_pcm('hello', config(), threading.Event(), opener)
            self.assertNotIn('fake-unit-test-key', str(caught.exception))
            self.assertNotIn('SECRET', str(caught.exception))
            self.assertEqual(opener.open.call_count, 1)

    def test_invalid_voice_id_and_key_cannot_become_urls_or_headers(self):
        for field, value in [('voice_id', '../other'), ('api_key', 'bad\nheader')]:
            selected = config()
            selected[field] = value
            opener = Mock()
            with self.assertRaises(cv.VoiceError):
                cv.generate_pcm('hello', selected, threading.Event(), opener)
            opener.open.assert_not_called()

    def test_api_credentials_never_follow_redirects(self):
        self.assertIsNone(cv.NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://other.test'))

    def test_audio_limit_and_invalid_pcm_rejected(self):
        for data, limit in ((b'123', 100), (b'12345678', 4), (b'', 100)):
            opener = Mock()
            opener.open.return_value = io.BytesIO(data)
            with patch.object(cv, 'MAX_AUDIO', limit), self.assertRaises(cv.VoiceError):
                cv.generate_pcm('hello', config(), threading.Event(), opener)

    def test_playback_stops_without_touching_unrelated_sounddevice_streams(self):
        stop = threading.Event()
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.write.side_effect = lambda _data: stop.set()
        sd = Mock()
        sd.RawOutputStream.return_value = stream
        with patch.dict(sys.modules, {'sounddevice': sd}):
            cv.play_pcm(b'\0\0' * 10000, stop)
        self.assertEqual(stream.write.call_count, 1)
        stream.abort.assert_called_once()
        sd.stop.assert_not_called()
        sd.rec.assert_not_called()

    def test_completed_playback_drains_final_samples_instead_of_aborting(self):
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        sd = Mock()
        sd.RawOutputStream.return_value = stream
        with patch.dict(sys.modules, {'sounddevice': sd}):
            cv.play_pcm(b'\0\0' * 100, threading.Event())
        stream.write.assert_called_once()
        stream.abort.assert_not_called()

    def test_session_key_does_not_enter_any_file(self):
        with tempfile.TemporaryDirectory() as directory:
            store = cv.VoiceSettings(directory)
            store.save('ElevenLabs', cv.VOICE_ID, 'ur', 'fake-unit-test-key', remember=False)
            self.assertEqual(store.key, 'fake-unit-test-key')
            self.assertFalse(store.key_path.exists())
            self.assertNotIn('fake-unit-test-key', store.path.read_text())
            self.assertEqual(cv.VoiceSettings(directory).key, '')

    def test_remember_uses_dpapi_and_forget_removes_saved_key(self):
        crypt = Mock()
        crypt.CryptProtectData.return_value = b'ENCRYPTED-UNIT-TEST'
        crypt.CryptUnprotectData.return_value = ('description', b'fake-unit-test-key')
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {'win32crypt': crypt}):
            store = cv.VoiceSettings(directory)
            store.save('ElevenLabs', cv.VOICE_ID, 'auto', 'fake-unit-test-key', remember=True)
            self.assertEqual(store.key_path.read_bytes(), b'ENCRYPTED-UNIT-TEST')
            self.assertNotIn('fake-unit-test-key', store.path.read_text())
            restored = cv.VoiceSettings(directory)
            self.assertEqual(restored.key, 'fake-unit-test-key')
            restored.forget()
            self.assertFalse(restored.key_path.exists())
            self.assertEqual(restored.key, '')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI integration')
    def test_real_windows_dpapi_roundtrip_in_temp_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            store = cv.VoiceSettings(directory)
            store.save('ElevenLabs', cv.VOICE_ID, 'ur', 'fake-unit-test-key', remember=True)
            self.assertNotIn(b'fake-unit-test-key', store.key_path.read_bytes())
            self.assertEqual(cv.VoiceSettings(directory).key, 'fake-unit-test-key')
            store.forget()
            self.assertFalse(store.key_path.exists())

    def test_undecryptable_saved_key_does_not_crash_or_leak(self):
        crypt = Mock()
        crypt.CryptUnprotectData.side_effect = RuntimeError('sensitive detail')
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {'win32crypt': crypt}):
            (Path(directory) / 'elevenlabs-key.bin').write_bytes(b'foreign user data')
            self.assertEqual(cv.VoiceSettings(directory).key, '')

    def test_speaker_routes_to_selected_provider_and_stop_cancels(self):
        settings = Mock()
        settings.snapshot.return_value = config()
        notify = Mock()
        speaker = Speaker(notify, settings=settings)
        with patch.object(cv, 'generate_pcm', return_value=b'\0\0') as generate, \
             patch.object(cv, 'play_pcm') as play:
            speaker.speak('Hello')
            speaker.thread.join(2)
            generate.assert_called_once()
            play.assert_called_once()
            speaker.stop()
            self.assertTrue(speaker.cancel.is_set())
        notify.assert_not_called()

    def test_readiness_does_not_claim_cloud_verified_or_expose_key(self):
        check = check_cloud_speaker(config())
        self.assertEqual(check.state, 'Configured, not verified')
        self.assertNotIn('fake-unit-test-key', check.detail)

    def test_main_stop_also_stops_sandbox_speech(self):
        sandbox = SimpleNamespace(closed=False, stop=Mock())
        host = SimpleNamespace(sandbox_window=sandbox, speaker=Mock(), stop=threading.Event(),
                               generation=1, pending=[], status=Mock())
        App.halt(host)
        sandbox.stop.assert_called_once()
        host.speaker.stop.assert_called_once()

    def test_ai_model_setup_dialog_is_not_a_string_function_call(self):
        host = SimpleNamespace(ai=SimpleNamespace(model='qwen2.5:1.5b'), ai_status=Mock(), root=Mock(), worker=Mock())
        with patch('app.messagebox.askokcancel', return_value=False) as dialog:
            App.confirm_model_setup(host, 'model_missing')
        self.assertIn('Lagbhag 1 GB', dialog.call_args.args[1])
        host.worker.assert_not_called()

    def test_native_settings_require_consent_and_hide_key(self):
        import tkinter as tk
        from voice_settings_ui import VoiceSettingsWindow
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest('No display for native Tk test: ' + str(exc))
        self.addCleanup(root.destroy)
        with tempfile.TemporaryDirectory() as directory:
            host = SimpleNamespace(root=root, voice_settings=cv.VoiceSettings(directory),
                                   speak_enabled=tk.BooleanVar(root, value=False),
                                   speaker=Mock(), stop=threading.Event(), sandbox_window=None, say=Mock())
            panel = VoiceSettingsWindow(host)
            root.update()
            self.assertTrue(panel.key_entry['show'])
            panel.provider.set('ElevenLabs')
            panel.api_key.set('fake-unit-test-key')
            with patch('voice_settings_ui.messagebox.showwarning') as warning:
                self.assertFalse(panel.save())
                warning.assert_called_once()
            self.assertFalse(host.voice_settings.path.exists())
            panel.consent.set(True)
            self.assertTrue(panel.save())
            self.assertEqual(panel.api_key.get(), '')
            self.assertEqual(host.voice_settings.provider, 'ElevenLabs')
            panel.forget()
            self.assertEqual(host.voice_settings.key, '')
            panel.close()
