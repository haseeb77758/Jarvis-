"""Explicit live, keyless voice smoke test. No microphone or audio playback.

Generates two small public test sentences; writes WAV samples for review.
This optional network check must not be described as passed if the service fails.
"""
from pathlib import Path
import sys
import threading
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from free_voice import generate_mp3, decode_mp3, PROVIDER

out = ROOT / 'dist' / 'free-voice-samples'
out.mkdir(parents=True, exist_ok=True)
for voice, text, name in (
    ('ur-PK-AsadNeural', 'السلام علیکم حسیب! میں جاروس ہوں، آپ کا اسسٹنٹ۔', 'Jarvis-Asad-Urdu.wav'),
    ('en-GB-RyanNeural', 'Hello Haseeb. Jarvis is ready to help you.', 'Jarvis-Ryan-English.wav'),
):
    stop = threading.Event()
    audio = generate_mp3(text, dict(provider=PROVIDER, free_voice=voice, free_rate='-5%'), stop)
    pcm = decode_mp3(audio, stop)
    if len(pcm) < 2400:
        raise RuntimeError('Live voice returned insufficient audio')
    with wave.open(str(out / name), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(pcm)
    print('PASS: live keyless neural speech / MP3 decode / WAV:', voice, len(pcm), 'PCM bytes')
