"""Deterministic voice-endpoint tests; never record a real microphone."""
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from adaptive_capture import SpeechGate, record_until_silence


class AdaptiveCaptureTests(unittest.TestCase):
    def _block(self, amplitude=0.0):
        return np.full(480, amplitude, dtype=np.float32)

    def test_short_command_ends_early_after_pause(self):
        gate = SpeechGate()
        for _ in range(5):
            self.assertFalse(gate.feed(self._block()))
        for _ in range(12):
            self.assertFalse(gate.feed(self._block(0.08)))
        ended = False
        for _ in range(35):
            if gate.feed(self._block()):
                ended = True
                break
        self.assertTrue(ended, 'Speech should end after 0.72s of silence')
        self.assertTrue(gate.heard)
        self.assertLess(len(gate.audio()), 2 * 16000)
        self.assertGreater(len(gate.audio()), 16000 // 2)

    def test_short_natural_pause_does_not_cut_off_sentence(self):
        gate = SpeechGate()
        for _ in range(10):
            gate.feed(self._block(0.05))
        for _ in range(12):
            self.assertFalse(gate.feed(self._block()))
        for _ in range(10):
            self.assertFalse(gate.feed(self._block(0.06)))
        self.assertEqual(gate.quiet_seconds, 0.0)
        ended = False
        for _ in range(30):
            if gate.feed(self._block()):
                ended = True
                break
        self.assertTrue(ended)

    def test_quiet_room_only_does_not_make_up_speech(self):
        gate = SpeechGate()
        for _ in range(200):
            self.assertFalse(gate.feed(self._block(0.002)))
        self.assertFalse(gate.heard)
        self.assertEqual(len(gate.audio()), 0)

    def test_stop_before_capture_does_not_open_device(self):
        stop = threading.Event()
        stop.set()
        fake = SimpleNamespace(InputStream=Mock())
        with patch.dict(sys.modules, {'sounddevice': fake}):
            with self.assertRaisesRegex(RuntimeError, 'Stopped'):
                record_until_silence(stop)
        fake.InputStream.assert_not_called()

    def test_fake_stream_releases_early_and_never_stops_global_sound(self):
        frames = ([self._block() for _ in range(4)] +
                  [self._block(0.06) for _ in range(9)] +
                  [self._block() for _ in range(29)])
        sd = SimpleNamespace(stop=Mock())
        class FakeStream:
            def __init__(self, **kwargs):
                self.callback = kwargs['callback']
                self.thread = None

            def __enter__(self):
                def pump():
                    for frame in frames:
                        self.callback(frame.reshape(-1, 1), 480, None, None)
                        time.sleep(0.002)
                self.thread = threading.Thread(target=pump, daemon=True)
                self.thread.start()
                return self

            def __exit__(self, *_args):
                self.thread.join(timeout=1)
        sd.InputStream = FakeStream
        notices = []
        with patch.dict(sys.modules, {'sounddevice': sd}):
            audio = record_until_silence(threading.Event(), notices.append)
        self.assertGreater(len(audio), 16000 // 2)
        self.assertLess(len(audio), 2 * 16000)
        self.assertIn('pause', notices[0])
        sd.stop.assert_not_called()

    def test_idle_stream_has_hard_timeout(self):
        sd = SimpleNamespace()
        class SilentStream:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
        sd.InputStream = SilentStream
        with patch.dict(sys.modules, {'sounddevice': sd}):
            audio = record_until_silence(threading.Event(), max_seconds=0.02)
        self.assertEqual(len(audio), 0)

    def test_cancel_during_capture_is_quick(self):
        stop = threading.Event()
        sd = SimpleNamespace()
        class CancelStream:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                stop.set()
                return self
            def __exit__(self, *_args):
                return False
        sd.InputStream = CancelStream
        with patch.dict(sys.modules, {'sounddevice': sd}):
            with self.assertRaisesRegex(RuntimeError, 'stopped'):
                record_until_silence(stop)

    def test_next_speech_does_not_wait_for_stalled_old_request(self):
        import free_voice as fv
        from voice import Speaker
        settings = Mock()
        settings.snapshot.return_value = {
            'provider': fv.PROVIDER, 'free_voice': 'en-GB-RyanNeural',
            'free_rate': '+0%', 'natural_urdu': False
        }
        entered = threading.Event()
        release = threading.Event()
        second_started = threading.Event()
        def generate(text, _config, _cancel):
            if text == 'first':
                entered.set()
                release.wait(0.8)
            elif text == 'second':
                second_started.set()
            return b'compressed'
        speaker = Speaker(settings=settings)
        try:
            with patch.object(fv, 'generate_mp3', side_effect=generate), patch.object(
                fv, 'decode_mp3', return_value=b'\\0\\0'
            ), patch('cloud_voice.play_pcm'):
                speaker.speak('first')
                self.assertTrue(entered.wait(0.4))
                speaker.speak('second')
                self.assertTrue(second_started.wait(0.45),
                                'New speech must not wait for slow old network work')
                speaker.thread.join(2)
        finally:
            release.set()
            speaker.stop()

    def test_whisper_receives_trimmed_clip_not_six_second_padding(self):
        from voice import listen
        audio = np.full(16000, 0.05, dtype=np.float32)
        model = Mock()
        model.transcribe.return_value = ([SimpleNamespace(text='Open calculator.')], None)
        notices = []
        with patch('voice.voice_model', return_value=model), patch(
            'adaptive_capture.record_until_silence', return_value=audio
        ) as capture:
            transcript = listen(threading.Event(), 'en', notices.append)
        self.assertEqual(transcript, 'Open calculator.')
        self.assertEqual(len(model.transcribe.call_args.args[0]), 16000)
        capture.assert_called_once()
        self.assertIn('Transcribed', notices[-1])


if __name__ == '__main__':
    unittest.main()
