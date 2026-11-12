"""ElevenLabs TTS over its official HTTPS API; no SDK/FFmpeg dependency.

Only opted-in reply text is sent. Keys are never logged or placed in preferences.
https://elevenlabs.io/docs/api-reference/text-to-speech/convert
"""
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

VOICE_ID = 'JBFqnCBsd6RMkjVDRZzb'
MODEL_ID = 'eleven_v3'
MAX_TEXT = 1800
MAX_AUDIO = 12_000_000


class VoiceError(RuntimeError):
    """A sanitized message safe for the app's activity log."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward API-key headers to another URL/host.
        return None


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='voice-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class VoiceSettings:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'voice-settings.json'
        self.key_path = self.directory / 'elevenlabs-key.bin'
        self.provider = 'Windows'
        self.voice_id = VOICE_ID
        self.language = 'auto'
        self.free_voice = 'ur-PK-AsadNeural'
        self.free_rate = '-5%'
        self.natural_urdu = True
        self.key = ''
        self.load()

    def load(self):
        try:
            if self.path.is_file() and self.path.stat().st_size <= 4096:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                self._validate(data['provider'], data['voice_id'], data['language'])
                from free_voice import validate_free_voice, DEFAULT_VOICE
                free_voice, free_rate = data.get('free_voice', DEFAULT_VOICE), data.get('free_rate', '-5%')
                validate_free_voice(free_voice, free_rate)
                natural_urdu = data.get('natural_urdu', True)
                if type(natural_urdu) is not bool:
                    raise ValueError('Invalid speech setting')
                self.provider, self.voice_id, self.language = data['provider'], data['voice_id'], data['language']
                self.free_voice, self.free_rate = free_voice, free_rate
                self.natural_urdu = natural_urdu
        except (OSError, ValueError, TypeError, KeyError, VoiceError):
            pass
        try:
            if self.key_path.is_file() and self.key_path.stat().st_size <= 8192:
                import win32crypt
                self.key = win32crypt.CryptUnprotectData(self.key_path.read_bytes(), None, None, None, 0)[1].decode('utf-8')
        except Exception:
            # A key encrypted by another Windows user must not crash startup.
            self.key = ''

    @staticmethod
    def _validate(provider, voice_id, language):
        if provider not in ('Windows', 'ElevenLabs', 'Edge Neural (free online)') or language not in ('auto', 'ur', 'en'):
            raise VoiceError('Voice provider/language invalid hai.')
        if not isinstance(voice_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', voice_id):
            raise VoiceError('Valid ElevenLabs voice ID enter karein (URL nahi).')

    def save(self, provider, voice_id, language, api_key, remember=False, *, free_voice=None, free_rate=None, natural_urdu=None):
        from free_voice import validate_free_voice
        free_voice = free_voice or self.free_voice
        free_rate = free_rate or self.free_rate
        validate_free_voice(free_voice, free_rate)
        natural_urdu = self.natural_urdu if natural_urdu is None else natural_urdu
        if type(natural_urdu) is not bool:
            raise VoiceError('Natural Urdu setting invalid hai.')
        self._validate(provider, voice_id, language)
        api_key = api_key.strip()
        if api_key and (not 8 <= len(api_key) <= 1024 or not api_key.isascii() or any(c.isspace() for c in api_key)):
            raise VoiceError('API key invalid hai. Key ko dobara paste karein.')
        if provider == 'ElevenLabs' and not api_key:
            raise VoiceError('ElevenLabs API key enter karein.')
        if api_key and remember:
            try:
                import win32crypt
                encrypted = win32crypt.CryptProtectData(api_key.encode('utf-8'), 'Jarvis ElevenLabs API key', None, None, None, 0)
                _atomic_write(self.key_path, encrypted)
            except Exception:
                raise VoiceError('Windows encrypted key save nahi hui. Remember key off karke session-only use karein.') from None
        elif self.key_path.exists():
            self.key_path.unlink()
        payload = dict(provider=provider, voice_id=voice_id, language=language, free_voice=free_voice, free_rate=free_rate, natural_urdu=natural_urdu)
        _atomic_write(self.path, json.dumps(payload).encode('utf-8'))
        self.provider, self.voice_id, self.language, self.key = provider, voice_id, language, api_key
        self.free_voice, self.free_rate = free_voice, free_rate
        self.natural_urdu = natural_urdu

    def forget(self):
        if self.key_path.exists():
            self.key_path.unlink()
        self.key = ''

    def snapshot(self):
        return dict(provider=self.provider, voice_id=self.voice_id,
                    language=self.language, api_key=self.key, free_voice=self.free_voice, free_rate=self.free_rate,
                    natural_urdu=self.natural_urdu)


def generate_pcm(text, config, cancel, opener=None):
    if cancel.is_set():
        return b''
    VoiceSettings._validate(config['provider'], config['voice_id'], config['language'])
    key = config.get('api_key', '')
    if not isinstance(key, str) or not 8 <= len(key) <= 1024 or not key.isascii() or any(c.isspace() for c in key):
        raise VoiceError('ElevenLabs key missing/invalid hai. Voice settings kholein.')
    text = str(text).strip()[:MAX_TEXT]
    if not text:
        return b''
    payload = dict(text=text, model_id=MODEL_ID)
    if config['language'] != 'auto':
        payload['language_code'] = config['language']
    request = Request(
        'https://api.elevenlabs.io/v1/text-to-speech/' + config['voice_id'] + '?output_format=pcm_24000',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'application/octet-stream'},
        method='POST')
    client = opener or build_opener(ProxyHandler({}), NoRedirect())
    try:
        # No retry: automatic retry could spend credits twice.
        with client.open(request, timeout=15) as response:
            audio = bytearray()
            deadline = time.monotonic() + 60
            while not cancel.is_set():
                chunk = response.read(8192)
                if not chunk:
                    break
                audio.extend(chunk)
                if len(audio) > MAX_AUDIO or time.monotonic() > deadline:
                    raise VoiceError('ElevenLabs audio limit/timeout. Chhota reply try karein.')
        if cancel.is_set():
            return b''
        if not audio or len(audio) % 2:
            raise VoiceError('ElevenLabs se valid PCM audio nahi mili.')
        return bytes(audio)
    except HTTPError as exc:
        messages = {
            401: 'API key reject hui. Voice settings mein key check karein.',
            402: 'ElevenLabs credits/plan check karein.',
            403: 'ElevenLabs access denied. Key permissions aur selected voice check karein.',
            404: 'Voice ID/model nahi mila. Apne ElevenLabs account ka voice ID use karein.',
            422: 'Voice/language request reject hui. Voice settings check karein.',
            429: 'ElevenLabs quota/rate limit. Credits check karein ya baad mein try karein.',
        }
        raise VoiceError(messages.get(exc.code, 'ElevenLabs service error. Baad mein dobara try karein.')) from None
    except (URLError, OSError, TimeoutError):
        raise VoiceError('ElevenLabs connect nahi hua. Internet check karein; text reply available hai.') from None


def play_pcm(audio, cancel):
    if cancel.is_set() or not audio:
        return
    import sounddevice as sd
    # Private stream: STOP must not stop unrelated audio or microphone streams.
    with sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16', latency='low') as stream:
        completed = False
        try:
            for start in range(0, len(audio), 4800):
                if cancel.is_set():
                    break
                stream.write(audio[start:start + 4800])
            completed = not cancel.is_set()
        finally:
            # Normal context exit drains the final samples; STOP/errors discard them.
            if not completed:
                stream.abort()
