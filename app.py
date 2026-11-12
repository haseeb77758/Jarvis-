"""HASEEB AI Windows 11 desktop workspace. Run START.bat."""
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import webbrowser
import shutil
import subprocess
import re
from memory import PreferenceStore
from voice import Speaker, listen, setup_voice, normalize_command, bundled_model
from core import Controller, LocalAI, CLOUD_URL, parse_command, parse_plan, setup_local_model, ollama_binary, ollama_status, MODEL
from tools.update_windows import check_update, install_update, installed_commit, UpdateError, GitHubAuthenticationRequired, github_cli, launch_github_login
from sandbox_chat import SandboxWindow, SandboxSession

BG, PANEL, TEXT, MUTED, CYAN = '#080e17', '#101c2b', '#eff7fa', '#9ab1c0', '#4ce2d2'
BORDER, SURFACE, DEEP = '#253b4d', '#142537', '#0b1521'


class App:
    def __init__(self, root, data_directory=None):
        self.root = root
        root.title('JARVIS | HASEEB AI — Windows 11')
        root.geometry('1320x840')
        root.minsize(1060, 650)
        root.configure(bg=BG)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        self.generation = 0
        self.history = []
        self.sandbox_session = SandboxSession()
        self.sandbox_window = None
        self.sleeping = False
        self.pending = []
        self.last_plan = []
        self.store = PreferenceStore(data_directory)
        self.speak_enabled = tk.BooleanVar(value=False)
        self.voice_language = tk.StringVar(value='Auto')
        from cloud_voice import VoiceSettings
        self.voice_settings = VoiceSettings(self.store.directory)
        self.speaker = Speaker(lambda text: self.events.put((self.generation, 'notice', text, '', None)), settings=self.voice_settings)
        self.control = Controller(Path.home(), self.stop, self.store.apps)
        self.ai = LocalAI(model=self.store.chat_model)
        self.mode = tk.StringVar(value='Local AI chat')
        self.ai_status = tk.StringVar(value='OLLAMA · CHECKING')
        self.status = tk.StringVar(value='Ready · local controls · no background monitoring')
        self.workspace = tk.StringVar(value=str(self.control.workspace))
        self.permission = tk.BooleanVar(value=False)
        from dashboard import make_dashboard
        make_dashboard(self)
        root.bind('<Escape>', lambda e: self.halt())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        root.after(600, self.check_ollama)
        root.after(2400, self.check_updates_silently)
        if os.name == 'nt':
            threading.Thread(target=self.global_stop, daemon=True).start()
        self.say('HASEEB AI', 'Salam! Yeh Jarvis AI Chat hai. Apna sawal neeche likho aur SEND dabao. Ollama ready na ho to Setup AI dabao. Computer control ke liye Desktop mode alag se select karo.')

    def global_stop(self):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, 1, 0x0002 | 0x0001 | 0x4000, 0x7B):
            self.events.put((self.generation, 'notice', 'Global stop unavailable: use STOP or app-focused Esc and mouse corner fail-safe.', '', None))
            return
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:
                    self.stop.set()
                    self.events.put((-1, 'hotkey', None, '', None))
        finally:
            user32.UnregisterHotKey(None, 1)

    def button(self, parent, text, command, accent=False):
        base = CYAN if accent else SURFACE
        hover = '#a1fff1' if accent else '#204052'
        item = tk.Button(parent, text=text, command=command, bg=base,
                         fg=BG if accent else TEXT, activebackground=hover,
                         activeforeground=BG if accent else TEXT,
                         relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=CYAN if accent else BORDER,
                         padx=15, pady=10, cursor='hand2', font=('Segoe UI', 10, 'bold' if accent else 'normal'))
        item.bind('<Enter>', lambda _e: item.configure(bg=hover) if str(item['state']) != 'disabled' else None)
        item.bind('<Leave>', lambda _e: item.configure(bg=base))
        return item

    def open_voice_settings(self):
        from voice_settings_ui import VoiceSettingsWindow
        current = getattr(self, "voice_settings_window", None)
        if current is not None and not current.closed:
            current.window.deiconify()
            current.window.lift()
            return
        self.voice_settings_window = VoiceSettingsWindow(self)

    def open_diagnostics(self):
        from diagnostics import DiagnosticsWindow
        current = getattr(self, "diagnostics_window", None)
        if current is not None and not current.closed:
            current.window.deiconify()
            current.window.lift()
            return
        self.diagnostics_window = DiagnosticsWindow(self)

    def open_toolkit(self):
        """Open user-driven tools without granting model actions."""
        from enhanced_ui import toolkit_window
        toolkit_window(self)

    def toggle_sleep_mode(self):
        """Explicit session-only sleep: no autonomous background wake listener."""
        if self.busy:
            self.say('NOTICE', 'Current request finish hone dein, phir Sleep/Wake dabayein.')
            return
        self.sleeping = not self.sleeping
        if self.sleeping:
            self.pending.clear()
            self.say('SLEEP', 'Jarvis sleeping hai. Wake up Jarvis likhein ya Toolkit mein Sleep/Wake dabayein. Mic sirf button dabane par sunega.')
            self.status.set('SLEEP MODE · Wake up Jarvis')
        else:
            self.say('WAKE', 'Jarvis awake hai. Commands review aur approval ke sath chalengi.')
            self.status.set('Ready · local controls')

    def open_sandbox(self):
        """Open the chat-only Ollama conversation space, never desktop controls."""
        if self.sandbox_window is not None and not self.sandbox_window.closed:
            if self.sandbox_window.window.winfo_exists():
                self.sandbox_window.window.deiconify()
                self.sandbox_window.window.lift()
                self.sandbox_window.entry.focus_set()
                return
        self.sandbox_window = SandboxWindow(self.root, self, self.sandbox_session)

    def make_ui(self):
        tk.Frame(self.root, bg=CYAN, height=3).pack(fill='x')
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=24, pady=(18, 10))
        tk.Label(header, text='◉', fg=CYAN, bg=BG, font=('Segoe UI', 26)).pack(side='left', padx=(0, 10))
        tk.Label(header, text='JARVIS', fg=TEXT, bg=BG, font=('Segoe UI', 25, 'bold')).pack(side='left')
        tk.Label(header, text='  DESKTOP INTELLIGENCE  /  WINDOWS 11\n  Created by Haseeb Crafts', fg=MUTED, bg=BG,
                 justify='left', font=('Segoe UI', 9)).pack(side='left')
        self.button(header, 'STOP / Esc', self.halt, True).pack(side='right', padx=5)
        self.button(header, 'Resume', self.resume).pack(side='right', padx=5)
        self.button(header, 'Setup local AI', self.setup_ai).pack(side='right', padx=5)
        self.button(header, 'Cloud chat ↗', lambda: webbrowser.open(CLOUD_URL)).pack(side='right', padx=5)
        statebar = tk.Frame(self.root, bg=DEEP, highlightbackground=BORDER, highlightthickness=1)
        statebar.pack(fill='x', padx=24, pady=(2, 2))
        tk.Label(statebar, text='●  SYSTEM STATUS', fg=CYAN, bg=DEEP, font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(13, 18), pady=11)
        tk.Label(statebar, textvariable=self.status, fg=TEXT, bg=DEEP, anchor='w', font=('Segoe UI', 9)).pack(side='left', fill='x', expand=True)
        tk.Label(statebar, text='LOCAL  •  PRIVATE  •  REVIEWED ACTIONS', fg=MUTED, bg=DEEP, font=('Segoe UI', 8)).pack(side='right', padx=14)
        tools = tk.Frame(self.root, bg=BG)
        tools.pack(fill='x', padx=24, pady=12)
        tk.Label(tools, text='QUICK ACTIONS', fg=MUTED, bg=BG, font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 14))
        for text, command in [('Chrome', 'chrome kholo'), ('Notepad', 'notepad kholo'),
                              ('Calculator', 'calculator kholo'), ('Screen', 'screenshot')]:
            self.button(tools, text, lambda c=command: self.submit(c)).pack(side='left', padx=(0, 7))
        self.button(tools, 'New chat', self.clear).pack(side='right')
        tk.Checkbutton(tools, text='Enable mouse / keyboard controls', variable=self.permission,
                       fg=TEXT, bg=BG, selectcolor=PANEL, activebackground=BG, activeforeground=TEXT).pack(side='left', padx=8)
        voicebar = tk.Frame(self.root, bg=BG)
        voicebar.pack(fill='x', padx=24, pady=(0, 12))
        self.button(voicebar, 'Mic · 6 seconds', self.listen_voice, True).pack(side='left', padx=(0, 6))
        self.button(voicebar, 'Setup voice', self.setup_voice).pack(side='left', padx=4)
        self.button(voicebar, 'Test voice', self.test_voice).pack(side='left', padx=4)
        ttk.Combobox(voicebar, textvariable=self.voice_language, state='readonly', width=8,
                     values=['Auto', 'Urdu', 'English']).pack(side='left', padx=6)
        tk.Checkbutton(voicebar, text='Speak replies', variable=self.speak_enabled,
                       bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG).pack(side='left', padx=5)
        self.button(voicebar, 'Memory', self.show_memory).pack(side='right', padx=4)
        self.button(voicebar, 'Save last plan', self.save_plan).pack(side='right', padx=4)
        self.button(voicebar, 'Add app', self.add_app).pack(side='right', padx=4)
        self.button(voicebar, 'Updates ↗', lambda: webbrowser.open('https://github.com/haseeb77758/Jarvis-/actions')).pack(side='right', padx=4)
        loc = tk.Frame(self.root, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        loc.pack(fill='x', padx=24)
        tk.Label(loc, text='  WORKSPACE  ', fg=CYAN, bg=SURFACE, font=('Segoe UI', 9, 'bold')).pack(side='left', padx=10, pady=11)
        tk.Label(loc, textvariable=self.workspace, fg=TEXT, bg=SURFACE, anchor='w').pack(side='left', fill='x', expand=True)
        self.button(loc, 'Choose folder', self.choose).pack(side='right')
        self.log = tk.Text(self.root, bg=DEEP, fg=TEXT, insertbackground=CYAN, relief='flat', wrap='word',
                           highlightthickness=1, highlightbackground=BORDER,
                           selectbackground='#245d67', selectforeground=TEXT,
                           font=('Segoe UI', 11), padx=22, pady=20, state='disabled', spacing3=6)
        self.log.pack(fill='both', expand=True, padx=24, pady=12)
        self.log.tag_config('name', foreground=CYAN, font=('Segoe UI', 10, 'bold'), spacing1=10)
        self.log.tag_config('user', foreground='#a8beec')
        self.log.tag_config('error', foreground='#ffab9f')
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill='x', padx=24, pady=(0, 8))
        style = ttk.Style()
        style.theme_use('clam')
        self.select = ttk.Combobox(bottom, textvariable=self.mode, state='readonly', width=20,
                                  values=['Computer commands', 'Local AI chat', 'AI action plan'])
        self.select.pack(side='left', padx=(0, 8))
        self.entry = tk.Entry(bottom, bg=SURFACE, fg=TEXT, insertbackground=CYAN, relief='flat',
                              highlightthickness=1, highlightbackground=BORDER,
                              highlightcolor=CYAN, font=('Segoe UI', 12))
        self.entry.pack(side='left', fill='x', expand=True, ipady=10)
        self.entry.bind('<Return>', lambda e: self.submit())
        self.send = self.button(bottom, 'Send', self.submit, True)
        self.send.pack(side='left', padx=(8, 0))
        tk.Label(self.root, text='Screen input: enable → review → 4-second countdown. Global STOP: Ctrl+Alt+F12. Mouse corner = fail-safe.\nNo delete, shell execution, automatic messages or payments. Screenshots stay local.',
                 fg=MUTED, bg=BG, justify='left', anchor='w', font=('Segoe UI', 9)).pack(fill='x', padx=26, pady=(0, 15))

    def say(self, name, text):
        # Text tags provide real chat styling without converting model text
        # into commands, HTML, or untrusted UI instructions.
        self.log.configure(state='normal')
        self.log.insert('end', name + '\n', 'error' if 'ERROR' in name else 'user' if name == 'YOU' else 'name')
        body_tag = 'user_body' if name == 'YOU' else (
            'ai_body' if name in {'HASEEB AI', 'HASEEB AI · LOCAL MODEL'} else None
        )
        if body_tag:
            self.log.insert('end', str(text) + '\n\n', body_tag)
        else:
            self.log.insert('end', str(text) + '\n\n')
        self.log.configure(state='disabled')
        self.log.see('end')
        if hasattr(self, 'activity_log') and (name in {'RESULT', 'ERROR', 'ACTION ERROR', 'SCREENSHOT', 'PERMISSION'} or name.startswith('PLAN ERROR')):
            self.activity_log.configure(state='normal')
            self.activity_log.insert('end', name + '  ·  ' + str(text)[:240] + '\n\n')
            self.activity_log.configure(state='disabled')
            self.activity_log.see('end')
        if name in {'RESULT', 'HASEEB AI · LOCAL MODEL'} and self.speak_enabled.get():
            self.speaker.speak(str(text))

    def set_busy(self, on):
        self.busy = on
        self.send.configure(state='disabled' if on else 'normal')
        self.status.set('Working…' if on else ('Stopped · Resume to continue' if self.stop.is_set() else 'Ready · local controls'))

    def test_voice(self):
        if not self.busy and not self.stop.is_set():
            self.speaker.speak('Jarvis ready. Aap ka desktop assistant tayyar hai.')

    def listen_voice(self):
        if self.busy or self.stop.is_set():
            return
        self.speaker.stop()
        language = {'Auto': 'auto', 'Urdu': 'ur', 'English': 'en'}[self.voice_language.get()]
        generation = self.generation
        notify = lambda text: self.events.put((generation, 'voice_status', text, '', None))
        self.worker(lambda: listen(self.stop, language, notify), 'voice')
        self.status.set('Preparing mic / recording 6 seconds · STOP cancels')

    def setup_voice(self):
        if self.busy or self.stop.is_set():
            return
        if bundled_model():
            self.say('NOTICE', 'Voice model is EXE mein included hai. Mic 6s dabayein; pehli recognition CPU par kuch seconds le sakti hai.')
            return
        if messagebox.askokcancel('Setup offline voice',
            'Multilingual Whisper tiny model ek dafa internet se download hoga (approximately 75–100 MB).\nUske baad microphone audio local CPU par process hoti hai. Voice quality mic aur language par depend karegi. Download karein?', parent=self.root):
            self.worker(lambda: setup_voice(self.stop), 'voice_setup')

    def review_voice(self, text):
        normalized = normalize_command(text)
        self.say('HEARD — NOT EXECUTED', text)
        if normalized.casefold() in {'stop', 'stop jarvis', 'jarvis stop'}:
            self.halt()
            return
        if messagebox.askokcancel('Review voice instruction',
            'Heard: ' + text + '\n\nRun: ' + normalized + '\n\nCancel karke entry box mein correction kar sakte hain.', parent=self.root):
            self.submit(normalized)
        else:
            self.entry.delete(0, 'end')
            self.entry.insert(0, normalized)
            self.entry.focus_set()

    def add_app(self):
        if self.busy:
            return
        executable = filedialog.askopenfilename(title='Choose an installed Windows app', filetypes=[('Application', '*.exe')])
        if not executable:
            return
        alias = simpledialog.askstring('App alias', 'English naam dein, jaise photoshop:', parent=self.root)
        if alias and messagebox.askokcancel('Register app', alias + '\n' + executable + '\n\nOnly this executable, without command-line arguments, will be launched.', parent=self.root):
            try:
                self.store.register_app(alias, executable)
                self.say('RESULT', 'App registered. Command: open ' + alias.casefold())
            except Exception as exc:
                self.say('ERROR', str(exc))

    def save_plan(self):
        if self.busy or not self.last_plan:
            self.say('NOTICE', 'Pehle koi valid direct action ya AI plan banayein.')
            return
        name = simpledialog.askstring('Save reviewed shortcut', 'Shortcut name:', parent=self.root)
        if name and messagebox.askokcancel('Save local shortcut', json.dumps(self.last_plan, ensure_ascii=False, indent=2) + '\n\nYeh code upgrade nahi; validated actions ka shortcut hai. Har run pe approvals rahengi.', parent=self.root):
            try:
                self.store.shortcut(name, self.last_plan)
                self.say('RESULT', 'Shortcut saved. Command: shortcut: ' + name)
            except Exception as exc:
                self.say('ERROR', str(exc))

    def show_memory(self):
        if self.busy:
            return
        win = tk.Toplevel(self.root)
        win.title('Local memory — explicit preferences, shortcuts and apps')
        win.geometry('700x440')
        win.configure(bg=BG)
        listing = tk.Listbox(win, bg=PANEL, fg=TEXT, font=('Segoe UI', 11), selectbackground='#245c62')
        listing.pack(fill='both', expand=True, padx=15, pady=15)
        items = []
        for fact in self.store.facts:
            listing.insert('end', 'Preference: ' + fact)
            items.append(('fact', fact))
        for name in self.store.shortcuts:
            listing.insert('end', 'Shortcut: ' + name)
            items.append(('shortcut', name))
        for name in self.store.apps:
            listing.insert('end', 'App: ' + name)
            items.append(('app', name))
        def remove():
            selected = listing.curselection()
            if not selected or not messagebox.askokcancel('Remove saved memory', 'Selected local preference/shortcut/app registration remove karein?', parent=win):
                return
            kind, value = items[selected[0]]
            if kind == 'fact':
                self.store.facts.remove(value)
            elif kind == 'shortcut':
                self.store.shortcuts.pop(value)
            else:
                self.store.apps.pop(value)
            self.store.save()
            win.destroy()
            self.show_memory()
        self.button(win, 'Remove selected', remove).pack(pady=(0, 12))

    def next_action(self):
        if self.pending and not self.stop.is_set():
            self.approve(self.pending.pop(0), from_plan=True)

    def check_ollama(self):
        """Refresh the local status label without blocking the tkinter UI."""
        if not self.root.winfo_exists():
            return
        def check():
            state = ollama_status(model=self.ai.model)
            self.events.put((self.generation, 'ollama_status', state, '', None))
        threading.Thread(target=check, daemon=True).start()

    def check_updates_silently(self):
        """Background notification only: never install code without approval."""
        if self.busy:
            return
        def check():
            try:
                sha, available = check_update(Path(__file__).resolve().parent)
                self.events.put((self.generation, 'update_notice', (sha, available), '', None))
            except (OSError, ValueError, UpdateError):
                # App works offline; a failed update check is not a fatal warning.
                return
        threading.Thread(target=check, daemon=True).start()

    def connect_github(self):
        """Offer official GitHub CLI install or browser sign-in, no copied tokens."""
        executable = github_cli()
        if not executable:
            if messagebox.askyesno(
                'Connect private GitHub',
                'Jarvis repo PRIVATE hai. Update ke liye authenticated GitHub access chahiye.\n\n'
                'Official GitHub CLI install karne ki website kholun?\n'
                'Install ke baad Jarvis restart karke Connect GitHub dobara dabayein.\n\n'
                'Apna password ya access token Jarvis chat mein kabhi share na karein.',
                parent=self.root
            ):
                webbrowser.open('https://cli.github.com/')
            return
        if not messagebox.askyesno(
            'Connect private GitHub',
            'Official GitHub CLI ki browser sign-in window kholun?\n\n'
            'Apne haseeb77758 GitHub account se sign in karein.\n'
            'GitHub CLI apna login Windows credential storage mein manage karta hai.\n'
            'Jarvis is login ko sirf private repo update read karne ke liye use karega.\n\n'
            'Sign in abhi shuru karein?',
            parent=self.root
        ):
            return
        try:
            launch_github_login()
            self.say('UPDATE', 'GitHub CLI browser sign-in shuru ki. Login complete karne ke baad Update Jarvis dobara dabayein.')
        except (UpdateError, OSError) as exc:
            self.say('ERROR', str(exc))

    def update_jarvis(self):
        """One-click review for a specific GitHub main commit."""
        if self.busy:
            return
        self.say('UPDATE', 'Private GitHub repo check ho rahi hai; GitHub CLI login required hai.')
        self.worker(lambda: check_update(Path(__file__).resolve().parent), 'update_check')

    def approve_update(self, result):
        sha, available = result
        if not available:
            self.say('UPDATE', 'Jarvis already latest approved source snapshot par hai.')
            return
        if not messagebox.askyesno(
            'Review Jarvis update',
            'GitHub repo: haseeb77758/Jarvis-\n'
            'New main commit: ' + sha[:12] + '\n\n'
            'Official GitHub source code download hoga. Runtime tests aur GUI '
            'smoke test pass honay par code files replace hongi.\n'
            'Ollama models, user memory aur local shortcuts preserve honge.\n'
            'Failed code update automatically rollback karega.\n'
            'Third-party Python dependencies requirements.txt ke mutabiq '
            'update ho sakti hain, jo rollback mein automatically reverse nahi hoti.\n'
            'Application ko update ke baad restart karna hoga.\n\n'
            'Is update ko approve karte hain?',
            parent=self.root
        ):
            self.say('UPDATE', 'Update cancel kar diya; koi code change nahi hua.')
            return
        self.say('UPDATE', 'Approved GitHub version download aur verification chal rahi hai...')
        self.worker(lambda: install_update(Path(__file__).resolve().parent, sha), 'update_apply')

    def setup_ai(self):
        """Guided local setup: explicit approval for official Ollama and model."""
        if self.busy:
            return
        if self.stop.is_set():
            self.say('HASEEB AI', 'Pehle Resume dabayein.')
            return
        executable = ollama_binary()
        if not executable:
            self.ai_status.set('OLLAMA · INSTALL REQUIRED')
            if messagebox.askokcancel(
                'Install official Ollama',
                'AI jawabat ke liye Ollama alag se install hoga.\n'
                'Official website kholun? Installer ko apne Windows par confirm karna hoga.\n'
                'Windows Security settings change nahi hongi.',
                parent=self.root
            ):
                webbrowser.open('https://ollama.com/download/windows')
            return
        self.ai_status.set('OLLAMA · CHECKING')
        self.worker(lambda: ollama_status(model=self.ai.model, executable=executable), 'setup_status')

    def confirm_model_setup(self, state):
        if state == 'ready':
            self.ai_status.set('OLLAMA · READY')
            self.mode.set('Local AI chat')
            self.say('HASEEB AI', 'Ollama model ready hai. Ab neeche apna sawal likhein.')
            self.entry.focus_set()
            return
        if state == 'stopped':
            self.ai_status.set('OLLAMA · OPEN APP')
            self.say('AI SETUP', 'Ollama install hai magar background service available nahi. Windows Start menu se Ollama khol kar Setup AI dobara dabayein.')
            if messagebox.askokcancel(
                'Ollama is not running',
                'Ollama Start menu se kholna hoga. Kya Ollama app ko abhi launch karun?',
                parent=self.root
            ):
                executable = ollama_binary()
                if not executable:
                    self.say('ERROR', 'Ollama executable nahi mila. Setup AI dabayein.')
                    return
                try:
                    subprocess.Popen([executable, 'serve'], shell=False,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    self.say('AI SETUP', 'Ollama local server start karne ki request bhej di. Setup AI dobara dabayein.')
                except OSError as exc:
                    self.say('ERROR', 'Ollama start nahi hua: ' + str(exc))
            return
        if state == 'model_missing':
            self.ai_status.set('OLLAMA · MODEL NEEDED')
            if messagebox.askokcancel(
                'Install local AI model',
                'Ollama chal raha hai, lekin ' + self.ai.model + ' model missing hai.\n' +
                ('Lagbhag 1.9 GB' if self.ai.model == 'qwen2.5:3b' else 'Lagbhag 1 GB') + ' model download hoga. Internet aur disk space required.\n'
                'Model apne PC par chalega; cloud API key nahi chahiye.\n'
                'Download shuru karun?',
                parent=self.root
            ):
                self.worker(lambda: setup_local_model(self.stop, model=self.ai.model), 'setup')
            return
        self.ai_status.set('OLLAMA · NOT INSTALLED')
        self.say('AI SETUP', 'Ollama install nahi. Setup AI button se official site kholo.')

    def choose(self):
        if self.busy:
            return
        path = filedialog.askdirectory(title='Choose files/search workspace', initialdir=str(self.control.workspace))
        if path:
            self.control.workspace = Path(path).resolve()
            self.workspace.set(path)

    def clear(self):
        if self.busy:
            return
        self.history = []
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.say('HASEEB AI', 'Nayi conversation shuru.')

    def halt(self):
        sandbox = getattr(self, 'sandbox_window', None)
        if sandbox is not None and not sandbox.closed:
            sandbox.stop()
        if hasattr(self, 'speaker'):
            self.speaker.stop()
        self.stop.set()
        self.generation += 1
        self.pending.clear()
        self.status.set('STOPPED · pending results/actions discarded · Resume to continue')
        # Running local inference may finish in Ollama, but its result is discarded.

    def resume(self):
        if self.busy:
            self.say('HASEEB AI', 'Current request finish hone dein. Stop ke baad uska result discard hoga.')
            return
        self.stop.clear()
        self.status.set('Ready · local controls')

    def send_local_chat(self, text):
        """Chat must never be interpreted as a privileged desktop command."""
        messages = self.history + [{'role': 'user', 'content': text}]
        self.worker(
            lambda: self.ai.ask(messages, False, self.store.facts, self.store.apps),
            'ai', text
        )

    def submit(self, value=None):
        if isinstance(value, str) and value.strip().casefold() in {'stop', 'jarvis stop', 'stop jarvis'}:
            self.halt()
            return
        if self.busy:
            return
        text = value if value is not None else self.entry.get().strip()
        if not text:
            return
        if text.casefold() in {'stop', 'jarvis stop', 'stop jarvis'}:
            self.halt()
            return
        if text.casefold() in {'wake up jarvis', 'jarvis wake up', 'jarvis uth jao', 'uth jao jarvis'}:
            if self.sleeping:
                self.toggle_sleep_mode()
            else:
                self.say('WAKE', 'Jarvis already awake hai.')
            return
        if text.casefold() in {'jarvis sleep', 'sleep jarvis', 'jarvis so jao'}:
            if not self.sleeping:
                self.toggle_sleep_mode()
            else:
                self.say('SLEEP', 'Jarvis already sleeping hai.')
            return
        if self.sleeping:
            self.say('SLEEP', 'Jarvis sleep mode mein hai. Wake up Jarvis likhein. STOP hamesha available hai.')
            return
        if self.stop.is_set():
            self.say('HASEEB AI', 'Stopped hai. Pehle Resume dabayein.')
            return
        if len(text) > 4000:
            self.say('HASEEB AI', 'Message 4,000 characters se chhota rakhein.')
            return
        self.entry.delete(0, 'end')
        self.say('YOU', text)
        if self.mode.get() == 'Local AI chat':
            self.send_local_chat(text)
            return
        try:
            if text.casefold().startswith('remember:'):
                fact = text.split(':', 1)[1].strip()
                if messagebox.askokcancel('Save preference locally', fact + '\n\nYeh local AI replies mein preference ke taur par use hogi. Passwords ya secrets save na karein.', parent=self.root):
                    self.store.remember(fact)
                    self.say('RESULT', 'Preference saved. Memory button se view/remove kar sakte hain.')
                return
            if text.casefold().startswith('shortcut:'):
                name = text.split(':', 1)[1].strip().casefold()
                if name not in self.store.shortcuts:
                    raise ValueError('Saved shortcut nahi mila. Memory button check karein.')
                from core import validate
                self.pending = [validate(a) for a in self.store.shortcuts[name]]
                self.next_action()
                return
            action = parse_command(text)
            if action is None:
                alias = re.sub(r'^(?:open|launch)\s+', '', text.casefold()).removesuffix(' kholo').strip()
                if alias in self.store.apps:
                    action = {'action': 'launch_custom', 'alias': alias}
            if action:
                self.last_plan = [action]
                self.approve(action)
            elif self.mode.get() == 'Computer commands':
                self.say('COMMAND HELP', 'windows · inspect: Window title · focus: Window title · wait: Window title\nbutton: Window title | Exact button name\nwrite: Window title | Hello Haseeb · press: Window title | ctrl+s\nremember: reply in Roman Urdu · shortcut: saved name\nchrome kholo · notepad kholo · calculator kholo · edge kholo · explorer kholo\nopen https://example.com\nfolder banao: Client Work\nfind: invoice\nnote: client meeting Monday\nscreenshot\nvolume up · volume down · volume mute · play pause · next song · previous song\nyoutube kholo · whatsapp kholo · google par search karo: website design\nwhatsapp draft: Hello (draft only — never auto sends)\ngoogle: website design · youtube: python tutorial · kitne baje hain\nScreen input: type: Hello Haseeb · key: ctrl+s · click: 300,400\nFree local AI ke liye Local AI chat / AI action plan select karein.')
            else:
                planning = self.mode.get() == 'AI action plan'
                messages = [{'role': 'user', 'content': text}] if planning else self.history + [{'role': 'user', 'content': text}]
                self.worker(lambda: self.ai.ask(messages, planning, self.store.facts, self.store.apps), 'plan' if planning else 'ai', text)
        except Exception as exc:
            self.say('ACTION ERROR', str(exc))

    def approve(self, action, from_plan=False):
        screen = action['action'] in {'type', 'click', 'key', 'focus', 'invoke', 'type_window', 'key_window'}
        if screen and not self.permission.get():
            self.pending.clear()
            self.say('PERMISSION', 'Pehle Enable mouse / keyboard controls tick karein. Har screen action ka review aur countdown hoga.')
            return
        confirm = from_plan or screen or action['action'] in {'folder', 'note', 'launch_custom'}
        if confirm:
            info = json.dumps(action, ensure_ascii=False, indent=2)
            if screen:
                info += '\n\n4 seconds mein focused app ko input milega. Target window select karein.\nClick/Enter sensitive actions submit kar sakte hain: screen aur target khud verify karein.\nCancel ya Esc se rok sakte hain.'
            if not messagebox.askokcancel('Review action', info, parent=self.root):
                self.pending.clear()
                self.say('HASEEB AI', 'Action cancel kar diya.')
                return
        if screen or action['action'] == 'screenshot':
            self.set_busy(True)
            self.root.iconify()
            self.countdown(action, 4, self.generation)
        else:
            self.worker(lambda: self.control.execute(action), 'action')

    def countdown(self, action, left, generation):
        if self.stop.is_set() or generation != self.generation:
            self.root.deiconify()
            self.set_busy(False)
            return
        if left <= 0:
            self.worker(lambda: self.control.execute(action), 'screenshot' if action['action'] == 'screenshot' else 'action')
            return
        self.status.set(f'{left}s · choose target window · mouse corner to abort')
        self.root.after(1000, lambda: self.countdown(action, left - 1, generation))

    def worker(self, fn, kind, user=''):
        self.set_busy(True)
        generation = self.generation
        def job():
            try:
                self.events.put((generation, kind, fn(), user, None))
            except Exception as exc:
                self.events.put((generation, kind, None, user, str(exc)))
        threading.Thread(target=job, daemon=True).start()

    def poll(self):
        try:
            while True:
                generation, kind, value, user, issue = self.events.get_nowait()
                if kind == 'hotkey':
                    self.halt()
                    self.root.deiconify()
                    continue
                if kind == 'update_notice':
                    if generation == self.generation and value[1]:
                        self.status.set('GitHub update available · Update Jarvis')
                    continue
                if kind == 'ollama_status':
                    self.ai_status.set({
                        'ready': 'OLLAMA · READY',
                        'model_missing': 'OLLAMA · MODEL NEEDED',
                        'missing': 'OLLAMA · INSTALL REQUIRED',
                        'stopped': 'OLLAMA · OPEN APP',
                    }.get(value, 'OLLAMA · CHECKING'))
                    continue
                if kind == 'voice_status':
                    if generation == self.generation and not self.stop.is_set():
                        self.status.set(value)
                    continue
                if kind == 'notice':
                    self.say('NOTICE', value)
                    continue
                self.set_busy(False)
                self.root.deiconify()
                if generation != self.generation or self.stop.is_set():
                    self.say('HASEEB AI', 'Stopped request ka result discard kar diya.')
                    continue
                if issue:
                    self.pending.clear()
                    self.say('ERROR', issue)
                    if kind in {'update_check', 'update_apply'} and 'PRIVATE GITHUB ACCESS' in issue:
                        self.say('UPDATE', 'Connect GitHub dabayein. GitHub repo private hai; browser sign-in required hai.')
                elif kind == 'voice':
                    self.review_voice(value)
                elif kind == 'screenshot':
                    self.show_screen(value)
                elif kind == 'update_check':
                    self.approve_update(value)
                elif kind == 'update_apply':
                    self.say('UPDATE', value)
                    self.status.set('Updated · restart Jarvis to use new code')
                    messagebox.showinfo('Jarvis update installed',
                                        value + '\\n\\nClose Jarvis and reopen the Desktop shortcut to activate it.',
                                        parent=self.root)
                elif kind == 'setup_status':
                    self.confirm_model_setup(value)
                elif kind == 'voice_setup':
                    self.say('VOICE SETUP', value)
                    self.status.set('Voice model ready · press Mic to test')
                elif kind == 'setup':
                    self.ai_status.set('OLLAMA · READY')
                    self.mode.set('Local AI chat')
                    self.say('AI SETUP', value)
                    self.entry.focus_set()
                elif kind == 'ai':
                    self.history = (self.history + [{'role': 'user', 'content': user}, {'role': 'assistant', 'content': value}])[-8:]
                    self.say('HASEEB AI · LOCAL MODEL', value)
                elif kind == 'plan':
                    try:
                        actions = parse_plan(value)
                        self.say('AI PLAN — NOT EXECUTED', json.dumps(actions, ensure_ascii=False, indent=2))
                        self.last_plan = actions
                        self.pending = actions.copy()
                    except Exception as exc:
                        self.say('PLAN ERROR', str(exc))
                else:
                    self.say('RESULT', value)
                if not issue and self.pending and not self.busy:
                    self.next_action()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def show_screen(self, image):
        from PIL import ImageTk
        win = tk.Toplevel(self.root)
        win.title('Local screen preview — click image to choose point')
        win.configure(bg=BG)
        w, h = image.size
        preview = image.copy()
        preview.thumbnail((960, 550))
        pw, ph = preview.size
        photo = ImageTk.PhotoImage(preview)
        view = tk.Label(win, image=photo, bg=BG)
        view.image = photo
        view.pack(padx=12, pady=12)
        point = tk.StringVar(value='Click preview to select a primary-screen point. Screenshot is not uploaded.')
        tk.Label(win, textvariable=point, fg=TEXT, bg=BG).pack(padx=12, pady=8)
        selected = []
        def pick(event):
            selected[:] = [min(w - 1, int(event.x * w / pw)), min(h - 1, int(event.y * h / ph))]
            point.set(f'Point: {selected[0]}, {selected[1]} — review before input')
        view.bind('<Button-1>', pick)
        def click():
            if selected:
                x, y = selected
                win.destroy()
                self.approve({'action': 'click', 'x': x, 'y': y})
        self.button(win, 'Review click at selected point', click, True).pack(pady=8)
        def save():
            filename = filedialog.asksaveasfilename(parent=win, defaultextension='.png', filetypes=[('PNG', '*.png')])
            if filename:
                try:
                    image.save(filename)
                    self.say('SCREENSHOT', 'User-selected screenshot saved locally.')
                except Exception as exc:
                    messagebox.showerror('Save failed', str(exc), parent=win)
        self.button(win, 'Save screenshot locally…', save).pack(pady=(0, 12))

    def close(self):
        if self.sandbox_window is not None and not self.sandbox_window.closed:
            self.sandbox_window.close()
        self.speaker.stop()
        self.stop.set()
        self.root.destroy()


if __name__ == '__main__':
    if os.name == 'nt':
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    import sys
    if '--self-test' in sys.argv:
        # Build-runner smoke test: create widgets, import bundled screen dependencies,
        # then exit. Never launch apps, capture user data or perform input here.
        import pyautogui
        import pywinauto
        import faster_whisper
        import edge_tts
        import sounddevice
        import win32com.client
        from PIL import ImageTk
        root.update_idletasks()
        root.update()
        assert root.winfo_exists()
        root.destroy()
    else:
        root.mainloop()

