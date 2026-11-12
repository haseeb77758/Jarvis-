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


class _MP3HeaderStripper:
    """Remove optional ID3v2 metadata before incremental MP3 frame decoding."""

    def __init__(self):
        self.pending = bytearray()
        self.ready = False

    def feed(self, data):
        if self.ready:
            return data
        self.pending.extend(data)
        if len(self.pending) < 10:
            return b''
        if self.pending[:3] == b'ID3':
            header = self.pending[:10]
            if any(part & 0x80 for part in header[6:10]):
                raise VoiceError('Invalid audio metadata.')
            size = 10 + ((header[6] & 127) << 21) + ((header[7] & 127) << 14) + ((header[8] & 127) << 7) + (header[9] & 127)
            if header[5] & 0x10:
                size += 10
            if size > 100_000:
                raise VoiceError('Audio metadata too large.')
            if len(self.pending) < size:
                return b''
        else:
            size = 0
        output = bytes(self.pending[size:])
        self.pending.clear()
        self.ready = True
        return output


async def _stream_pcm_play(text, voice, rate, cancel, notify=None):
    """Decode MP3 fragments as they arrive and play PCM without waiting for full TTS."""
    import av
    import sounddevice as sd
    import edge_tts
    import time
    from contextlib import ExitStack

    codec = av.CodecContext.create('mp3', 'r')
    metadata = _MP3HeaderStripper()
    resampler = av.AudioResampler(format='s16', layout='mono', rate=24000)
    compressed_size = 0
    decoded_size = 0
    started = time.monotonic()
    first_sound = False
    stream = None
    client = edge_tts.Communicate(text, voice=voice, rate=rate,
                                  connect_timeout=10, receive_timeout=15)

    with ExitStack() as stack:
        def play_frames(frames):
            nonlocal stream, decoded_size, first_sound
            for frame in frames:
                if cancel.is_set():
                    return
                for converted in resampler.resample(frame):
                    payload = bytes(converted.planes[0])[:converted.samples * 2]
                    if not payload:
                        continue
                    decoded_size += len(payload)
                    if decoded_size > MAX_AUDIO:
                        raise VoiceError('Free voice audio limit. Chhota reply try karein.')
                    if stream is None:
                        stream = stack.enter_context(sd.RawOutputStream(
                            samplerate=24000, channels=1, dtype='int16', latency='low'))
                    if not first_sound:
                        first_sound = True
                        if notify:
                            notify(f'Voice playback started in {time.monotonic() - started:.1f}s')
                    stream.write(payload)

        try:
            async for chunk in client.stream():
                if cancel.is_set():
                    break
                if time.monotonic() - started > 60:
                    raise VoiceError('Free voice service timeout. Internet check karein.')
                if chunk.get('type') != 'audio':
                    continue
                data = chunk.get('data', b'')
                compressed_size += len(data)
                if compressed_size > MAX_AUDIO:
                    raise VoiceError('Free voice audio limit. Chhota reply try karein.')
                for packet in codec.parse(metadata.feed(data)):
                    try:
                        play_frames(codec.decode(packet))
                    except av.error.InvalidDataError:
                        if first_sound:
                            raise
                        # Some MP3 streams send an initial non-audio header packet.
                        # Ignore it only before any decoded audio exists.
            if not cancel.is_set():
                for packet in codec.parse(None):
                    play_frames(codec.decode(packet))
                play_frames(codec.decode(None))
                for converted in resampler.resample(None):
                    payload = bytes(converted.planes[0])[:converted.samples * 2]
                    if payload:
                        decoded_size += len(payload)
                        if decoded_size > MAX_AUDIO:
                            raise VoiceError('Free voice audio limit. Chhota reply try karein.')
                        if stream is None:
                            stream = stack.enter_context(sd.RawOutputStream(
                                samplerate=24000, channels=1, dtype='int16', latency='low'))
                        stream.write(payload)
                if not decoded_size:
                    raise VoiceError('Free voice se valid audio nahi mili.')
        finally:
            # A private stream is aborted only if playback was interrupted.
            if cancel.is_set() and stream is not None:
                stream.abort()


def stream_and_play(text, config, cancel, notify=None):
    """Keyless, bounded online Urdu/English TTS with early playback and STOP."""
    if cancel.is_set():
        return
    validate_free_voice(config['free_voice'], config['free_rate'])
    text = str(text).strip()[:MAX_TEXT]
    if not text:
        return
    try:
        asyncio.run(_stream_pcm_play(text, config['free_voice'],
                                     config['free_rate'], cancel, notify))
    except VoiceError:
        raise
    except ImportError:
        raise VoiceError('Free voice library missing hai. Jarvis update/setup dobara chalayein.') from None
    except Exception:
        if not cancel.is_set():
            raise VoiceError('Streaming free voice unavailable. Internet/audio output check karein.') from None
