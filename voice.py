"""Opt-in local microphone transcription and Windows speech output."""
import os
import sys
from pathlib import Path
import threading
import time


def data_dir():
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'HaseebCrafts/Jarvis/voice-model'


def bundled_model():
    path = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'voice-model'
    return path if (path / 'model.bin').is_file() else None


_MODEL = None


def voice_model(download=False):
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    from faster_whisper import WhisperModel
    bundled = bundled_model()
    if bundled:
        _MODEL = WhisperModel(str(bundled), device='cpu', compute_type='int8', cpu_threads=2)
        return _MODEL
    _MODEL = WhisperModel('tiny', device='cpu', compute_type='int8', cpu_threads=2,
                          download_root=str(data_dir()), local_files_only=not download)
    return _MODEL


def setup_voice(stop):
    if stop.is_set():
        raise RuntimeError('Stopped.')
    voice_model(download=True)
    if stop.is_set():
        raise RuntimeError('Stopped. Model download may have completed locally.')
    return 'Voice model ready. Mic 6s dabayein; transcript review ke baad Run karein.'


def listen(stop, language='auto', notify=None):
    import numpy as np
    import sounddevice as sd
    if stop.is_set():
        raise RuntimeError('Stopped.')
    try:
        model = voice_model(download=False)
    except Exception as exc:
        raise RuntimeError('Pehle Setup voice dabayein. Voice model ek dafa download hota hai.') from exc
    try:
        if notify:
            notify('Listening now · 6 seconds · STOP cancels')
        if os.name == 'nt':
            import winsound
            winsound.Beep(1000, 120)
        audio = sd.rec(6 * 16000, samplerate=16000, channels=1, dtype='float32')
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if stop.wait(0.05):
                sd.stop()
                raise RuntimeError('Microphone recording stopped.')
        sd.wait()
    except Exception as exc:
        sd.stop()
        if stop.is_set():
            raise RuntimeError('Microphone stopped.') from exc
        raise RuntimeError('Microphone record nahi hua. Windows Settings → Privacy & security → Microphone mein desktop-app permission aur default mic check karein.') from exc
    if stop.is_set():
        raise RuntimeError('Stopped.')
    if float(np.max(np.abs(audio))) < 0.008:
        raise RuntimeError('Awaaz bohat kam hai. Mic level check karke dobara try karein.')
    if notify:
        notify('Transcribing locally · audio stays on this PC')
    segments, info = model.transcribe(audio.reshape(-1), language=None if language == 'auto' else language,
                                      task='transcribe', beam_size=1, vad_filter=False,
                                      condition_on_previous_text=False)
    result = ' '.join(segment.text.strip() for segment in segments).strip()
    if stop.is_set():
        raise RuntimeError('Stopped. Transcript discarded.')
    if not result:
        raise RuntimeError('Speech samajh nahi aayi. Chhoti aur saaf instruction dobara bolein.')
    return result[:4000]


def normalize_command(text):
    compact = ''.join(c for c in text.casefold() if c.isalnum())
    aliases = {
        'کرومکھولو': 'chrome kholo', 'کرومکھولدو': 'chrome kholo', 'کرومکھولیں': 'chrome kholo',
        'chromekholdo': 'chrome kholo', 'گوگلکرومکھولو': 'chrome kholo',
        'نوٹپیڈکھولو': 'notepad kholo', 'کیلکولیٹرکھولو': 'calculator kholo',
        'ایجکھولو': 'edge kholo', 'اسکرینشاٹ': 'screenshot', 'سکرینشاٹ': 'screenshot',
        'رکجاؤ': 'stop', 'رکجاو': 'stop', 'سٹاپ': 'stop', 'اسٹاپ': 'stop',
        'اوپنکروم': 'chrome kholo', 'اوپننوٹپیڈ': 'notepad kholo',
        'openchromebrowser': 'chrome kholo', 'opengooglechrome': 'chrome kholo',
        'takeascreenshot': 'screenshot', 'takescreenshot': 'screenshot',
        'listwindows': 'windows', 'showwindows': 'windows',
    }
    for app in ('chrome', 'edge', 'notepad', 'calculator', 'paint', 'explorer'):
        aliases['open' + app] = app + ' kholo'
        aliases[app + 'kholo'] = app + ' kholo'
    for phrase in ('stop', 'stopjarvis', 'jarvisstop'):
        aliases[phrase] = 'stop'
    aliases['کیلکولیٹرکھولدو'] = 'calculator kholo'
    return aliases.get(compact, text.strip())


class Speaker:
    def __init__(self, notify=None, settings=None):
        self.notify = notify or (lambda text: None)
        self.settings = settings
        self.cancel = threading.Event()
        self.thread = None

    def stop(self):
        self.cancel.set()

    def speak(self, text):
        config = self.settings.snapshot() if self.settings is not None else {"provider": "Windows"}
        self.stop()
        previous = self.thread
        cancel = threading.Event()
        self.cancel = cancel
        def run():
            if previous:
                previous.join(timeout=2)
            if cancel.is_set():
                return
            if config["provider"] == "Edge Neural (free online)":
                from free_voice import generate_mp3, decode_mp3
                from cloud_voice import play_pcm, VoiceError
                try:
                    compressed = generate_mp3(text, config, cancel)
                    if not cancel.is_set():
                        audio = decode_mp3(compressed, cancel)
                        if not cancel.is_set():
                            play_pcm(audio, cancel)
                except VoiceError as exc:
                    if not cancel.is_set():
                        self.notify(str(exc))
                except Exception:
                    if not cancel.is_set():
                        self.notify("Free voice playback unavailable. Audio output settings check karein.")
                return
            if config["provider"] == "ElevenLabs":
                from cloud_voice import generate_pcm, play_pcm, VoiceError
                try:
                    audio = generate_pcm(text, config, cancel)
                    if not cancel.is_set():
                        play_pcm(audio, cancel)
                except VoiceError as exc:
                    if not cancel.is_set():
                        self.notify(str(exc))
                except Exception:
                    if not cancel.is_set():
                        self.notify("ElevenLabs playback unavailable. Audio output settings check karein; text reply available hai.")
                return
            try:
                import pythoncom
                import win32com.client
                pythoncom.CoInitialize()
                try:
                    engine = win32com.client.Dispatch('SAPI.SpVoice')
                    engine.Rate = 0
                    engine.Speak(str(text)[:1800], 1)
                    while not engine.WaitUntilDone(100):
                        if cancel.is_set():
                            engine.Speak('', 3)
                            break
                finally:
                    pythoncom.CoUninitialize()
            except Exception:
                self.notify('Windows speech voice unavailable. Text replies still work.')
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

