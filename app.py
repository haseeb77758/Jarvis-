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
from core import Controller, parse_command
from gemini_chat import GeminiClient, GeminiStore, open_settings as gemini_settings
from tools.update_windows import check_update, install_update, installed_commit, UpdateError, GitHubAuthenticationRequired, github_cli, launch_github_login

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
        self.livekit_window = None
        self.livekit_voice_state = tk.StringVar(value='LIVEKIT · OFF · click Talk Live to begin')
        self.sleeping = False
        self.pending = []
        self.last_plan = []
        self.store = PreferenceStore(data_directory)
        self.gemini_store = GeminiStore()
        self.control = Controller(Path.home(), self.stop, self.store.apps)
        # Gemini is explicit opt-in text chat; LiveKit remains a separate
        # consented voice provider. No legacy relay is started.
        self.mode = tk.StringVar(value='Computer commands')
        self.status = tk.StringVar(value='Ready · local controls · no background monitoring')
        self.workspace = tk.StringVar(value=str(self.control.workspace))
        self.permission = tk.BooleanVar(value=False)
        from dashboard import make_dashboard
        make_dashboard(self)
        root.bind('<Escape>', lambda e: self.halt())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        root.after(2400, self.check_updates_silently)
        if os.name == 'nt':
            threading.Thread(target=self.global_stop, daemon=True).start()
        self.say('JARVIS', 'Local commands ready. Gemini AI chat ke liye Gemini Setup mein API key save karein, phir Gemini AI chat mode select karein. LiveKit voice alag optional mode hai. AI chat Windows actions automatically execute nahi karti.')

    def global_stop(self):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        # Other applications may already own Ctrl+Alt+F12. Try a second
        # reviewed emergency chord; never replace or intercept another app's key.
        shortcuts = (
            (0x0002 | 0x0001 | 0x4000, 'Ctrl+Alt+F12'),
            (0x0002 | 0x0004 | 0x4000, 'Ctrl+Shift+F12'),
        )
        active = None
        for modifiers, label in shortcuts:
            if user32.RegisterHotKey(None, 1, modifiers, 0x7B):
                active = label
                break
        if active is None:
            self.events.put((self.generation, 'notice',
                             'Global STOP hotkeys occupied. Use the large STOP button or app-focused Esc.',
                             '', None))
            return
        if active != 'Ctrl+Alt+F12':
            self.events.put((self.generation, 'notice',
                             'Global STOP available on ' + active +
                             ' (Ctrl+Alt+F12 is used by another application).', '', None))
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

    def open_livekit_voice(self):
        """Open reusable LiveKit primary-voice settings without starting billing."""
        from livekit_window import LiveKitVoiceWindow
        current = getattr(self, 'livekit_window', None)
        if current is not None and not current.closed:
            current.window.deiconify()
            current.window.lift()
            return
        self.livekit_window = LiveKitVoiceWindow(self)

    def open_gemini_settings(self):
        """Show the opt-in Gemini API key dialog; never reveal stored secrets."""
        open_settings(self.root, self.gemini_store)

    def toggle_livekit_voice(self):
        """Primary voice control: user-clicked start with explicit cloud consent."""
        current = getattr(self, 'livekit_window', None)
        if current is not None and not current.closed:
            direct = getattr(current, "direct_service", None)
            if current.console.is_running() or (
                    direct is not None and direct.status()["active"]):
                current.stop()
                return
        self.open_livekit_voice()
        current = getattr(self, 'livekit_window', None)
        if current is not None and not current.closed:
            current.start()

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

    def say(self, name, text):
        # Text tags provide real chat styling without converting model text
        # into commands, HTML, or untrusted UI instructions.
        self.log.configure(state='normal')
        self.log.insert('end', name + '\n', 'error' if 'ERROR' in name else 'user' if name == 'YOU' else 'name')
        body_tag = 'user_body' if name == 'YOU' else (
            'ai_body' if name in {'HASEEB AI', 'JARVIS'} else None
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

    def set_busy(self, on):
        self.busy = on
        self.send.configure(state='disabled' if on else 'normal')
        self.status.set('Working…' if on else ('Stopped · Resume to continue' if self.stop.is_set() else 'Ready · local controls'))

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
            'User memory, voice settings aur local shortcuts preserve honge.\n'
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
        """Compatibility entry point: direct legacy callers to LiveKit only."""
        return self.open_livekit_voice()

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
        self.say('JARVIS', 'Activity cleared. Gemini conversation context reset; LiveKit voice alag hai.')

    def halt(self):
        livekit = getattr(self, 'livekit_window', None)
        if livekit is not None and not livekit.closed:
            livekit.stop()  # Global STOP also ends the billable voice process.
        self.stop.set()
        self.generation += 1
        self.pending.clear()
        self.status.set('STOPPED · pending results/actions discarded · Resume to continue')
        # An already-sent cloud request may finish, but its result is discarded.

    def resume(self):
        if self.busy:
            self.say('HASEEB AI', 'Current request finish hone dein. Stop ke baad uska result discard hoga.')
            return
        self.stop.clear()
        self.status.set('Ready · local controls')

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
        if re.search(r'\bAIza[A-Za-z0-9_-]{25,}\b', text):
            # Reject before writing user text to the chat/activity transcript.
            self.say('ERROR', 'API key chat mein mat bhejein. Gemini setup mein securely save karein.')
            return
        self.entry.delete(0, 'end')
        self.say('YOU', text)
        try:
            if self.mode.get() == 'Gemini AI chat':
                # Explicit chat mode cannot execute actions, even if the model
                # suggests a command. User must switch to reviewed local mode.
                past = list(self.history)
                self.worker(lambda: GeminiClient(self.gemini_store).ask(
                    text, past, self.stop), 'gemini_reply', text)
                return
            if text.casefold().startswith('remember:'):
                fact = text.split(':', 1)[1].strip()
                if messagebox.askokcancel('Save local preference', fact + '\n\nYeh sirf PC par save hogi. Isay LiveKit ya kisi chatbot ko automatically nahi bheja jayega.', parent=self.root):
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
            else:
                self.say('COMMAND HELP', 'Local desktop commands: calculator kholo, notepad kholo, windows, screenshot, volume up, note: meeting, folder banao: Client Work. General sawal ke liye Gemini AI chat mode select karein; desktop command mode cloud ko text nahi bhejta.')
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
                elif kind == 'screenshot':
                    self.show_screen(value)
                elif kind == 'update_check':
                    self.approve_update(value)
                elif kind == 'gemini_reply':
                    self.history.extend([
                        {'role': 'user', 'content': user},
                        {'role': 'assistant', 'content': value},
                    ])
                    self.history = self.history[-8:]
                    self.say('JARVIS', value)
                elif kind == 'update_apply':
                    self.say('UPDATE', value)
                    self.status.set('Updated · restart Jarvis to use new code')
                    messagebox.showinfo('Jarvis update installed',
                                        value + '\\n\\nClose Jarvis and reopen the Desktop shortcut to activate it.',
                                        parent=self.root)
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
        if self.livekit_window is not None and not self.livekit_window.closed:
            self.livekit_window.close()
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

