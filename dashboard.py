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

BG = '#07111d'
PANEL = '#101e2d'
PANEL_2 = '#142637'
DEEP = '#0b1623'
LINE = '#263e50'
TEXT = '#e8f3fa'
MUTED = '#93a9bc'
CYAN = '#38dcd7'
GREEN = '#35d994'
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


def draw_orb(parent):
    canvas = tk.Canvas(parent, width=224, height=204, bg=PANEL, highlightthickness=0)
    canvas.pack(expand=True)
    cx, cy = 112, 103
    canvas.create_oval(cx - 83, cy - 83, cx + 83, cy + 83, outline='#1c5564', width=1)
    # A deterministic Fibonacci sphere: fast to render on integrated graphics.
    for i in range(260):
        z = 1 - 2 * (i + .5) / 260
        angle = i * 2.3999632297
        rad = math.sqrt(max(0, 1 - z * z))
        x = rad * math.cos(angle)
        y = rad * math.sin(angle)
        # Tilt to give the cloud a 3D appearance without animation overhead.
        px = cx + (x * .84 + z * .16) * 79
        py = cy + (y * .86 - z * .20) * 79
        size = 0.75 + max(0, z + 1) * .36
        tint = '#1d7884' if z < -.18 else '#36c8cd' if z < .55 else '#8af9ed'
        canvas.create_oval(px - size, py - size, px + size, py + size, fill=tint, outline='')
    canvas.create_text(cx, cy + 95, text='READY FOR COMMANDS', fill=CYAN, font=('Segoe UI', 9, 'bold'))
    return canvas


def make_dashboard(app):
    root = app.root
    root.configure(bg=BG)
    root.title('HASEEB AI  |  JARVIS — Desktop Intelligence')
    root.geometry('1260x780')
    root.minsize(980, 620)

    header = tk.Frame(root, bg=DEEP, height=54, highlightbackground=LINE, highlightthickness=1)
    header.pack(fill='x')
    header.pack_propagate(False)
    identity = tk.Frame(header, bg=DEEP)
    identity.pack(side='left', padx=(18, 30), pady=7)
    label(identity, 'H A S E E B  A I', 13, CYAN, True, bg=DEEP).pack(anchor='w')
    label(identity, 'Created by Haseeb Crafts', 8, MUTED, bg=DEEP).pack(anchor='w')
    for title, command in [('AI Chat', lambda: (app.mode.set('Local AI chat'), app.entry.focus_set())),
                           ('Notes', lambda: note_window(app)),
                           ('Tasks', lambda: tasks_window(app))]:
        tab = tk.Button(header, text=title, command=command, bg=DEEP, fg=CYAN if title == 'Intelligence' else MUTED,
                        activebackground=DEEP, activeforeground=CYAN, bd=0, font=('Segoe UI', 10),
                        cursor='hand2', padx=14, pady=15)
        tab.pack(side='left')
    btn(header, 'STOP  /  Esc', app.halt, True, True).pack(side='right', padx=(6, 16), pady=10)
    btn(header, 'Resume', app.resume, compact=True).pack(side='right', padx=4, pady=10)
    btn(header, 'Update Jarvis', app.update_jarvis, compact=True).pack(side='right', padx=4, pady=10)
    btn(header, 'Setup AI', app.setup_ai, compact=True).pack(side='right', padx=4, pady=10)
    btn(header, 'AI Sandbox', app.open_sandbox, compact=True).pack(side='right', padx=4, pady=10)
    btn(header, 'Ask Jarvis', lambda: (app.mode.set('Local AI chat'), app.entry.focus_set()), compact=True).pack(side='right', padx=4, pady=10)
    label(header, '', 9, CYAN, bg=DEEP, textvariable=app.ai_status).pack(side='right', padx=(6, 12))

    body = tk.Frame(root, bg=BG)
    body.pack(fill='both', expand=True, padx=12, pady=(12, 10))
    body.grid_columnconfigure(0, minsize=194)
    body.grid_columnconfigure(1, weight=1)
    body.grid_columnconfigure(2, minsize=207)
    body.grid_rowconfigure(0, weight=1)

    sidebar = panel(body)
    sidebar.grid(row=0, column=0, sticky='nsew', padx=(0, 11))
    sidebar.grid_propagate(False)
    sidebar.configure(width=198)
    clock = label(sidebar, '--:--', 25, TEXT)
    clock.pack(anchor='w', padx=15, pady=(16, 0))
    date_label = label(sidebar, '', 9, MUTED, wraplength=185, justify='left')
    date_label.pack(anchor='w', padx=15, pady=(0, 10))
    def tick():
        if not root.winfo_exists():
            return
        now = datetime.now().astimezone()
        clock.configure(text=now.strftime('%H:%M'))
        date_label.configure(text=now.strftime('%A %d %B\n%Z / Local time'))
        root.after(30000, tick)
    tick()
    tk.Frame(sidebar, bg=LINE, height=1).pack(fill='x', padx=14, pady=(0, 12))
    label(sidebar, 'WORKSPACE TOOLS', 9, MUTED, True).pack(anchor='w', padx=15, pady=(0, 5))
    entries = [
        ('⌕   Web search', lambda: command_search(app, 'google')),
        ('▣   Files & CSV', app.choose),
        ('✉   Message draft', lambda: (app.mode.set('Local AI chat'), app.entry.insert(0, 'Draft a message: '), app.entry.focus_set())),
        ('▤   Notes', lambda: note_window(app)),
        ('≡   Tasks & shortcuts', lambda: tasks_window(app)),
        ('⚙   System info', lambda: system_window(app)),
    ]
    for title, action in entries:
        b = tk.Button(sidebar, text=title, command=action, anchor='w', bg=PANEL, fg=TEXT,
                      activebackground=PANEL_2, activeforeground=CYAN, relief='flat', bd=0,
                      font=('Segoe UI', 10), cursor='hand2', padx=15, pady=8)
        b.pack(fill='x', padx=5)
    label(sidebar, 'OPEN APP', 9, MUTED, True).pack(anchor='w', padx=15, pady=(16, 4))
    for name, command in [('Google Chrome', 'chrome kholo'), ('Microsoft Edge', 'edge kholo'),
                          ('Calculator', 'calculator kholo'), ('Notepad', 'notepad kholo'),
                          ('YouTube', 'youtube kholo'), ('WhatsApp Web', 'whatsapp kholo')]:
        tk.Button(sidebar, text='◫  ' + name, anchor='w', command=lambda c=command: app.submit(c),
                  bg=PANEL, fg=TEXT, activebackground=PANEL_2, activeforeground=CYAN,
                  relief='flat', bd=0, cursor='hand2', font=('Segoe UI', 9), padx=15, pady=6).pack(fill='x', padx=6)

    label(sidebar, 'MEDIA CONTROLS', 9, MUTED, True).pack(anchor='w', padx=15, pady=(13, 4))
    media = tk.Frame(sidebar, bg=PANEL)
    media.pack(fill='x', padx=10)
    for title, command in [('◀', 'previous song'), ('⏯', 'play pause'), ('▶', 'next song')]:
        btn(media, title, lambda c=command: app.submit(c), compact=True).pack(side='left', padx=2, pady=2)

    center = tk.Frame(body, bg=BG)
    center.grid(row=0, column=1, sticky='nsew')
    conversation = panel(center, DEEP)
    conversation.pack(fill='both', expand=True)
    intro = tk.Frame(conversation, bg=DEEP)
    intro.pack(fill='x', padx=17, pady=(15, 2))
    label(intro, 'JARVIS  /  AI CHAT', 15, CYAN, True, bg=DEEP).pack(anchor='w')
    label(intro, 'Ask anything in Roman Urdu or English. Answers come from your Ollama model on this PC.',
          9, MUTED, bg=DEEP, wraplength=650, justify='left').pack(anchor='w', pady=(2, 0))
    controls = tk.Frame(conversation, bg=DEEP)
    controls.pack(fill='x', padx=14, pady=(7, 7))
    app.mode.set('Local AI chat')
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Jarvis.TCombobox', fieldbackground=PANEL_2, background=PANEL_2, foreground=TEXT)
    app.select = ttk.Combobox(controls, textvariable=app.mode, state='readonly', width=19,
                              style='Jarvis.TCombobox',
                              values=['Local AI chat', 'Computer commands', 'AI action plan'])
    app.select.pack(side='left', padx=4)
    btn(controls, 'New chat', app.clear, compact=True).pack(side='right', padx=3)
    btn(controls, 'Desktop mode', lambda: (app.mode.set('Computer commands'), app.entry.focus_set()),
        compact=True).pack(side='right', padx=3)
    btn(controls, 'AI chat', lambda: (app.mode.set('Local AI chat'), app.entry.focus_set()),
        compact=True).pack(side='right', padx=3)
    app.log = tk.Text(conversation, bg=PANEL, fg=TEXT, insertbackground=CYAN,
                      relief='flat', wrap='word', font=('Segoe UI', 11),
                      padx=19, pady=14, state='disabled', spacing3=9,
                      selectbackground='#235265', highlightthickness=1,
                      highlightbackground=LINE)
    app.log.pack(fill='both', expand=True, padx=13, pady=(3, 7))
    app.log.tag_config('name', foreground=CYAN, font=('Segoe UI', 10, 'bold'), spacing1=12)
    app.log.tag_config('user', foreground='#a8beec', font=('Segoe UI', 10, 'bold'))
    app.log.tag_config('error', foreground='#ffab9f')
    prompts = tk.Frame(conversation, bg=DEEP)
    prompts.pack(fill='x', padx=14, pady=(0, 4))
    label(prompts, 'TRY:', 8, MUTED, bg=DEEP).pack(side='left', padx=(0, 6))
    for title, prompt in [
        ('Salam Jarvis', 'Salam Jarvis, mujhe apna introduction do.'),
        ('Website ideas', 'Mujhe ek business website ke 3 creative ideas do.'),
        ('Content script', 'Haseeb Crafts ke liye 15 second ki video script likho.'),
    ]:
        btn(prompts, title, lambda p=prompt: (app.mode.set('Local AI chat'), preset_prompt(app.entry, p)),
            compact=True).pack(side='left', padx=3)
    footer = tk.Frame(conversation, bg=DEEP)
    footer.pack(fill='x', padx=13, pady=(3, 5))
    app.entry = ChatComposer(footer, bg=PANEL_2, fg=TEXT, insertbackground=CYAN,
                            relief='flat', font=('Segoe UI', 11), height=3, wrap='word',
                            padx=12, pady=9, highlightthickness=1,
                            highlightbackground=LINE, highlightcolor=CYAN,
                            undo=True)
    app.entry.pack(side='left', fill='both', expand=True)
    app.entry.bind('<Return>', lambda event: on_return(event, app.submit))
    app.send = btn(footer, 'SEND', app.submit, accent=True)
    app.send.pack(side='right', padx=(9, 0))
    btn(footer, 'Mic', app.listen_voice, compact=True).pack(side='right', padx=3)
    label(conversation, 'ENTER to send   ·   SHIFT+ENTER for new line   ·   No cloud API key needed',
          8, MUTED, bg=DEEP).pack(anchor='w', padx=15, pady=(0, 7))
    voice_footer = tk.Frame(conversation, bg=DEEP)
    voice_footer.pack(fill='x', padx=12, pady=(0, 8))
    btn(voice_footer, 'Setup voice', app.setup_voice, compact=True).pack(side='left', padx=3)
    btn(voice_footer, 'Test voice', app.test_voice, compact=True).pack(side='left', padx=3)
    ttk.Combobox(voice_footer, textvariable=app.voice_language, width=8, state='readonly',
                 values=['Auto', 'Urdu', 'English']).pack(side='left', padx=4)
    tk.Checkbutton(voice_footer, text='Speak replies', variable=app.speak_enabled, bg=DEEP, fg=MUTED,
                   activebackground=DEEP, activeforeground=TEXT, selectcolor=PANEL_2).pack(side='left', padx=4)
    tk.Checkbutton(voice_footer, text='Enable reviewed screen input', variable=app.permission, bg=DEEP, fg=MUTED,
                   activebackground=DEEP, activeforeground=TEXT, selectcolor=PANEL_2).pack(side='right')

    activity = panel(body)
    activity.grid(row=0, column=2, sticky='nsew', padx=(11, 0))
    activity.configure(width=218)
    activity.grid_propagate(False)
    label(activity, 'ACTIVITY', 13, TEXT, True).pack(anchor='w', padx=15, pady=(16, 10))
    label(activity, 'Only actual outcomes appear here.\nNo background monitoring.', 9, MUTED,
          justify='left', wraplength=208).pack(anchor='w', padx=15, pady=(0, 12))
    app.activity_log = tk.Text(activity, bg=PANEL, fg=MUTED, wrap='word', relief='flat',
                                font=('Segoe UI', 9), state='disabled', padx=12, pady=9,
                                highlightthickness=0)
    app.activity_log.pack(fill='both', expand=True, padx=4)
    tk.Frame(activity, bg=LINE, height=1).pack(fill='x', padx=12, pady=(6, 6))
    label(activity, 'SYSTEM STATUS', 9, CYAN, True).pack(anchor='w', padx=15, pady=(4, 6))
    label(activity, '', 9, TEXT, bg=PANEL, textvariable=app.status, wraplength=208,
          justify='left').pack(anchor='w', padx=15, pady=(0, 12))
    btn(activity, 'Add an installed app', app.add_app, compact=True).pack(fill='x', padx=12, pady=(0, 6))
    btn(activity, 'Choose workspace', app.choose, compact=True).pack(fill='x', padx=12, pady=(0, 12))
    label(root, 'LOCAL DESKTOP  ·  Screen input requires opt-in + review  ·  STOP: Ctrl+Alt+F12 / Esc',
          8, MUTED, bg=BG).pack(anchor='w', padx=16, pady=(0, 8))
