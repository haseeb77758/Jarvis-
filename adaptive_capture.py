"""Bounded, button-activated microphone capture with early end-of-speech.

No audio is sent over the network, recorded to disk, or captured in background.
This is a lightweight energy gate, not a semantic voice activity detector.
"""
from collections import deque
import queue
import threading
import time

MAX_SECONDS = 6.0
SILENCE_SECONDS = 0.72
MIN_SPEECH_SECONDS = 0.12
BLOCK_SIZE = 480  # 30 ms at 16 kHz


class SpeechGate:
    """Collect audio including a short pre-roll; finish after a spoken pause."""

    def __init__(self, sample_rate=16000, silence_seconds=SILENCE_SECONDS,
                 min_speech_seconds=MIN_SPEECH_SECONDS):
        self.sample_rate = sample_rate
        self.silence_seconds = silence_seconds
        self.min_speech_seconds = min_speech_seconds
        self.preroll = deque(maxlen=12)
        self.parts = []
        self.heard = False
        self.voiced_seconds = 0.0
        self.quiet_seconds = 0.0
        self.sample_count = 0

    def feed(self, samples):
        import numpy as np
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if not len(samples):
            return False
        self.sample_count += len(samples)
        duration = len(samples) / self.sample_rate
        rms = float(np.sqrt(np.mean(samples * samples)))
        # A modest fixed floor keeps CPU cost low. Background noise may still
        # prevent early stopping; the hard six-second cap always applies.
        voiced = rms >= 0.009
        if not self.heard:
            if not voiced:
                self.preroll.append(samples)
                return False
            self.heard = True
            self.parts.extend(self.preroll)
            self.preroll.clear()
        self.parts.append(samples)
        if voiced:
            self.voiced_seconds += duration
            self.quiet_seconds = 0.0
        else:
            self.quiet_seconds += duration
        return (self.voiced_seconds >= self.min_speech_seconds
                and self.quiet_seconds >= self.silence_seconds)

    def audio(self):
        import numpy as np
        return np.concatenate(self.parts) if self.parts else np.empty(0, dtype=np.float32)


def record_until_silence(stop, notify=None, *, sample_rate=16000, max_seconds=MAX_SECONDS):
    """Return local float32 mono audio. STOP only closes our private mic stream."""
    import sounddevice as sd
    if stop.is_set():
        raise RuntimeError('Stopped.')
    frames = queue.Queue(maxsize=64)
    overflow = threading.Event()
    gate = SpeechGate(sample_rate=sample_rate)

    def callback(indata, _frame_count, _time_info, status):
        if stop.is_set():
            return
        # Never block PortAudio's real-time callback.
        if status and getattr(status, 'input_overflow', False):
            overflow.set()
        try:
            frames.put_nowait(indata[:, 0].copy())
        except queue.Full:
            overflow.set()

    if notify:
        notify('Listening · finishes after a pause · maximum 6 seconds')
    # A dedicated InputStream prevents STOP from affecting system-wide audio.
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32',
                        blocksize=BLOCK_SIZE, callback=callback):
        deadline = time.monotonic() + max_seconds
        while time.monotonic() < deadline:
            if stop.is_set():
                raise RuntimeError('Microphone stopped.')
            if overflow.is_set():
                raise RuntimeError('Mic input overloaded. Close heavy apps and try again.')
            try:
                block = frames.get(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if gate.feed(block):
                break
            if gate.sample_count >= sample_rate * max_seconds:
                break
    if stop.is_set():
        raise RuntimeError('Microphone stopped.')
    if overflow.is_set():
        raise RuntimeError('Mic input overloaded. Close heavy apps and try again.')
    return gate.audio()
