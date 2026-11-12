"""Keyless online neural speech via rany2/edge-tts; not an offline voice model."""
import asyncio
import io

from cloud_voice import VoiceError, MAX_TEXT, MAX_AUDIO

PROVIDER = 'Edge Neural (free online)'
VOICES = {
    'Asad · Urdu male': 'ur-PK-AsadNeural',
    'Uzma · Urdu female': 'ur-PK-UzmaNeural',
    'Ryan · English male': 'en-GB-RyanNeural',
    'Sonia · English female': 'en-GB-SoniaNeural',
    'Guy · English male (US)': 'en-US-GuyNeural',
    'Jenny · English female (US)': 'en-US-JennyNeural',
}
DEFAULT_VOICE = 'ur-PK-AsadNeural'
RATES = ('-10%', '-5%', '+0%', '+5%', '+10%')


def validate_free_voice(voice, rate):
    if voice not in VOICES.values() or rate not in RATES:
        raise VoiceError('Free voice/rate invalid hai. List se voice choose karein.')


async def _receive(text, voice, rate, cancel):
    import edge_tts
    audio = bytearray()
    client = edge_tts.Communicate(text, voice=voice, rate=rate,
                                  connect_timeout=10, receive_timeout=15)
    async for chunk in client.stream():
        if cancel.is_set():
            return b''
        if chunk.get('type') == 'audio':
            audio.extend(chunk['data'])
            if len(audio) > MAX_AUDIO:
                raise VoiceError('Free voice audio limit. Chhota reply try karein.')
    return bytes(audio)


async def _cancellable_receive(text, voice, rate, cancel):
    task = asyncio.create_task(_receive(text, voice, rate, cancel))
    try:
        deadline = asyncio.get_running_loop().time() + 60
        while not task.done():
            if cancel.is_set():
                return b''
            if asyncio.get_running_loop().time() > deadline:
                raise VoiceError('Free voice service timeout. Internet check karein.')
            await asyncio.wait((task,), timeout=0.05)
        return task.result() if not cancel.is_set() else b''
    finally:
        if not task.done():
            task.cancel()
        # Retrieve cancellation/errors to avoid background unhandled-task warnings.
        await asyncio.gather(task, return_exceptions=True)


def generate_mp3(text, config, cancel):
    if cancel.is_set():
        return b''
    validate_free_voice(config['free_voice'], config['free_rate'])
    text = str(text).strip()[:MAX_TEXT]
    if not text:
        return b''
    try:
        result = asyncio.run(_cancellable_receive(text, config['free_voice'], config['free_rate'], cancel))
        if cancel.is_set():
            return b''
        if not result:
            raise VoiceError('Free voice se audio nahi aayi. Internet/service check karein.')
        return result
    except VoiceError:
        raise
    except ImportError:
        raise VoiceError('Free voice library missing hai. Jarvis Update/setup dobara chalayein.') from None
    except Exception:
        raise VoiceError('Free voice service unavailable. Internet check karein ya Windows offline voice select karein.') from None


def decode_mp3(audio, cancel):
    """Decode bounded MP3 to mono 24 kHz signed PCM with already-installed PyAV."""
    if cancel.is_set() or not audio:
        return b''
    import av
    pcm = bytearray()
    resampler = av.AudioResampler(format='s16', layout='mono', rate=24000)
    with av.open(io.BytesIO(audio), format='mp3') as container:
        for frame in container.decode(audio=0):
            if cancel.is_set():
                return b''
            for converted in resampler.resample(frame):
                # Exclude any alignment padding in the plane.
                pcm.extend(bytes(converted.planes[0])[:converted.samples * 2])
            if len(pcm) > MAX_AUDIO:
                raise VoiceError('Decoded free voice audio limit.')
        for converted in resampler.resample(None):
            pcm.extend(bytes(converted.planes[0])[:converted.samples * 2])
    if cancel.is_set():
        return b''
    if not pcm or len(pcm) > MAX_AUDIO:
        raise VoiceError('Free voice se valid audio nahi mili.')
    return bytes(pcm)
