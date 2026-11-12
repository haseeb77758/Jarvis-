"""Windows 11-inspired Jarvis dashboard.

Presentation only. Every action delegates to App's existing reviewed execution flow.
No web server, shell, remote control, or background microphone is added.
"""
from datetime import datetime
import math
from pathlib import Path
import platform
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from chat_ui import ChatComposer, on_return, preset_prompt

BG = '#06101e'
PANEL = '#0d2032'
PANEL_2 = '#112c41'
DEEP = '#071727'
LINE = '#174158'
TEXT = '#eaf8ff'
MUTED = '#91b2c7'
CYAN = '#31e4e2'
GREEN = '#42e5a1'
AMBER = '#f2b958'


def label(parent, text, size=10, color=TEXT, bold=False, bg=None, **kwargs):
    return tk.Label(parent, text=text, fg=color, bg=bg or parent['bg'],
                    font=('Segoe UI', size, 'bold' if bold else 'normal'), **kwargs)


def btn(parent, title, action, accent=False, compact=False):
    normal = CYAN if accent else PANEL_2
    hover = '#99fff0' if accent else '#1d3850'
    item = tk.Button(parent, text=title, command=action, bg=normal,
                     fg=BG if accent else TEXT, activebackground=hover,
                     activeforeground=BG if accent else TEXT,
                     font=('Segoe UI', 9, 'bold' if accent else 'normal'),
                     bd=0, relief='flat', highlightthickness=1,
                     highlightbackground=CYAN if accent else LINE,
                     cursor='hand2', padx=10 if compact else 13,
                     pady=6 if compact else 9)
    item.bind('<Enter>', lambda _e: item.configure(bg=hover) if str(item['state']) == 'normal' else None)
    item.bind('<Leave>', lambda _e: item.configure(bg=normal))
    return item


def panel(parent, bg=PANEL):
    return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=LINE)


def command_search(app, kind):
    prompt = 'Google par kya search karna hai?' if kind == 'google' else 'YouTube par kya search karna hai?'
    query = simpledialog.askstring('Jarvis search', prompt, parent=app.root)
    if query and query.strip():
        app.submit(kind + ': ' + query.strip())


def note_window(app):
    """Only display notes directly inside the user-selected workspace."""
    win = tk.Toplevel(app.root)
    win.title('Jarvis | Notes')
    win.geometry('660x480')
    win.configure(bg=BG)
    label(win, 'NOTES  /  SELECTED WORKSPACE', 13, CYAN, True).pack(anchor='w', padx=20, pady=(20, 4))
    label(win, 'Local text notes. Nothing is uploaded.', 9, MUTED).pack(anchor='w', padx=20, pady=(0, 12))
    outer = panel(win)
    outer.pack(fill='both', expand=True, padx=20)
    listing = tk.Listbox(outer, bg=DEEP, fg=TEXT, selectbackground='#245264',
                         borderwidth=0, highlightthickness=0, font=('Segoe UI', 10))
    listing.pack(side='left', fill='y', padx=8, pady=8)
    preview = tk.Text(outer, bg=DEEP, fg=TEXT, insertbackground=CYAN,
                      wrap='word', relief='flat', state='disabled', font=('Segoe UI', 10))
    preview.pack(side='left', fill='both', expand=True, padx=(0, 8), pady=8)
    base = Path(app.control.workspace).resolve()
    items = []
    try:
        items = [p for p in sorted(base.iterdir(), key=lambda p: p.name.lower())
                 if p.suffix.lower() == '.txt' and p.is_file() and not p.is_symlink()
                 and p.resolve().parent == base][:100]
    except OSError as exc:
        label(win, 'Cannot list notes: ' + str(exc), 9, AMBER).pack(anchor='w', padx=20)
    for item in items:
        listing.insert('end', item.name)
    if not items:
        listing.insert('end', 'No .txt notes in this workspace yet.')
    def inspect(_event=None):
        selection = listing.curselection()
        if not selection or selection[0] >= len(items):
            return
        path = items[selection[0]]
        try:
            value = path.read_text(encoding='utf-8')[:20000]
        except (OSError, UnicodeError) as exc:
            value = 'Cannot read this file: ' + str(exc)
        preview.configure(state='normal')
        preview.delete('1.0', 'end')
        preview.insert('1.0', value)
        preview.configure(state='disabled')
    listing.bind('<<ListboxSelect>>', inspect)
    def create():
        body = simpledialog.askstring('Create note', 'Note text:', parent=win)
        if body and body.strip():
            win.destroy()
            app.submit('note: ' + body.strip())
    btn(win, '+ Create reviewed note', create, True).pack(anchor='e', padx=20, pady=14)


def tasks_window(app):
    """Saved reviewed shortcuts, not an invented reminder scheduler."""
    win = tk.Toplevel(app.root)
    win.title('Jarvis | Tasks & shortcuts')
    win.geometry('580x450')
    win.configure(bg=BG)
    label(win, 'TASKS  /  REVIEWED SHORTCUTS', 13, CYAN, True).pack(anchor='w', padx=20, pady=(20, 8))
    label(win, 'Saved actions require their normal approvals. Reminders are not enabled.', 9, MUTED).pack(anchor='w', padx=20, pady=(0, 14))
    if not app.store.shortcuts:
        label(win, 'No shortcuts saved. Generate an AI action plan, then Save last plan.', 10, MUTED,
              wraplength=500, justify='left').pack(anchor='w', padx=20)
    else:
        for title, actions in list(app.store.shortcuts.items())[:20]:
            line = panel(win)
            line.pack(fill='x', padx=20, pady=3)
            label(line, title + '   ·   ' + str(len(actions)) + ' actions', 10, TEXT).pack(side='left', padx=12, pady=10)
            btn(line, 'Review & run', lambda name=title: (win.destroy(), app.submit('shortcut: ' + name)), compact=True).pack(side='right', padx=7)
    btn(win, 'Memory & saved apps', lambda: (win.destroy(), app.show_memory())).pack(anchor='e', padx=20, pady=15)


def system_window(app):
    details = [
        'OS: ' + platform.platform(),
        'Workspace: ' + str(app.control.workspace),
        'Local AI: optional Ollama model; availability depends on local setup',
        'Voice: opt-in, transcription runs locally after setup',
        'Control: explicit action approval, emergency STOP enabled',
        'Network: no remote desktop-control server',
    ]
    messagebox.showinfo('Jarvis | System information', '\n'.join(details), parent=app.root)


def _sphere_points(count=140):
    """Deterministic 3-D point cloud; no GPU or external animation dependency."""
    if not isinstance(count, int) or not 1 <= count <= 500:
        raise ValueError("Orb point count must be between 1 and 500.")
    points = []
    for i in range(count):
        y = 1.0 - 2.0 * (i + .5) / count
        theta = i * 2.399963229728653
        r = math.sqrt(max(0.0, 1.0 - y * y))
        points.append((math.cos(theta) * r, y, math.sin(theta) * r))
    return tuple(points)


def _project_orb_point(point, phase, radius=61):
    """Y-axis rotation with depth-dependent size; bounded frame coordinates."""
    x, y, z = point
    xrot = x * math.cos(phase) + z * math.sin(phase)
    zrot = z * math.cos(phase) - x * math.sin(phase)
    depth = .78 + .22 * (zrot + 1.0) / 2.0
    return xrot * radius * depth, y * radius * .87 * depth, zrot


class RotatingOrb:
    """Low-cost, real rotating AI sphere for Tkinter on integrated graphics.

    All animation happens in the Tk main thread. No microphones, network calls,
    threads or system operations are involved. The loop stops when destroyed.
    """

    FRAME_MS = 85

    def __init__(self, parent, width=188, height=132):
        self.canvas = tk.Canvas(parent, width=width, height=height, bg=DEEP,
                                highlightthickness=0, bd=0)
        self.canvas.pack(side='right', padx=(0, 6), pady=2)
        self.cx = width / 2
        self.cy = height / 2
        self.points = _sphere_points(144)
        self.phase = 0.0
        self.running = True
        self.alive = True
        self.canvas.create_oval(self.cx - 67, self.cy - 61, self.cx + 67, self.cy + 61,
                                outline='#18526a', width=1)
        self.orbit = self.canvas.create_arc(self.cx - 77, self.cy - 37,
                                            self.cx + 77, self.cy + 37,
                                            start=10, extent=285, style='arc',
                                            outline='#248da1', width=2)
        self.halo = self.canvas.create_oval(self.cx - 44, self.cy - 44,
                                             self.cx + 44, self.cy + 44,
                                             outline='#13475b', width=1)
        self.dots = [self.canvas.create_oval(0, 0, 1, 1, fill=CYAN, outline='')
                     for _ in self.points]
        self.satellite = self.canvas.create_oval(0, 0, 5, 5, fill='#a6fff7', outline='')
        self.center_text = self.canvas.create_text(self.cx, self.cy, text='AI',
                                      font=('Segoe UI', 13, 'bold'), fill='#b3fffb')
        self.canvas.bind('<Destroy>', self._on_destroy, add='+')
        self._tick()

    def _on_destroy(self, event):
        if event.widget is self.canvas:
            self.alive = False

    def toggle(self):
        self.running = not self.running
        return self.running

    def _tick(self):
        if not self.alive:
            return
        try:
            if not self.canvas.winfo_exists():
                self.alive = False
                return
            if self.running and self.canvas.winfo_viewable():
                self.phase = (self.phase + .042) % (2 * math.pi)
                self.canvas.itemconfigure(self.orbit, start=(15 + math.degrees(self.phase) * 2) % 360)
                for item, point in zip(self.dots, self.points):
                    dx, dy, depth = _project_orb_point(point, self.phase)
                    radius = .65 + (depth + 1) * .52
                    x, y = self.cx + dx, self.cy + dy
                    self.canvas.coords(item, x - radius, y - radius, x + radius, y + radius)
                    tint = '#146274' if depth < -.35 else '#238fa6' if depth < .15 else (
                        '#3ee4e3' if depth < .65 else '#a4fff5')
                    self.canvas.itemconfigure(item, fill=tint)
                angle = self.phase * 2.0
                ox = self.cx + 77 * math.cos(angle)
                oy = self.cy + 37 * math.sin(angle)
                self.canvas.coords(self.satellite, ox - 3, oy - 3, ox + 3, oy + 3)
                self.canvas.tag_raise(self.satellite)
                self.canvas.tag_raise(self.center_text)
            self.canvas.after(self.FRAME_MS if self.running else 250, self._tick)
        except tk.TclError:
            self.alive = False


def draw_orb(parent):
    """Compatibility helper for callers expecting a decorative orb widget."""
    return RotatingOrb(parent).canvas


def _set_compact_button_focus(button):
    """Keep keyboard navigation visibly available."""
    button.configure(takefocus=1)
    return button


def make_dashboard(app):
    """Polished Windows AI dashboard, inspired by the approved design reference.

    The screenshot is a visual reference, not a background image: every button
    is a live Tkinter control wired to the existing reviewed Jarvis handlers.
    """
    root = app.root
    root.configure(bg=BG)
    root.title('HASEEB AI | JARVIS — Desktop Intelligence')
    usable_width = max(1020, min(1480, root.winfo_screenwidth() - 36))
    usable_height = max(660, min(900, root.winfo_screenheight() - 88))
    root.geometry(f'{usable_width}x{usable_height}')
    root.minsize(1020, 660)

    # A wide but compact native title/navigation bar. More retains GitHub
    # connection and resume without hiding the emergency STOP button.
    header = tk.Frame(root, bg=DEEP, height=68, highlightthickness=1, highlightbackground=LINE)
    header.pack(fill='x')
    header.pack_propagate(False)
    identity = tk.Frame(header, bg=DEEP)
    identity.pack(side='left', padx=(18, 16), pady=8)
    brand = tk.Frame(identity, bg=DEEP)
    brand.pack(anchor='w')
    label(brand, '◈', 16, CYAN, True, bg=DEEP).pack(side='left', padx=(0, 6))
    label(brand, 'HASEEB AI', 13, CYAN, True, bg=DEEP).pack(side='left')
    label(brand, '  |  JARVIS', 12, TEXT, True, bg=DEEP).pack(side='left')
    label(identity, 'Local Desktop Assistant  ·  Haseeb Crafts', 8, MUTED, bg=DEEP).pack(anchor='w')

    navigation = tk.Frame(header, bg=DEEP)
    navigation.pack(side='left')
    for title, action in [
        ('AI Chat', lambda: (app.mode.set('Local AI chat'), app.entry.focus_set())),
        ('Notes', lambda: note_window(app)),
        ('Tasks', lambda: tasks_window(app)),
        ('Toolbox', app.open_toolkit),
    ]:
        is_chat = title == 'AI Chat'
        item = tk.Button(navigation, text=title, command=action,
                         bg=DEEP, fg=CYAN if is_chat else MUTED, bd=0,
                         activebackground=DEEP, activeforeground=CYAN,
                         cursor='hand2', font=('Segoe UI', 10, 'bold' if is_chat else 'normal'),
                         padx=10, pady=15)
        item.pack(side='left', padx=2)
        if is_chat:
            tk.Frame(navigation, bg=CYAN, height=2, width=1).place(in_=item, relx=0, rely=1,
                                                                   relwidth=1, anchor='sw')

    actions = tk.Frame(header, bg=DEEP)
    actions.pack(side='right', padx=(4, 13))
    btn(actions, 'STOP / Esc', app.halt, True, True).pack(side='right', padx=3)
    more = tk.Menubutton(actions, text='•••', bg=PANEL_2, fg=TEXT,
                         activebackground='#1d3850', activeforeground=CYAN,
                         relief='flat', padx=10, pady=8,
                         font=('Segoe UI', 10), cursor='hand2')
    menu = tk.Menu(more, tearoff=False, bg=PANEL, fg=TEXT,
                   activebackground=PANEL_2, activeforeground=CYAN)
    menu.add_command(label='Connect GitHub', command=app.connect_github)
    menu.add_command(label='Resume', command=app.resume)
    menu.add_separator()
    menu.add_command(label='Memory', command=app.show_memory)
    menu.add_command(label='Choose workspace', command=app.choose)
    more.configure(menu=menu)
    more.pack(side='right', padx=3)
    btn(actions, 'Update', app.update_jarvis, compact=True).pack(side='right', padx=3)
    btn(actions, 'Sandbox', app.open_sandbox, compact=True).pack(side='right', padx=3)
    btn(actions, 'Setup AI', app.setup_ai, compact=True).pack(side='right', padx=3)
    label(actions, '', 9, GREEN, True, bg=DEEP, textvariable=app.ai_status).pack(
        side='right', padx=(4, 9))

    body = tk.Frame(root, bg=BG)
    body.pack(fill='both', expand=True, padx=11, pady=(11, 7))
    body.grid_columnconfigure(0, minsize=235, weight=0)
    body.grid_columnconfigure(1, weight=1, minsize=0)
    body.grid_columnconfigure(2, minsize=290, weight=0)
    body.grid_rowconfigure(0, weight=1)

    # Sidebar – navigation and genuine local shortcuts, no fake app entries.
    sidebar = panel(body)
    sidebar.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
    sidebar.configure(width=225)
    # Children are packed, not gridded: pack propagation must be disabled.
    # Otherwise the default 394px-wide Canvas forces an enormous sidebar.
    sidebar.pack_propagate(False)
    clock_card = tk.Frame(sidebar, bg='#102c42')
    clock_card.pack(fill='x', padx=8, pady=(9, 10))
    clock = label(clock_card, '--:--', 29, TEXT, bg='#102c42')
    clock.pack(anchor='w', padx=14, pady=(8, 0))
    date_label = label(clock_card, '', 9, MUTED, bg='#102c42',
                       justify='left', wraplength=200)
    date_label.pack(anchor='w', padx=14)
    wave = tk.Canvas(clock_card, bg='#102c42', width=178, height=27,
                     bd=0, highlightthickness=0)
    wave.pack(fill='x', padx=5, pady=(3, 2))
    def draw_wave(event=None):
        wave.delete('wave')
        width = max(185, wave.winfo_width())
        for row in range(3):
            coords = []
            for x in range(0, width, 4):
                val = 15 - 7 * math.sin(x / 22.0 + row / 2) * math.exp(-((x - width * .62) / (width * .45)) ** 2)
                coords.extend((x, val + row * 3))
            wave.create_line(*coords, fill=('#185a77', '#1d7890', '#29a6af')[row],
                             smooth=True, width=1, tags='wave')
    wave.bind('<Configure>', draw_wave)
    def tick():
        if not root.winfo_exists():
            return
        now = datetime.now().astimezone()
        clock.configure(text=now.strftime('%H:%M'))
        date_label.configure(text=now.strftime('%a, %d %B %Y') + '\nLocal time')
        root.after(30000, tick)
    tick()

    label(sidebar, 'WORKSPACE TOOLS', 9, MUTED, True).pack(anchor='w', padx=16, pady=(0, 6))
    sidebar_items = [
        ('◉   AI Chat', lambda: (app.mode.set('Local AI chat'), app.entry.focus_set())),
        ('⌕   Web search', lambda: command_search(app, 'google')),
        ('▤   Files & workspace', app.choose),
        ('✉   Message draft', lambda: (app.mode.set('Local AI chat'),
                                      preset_prompt(app.entry, 'Draft a professional message: '))),
        ('▣   Notes', lambda: note_window(app)),
        ('≡   Tasks & shortcuts', lambda: tasks_window(app)),
        ('◈   AI Toolbox / Schedule', app.open_toolkit),
        ('⚙   System info', lambda: system_window(app)),
    ]
    for i, (title, action) in enumerate(sidebar_items):
        focused = i == 0
        b = tk.Button(sidebar, text=title, command=action, anchor='w',
                      bg='#103c4b' if focused else PANEL,
                      fg=CYAN if focused else TEXT,
                      activebackground='#16465a', activeforeground=CYAN,
                      highlightthickness=1 if focused else 0,
                      highlightbackground=CYAN,
                      relief='flat', bd=0, cursor='hand2', padx=12, pady=6,
                      font=('Segoe UI', 9, 'bold' if focused else 'normal'))
        b.pack(fill='x', padx=8, pady=1)

    label(sidebar, 'DESKTOP HELPER', 9, MUTED, True).pack(
        anchor='w', padx=15, pady=(13, 6))
    helper = tk.Frame(sidebar, bg=PANEL)
    helper.pack(fill='x', padx=8)
    for i, (title, action) in enumerate([
        ('Apps', app.add_app),
        ('Calculator', lambda: app.submit('calculator kholo')),
        ('Notepad', lambda: app.submit('notepad kholo')),
        ('Browser', lambda: app.submit('chrome kholo')),
        ('Explorer', lambda: app.submit('explorer kholo')),
        ('Commands', lambda: (app.mode.set('Computer commands'), app.entry.focus_set())),
    ]):
        b = tk.Button(helper, text=title, command=action,
                      bg=PANEL_2, fg=TEXT, activebackground='#1a4256',
                      activeforeground=CYAN, relief='flat',
                      highlightthickness=1, highlightbackground=LINE,
                      font=('Segoe UI', 8), cursor='hand2',
                      padx=2, pady=10)
        b.grid(row=i // 3, column=i % 3, sticky='ew', padx=2, pady=2)
    for col in range(3):
        helper.grid_columnconfigure(col, weight=1, uniform='help')

    # Chat area – native controls and a real, circular rotating AI visualization.
    center = tk.Frame(body, bg=BG)
    center.grid(row=0, column=1, sticky='nsew')
    conversation = panel(center, DEEP)
    conversation.pack(fill='both', expand=True)
    intro = tk.Frame(conversation, bg=DEEP, height=141)
    intro.pack(fill='x', padx=15, pady=(11, 0))
    intro.pack_propagate(False)
    app.orb = RotatingOrb(intro, width=166, height=130)
    intro_text = tk.Frame(intro, bg=DEEP)
    intro_text.pack(side='left', fill='both', expand=True, padx=(5, 2), pady=(12, 5))
    label(intro_text, 'JARVIS / AI CHAT', 16, CYAN, True, bg=DEEP).pack(anchor='w', pady=(0, 7))
    label(intro_text, 'Your private AI desktop companion  ·  Roman Urdu & English',
          9, MUTED, bg=DEEP, wraplength=410, justify='left').pack(anchor='w')
    model_name = tk.StringVar(value='LOCAL  /  ' + app.ai.model)
    label(intro_text, '', 9, GREEN, True, bg=DEEP, textvariable=model_name).pack(
        anchor='w', pady=(12, 0))
    def refresh_model_name():
        if not root.winfo_exists():
            return
        model_name.set('LOCAL  /  ' + str(app.ai.model))
        root.after(2500, refresh_model_name)
    root.after(2500, refresh_model_name)

    controls = tk.Frame(conversation, bg=DEEP)
    controls.pack(fill='x', padx=13, pady=(0, 8))
    app.mode.set('Local AI chat')
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Jarvis.TCombobox', fieldbackground=PANEL_2,
                    background=PANEL_2, foreground=TEXT, arrowcolor=CYAN,
                    bordercolor=LINE)
    app.select = ttk.Combobox(controls, textvariable=app.mode,
                              state='readonly', width=18, style='Jarvis.TCombobox',
                              values=['Local AI chat', 'Computer commands', 'AI action plan'])
    app.select.pack(side='left', padx=2)
    btn(controls, '+ New chat', app.clear, compact=True).pack(side='right', padx=2)
    btn(controls, 'Desktop mode', lambda: (app.mode.set('Computer commands'),
                                          app.entry.focus_set()), compact=True).pack(side='right', padx=2)
    btn(controls, 'AI chat', lambda: (app.mode.set('Local AI chat'), app.entry.focus_set()),
        compact=True).pack(side='right', padx=2)
    motion_button = btn(controls, 'Pause orb', lambda: None, compact=True)
    def toggle_motion():
        running = app.orb.toggle()
        motion_button.configure(text='Pause orb' if running else 'Play orb')
    motion_button.configure(command=toggle_motion)
    motion_button.pack(side='right', padx=2)

    # Pack controls from the bottom first, before the expanding conversation.
    # Tk otherwise gives the oversized text area priority and hides Send/Mic.
    label(conversation, 'Enter: send  ·  Shift+Enter: new line  ·  No always-on microphone',
          8, MUTED, bg=DEEP).pack(side='bottom', anchor='w', padx=16, pady=(0, 6))

    voice_footer = tk.Frame(conversation, bg=DEEP)
    voice_footer.pack(side='bottom', fill='x', padx=13, pady=(0, 8))
    btn(voice_footer, 'Setup voice', app.setup_voice, compact=True).pack(side='left', padx=2)
    btn(voice_footer, 'Test voice', app.test_voice, compact=True).pack(side='left', padx=2)
    ttk.Combobox(voice_footer, textvariable=app.voice_language, width=7,
                 state='readonly', values=['Auto', 'Urdu', 'English']).pack(side='left', padx=3)
    tk.Checkbutton(voice_footer, text='Speak replies', variable=app.speak_enabled,
                   bg=DEEP, fg=MUTED, activebackground=DEEP, activeforeground=TEXT,
                   selectcolor=PANEL_2).pack(side='left', padx=2)
    tk.Checkbutton(voice_footer, text='Reviewed screen input',
                   variable=app.permission, bg=DEEP, fg=MUTED,
                   activebackground=DEEP, activeforeground=TEXT,
                   selectcolor=PANEL_2).pack(side='right', padx=1)
    footer = tk.Frame(conversation, bg=DEEP)
    footer.pack(side='bottom', fill='x', padx=14, pady=(2, 4))
    app.entry = ChatComposer(footer, width=1,
                            bg='#102b40', fg=TEXT, insertbackground=CYAN,
                            relief='flat', font=('Segoe UI', 11), height=3, wrap='word',
                            padx=12, pady=9, highlightthickness=1,
                            highlightbackground='#277b91', highlightcolor=CYAN, undo=True)
    app.entry.pack(side='left', fill='both', expand=True)
    app.entry.bind('<Return>', lambda event: on_return(event, app.submit))
    app.send = btn(footer, '➤  SEND', app.submit, True)
    app.send.pack(side='right', padx=(8, 0))
    btn(footer, 'Mic', app.listen_voice, compact=True).pack(side='right', padx=3)

    prompts = tk.Frame(conversation, bg=DEEP)
    prompts.pack(side='bottom', fill='x', padx=15, pady=(0, 5))
    label(prompts, '✦  QUICK PROMPTS:', 8, MUTED, bg=DEEP).pack(side='left', padx=(0, 6))
    for title, prompt in [
        ('Salam', 'Salam Jarvis, tum kaise ho?'),
        ('Website idea', 'Mujhe Haseeb Crafts ke liye 3 creative website ideas do.'),
        ('Video script', 'Haseeb Crafts ke liye 15 second ki professional video script do.'),
        ('Plan', 'Mujhe aaj ke 3 practical tasks suggest karo.'),
    ]:
        btn(prompts, title, lambda p=prompt: (app.mode.set('Local AI chat'),
                                              preset_prompt(app.entry, p)),
            compact=True).pack(side='left', padx=2)

    chat_frame = tk.Frame(conversation, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    chat_frame.pack(fill='both', expand=True, padx=13, pady=(0, 8))
    app.log = tk.Text(chat_frame, width=1, height=7,
                      bg='#0a1b2c', fg=TEXT, insertbackground=CYAN,
                      relief='flat', wrap='word', font=('Segoe UI', 11),
                      padx=20, pady=13, state='disabled', spacing3=7,
                      selectbackground='#1e5e70', highlightthickness=0)
    app.log.pack(fill='both', expand=True, padx=5, pady=5)
    app.log.tag_config('name', foreground=CYAN, font=('Segoe UI', 10, 'bold'), spacing1=14)
    app.log.tag_config('user', foreground='#85faf3', font=('Segoe UI', 10, 'bold'), spacing1=12)
    app.log.tag_config('error', foreground='#ffa9a0')
    app.log.tag_config('user_body', foreground='#d5fffc', background='#114452')
    app.log.tag_config('ai_body', foreground=TEXT, background='#102e44')

    # Right column: real session activity and status (never fabricated CPU or
    # RAM values from the reference artwork).
    right = tk.Frame(body, bg=BG, width=278)
    right.grid(row=0, column=2, sticky='nsew', padx=(10, 0))
    right.pack_propagate(False)
    # Reserve the status card at the bottom before the expanding activity log.
    status_card = panel(right)
    status_card.pack(side='bottom', fill='x', pady=(10, 0))
    label(status_card, '◈  SYSTEM STATUS', 12, TEXT, True).pack(
        anchor='w', padx=13, pady=(13, 11))
    local_row = tk.Frame(status_card, bg=PANEL_2)
    local_row.pack(fill='x', padx=12, pady=(0, 10))
    label(local_row, '◉  Ollama / Local AI', 10, CYAN, True, bg=PANEL_2).pack(
        anchor='w', padx=9, pady=(9, 3))
    label(local_row, '', 9, GREEN, bg=PANEL_2, textvariable=app.ai_status,
          wraplength=218, justify='left').pack(anchor='w', padx=9, pady=(0, 8))
    label(status_card, 'Model:', 9, MUTED, True).pack(anchor='w', padx=13)
    label(status_card, '', 9, TEXT, textvariable=model_name,
          wraplength=215, justify='left').pack(anchor='w', padx=13, pady=(1, 8))
    tk.Frame(status_card, bg=LINE, height=1).pack(fill='x', padx=12)
    label(status_card, 'Current request:', 9, MUTED, True).pack(
        anchor='w', padx=13, pady=(8, 2))
    label(status_card, '', 9, TEXT, textvariable=app.status,
          wraplength=212, justify='left').pack(anchor='w', padx=13, pady=(0, 9))
    btn(status_card, 'Toolbox', app.open_toolkit, compact=True).pack(
        side='left', padx=(12, 4), pady=(0, 11))
    btn(status_card, 'Workspace', app.choose, compact=True).pack(
        side='left', padx=3, pady=(0, 11))

    activity = panel(right)
    activity.pack(fill='both', expand=True)
    heading = tk.Frame(activity, bg=PANEL)
    heading.pack(fill='x', padx=12, pady=(14, 6))
    label(heading, '⌁  ACTIVITY', 13, TEXT, True, bg=PANEL).pack(side='left')
    label(heading, 'SESSION', 8, GREEN, True, bg=PANEL).pack(side='right')
    label(activity, 'Only real local events are listed. No background monitoring.',
          9, MUTED, justify='left', wraplength=226).pack(
          anchor='w', padx=15, pady=(0, 8))
    tk.Frame(activity, height=1, bg=LINE).pack(fill='x', padx=12)
    app.activity_log = tk.Text(activity, width=1, height=7,
                               bg=PANEL, fg=MUTED,
                               wrap='word', relief='flat',
                               font=('Segoe UI', 9), state='disabled',
                               padx=12, pady=8, highlightthickness=0)
    app.activity_log.pack(fill='both', expand=True, padx=4, pady=4)

    label(root, 'HASEEB AI  ·  Created by Haseeb Crafts   |   LOCAL-FIRST  ·  STOP: Ctrl+Alt+F12 or Esc  ·  Screen actions need review',
          8, MUTED, bg=BG).pack(anchor='w', padx=17, pady=(0, 7))
