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
import re
from memory import PreferenceStore
from voice import Speaker, listen, setup_voice, normalize_command, bundled_model
from core import Controller, LocalAI, CLOUD_URL, parse_command, parse_plan, setup_local_model

BG, PANEL, TEXT, MUTED, CYAN = '#080e17', '#101c2b', '#eff7fa', '#9ab1c0', '#4ce2d2'
BORDER, SURFACE, DEEP = '#253b4d', '#142537', '#0b1521'


class App:
    def __init__(self, root, data_directory=None):
        self.root = root
        root.title('JARVIS | HASEEB AI — Windows 11')
        root.geometry('1320x840')
        root.minsize(1060, 650)
        root.option_add('*Font', 'Segoe UI 10')
        root.configure(bg=BG)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        self.generation = 0
        self.history = []
        self.pending = []
        self.last_plan = []
        self.store = PreferenceStore(data_directory)
        self.speak_enabled = tk.BooleanVar(value=False)
        self.voice_language = tk.StringVar(value='Auto')
        self.speaker = Speaker(lambda text: self.events.put((self.generation, 'notice', text, '', None)))
        self.control = Controller(Path.home(), self.stop, self.store.apps)
        self.ai = LocalAI()
        self.mode = tk.StringVar(value='Computer commands')
        self.status = tk.StringVar(value='Ready · local controls · no background monitoring')
        self.workspace = tk.StringVar(value=str(self.control.workspace))
        self.permission = tk.BooleanVar(value=False)
        self.make_ui()
        root.bind('<Escape>', lambda e: self.halt())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        if os.name == 'nt':
            threading.Thread(target=self.global_stop, daemon=True).start()
        self.say('HASEEB AI', 'Salam Haseeb bhai! Chrome kholo, calculator kholo, folder banao: Client Work, find: invoice, ya screenshot likhein.\nFree local AI ke liye Setup local AI button use karein. Cloud chat button pehle wali online app kholta hai; woh computer control nahi karti.')

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
        self.log.configure(state='normal')
        self.log.insert('end', name + '\n', 'error' if 'ERROR' in name else 'user' if name == 'YOU' else 'name')
        self.log.insert('end', str(text) + '\n\n')
        self.log.configure(state='disabled')
        self.log.see('end')
        if name in {'RESULT', 'HASEEB AI · LOCAL MODEL', 'ERROR'} and self.speak_enabled.get():
            self.speaker.speak(str(text))

    def set_busy(self, on):
        self.busy = on
        self.send.configure(state='disabled' if on else 'normal')
        self.status.set('Working…' if on else ('Stopped · Resume to continue' if self.stop.is_set() else 'Ready · local controls'))

    def test_voice(self):
        if not self.busy:
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
            self.worker(lambda: setup_voice(self.stop), 'setup')

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

    def setup_ai(self):
        if self.busy:
            return
        if self.stop.is_set():
            self.say('HASEEB AI', 'Pehle Resume dabayein.')
            return
        installed = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Ollama/ollama.exe'
        if not installed.is_file() and not shutil.which('ollama.exe'):
            if messagebox.askokcancel('Install local AI runtime',
                'Local AI ke liye Ollama install karna hoga. Official download page kholun?\nInstallation ke baad isi Setup local AI button ko dobara dabayein.', parent=self.root):
                webbrowser.open('https://ollama.com/download/windows')
            return
        if messagebox.askokcancel('Download free local AI',
            'qwen2.5:1.5b model approximately 986 MB download hoga. Internet aur disk space chahiye.\nAPI key ya paid plan nahi chahiye. Download shuru karein?', parent=self.root):
            self.worker(lambda: setup_local_model(self.stop), 'setup')

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
        if self.stop.is_set():
            self.say('HASEEB AI', 'Stopped hai. Pehle Resume dabayein.')
            return
        self.entry.delete(0, 'end')
        self.say('YOU', text)
        if len(text) > 4000:
            self.say('HASEEB AI', 'Message 4,000 characters se chhota rakhein.')
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
                self.say('COMMAND HELP', 'windows · inspect: Window title · focus: Window title · wait: Window title\nbutton: Window title | Exact button name\nwrite: Window title | Hello Haseeb · press: Window title | ctrl+s\nremember: reply in Roman Urdu · shortcut: saved name\nchrome kholo · notepad kholo · calculator kholo · edge kholo · explorer kholo\nopen https://example.com\nfolder banao: Client Work\nfind: invoice\nnote: client meeting Monday\nscreenshot\nvolume up · volume down · volume mute\ngoogle: website design · youtube: python tutorial · kitne baje hain\nScreen input: type: Hello Haseeb · key: ctrl+s · click: 300,400\nFree local AI ke liye Local AI chat / AI action plan select karein.')
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
                elif kind == 'voice':
                    self.review_voice(value)
                elif kind == 'screenshot':
                    self.show_screen(value)
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
        import sounddevice
        import win32com.client
        from PIL import ImageTk
        root.update_idletasks()
        root.update()
        assert root.winfo_exists()
        root.destroy()
    else:
        root.mainloop()
