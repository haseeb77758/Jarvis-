"""Graphical, opt-in Jarvis source installer for personal Windows testing.

Requires separately installed, official Python 3.12 with tkinter.
Does not run unsigned Jarvis.exe/CMD, change security policies, or gain elevation.
The user explicitly approves third-party dependency installation.
"""
from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

ROOT = Path(__file__).resolve().parent
BG = "#0a1520"
PANEL = "#112234"
CYAN = "#40ddd2"
WHITE = "#eaf5fa"
MUTED = "#9ab1bd"
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HaseebCrafts" / "JarvisApp"


def official_python_binary() -> Path:
    """A Python GUI entrypoint may be hosted by pythonw.exe; child needs stdout."""
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        executable = executable.with_name("python.exe")
    return executable


class JarvisSetup:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events = queue.Queue()
        self.process = None
        self.installing = False
        self.root.title("HASEEB AI | Personal Windows Setup")
        self.root.geometry("670x570")
        self.root.minsize(590, 520)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        wrapper = tk.Frame(root, bg=BG)
        wrapper.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(wrapper, text="H A S E E B   A I", fg=CYAN, bg=BG,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(wrapper, text="JARVIS  /  PERSONAL WINDOWS 11 TEST",
                 fg=MUTED, bg=BG, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))
        tk.Label(wrapper, text="Official Python 3.12 required. No EXE or CMD launcher.",
                 fg=WHITE, bg=BG, font=("Segoe UI", 11), justify="left").pack(anchor="w")
        tk.Label(wrapper,
                 text="After approval, dependencies install in an isolated local folder. "
                      "No administrator permission or Windows Security changes are requested. "
                      "An unsigned component may still be blocked by Smart App Control.",
                 fg=MUTED, bg=BG, justify="left", wraplength=600,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 14))

        agreement_box = tk.Frame(wrapper, bg=PANEL, padx=12, pady=10)
        agreement_box.pack(fill="x", pady=(0, 12))
        self.agreed = tk.BooleanVar(value=False)
        tk.Checkbutton(
            agreement_box,
            text="I approve installing the Python packages listed in requirements.txt.",
            variable=self.agreed, onvalue=True, offvalue=False,
            bg=PANEL, fg=WHITE, activebackground=PANEL,
            activeforeground=WHITE, selectcolor=BG,
            wraplength=570, justify="left", font=("Segoe UI", 10)
        ).pack(anchor="w")
        self.install_btn = tk.Button(
            wrapper, text="INSTALL & OPEN JARVIS", command=self.begin,
            bg=CYAN, fg=BG, activebackground="#a4fff3", activeforeground=BG,
            font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2", padx=20, pady=11
        )
        self.install_btn.pack(fill="x")
        self.status = tk.StringVar(value="Ready · no software installed yet")
        tk.Label(wrapper, textvariable=self.status, bg=BG, fg=CYAN,
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", pady=(12, 5))
        self.log = scrolledtext.ScrolledText(wrapper, height=12, bg="#07111c",
                                             fg=WHITE, insertbackground=CYAN,
                                             font=("Consolas", 9), relief="flat",
                                             state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)
        tk.Label(wrapper, text="Created by Haseeb Crafts  ·  Private local testing  ·  No remote desktop server",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 0))
        self.root.after(120, self.poll)

    def record(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line.rstrip() + "\n")
        self.log.configure(state="disabled")
        self.log.see("end")

    def begin(self) -> None:
        if self.installing:
            return
        if os.name != "nt" or sys.version_info[:2] != (3, 12):
            messagebox.showerror("Python 3.12 required",
                                 "Install official Python 3.12 from python.org first, "
                                 "then open this setup with that version.", parent=self.root)
            return
        try:
            import tkinter  # noqa: F401
            if not (ROOT / "tools" / "install_windows.py").is_file():
                raise FileNotFoundError("Extract the COMPLETE ZIP before launching this file.")
            if not (ROOT / "requirements.txt").is_file():
                raise FileNotFoundError("requirements.txt missing from extracted folder.")
        except (ImportError, FileNotFoundError) as exc:
            messagebox.showerror("Missing setup files", str(exc), parent=self.root)
            return
        if not self.agreed.get():
            messagebox.showinfo("Your approval is required",
                                "Tick the checkbox first. Jarvis will not install packages without approval.",
                                parent=self.root)
            return
        self.installing = True
        self.install_btn.configure(state="disabled")
        self.status.set("Installing in your Windows user folder…")
        self.record("Installing only after your approval. Windows Security is unchanged.")
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self) -> None:
        try:
            python = official_python_binary()
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.process = subprocess.Popen(
                [str(python), str(ROOT / "tools" / "install_windows.py")],
                cwd=str(ROOT), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", text=True,
                bufsize=1, shell=False, creationflags=flags
            )
            if self.process.stdin:
                # GUI checkbox + button is the explicit consent for this YES.
                self.process.stdin.write("YES\n")
                self.process.stdin.flush()
                self.process.stdin.close()
            if self.process.stdout:
                for line in self.process.stdout:
                    self.events.put(("log", line))
            result = self.process.wait()
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def poll(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.record(value)
                elif kind == "error":
                    self.status.set("Installation failed — see details below")
                    self.record("ERROR: " + value)
                    self.installing = False
                    self.install_btn.configure(state="normal")
                elif kind == "done":
                    self.installing = False
                    if value == 0:
                        self.status.set("Installed. Launching your Jarvis desktop assistant…")
                        self.record("PASS: Dependencies and local tests installed successfully.")
                        self.launch()
                    else:
                        self.status.set("Setup failed — read the error log")
                        self.record("Setup process exited with code " + str(value))
                        self.install_btn.configure(state="normal")
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(120, self.poll)

    def launch(self) -> None:
        pythonw = LOCAL / ".venv" / "Scripts" / "pythonw.exe"
        app = LOCAL / "app.py"
        if not pythonw.is_file() or not app.is_file():
            self.status.set("Installation incomplete — required runtime missing")
            self.record("ERROR: Cannot find Python runtime/app at " + str(LOCAL))
            self.install_btn.configure(state="normal")
            return
        try:
            subprocess.Popen([str(pythonw), str(app)], cwd=str(LOCAL), shell=False)
        except OSError as exc:
            self.status.set("Installed, but Jarvis did not open")
            self.record("Launch error: " + str(exc))
            self.install_btn.configure(state="normal")
        else:
            self.status.set("Jarvis launch requested · use your Desktop shortcut later")
            self.record("Jarvis launch requested. Verify its window opened on your screen.")
            self.install_btn.configure(state="normal")

    def close(self) -> None:
        if self.installing:
            if not messagebox.askyesno("Cancel setup?",
                                       "Canceling can leave partially installed dependencies. Close anyway?",
                                       parent=self.root):
                return
            if self.process and self.process.poll() is None:
                self.process.terminate()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    setup = JarvisSetup(root)
    if "--self-test" in sys.argv:
        root.update_idletasks()
        assert setup.install_btn.winfo_exists()
        assert setup.agreed.get() is False
        assert setup.installing is False
        root.destroy()
        print("PASS: Jarvis GUI setup renders with explicit dependency consent and no installer launched.")
        return
    root.mainloop()


if __name__ == "__main__":
    main()
