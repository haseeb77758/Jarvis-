"""Jarvis primary realtime voice settings and session controls.

The verified LiveKit console agent is preserved. Dashboard voice is its
persistent one-click entry point; cloud sessions always require consent.
"""
import os
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from livekit_bridge import (
    LiveKitConsole, LiveKitSetupError, configured, create_credentials_template,
    environment_python, install_optional, preflight_runtime,
    credential_issue, session_log_path, safe_log_tail,
)

BG, PANEL, TEXT, MUTED, CYAN = '#080e17', '#101c2b', '#eff7fa', '#9ab1c0', '#4ce2d2'
LIVEKIT_DASHBOARD = 'https://cloud.livekit.io/'
LIVEKIT_KEYS_GUIDE = 'https://docs.livekit.io/reference/api/projects/keys/'
LIVEKIT_PRICING = 'https://livekit.com/pricing/inference'


class LiveKitVoiceWindow:
    def __init__(self, host):
        self.host = host
        self.closed = False
        self.busy = False
        self.setup_issue = ""
        self.browser_opened = False
        self.tool_requests = queue.Queue()
        self.direct_service = None
        self.console = LiveKitConsole()
        self.window = tk.Toplevel(host.root)
        self.window.title('Jarvis · LiveKit ONLY Voice · GPT-Live-1')
        self.window.geometry('760x790')
        self.window.minsize(700, 690)
        self.window.configure(bg=BG)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.status = tk.StringVar(
            master=self.window, value='Cloud voice OFF · no session running.'
        )

        tk.Label(self.window, text='JARVIS · REALTIME VOICE', font=('Segoe UI', 18, 'bold'),
                 bg=BG, fg=CYAN).pack(anchor='w', padx=22, pady=(18, 8))
        description = (
            'Direct LiveKit WebRTC inside a dedicated Jarvis desktop voice window. '
            'Connect, disconnect, microphone and agent audio without Cloud Console '
            'navigation or native blingfire DLL imports.\n\n'
            'Voice sessions use your own LiveKit Cloud credits, not unlimited free. '
            'Each session needs approval and auto-ends after 10 minutes with a '
            'server-side RoomService stop attempt. This is not a spending cap.\n\n'
            'Voice can request limited desktop actions only after the matching '
            'Client Tool is enabled in LiveKit Builder. Every app/file action '
            'requires a separate native Jarvis approval. No shell, deletion, '
            'screen typing, unrestricted file reads or automatic permissions.'
        )
        tk.Label(self.window, text=description, bg=PANEL, fg=TEXT,
                 font=('Segoe UI', 10), justify='left', wraplength=660,
                 padx=17, pady=13).pack(fill='x', padx=20, pady=4)

        self.start_button = self._button(
            '● Talk Live · Direct Jarvis WebRTC (recommended)', self.start, primary=True)
        self.start_button.pack(fill='x', padx=25, pady=(10, 9))
        tk.Label(
            self.window,
            text='Direct voice uses saved LiveKit Cloud project credentials and '
                 'a private loopback token service. No local LiveKit Python SDK '
                 'or blocked DLL. One-time key setup only; no Cloud Console.',
            bg=BG, fg=CYAN, wraplength=660, justify='left',
            font=('Segoe UI', 9),
        ).pack(fill='x', padx=25, pady=(0, 8))
        tk.Label(
            self.window, text='ADVANCED · LOCAL PYTHON CONSOLE (OPTIONAL)',
            bg=BG, fg=MUTED, font=('Segoe UI', 10, 'bold')
        ).pack(anchor='w', padx=25, pady=(4, 1))

        self.noise_enhancement = tk.BooleanVar(master=self.window, value=False)
        tk.Checkbutton(
            self.window,
            text='AI-Coustics (optional · extra install/download, possibly billed)',
            variable=self.noise_enhancement, bg=BG, fg=MUTED, selectcolor=PANEL,
            activebackground=BG, activeforeground=TEXT,
        ).pack(anchor='w', padx=26, pady=(5, 3))

        cap = tk.Frame(self.window, bg=BG)
        cap.pack(fill='x', padx=25, pady=(2, 7))
        tk.Label(cap, text='Advanced Python STOP after:', bg=BG, fg=TEXT,
                 font=('Segoe UI', 10)).pack(side='left')
        self.max_minutes = tk.StringVar(master=self.window, value='10')
        ttk.Combobox(cap, textvariable=self.max_minutes, values=['5', '10', '15'],
                     width=4, state='readonly').pack(side='left', padx=12)
        tk.Label(cap, text='minutes · direct WebRTC has separate 10 min limit',
                 bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='left')

        links = tk.Frame(self.window, bg=BG)
        links.pack(fill='x', padx=23, pady=(0, 8))
        self._button('Get LiveKit API key ↗',
                     lambda: webbrowser.open(LIVEKIT_DASHBOARD)).pack(side='left', padx=3)
        self._button('Key instructions ↗',
                     lambda: webbrowser.open(LIVEKIT_KEYS_GUIDE)).pack(side='left', padx=3)
        self._button('LiveKit pricing ↗',
                     lambda: webbrowser.open(LIVEKIT_PRICING)).pack(side='left', padx=3)

        self.setup_button = self._button('Advanced 1 · Install / repair local Python voice', self.install)
        self.setup_button.pack(fill='x', padx=25, pady=5)
        self.credentials_button = self._button('One-time LiveKit project keys (direct voice + advanced)',
                                               self.edit_credentials)
        self.credentials_button.pack(fill='x', padx=25, pady=5)
        self.local_start_button = self._button(
            'Advanced 3 · Start local Python voice (Windows may block DLL)', self.start_local)
        self.local_start_button.pack(fill='x', padx=25, pady=4)
        self.stop_button = self._button('■ End Voice · Stop LiveKit room', self.stop)
        self.stop_button.pack(fill='x', padx=25, pady=5)
        self._button('View last LiveKit error / diagnostic log', self.open_diagnostics).pack(
            fill='x', padx=25, pady=4)

        tk.Label(self.window, textvariable=self.status, bg=BG, fg=CYAN,
                 wraplength=655, font=('Segoe UI', 10), justify='left').pack(
                     anchor='w', padx=25, pady=(10, 3))
        self.refresh()
        self.window.after(1000, self._tick)
        self.window.after(120, self._poll_desktop_tools)

    def _button(self, text, command, primary=False):
        return tk.Button(
            self.window, text=text, command=command,
            bg=CYAN if primary else PANEL, fg=BG if primary else TEXT,
            activebackground='#a0fff4' if primary else '#204052',
            activeforeground=BG if primary else TEXT, font=('Segoe UI', 10),
            relief='flat', bd=0, padx=12, pady=8, cursor='hand2')

    def _tick(self):
        if self.closed:
            return
        self.refresh()
        self.window.after(1000, self._tick)

    def refresh(self):
        if self.closed:
            return
        direct = self.direct_service
        direct_state = direct.status() if direct else None
        direct_active = bool(direct_state and direct_state["active"])
        local_active = self.console.is_running()
        if direct_active:
            remaining = direct_state["remainingSeconds"]
            mins, secs = divmod(remaining, 60)
            phrase = ("LIVEKIT WEBRTC · " + direct_state["state"] +
                      f" · auto STOP in {mins}:{secs:02d}")
        elif local_active:
            remaining = self.console.remaining_seconds()
            mins, secs = divmod(remaining, 60)
            phrase = f"ADVANCED LOCAL LIVE · auto STOP in {mins}:{secs:02d}"
        else:
            phrase = ("DIRECT LIVEKIT READY · Talk Live opens your desktop voice "
                      "window · credentials required only on this PC")
        self.start_button.configure(state="disabled" if direct_active or local_active else "normal")
        self.local_start_button.configure(state="disabled" if direct_active else "normal")
        self.stop_button.configure(state="normal" if direct_active or local_active else "disabled")
        if hasattr(self.host, "livekit_voice_state"):
            self.host.livekit_voice_state.set(phrase)
        button = getattr(self.host, "livekit_primary_button", None)
        if button is not None:
            button.configure(text="■ End Live Voice" if direct_active or local_active
                             else "● Talk Live")
        if not self.busy:
            self.status.set(phrase)

    def _launch_direct_browser(self, url):
        """App-mode browser window looks native; never imports blocked native SDK."""
        candidates = []
        for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(env)
            if root:
                candidates.extend([
                    Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe",
                ])
        for executable in candidates:
            if executable.is_file():
                try:
                    subprocess.Popen(
                        [str(executable), "--app=" + url, "--window-size=1200,800"],
                        shell=False, close_fds=True)
                    return True
                except OSError:
                    continue
        try:
            return bool(webbrowser.open(url, new=2))
        except (OSError, webbrowser.Error):
            return False

    def _poll_desktop_tools(self):
        if self.closed:
            return
        try:
            while True:
                task = self.tool_requests.get_nowait()
                action = task.action
                if getattr(self.host, "stop", None) is not None and self.host.stop.is_set():
                    task.result = "DENIED: Jarvis is STOPPED."
                    task.event.set()
                    continue
                if not self.direct_service or not self.direct_service.status()["active"]:
                    task.result = "DENIED: Voice session not active."
                    task.event.set()
                    continue
                preview = __import__("json").dumps(action, ensure_ascii=False, indent=2)
                # A *native* messagebox is not controlled by the agent/browser.
                # Private filenames or search results may be returned to the
                # Cloud agent only after this explicit local consent.
                self.host.root.deiconify()
                self.host.root.lift()
                allowed = messagebox.askyesno(
                    "JARVIS VOICE · REVIEW DESKTOP ACTION",
                    "Cloud AI requested this local action:\n\n" + preview +
                    "\n\nOnly a small allowlisted set is supported. "
                    "If approved, the action result may be spoken by LiveKit "
                    "and transmitted to your Cloud project. Approve?",
                    parent=self.host.root,
                )
                if not allowed:
                    task.result = "DENIED: User declined in desktop approval."
                    task.event.set()
                    continue

                def execute_one(request=task):
                    try:
                        # Controller.validate and safe_child additionally enforce
                        # allowed app names and restrict file operations to workspace.
                        result = self.host.control.execute(request.action)
                        request.result = "DONE: " + str(result)[:1650]
                    except Exception as exc:
                        request.result = "ERROR: " + str(exc)[:1200]
                    finally:
                        request.event.set()
                        try:
                            self.host.events.put((
                                self.host.generation, "notice",
                                "Voice action reviewed: " + request.result[:350],
                                "", None))
                        except Exception:
                            pass
                threading.Thread(target=execute_one, daemon=True).start()
        except queue.Empty:
            pass
        self.window.after(120, self._poll_desktop_tools)

    def open_diagnostics(self):
        """Only open a local, small log, never upload API keys anywhere."""
        try:
            log = session_log_path()
            log.parent.mkdir(parents=True, exist_ok=True)
            if not log.exists():
                log.write_text("No LiveKit session diagnostics yet.\n", encoding="utf-8")
            # Display redacted information, NOT the unfiltered SDK raw file.
            view = log.parent / "last-session-redacted.txt"
            view.write_text(safe_log_tail(12000) or "No logged error details available.\n",
                            encoding="utf-8")
            if os.name == "nt":
                subprocess.Popen(['notepad.exe', str(view)])
            else:
                self.status.set('Diagnostics: ' + str(view))
        except OSError:
            messagebox.showerror('LiveKit diagnostics',
                                 'Local diagnostics file nahi khul saki.',
                                 parent=self.window)

    def edit_credentials(self):
        try:
            path = create_credentials_template()
            if os.name != 'nt':
                raise LiveKitSetupError('Open this file with your editor on Windows.')
            subprocess.Popen(['notepad.exe', str(path)])
            self.status.set(
                'Your keys stay in the private local file. Save LIVEKIT_URL, '
                'LIVEKIT_API_KEY, LIVEKIT_API_SECRET; never share them in chat.'
            )
        except (OSError, LiveKitSetupError) as exc:
            messagebox.showerror('LiveKit credentials', str(exc), parent=self.window)

    def install(self):
        if self.busy:
            return
        if not messagebox.askyesno(
            'Install LiveKit voice tools?',
            'This installs required LiveKit packages in a separate Python environment. '
            'Normal GPT-Live-1 voice does NOT download local speech models. '
            'AI-Coustics downloads optional assets only if checked. '
            'Internet required; this does not start a billed session. '
            'Install or repair?',
            parent=self.window
        ):
            return
        self.busy = True
        self.setup_button.configure(state='disabled')
        noise = bool(self.noise_enhancement.get())
        self.status.set('Checking/installing only the required LiveKit components...')
        def job():
            try:
                result, error = install_optional(noise_enhancement=noise), None
            except Exception as exc:
                result, error = None, (str(exc) if isinstance(exc, LiveKitSetupError)
                                       else 'Installation failed. Check Python/internet.')
            def finished():
                if self.closed:
                    return
                self.busy = False
                self.setup_issue = error or ""
                self.setup_button.configure(state='normal')
                self.status.set(error or result)
            try:
                self.window.after(0, finished)
            except tk.TclError:
                pass
        threading.Thread(target=job, daemon=True).start()

    def start(self):
        """One-click consented direct WebRTC with local-only token minting."""
        if self.closed or self.busy:
            return False
        if self.console.is_running():
            messagebox.showwarning(
                "Duplicate voice", "Pehle advanced Python session STOP karo.",
                parent=self.window)
            return False
        if self.direct_service and self.direct_service.status()["active"]:
            self.status.set("Already connected. End Live Voice to stop the active room.")
            self.refresh()
            return False
        from direct_livekit import DirectVoiceService, get_project_settings
        try:
            # This reads the LOCAL credentials file without importing LiveKit's
            # Windows-blocked native blingfire dependency.
            get_project_settings()
        except LiveKitSetupError as exc:
            self.window.deiconify()
            self.window.lift()
            messagebox.showinfo(
                "One-time LiveKit credentials setup",
                str(exc) + "\n\nClick 'Advanced 2 · Edit local Python API key' "
                "to save LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET. "
                "They remain local and are not sent to the browser.",
                parent=self.window)
            return False
        if not messagebox.askyesno(
            "Start Jarvis Direct LiveKit voice?",
            "Connect to your deployed training-2057 agent? Voice uses LiveKit "
            "Cloud credits. Automatically stop/close the room after 10 minutes "
            "(network conditions may delay confirmation). This is NOT a cash cap.\n\n"
            "Limited voice-initiated Windows/file commands require a separate "
            "native Jarvis approval EACH TIME. No shell or file deletion. "
            "Start one voice session?",
            parent=self.window,
        ):
            return False
        try:
            if self.direct_service is None:
                self.direct_service = DirectVoiceService(self.tool_requests)
            url = self.direct_service.start() + "~auto"
            if not self._launch_direct_browser(url):
                raise OSError("No compatible desktop browser opened.")
            self.browser_opened = True
            self.refresh()
            self.window.withdraw()
            return True
        except (OSError, RuntimeError, LiveKitSetupError) as exc:
            self.window.deiconify()
            self.status.set("Direct voice launch failed: " + str(exc)[:300])
            messagebox.showerror("Jarvis WebRTC", str(exc), parent=self.window)
            return False

    def start_local(self):
        """Advanced, user-approved native Python console; may be blocked by policy."""
        if self.closed or self.busy:
            return False
        if self.console.is_running():
            self.refresh()
            return True
        if not configured():
            self.window.deiconify()
            self.window.lift()
            self.status.set('First create project keys, then save them locally.')
            messagebox.showinfo(
                'LiveKit API keys required',
                'Get keys from https://cloud.livekit.io/ and enter the '
                'LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET in the '
                'LOCAL credentials file. Your keys are not sent to ChatGPT.',
                parent=self.window,
            )
            return False
        if not environment_python().is_file():
            self.window.deiconify()
            self.window.lift()
            messagebox.showinfo(
                'LiveKit not installed',
                'Install / repair LiveKit voice tools first.',
                parent=self.window,
            )
            return False
        if self.setup_issue:
            self.window.deiconify()
            self.window.lift()
            messagebox.showwarning(
                'Repair LiveKit setup first',
                'Pichli LiveKit installation fail hui thi. Install / repair dabao. '
                'Agar error aaye to View last LiveKit error kholo. '
                'Abhi metered voice start nahi hogi.',
                parent=self.window,
            )
            return False
        cap = int(self.max_minutes.get())
        if not messagebox.askyesno(
            'Start metered LiveKit voice?',
            f'The GPT-Live-1 voice session uses your LiveKit Cloud credits or '
            f'billing allowance. It will automatically stop after {cap} minutes '
            'or earlier if you press STOP. This is NOT a money-spending cap. '
            'AI-Coustics may cost extra when enabled. '
            'Start this one voice conversation?',
            parent=self.window
        ):
            return False
        # Check imports without starting cloud inference, then launch in Tk's
        # main thread; never freeze the UI while Python is being checked.
        self.busy = True
        self.start_button.configure(state='disabled')
        self.status.set('Checking installed LiveKit engine before starting voice...')
        noise = self.noise_enhancement.get()

        def job():
            try:
                preflight_runtime(noise_enhancement=noise)
                error = None
            except LiveKitSetupError as exc:
                error = str(exc)
            except Exception:
                error = 'LiveKit preflight failed; repair voice tools.'

            def finish():
                if self.closed:
                    return
                self.busy = False
                if error:
                    self.setup_issue = error
                    self.window.deiconify()
                    self.window.lift()
                    self.status.set('VOICE SETUP ERROR · ' + error)
                    messagebox.showerror('LiveKit voice preflight', error, parent=self.window)
                    return
                try:
                    self.console.start(consent=True, noise_enhancement=noise, max_minutes=cap)
                    self.setup_issue = ""
                    self.refresh()
                    self.window.withdraw()
                    self.host.root.lift()
                except (OSError, LiveKitSetupError) as exc:
                    self.window.deiconify()
                    self.status.set('VOICE START FAILED · ' + str(exc))
                    messagebox.showerror('LiveKit voice', str(exc), parent=self.window)
            try:
                self.window.after(0, finish)
            except tk.TclError:
                pass
        threading.Thread(target=job, daemon=True).start()
        return True

    def stop(self):
        self.console.stop()
        if self.direct_service and self.direct_service.status()["active"]:
            # Stop is immediate in the local state; HTTP RoomService DeleteRoom
            # happens in a background thread to keep the STOP button responsive.
            service = self.direct_service
            threading.Thread(target=service.disconnect, daemon=True).start()
            self.status.set("ENDING LIVEKIT ROOM · disconnect requested...")
        self.refresh()

    def close(self):
        if self.closed:
            return
        self.console.stop()
        if self.direct_service:
            self.direct_service.close()  # End room before terminating desktop helper.
            self.direct_service = None
        self.closed = True
        self.window.destroy()
