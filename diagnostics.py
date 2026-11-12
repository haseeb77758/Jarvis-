"""Read-only device readiness checks. Never record, download, or execute actions."""
from dataclasses import dataclass
import os
from pathlib import Path
import queue
import threading
import tkinter as tk

from core import ollama_status
from voice import bundled_model, data_dir


@dataclass(frozen=True)
class Check:
    name: str
    state: str
    detail: str


def check_ai(model):
    state = ollama_status(model)
    details = {
        'ready': ('Ready', model + ' installed hai. Reply speed aap ke CPU/RAM par depend karegi.'),
        'model_missing': ('Setup needed', model + ' download nahi hua. Setup AI dabayein.'),
        'missing': ('Setup needed', 'Ollama nahi mila. Setup AI se official installer kholein.'),
        'stopped': ('Open Ollama', 'Local service respond nahi kar rahi. Start menu se Ollama kholein, phir Refresh.'),
    }
    status, detail = details.get(state, ('Unavailable', 'AI status check nahi ho saka.'))
    return Check('Local AI chat', status, detail)


def check_microphone():
    try:
        import sounddevice as sd
        device = sd.query_devices(kind='input')
        if device['max_input_channels'] < 1:
            raise RuntimeError('No input channels')
        sd.check_input_settings(channels=1, samplerate=16000, dtype='float32')
        return Check('Microphone', 'Device found', str(device['name']) +
                     ' · 16 kHz input supported. Actual recording/permission Mic button se test hogi.')
    except ImportError:
        return Check('Microphone', 'Setup needed', 'sounddevice missing hai. Jarvis setup dobara chalayein.')
    except Exception:
        return Check('Microphone', 'Check settings',
                     'Default mic ya 16 kHz input unavailable. Windows Sound aur Microphone permissions check karein.')


def check_voice_model():
    try:
        import faster_whisper  # noqa: F401 -- verify native dependency imports too
        path = bundled_model()
        if path is None:
            from huggingface_hub import snapshot_download
            path = Path(snapshot_download('Systran/faster-whisper-tiny',
                                         cache_dir=str(data_dir()), local_files_only=True))
        required = ('model.bin', 'config.json', 'tokenizer.json')
        if not all((path / name).is_file() for name in required):
            raise FileNotFoundError('Incomplete model')
        if not any((path / name).is_file() for name in ('vocabulary.txt', 'vocabulary.json')):
            raise FileNotFoundError('Missing vocabulary')
        return Check('Offline speech recognition', 'Files found',
                     'Whisper tiny files local hain. Mic se actual transcription test karein; koi download nahi kiya gaya.')
    except ImportError:
        return Check('Offline speech recognition', 'Setup needed',
                     'Voice libraries missing hain. Jarvis setup dobara chalayein.')
    except Exception:
        return Check('Offline speech recognition', 'Setup needed',
                     'Complete local voice model verify nahi hua. Setup voice dabayein; download aap ki approval se hoga.')


def check_speaker():
    if os.name != 'nt':
        return Check('Spoken replies', 'Windows required', 'Windows SAPI voice is device par available nahi.')
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            engine = win32com.client.Dispatch('SAPI.SpVoice')
            voices = engine.GetVoices()
            count = voices.Count
            del voices, engine
        finally:
            pythoncom.CoUninitialize()
        if not count:
            raise RuntimeError('No SAPI voices')
        return Check('Spoken replies', 'Voice found',
                     'Windows speech voice available. Test voice se sun kar check karein, phir Speak replies enable karein.')
    except Exception:
        return Check('Spoken replies', 'Check settings',
                     'Windows speech voice load nahi hui. Windows Speech settings aur Jarvis installation check karein.')


def collect_checks(model):
    checks = []
    for name, fn in (
        ('Local AI chat', lambda: check_ai(model)),
        ('Microphone', check_microphone),
        ('Offline speech recognition', check_voice_model),
        ('Spoken replies', check_speaker),
    ):
        try:
            checks.append(fn())
        except Exception:
            # A broken driver/service must not prevent the other checks or UI.
            checks.append(Check(name, 'Unavailable', 'Check complete nahi hua. Setup aur device settings check karein.'))
    return checks


class DiagnosticsWindow:
    def __init__(self, host):
        from dashboard import BG, PANEL, TEXT, MUTED, CYAN, btn, label
        self.host = host
        self.window = tk.Toplevel(host.root)
        self.window.title('Jarvis · Device readiness')
        self.window.configure(bg=BG)
        self.window.geometry('690x610')
        self.window.minsize(580, 560)
        self.closed = False
        self.running = False
        self.results = queue.Queue()
        self.timer = None
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        label(self.window, 'DEVICE READINESS', 18, CYAN, True, bg=BG).pack(anchor='w', padx=20, pady=(18, 5))
        label(self.window, 'Read-only checks · no mic recording, downloads or desktop actions',
              10, MUTED, bg=BG).pack(anchor='w', padx=20, pady=(0, 10))
        self.summary = tk.StringVar(master=self.window, value='Checking this device…')
        label(self.window, '', 10, TEXT, bg=BG, textvariable=self.summary).pack(anchor='w', padx=20)
        self.rows = []
        for title in ('Local AI chat', 'Microphone', 'Offline speech recognition', 'Spoken replies'):
            card = tk.Frame(self.window, bg=PANEL)
            card.pack(fill='x', padx=20, pady=6)
            state = tk.StringVar(master=self.window, value=title + ' · Checking…')
            detail = tk.StringVar(master=self.window, value='Please wait')
            label(card, '', 11, CYAN, True, textvariable=state).pack(anchor='w', padx=12, pady=(9, 3))
            line = label(card, '', 10, TEXT, textvariable=detail, wraplength=610, justify='left')
            line.pack(fill='x', padx=12, pady=(0, 9))
            line.bind('<Configure>', lambda e, w=line: w.configure(wraplength=max(200, e.width)))
            self.rows.append((state, detail))
        actions = tk.Frame(self.window, bg=BG)
        actions.pack(fill='x', padx=18, pady=8)
        self.refresh_button = btn(actions, 'Refresh', self.refresh, True, True)
        self.refresh_button.pack(side='left', padx=2)
        for title, action in [('Setup AI', host.setup_ai), ('Setup voice', host.setup_voice),
                              ('Test voice', host.test_voice)]:
            btn(actions, title, action, compact=True).pack(side='left', padx=3)
        label(self.window, 'Mic recording: close this window and press Mic. Review the transcript before running it.',
              9, MUTED, bg=BG, wraplength=620, justify='left').pack(anchor='w', padx=20, pady=5)
        self.refresh()
        self.poll()

    def refresh(self):
        if self.running or self.closed:
            return
        self.running = True
        self.summary.set('Checking this device…')
        self.refresh_button.configure(state='disabled')
        model = self.host.ai.model
        # Worker never touches Tk, app.busy, command queues, or permissions.
        threading.Thread(target=lambda: self.results.put(collect_checks(model)), daemon=True).start()

    def poll(self):
        if self.closed:
            return
        try:
            checks = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            for (state, detail), check in zip(self.rows, checks):
                state.set(check.name + ' · ' + check.state)
                detail.set(check.detail)
            self.running = False
            self.refresh_button.configure(state='normal')
            self.summary.set('Checks complete · status is a snapshot; Refresh after setup or device changes.')
            self.host.check_ollama()
        self.timer = self.window.after(100, self.poll)

    def close(self):
        self.closed = True
        if self.timer:
            self.window.after_cancel(self.timer)
        self.window.destroy()
