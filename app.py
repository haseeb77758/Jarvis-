"""HASEEB AI Windows 11 desktop workspace. Run START.bat."""
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import shutil
from core import Controller, LocalAI, CLOUD_URL, parse_command, parse_plan, setup_local_model

BG, PANEL, TEXT, MUTED, CYAN = '#080f18', '#122231', '#e5f1f5', '#92a9b9', '#36dccf'


class App:
    def __init__(self, root):
        self.root = root
        root.title('JARVIS | HASEEB AI — Windows 11')
        root.geometry('1240x800')
        root.minsize(1060, 620)
        root.configure(bg=BG)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        self.generation = 0
        self.history = []
        self.pending = []
        self.control = Controller(Path.home(), self.stop)
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
        return tk.Button(parent, text=text, command=command, bg=CYAN if accent else PANEL,
                         fg=BG if accent else TEXT, activebackground=CYAN,
                         relief='flat', padx=13, pady=9, cursor='hand2', font=('Segoe UI', 10))

    def make_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=24, pady=(18, 10))
        tk.Label(header, text='JARVIS', fg=CYAN, bg=BG, font=('Segoe UI', 23, 'bold')).pack(side='left')
        tk.Label(header, text='  WINDOWS WORKSPACE\n  Created by Haseeb Crafts', fg=MUTED, bg=BG,
                 justify='left', font=('Segoe UI', 9)).pack(side='left')
        self.button(header, 'STOP / Esc', self.halt, True).pack(side='right', padx=5)
        self.button(header, 'Resume', self.resume).pack(side='right', padx=5)
        self.button(header, 'Setup local AI', self.setup_ai).pack(side='right', padx=5)
        self.button(header, 'Cloud chat ↗', lambda: webbrowser.open(CLOUD_URL)).pack(side='right', padx=5)
        tk.Label(self.root, textvariable=self.status, fg=MUTED, bg=BG, anchor='w').pack(fill='x', padx=26)
        tools = tk.Frame(self.root, bg=BG)
        tools.pack(fill='x', padx=24, pady=12)
        for text, command in [('Chrome', 'chrome kholo'), ('Notepad', 'notepad kholo'),
                              ('Calculator', 'calculator kholo'), ('Screen', 'screenshot')]:
            self.button(tools, text, lambda c=command: self.submit(c)).pack(side='left', padx=(0, 7))
        self.button(tools, 'New chat', self.clear).pack(side='right')
        tk.Checkbutton(tools, text='Enable mouse / keyboard controls', variable=self.permission,
                       fg=TEXT, bg=BG, selectcolor=PANEL, activebackground=BG, activeforeground=TEXT).pack(side='left', padx=8)
        loc = tk.Frame(self.root, bg=PANEL)
        loc.pack(fill='x', padx=24)
        tk.Label(loc, text='WORKSPACE  ', fg=CYAN, bg=PANEL).pack(side='left', padx=10)
        tk.Label(loc, textvariable=self.workspace, fg=TEXT, bg=PANEL, anchor='w').pack(side='left', fill='x', expand=True)
        self.button(loc, 'Choose folder', self.choose).pack(side='right')
        self.log = tk.Text(self.root, bg=PANEL, fg=TEXT, insertbackground=CYAN, relief='flat', wrap='word',
                           font=('Segoe UI', 11), padx=18, pady=18, state='disabled')
        self.log.pack(fill='both', expand=True, padx=24, pady=12)
        self.log.tag_config('name', foreground=CYAN, font=('Segoe UI', 10, 'bold'))
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill='x', padx=24, pady=(0, 8))
        style = ttk.Style()
        style.theme_use('clam')
        self.select = ttk.Combobox(bottom, textvariable=self.mode, state='readonly', width=20,
                                  values=['Computer commands', 'Local AI chat', 'AI action plan'])
        self.select.pack(side='left', padx=(0, 8))
        self.entry = tk.Entry(bottom, bg=PANEL, fg=TEXT, insertbackground=CYAN, relief='flat', font=('Segoe UI', 12))
        self.entry.pack(side='left', fill='x', expand=True, ipady=10)
        self.entry.bind('<Return>', lambda e: self.submit())
        self.send = self.button(bottom, 'Send', self.submit, True)
        self.send.pack(side='left', padx=(8, 0))
        tk.Label(self.root, text='Screen input: enable → review → 4-second countdown. Global STOP: Ctrl+Alt+F12. Mouse corner = fail-safe.\nNo delete, shell execution, automatic messages or payments. Screenshots stay local.',
                 fg=MUTED, bg=BG, justify='left', anchor='w', font=('Segoe UI', 9)).pack(fill='x', padx=26, pady=(0, 15))

    def say(self, name, text):
        self.log.configure(state='normal')
        self.log.insert('end', name + '\n', 'name')
        self.log.insert('end', str(text) + '\n\n')
        self.log.configure(state='disabled')
        self.log.see('end')

    def set_busy(self, on):
        self.busy = on
        self.send.configure(state='disabled' if on else 'normal')
        self.status.set('Working…' if on else ('Stopped · Resume to continue' if self.stop.is_set() else 'Ready · local controls'))

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
        if self.busy:
            return
        text = value if value is not None else self.entry.get().strip()
        if not text:
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
            action = parse_command(text)
            if action:
                self.approve(action)
            elif self.mode.get() == 'Computer commands':
                self.say('COMMAND HELP', 'chrome kholo · notepad kholo · calculator kholo · edge kholo · explorer kholo\nopen https://example.com\nfolder banao: Client Work\nfind: invoice\nnote: client meeting Monday\nscreenshot\nScreen input: type: Hello Haseeb · key: ctrl+s · click: 300,400\nFree local AI ke liye Local AI chat / AI action plan select karein.')
            else:
                planning = self.mode.get() == 'AI action plan'
                messages = [{'role': 'user', 'content': text}] if planning else self.history + [{'role': 'user', 'content': text}]
                self.worker(lambda: self.ai.ask(messages, planning), 'plan' if planning else 'ai', text)
        except Exception as exc:
            self.say('ACTION ERROR', str(exc))

    def approve(self, action):
        screen = action['action'] in {'type', 'click', 'key'}
        if screen and not self.permission.get():
            self.pending.clear()
            self.say('PERMISSION', 'Pehle Enable mouse / keyboard controls tick karein. Har screen action ka review aur countdown hoga.')
            return
        confirm = screen or action['action'] in {'folder', 'note'} or bool(self.pending)
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
                elif kind == 'screenshot':
                    self.show_screen(value)
                elif kind == 'ai':
                    self.history = (self.history + [{'role': 'user', 'content': user}, {'role': 'assistant', 'content': value}])[-8:]
                    self.say('HASEEB AI · LOCAL MODEL', value)
                elif kind == 'plan':
                    try:
                        actions = parse_plan(value)
                        self.say('AI PLAN — NOT EXECUTED', json.dumps(actions, ensure_ascii=False, indent=2))
                        self.pending = actions
                    except Exception as exc:
                        self.say('PLAN ERROR', str(exc))
                else:
                    self.say('RESULT', value)
                if not issue and self.pending:
                    action = self.pending.pop(0)
                    # Include a review for the final/single action too.
                    if messagebox.askokcancel('AI plan — next action', json.dumps(action, ensure_ascii=False, indent=2), parent=self.root):
                        self.approve(action)
                    else:
                        self.pending.clear()
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
        from PIL import ImageTk
        root.update_idletasks()
        root.update()
        assert root.winfo_exists()
        root.destroy()
    else:
        root.mainloop()
