"""Synthetic English speech round trip, never user microphone input."""
from pathlib import Path
import tempfile
import pythoncom
import win32com.client
from faster_whisper import WhisperModel

pythoncom.CoInitialize()
try:
    with tempfile.TemporaryDirectory() as data:
        wav = Path(data) / 'synthetic.wav'
        engine = win32com.client.Dispatch('SAPI.SpVoice')
        stream = win32com.client.Dispatch('SAPI.SpFileStream')
        stream.Open(str(wav), 3)
        try:
            engine.AudioOutputStream = stream
            engine.Speak('Open calculator.', 0)
        finally:
            stream.Close()
        assert wav.is_file() and wav.stat().st_size > 44
        model = WhisperModel('build-assets/voice-model', device='cpu', compute_type='int8', cpu_threads=2)
        segments, info = model.transcribe(str(wav), language='en', beam_size=1, vad_filter=False)
        transcript = ' '.join(s.text for s in segments).lower()
        assert 'calculator' in transcript, repr(transcript)
        print('PASS: Windows speech synthesis to WAV and local Whisper transcription:', transcript)
        print('Urdu quality, live microphone and audio-device playback remain target-PC tests.')
finally:
    pythoncom.CoUninitialize()
