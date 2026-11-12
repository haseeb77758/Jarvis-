"""Free online voice routing, bounded network work, and offline codec/UI tests."""
import asyncio
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import free_voice as fv
from cloud_voice import VoiceSettings, VoiceError
from voice import Speaker


def config():
    return dict(provider=fv.PROVIDER, free_voice=fv.DEFAULT_VOICE, free_rate='-5%', api_key='must-never-be-sent')


class FreeVoiceTests(unittest.TestCase):
    def test_free_provider_saves_without_key_and_restores_voice_speed(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = VoiceSettings(directory)
            settings.save(fv.PROVIDER, settings.voice_id, 'auto', '', free_voice='ur-PK-UzmaNeural', free_rate='+0%')
            restored = VoiceSettings(directory)
            self.assertEqual(restored.provider, fv.PROVIDER)
            self.assertEqual(restored.free_voice, 'ur-PK-UzmaNeural')
            self.assertEqual(restored.free_rate, '+0%')
            self.assertEqual(restored.key, '')
            self.assertFalse(restored.key_path.exists())

    def test_existing_voice_preferences_migrate_with_default_free_voice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice-settings.json'
            path.write_text(json.dumps(dict(provider='Windows', voice_id='oldVoice', language='auto')))
            settings = VoiceSettings(directory)
            self.assertEqual(settings.provider, 'Windows')
            self.assertEqual(settings.free_voice, fv.DEFAULT_VOICE)

    def test_corrupt_free_voice_preference_does_not_crash_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice-settings.json'
            path.write_text(json.dumps(dict(provider=fv.PROVIDER, voice_id='oldVoice', language='auto', free_voice='BAD_URL')))
            settings = VoiceSettings(directory)
            self.assertEqual(settings.provider, 'Windows')
            self.assertEqual(settings.free_voice, fv.DEFAULT_VOICE)

    def test_invalid_voice_or_speed_cannot_become_endpoint_or_ssml(self):
        for voice, rate in (('https://other.test', '-5%'), (fv.DEFAULT_VOICE, '<prosody/>')):
            with self.assertRaises(VoiceError):
                fv.validate_free_voice(voice, rate)

    def test_keyless_request_only_passes_bounded_text_voice_rate(self):
        class Client:
            async def stream(self):
                yield {'type': 'WordBoundary', 'text': 'metadata'}
                yield {'type': 'audio', 'data': b'fake-mp3'}
        module = SimpleNamespace(Communicate=Mock(return_value=Client()))
        with patch.dict(sys.modules, {'edge_tts': module}):
            self.assertEqual(fv.generate_mp3('x' * 3000, config(), threading.Event()), b'fake-mp3')
        call = module.Communicate.call_args
        self.assertEqual(len(call.args[0]), 1800)
        self.assertEqual(call.kwargs, dict(voice=fv.DEFAULT_VOICE, rate='-5%', connect_timeout=10, receive_timeout=15))
        self.assertNotIn('must-never-be-sent', str(call))

    def test_stop_before_request_does_not_start_network(self):
        stop = threading.Event()
        stop.set()
        with patch.object(fv, '_receive') as receive:
            self.assertEqual(fv.generate_mp3('hello', config(), stop), b'')
        receive.assert_not_called()

    def test_stop_cancels_pending_async_network_task(self):
        stop = threading.Event()
        cleaned = []
        async def receive(*args):
            try:
                asyncio.get_running_loop().call_later(0.01, stop.set)
                await asyncio.Event().wait()
            finally:
                cleaned.append(True)
        with patch.object(fv, '_receive', receive):
            self.assertEqual(fv.generate_mp3('hello', config(), stop), b'')
        self.assertEqual(cleaned, [True])

    def test_empty_network_result_and_private_errors_are_safe(self):
        for issue in (None, RuntimeError('PRIVATE_KEY_AND_TEXT')):
            async def receive(*args):
                if issue:
                    raise issue
                return b''
            with patch.object(fv, '_receive', receive), self.assertRaises(VoiceError) as caught:
                fv.generate_mp3('hello', config(), threading.Event())
            self.assertNotIn('PRIVATE_KEY_AND_TEXT', str(caught.exception))

    def test_network_audio_has_a_size_limit(self):
        class Client:
            async def stream(self):
                yield {'type': 'audio', 'data': b'12345678'}
        with patch.dict(sys.modules, {'edge_tts': SimpleNamespace(Communicate=Mock(return_value=Client()))}), \
             patch.object(fv, 'MAX_AUDIO', 4), self.assertRaises(VoiceError):
            fv.generate_mp3('hello', config(), threading.Event())

    def test_free_provider_never_calls_paid_generator(self):
        settings = Mock()
        settings.snapshot.return_value = config()
        speaker = Speaker(settings=settings)
        with patch.object(fv, 'generate_mp3', return_value=b'mp3') as generate, \
             patch.object(fv, 'decode_mp3', return_value=b'\0\0') as decode, \
             patch('cloud_voice.play_pcm') as play, patch('cloud_voice.generate_pcm') as paid:
            speaker.speak('Hello')
            speaker.thread.join(2)
        generate.assert_called_once()
        decode.assert_called_once()
        play.assert_called_once()
        paid.assert_not_called()

    def test_decode_stopped_audio_does_not_import_or_process_codec(self):
        stop = threading.Event()
        stop.set()
        self.assertEqual(fv.decode_mp3(b'any', stop), b'')

    def test_real_pyav_mp3_to_pcm_without_network_or_playback(self):
        try:
            import av
            import numpy as np
        except ImportError:
            self.skipTest('PyAV codec dependency not installed on this host')
        output = io.BytesIO()
        with av.open(output, 'w', format='mp3') as container:
            stream = container.add_stream('mp3', rate=24000)
            stream.layout = 'mono'
            frame = av.AudioFrame.from_ndarray(np.zeros((1, 7200), dtype=np.float32), format='fltp', layout='mono')
            frame.sample_rate = 24000
            for packet in stream.encode(frame):
                container.mux(packet)
            for packet in stream.encode(None):
                container.mux(packet)
        pcm = fv.decode_mp3(output.getvalue(), threading.Event())
        self.assertGreater(len(pcm), 10000)
        self.assertEqual(len(pcm) % 2, 0)

    def test_native_free_voice_form_needs_no_key_and_keeps_test_button_visible(self):
        import tkinter as tk
        from voice_settings_ui import VoiceSettingsWindow
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest('No display: ' + str(exc))
        self.addCleanup(root.destroy)
        with tempfile.TemporaryDirectory() as directory:
            host = SimpleNamespace(root=root, voice_settings=VoiceSettings(directory),
                                   speak_enabled=tk.BooleanVar(root, value=False),
                                   speaker=Mock(), stop=threading.Event(), sandbox_window=None, say=Mock())
            panel = VoiceSettingsWindow(host)
            panel.provider.set(fv.PROVIDER)
            panel.on_provider_change()
            root.update()
            self.assertTrue(panel.free_form.winfo_ismapped())
            self.assertFalse(panel.paid_form.winfo_ismapped())
            with patch('voice_settings_ui.messagebox.showwarning') as warning:
                self.assertFalse(panel.save())
                warning.assert_called_once()
            panel.consent.set(True)
            self.assertTrue(panel.save())
            self.assertEqual(host.voice_settings.key, '')
            panel.test_button.invoke()
            self.assertIn('السلام', host.speaker.speak.call_args.args[0])
            self.assertLess(panel.test_button.winfo_rooty() + panel.test_button.winfo_height(),
                            panel.window.winfo_rooty() + panel.window.winfo_height())
            panel.close()
