"""Local Urdu speech, streaming playback and migration tests (no live services)."""
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

from cloud_voice import VoiceSettings
import free_voice as fv
from roman_urdu_speech import spoken_urdu
from voice import Speaker


class FastUrduVoiceTests(unittest.TestCase):
    def test_locally_converts_conversational_roman_urdu(self):
        result = spoken_urdu('Haseeb, main tayyar hoon. Aap kaise hain?')
        self.assertTrue(any('\u0600' <= char <= '\u06ff' for char in result), repr(result))
        self.assertNotEqual(result, 'Haseeb, main tayyar hoon. Aap kaise hain?')
        print('Roman Urdu voice script sample:', result)

    def test_english_and_urdu_only_inputs_are_unchanged(self):
        self.assertEqual(spoken_urdu('Welcome to the dashboard.'), 'Welcome to the dashboard.')
        self.assertEqual(spoken_urdu('میں تیار ہوں۔'), 'میں تیار ہوں۔')

    def test_default_fast_setting_migrates_without_touching_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice-settings.json'
            path.write_text(json.dumps({
                'provider': fv.PROVIDER,
                'voice_id': 'voice123',
                'language': 'auto',
                'natural_urdu': True,
            }))
            settings = VoiceSettings(directory)
            self.assertTrue(settings.fast_urdu)
            self.assertTrue(settings.snapshot()['stream_audio'])
            settings.save(fv.PROVIDER, settings.voice_id, 'auto', '',
                          fast_urdu=False, natural_urdu=True)
            self.assertFalse(VoiceSettings(directory).fast_urdu)

    def test_invalid_fast_preference_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = VoiceSettings(directory)
            with self.assertRaisesRegex(RuntimeError, 'Urdu speech'):
                settings.save(fv.PROVIDER, settings.voice_id, 'auto', '',
                              fast_urdu='yes')

    def test_fast_urdu_speaker_skips_second_ai_call_and_starts_stream(self):
        settings = Mock()
        settings.snapshot.return_value = {
            'provider': fv.PROVIDER, 'free_voice': fv.DEFAULT_VOICE,
            'free_rate': '+0%', 'natural_urdu': True,
            'fast_urdu': True, 'stream_audio': True,
        }
        converter = Mock(return_value='حسیب، میں تیار ہوں۔')
        ai = Mock()
        streamed = Mock()
        speaker = Speaker(settings=settings, prepare_speech=ai)
        with patch('roman_urdu_speech.spoken_urdu', converter), patch.object(
                fv, 'stream_and_play', streamed), patch.object(
                fv, 'generate_mp3') as legacy:
            speaker.speak('Haseeb, main tayyar hoon.')
            speaker.thread.join(3)
        converter.assert_called_once()
        self.assertEqual(streamed.call_args.args[0], 'حسیب، میں تیار ہوں۔')
        ai.assert_not_called()
        legacy.assert_not_called()

    def test_old_ai_mode_remains_available_when_fast_urdu_disabled(self):
        settings = Mock()
        settings.snapshot.return_value = {
            'provider': fv.PROVIDER, 'free_voice': fv.DEFAULT_VOICE,
            'free_rate': '+0%', 'natural_urdu': True,
            'fast_urdu': False, 'stream_audio': True,
        }
        ai = Mock(return_value='میں حاضر ہوں۔')
        speaker = Speaker(settings=settings, prepare_speech=ai)
        with patch.object(fv, 'stream_and_play') as streamed:
            speaker.speak('Main hazir hoon.')
            speaker.thread.join(3)
        ai.assert_called_once()
        self.assertEqual(streamed.call_args.args[0], 'میں حاضر ہوں۔')


class StreamedAudioTests(unittest.TestCase):
    @staticmethod
    def sample_mp3():
        import av
        import numpy as np
        dest = io.BytesIO()
        with av.open(dest, 'w', format='mp3') as container:
            track = container.add_stream('mp3', rate=24000)
            track.layout = 'mono'
            # 1.2 seconds to ensure the first chunk contains several MP3 frames.
            frame = av.AudioFrame.from_ndarray(
                np.zeros((1, 28800), dtype=np.float32), format='fltp', layout='mono')
            frame.sample_rate = 24000
            for packet in track.encode(frame):
                container.mux(packet)
            for packet in track.encode(None):
                container.mux(packet)
        return dest.getvalue()

    def test_audio_starts_before_all_compressed_bytes_are_received(self):
        sample = self.sample_mp3()
        played = []
        class FakeStream:
            def __init__(self, **kwargs):
                self.settings = kwargs
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return None
            def write(self, data):
                played.append(len(data))
            def abort(self):
                played.append('aborted')
        class FakeClient:
            async def stream(self):
                split = max(1024, int(len(sample) * 0.75))
                yield {'type': 'audio', 'data': sample[:split]}
                self_earliest_playback = bool(played)
                assert self_earliest_playback, 'Audio waited for the full MP3 stream'
                yield {'type': 'audio', 'data': sample[split:]}
        sd = SimpleNamespace(RawOutputStream=FakeStream)
        edge = SimpleNamespace(Communicate=Mock(return_value=FakeClient()))
        notices = []
        with patch.dict(sys.modules, {'sounddevice': sd, 'edge_tts': edge}):
            fv.stream_and_play('السلام علیکم', {
                'free_voice': fv.DEFAULT_VOICE, 'free_rate': '+0%'}, threading.Event(), notices.append)
        self.assertTrue(played)
        self.assertNotIn('aborted', played)
        self.assertIn('playback started', notices[0].lower())

    def test_stop_before_stream_does_not_touch_network(self):
        stop = threading.Event()
        stop.set()
        with patch.object(fv, '_stream_pcm_play') as stream:
            fv.stream_and_play('hello', {
                'free_voice': fv.DEFAULT_VOICE, 'free_rate': '+0%'}, stop)
            stream.assert_not_called()


if __name__ == '__main__':
    unittest.main()
