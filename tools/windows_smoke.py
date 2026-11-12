"""Windows smoke: only an isolated synthetic target receives UI input."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import App
import desktop
from core import Controller
import pyautogui
import sounddevice
import faster_whisper
import pythoncom
import win32com.client

root = tk.Tk()
process = None
with tempfile.TemporaryDirectory() as data:
    try:
        app = App(root, data_directory=data)
        root.update_idletasks()
        root.update()
        assert root.winfo_exists()
        assert app.mode.get() == 'Computer commands', 'Local desktop commands must be default'
        assert tuple(app.select.cget('values')) == ('Computer commands',), 'Legacy chatbot mode is still available'
        assert app.entry.winfo_class() == 'Text', 'Multiline local command composer is missing'
        assert app.permission.get() is False
        assert hasattr(app, 'activity_log'), 'Dashboard activity panel missing'
        assert app.entry.winfo_exists() and app.log.winfo_exists()
        assert app.send.winfo_exists() and app.select.winfo_exists()
        assert not hasattr(app, 'ai') and not hasattr(app, 'chat_bridge'), 'Legacy AI chatbot unexpectedly started'
        assert not hasattr(app, 'sandbox_window'), 'Legacy sandbox unexpectedly started'
        assert app.livekit_primary_button.winfo_exists(), 'Primary LiveKit voice button missing'
        app.open_livekit_voice()
        root.update_idletasks()
        root.update()
        assert app.livekit_window.window.winfo_exists(), 'LiveKit setup window missing'
        assert not app.livekit_window.console.is_running(), 'Voice started without explicit user consent'
        app.livekit_window.close()
        app.say('RESULT', 'Dashboard activity check')
        assert 'Dashboard activity check' in app.activity_log.get('1.0', 'end')
        width, height = pyautogui.size()
        image = pyautogui.screenshot()
        assert min(width, height, image.width, image.height) > 0
        script = ROOT / 'tools/ui_target.ps1'
        powershell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        process = subprocess.Popen([str(powershell), '-NoProfile', '-File', str(script)], shell=False)
        desktop.wait_window('Jarvis CI Target', app.stop)
        assert 'Jarvis CI Target' in '\n'.join(desktop.windows())
        snapshot = desktop.inspect('Jarvis CI Target')
        assert 'Jarvis Test Button' in snapshot, snapshot
        desktop.focus('Jarvis CI Target')
        desktop.match_window('Jarvis CI Target').descendants(title='Jarvis test input', control_type='Edit')[0].set_focus()
        Controller(data).execute({'action': 'type_window', 'title': 'Jarvis CI Target', 'text': 'Hello Jarvis'})
        assert 'TYPE PASSED' in desktop.inspect('Jarvis CI Target')
        desktop.invoke('Jarvis CI Target', 'Jarvis Test Button')
        end = time.monotonic() + 5
        while time.monotonic() < end:
            if 'INVOKE PASSED' in desktop.inspect('Jarvis CI Target'):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError('Synthetic button invocation did not update the target label.')
        pythoncom.CoInitialize()
        speaker = win32com.client.Dispatch('SAPI.SpVoice')
        assert speaker.GetVoices().Count > 0
        app.halt()
        assert app.stop.is_set()
        print(f'PASS: GUI, screenshot ({width}x{height}), exact-window focus, targeted typing, exact-button invoke and SAPI voice enumeration.')
        print('No real user microphone/audio or external desktop apps were used.')
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        root.destroy()

