"""Opt-in Windows productivity, creative, and system tools for HASEEB AI Jarvis.

These dialogs operate as explicit user actions. They never expose a control
server, enable unattended listening, or accept model-generated commands.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import webbrowser

from enhanced_tools import ScheduleStore, read_code_for_review, system_action, weather_search_url, generate_cloud_image

BG, PANEL, FG, MUTE, CYAN = "#080e17", "#142537", "#eff7fa", "#9ab1c0", "#4ce2d2"


def window(parent, heading, geometry="700x560"):
    win = tk.Toplevel(parent)
    win.title("HASEEB AI | " + heading)
    win.geometry(geometry)
    win.minsize(560, 400)
    win.configure(bg=BG)
    tk.Label(win, text=heading.upper(), font=("Segoe UI", 16, "bold"),
             bg=BG, fg=CYAN).pack(anchor="w", padx=22, pady=(20, 8))
    return win


def info(parent, content):
    tk.Label(parent, text=content, font=("Segoe UI", 10), bg=BG,
             fg=MUTE, justify="left", wraplength=640).pack(anchor="w", padx=22, pady=(0, 10))


def button(parent, text, callback):
    return tk.Button(parent, text=text, command=callback, bg=PANEL, fg=FG,
                     activebackground="#204052", activeforeground=CYAN,
                     relief="flat", padx=15, pady=10, cursor="hand2",
                     font=("Segoe UI", 10))


def schedule_window(app):
    win = window(app.root, "Schedule & timetable")
    info(win, "Schedule entries sirf local CSV mein save hoti hain. Reminders/background monitoring enabled nahi.")
    store = ScheduleStore(app.store.directory)
    columns = ("date", "time", "title")
    grid = ttk.Treeview(win, columns=columns, show="headings", selectmode="browse", height=12)
    for name, width in (("date", 120), ("time", 85), ("title", 365)):
        grid.heading(name, text=name.title())
        grid.column(name, width=width, anchor="w")
    grid.pack(fill="both", expand=True, padx=20, pady=8)

    def refresh():
        for item in grid.get_children():
            grid.delete(item)
        try:
            records = store.list_items()
        except (ValueError, OSError) as exc:
            messagebox.showerror("Schedule problem", str(exc), parent=win)
            return
        for index, record in enumerate(records):
            grid.insert("", "end", iid=str(index), values=(record["date"], record["time"], record["title"]))

    def add():
        date = simpledialog.askstring("Schedule date", "Date (YYYY-MM-DD)", parent=win,
                                      initialvalue=datetime.now().strftime("%Y-%m-%d"))
        if date is None:
            return
        time = simpledialog.askstring("Schedule time", "Time (24-hour HH:MM)", parent=win,
                                      initialvalue="10:00")
        if time is None:
            return
        title = simpledialog.askstring("Schedule title", "Task / meeting title", parent=win)
        if title is None:
            return
        try:
            store.add(date, time, title)
            refresh()
        except (ValueError, OSError) as exc:
            messagebox.showerror("Schedule not saved", str(exc), parent=win)

    def remove():
        selected = grid.selection()
        if not selected:
            return
        idx = int(selected[0])
        if messagebox.askyesno("Delete scheduled item",
                               "Selected local schedule entry delete karein?", parent=win):
            try:
                store.delete(idx)
                refresh()
            except (ValueError, OSError) as exc:
                messagebox.showerror("Schedule delete failed", str(exc), parent=win)

    actions = tk.Frame(win, bg=BG)
    actions.pack(fill="x", padx=18, pady=(4, 18))
    button(actions, "Add entry", add).pack(side="left", padx=4)
    button(actions, "Delete selected", remove).pack(side="left", padx=4)
    button(actions, "Refresh", refresh).pack(side="right", padx=4)
    refresh()


def weather_window(app):
    city = simpledialog.askstring("Weather lookup", "Kis shehar ka mausam check karna hai?\n"
                                   "Browser mein search results khulenge, Jarvis forecast invent nahi karega.",
                                   parent=app.root)
    if city is None:
        return
    try:
        url = weather_search_url(city)
        if not webbrowser.open(url):
            raise RuntimeError("Browser open nahi hua.")
        app.say("RESULT", "Weather results browser mein kholne ki request bhej di: " + city.strip())
    except (ValueError, RuntimeError) as exc:
        messagebox.showerror("Weather lookup", str(exc), parent=app.root)


def code_studio(app):
    if app.busy or app.stop.is_set():
        messagebox.showinfo("Jarvis is busy", "Pehle request finish hone dein ya Resume dabayein.", parent=app.root)
        return
    selected = filedialog.askopenfilename(
        title="Choose a code file for read-only AI review",
        filetypes=[("Code / text", "*.py *.html *.css *.js *.jsx *.ts *.tsx *.php *.json *.java *.cpp *.cs *.md *.txt")]
    )
    if not selected:
        return
    try:
        source = read_code_for_review(selected)
    except (ValueError, OSError) as exc:
        messagebox.showerror("Code review", str(exc), parent=app.root)
        return
    if not messagebox.askyesno(
        "Review code with local Ollama",
        "File: " + Path(selected).name + "\n\n"
        "Is file ka text local Ollama model ko send hoga. 25KB limit hai. "
        "Koi code execute ya file overwrite nahi hogi.\n\n"
        "Passwords, API keys aur private data wali files select na karein. Continue?",
        parent=app.root
    ):
        return
    # The model receives only selected text. Its output is advice, never executed.
    instruction = (
        "Review this code as a read-only assistant. Identify up to 5 concrete problems, "
        "suggest safe fixes in Roman Urdu and explicitly say when uncertain. "
        "Never claim that you executed or fixed the code.\n\n"
        "Filename: " + Path(selected).name + "\nCODE:\n" + source
    )
    app.say("YOU", "Review file: " + Path(selected).name)
    app.worker(lambda: app.ai.ask([{"role": "user", "content": instruction}]),
               "ai", "Review file: " + Path(selected).name)


def code_generator(app):
    """Generate a read-only code suggestion; no shell, files or auto-execution."""
    if app.busy or app.stop.is_set():
        messagebox.showinfo("Jarvis is busy", "Pehle request finish karein ya Resume dabayein.", parent=app.root)
        return
    description = simpledialog.askstring(
        "AI Code Generator",
        "Kya code banana hai? Details likhein (1-500 characters).\n"
        "Generated code sirf chat mein dikhaya jayega, run/save nahi hoga.",
        parent=app.root
    )
    if description is None:
        return
    description = description.strip()
    if not 1 <= len(description) <= 500:
        messagebox.showerror("Invalid request", "Code description 1-500 characters ki honi chahiye.", parent=app.root)
        return
    if not messagebox.askyesno(
        "Generate suggested code",
        "Local Ollama model code suggest karega. "
        "Code execute nahi hoga, koi file automatically overwrite nahi hogi.\n\nContinue?",
        parent=app.root
    ):
        return
    task = ("Generate a minimal, explained code example for this request. "
            "Return code and practical next steps. Avoid shell commands that alter system settings. "
            "Do not claim the code was executed or tested.\n\nRequest: " + description)
    app.say("YOU", "Generate code: " + description)
    app.worker(lambda: app.ai.ask([{"role": "user", "content": task}]),
               "ai", "Generate code: " + description)


def system_window(app):
    win = window(app.root, "Reviewed Windows system controls", "600x420")
    info(win, "Sensitive system operations AI chat se automatically run nahi hotin.\n"
              "Shutdown/restart 60 seconds ka cancellation window dete hain. Unsaved work save karein.")
    def act(mode):
        messages = {
            "lock": "Abhi Windows session lock karni hai?",
            "shutdown": "Windows ko 60 seconds baad SHUTDOWN schedule karein? Unsaved work risk mein hai.",
            "restart": "Windows ko 60 seconds baad RESTART schedule karein? Unsaved work risk mein hai.",
            "cancel": "Pending shutdown/restart cancel karne ki request bhejein?",
        }
        if not messagebox.askyesno("Confirm " + mode, messages[mode], parent=win):
            return
        try:
            result = system_action(mode)
            app.say("RESULT", result)
            messagebox.showinfo("System action", result, parent=win)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("System action failed", str(exc), parent=win)
    for label, mode in (("Lock Windows", "lock"), ("Shutdown in 60 seconds", "shutdown"),
                        ("Restart in 60 seconds", "restart"), ("Cancel pending power", "cancel")):
        button(win, label, lambda m=mode: act(m)).pack(fill="x", padx=20, pady=5)


def image_studio(app):
    win = window(app.root, "AI image studio (optional paid API)", "730x610")
    info(win, "Cloud image generation optional hai. OpenAI API billing ChatGPT subscription se alag hai.\n"
              "Prompt aur API request cloud provider ko jayenge; local Ollama 3B model images generate nahi karta.\n"
              "API key sirf is request ke liye memory mein rahegi, file mein save nahi hoti.")
    tk.Label(win, text="Image prompt", bg=BG, fg=FG).pack(anchor="w", padx=22)
    prompt = tk.Text(win, height=6, bg=PANEL, fg=FG, insertbackground=CYAN,
                     font=("Segoe UI", 11), wrap="word", padx=10, pady=8)
    prompt.pack(fill="x", padx=22, pady=(4, 12))
    tk.Label(win, text="OpenAI API key (not saved)", bg=BG, fg=FG).pack(anchor="w", padx=22)
    entry = tk.Entry(win, show="*", bg=PANEL, fg=FG, insertbackground=CYAN,
                     font=("Segoe UI", 11), relief="flat")
    entry.pack(fill="x", padx=22, pady=(4, 12), ipady=8)
    status = tk.StringVar(value="Ready · click Generate to review cost and privacy.")
    tk.Label(win, textvariable=status, bg=BG, fg=MUTE, wraplength=645,
             justify="left").pack(anchor="w", padx=22, pady=(4, 12))
    action = button(win, "Generate 1024x1024 PNG", lambda: None)
    import queue
    results = queue.Queue()
    def poll_result():
        if not win.winfo_exists():
            return
        try:
            outcome = results.get_nowait()
        except queue.Empty:
            pass
        else:
            complete(outcome)
        win.after(150, poll_result)
    win.after(150, poll_result)

    def generate():
        text = prompt.get("1.0", "end").strip()
        key = entry.get().strip()
        if not text or not key:
            messagebox.showerror("Missing details", "Prompt aur API key required hain.", parent=win)
            return
        directory = filedialog.askdirectory(title="Choose folder for generated image", parent=win)
        if not directory:
            return
        if not messagebox.askyesno(
            "Approve external image generation",
            "Is action ke liye OpenAI Images API se paid request jayegi.\n"
            "Prompt cloud provider ko send hoga, aur output aapke selected folder mein save hoga.\n"
            "Quality: low · 1024x1024 · 1 image.\n\nProceed?",
            parent=win
        ):
            return
        entry.delete(0, "end")  # Do not retain credentials in a visible control.
        action.configure(state="disabled")
        status.set("Image API request in progress (cloud / paid)...")
        def work():
            try:
                file = generate_cloud_image(text, key, directory)
                result = ("success", str(file))
            except Exception:
                # Error text must never expose a provider response containing secrets.
                result = ("failure", "API request failed. Billing, API key, network aur model access check karein.")
            # A background worker never touches Tk widgets. The root UI polls
            # the thread-safe queue and performs callbacks on its own thread.
            results.put(result)
        def complete(result):
            action.configure(state="normal")
            if result[0] == "success":
                status.set("Image saved: " + result[1])
                app.say("RESULT", "Image file save hui: " + result[1])
                messagebox.showinfo("Image created", "Saved: " + result[1], parent=win)
            else:
                status.set(result[1])
                messagebox.showerror("Image generation", result[1], parent=win)
        threading.Thread(target=work, daemon=True).start()
    action.configure(command=generate)
    action.pack(anchor="w", padx=22, pady=5)


def toolkit_window(app):
    win = window(app.root, "Stonic-inspired creative toolkit", "700x580")
    info(win, "HASEEB AI safe tools · local by default · dangerous operations always reviewed.\n"
              "Existing voice, mouse/keyboard, apps, Google, YouTube, media aur GitHub updater stay intact.")
    entries = [
        ("Daily schedule & timetable", lambda: schedule_window(app),
         "Add/delete dated tasks in a local CSV; no automatic reminders"),
        ("Weather in browser", lambda: weather_window(app),
         "Uses browser search; never guesses a forecast"),
        ("AI Code Review", lambda: code_studio(app),
         "Read a selected code file; local model suggests fixes, never writes code"),
        ("AI Code Generator", lambda: code_generator(app),
         "Ask the local model for draft code; never auto-executes"),
        ("AI Image Studio", lambda: image_studio(app),
         "Optional paid image API; per-request approval and no saved key"),
        ("Reviewed power controls", lambda: system_window(app),
         "Manual lock, delayed restart/shutdown and cancel"),
        ("Sleep / Wake Jarvis", app.toggle_sleep_mode,
         "Pause main chat/commands; type Wake up Jarvis to resume"),
    ]
    for label, invoke, detail in entries:
        panel = tk.Frame(win, bg=PANEL)
        panel.pack(fill="x", padx=19, pady=5)
        button(panel, label, invoke).pack(side="left", padx=6, pady=3)
        tk.Label(panel, text=detail, bg=PANEL, fg=MUTE,
                 justify="left", wraplength=330, font=("Segoe UI", 9)).pack(
            side="left", padx=6, pady=7)
