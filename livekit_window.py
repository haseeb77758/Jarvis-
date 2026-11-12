"""Jarvis primary realtime voice settings and session controls.

The verified LiveKit console agent is preserved. Dashboard voice is its
persistent one-click entry point; cloud sessions always require consent.
"""
import os
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
        self.console = LiveKitConsole()
        self.window = tk.Toplevel(host.root)
        self.window.title('Jarvis · LiveKit ONLY Voice · GPT-Live-1')
        self.window.geometry('720x695')
        self.window.minsize(660, 625)
        self.window.configure(bg=BG)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.status = tk.StringVar(
            master=self.window, value='Cloud voice OFF · no session running.'
        )

        tk.Label(self.window, text='JARVIS · REALTIME VOICE', font=('Segoe UI', 18, 'bold'),
                 bg=BG, fg=CYAN).pack(anchor='w', padx=22, pady=(18, 8))
        description = (
            'Recommended: use your existing deployed training-2057 agent '
            'in the official LiveKit Cloud Agent Console in the browser. '
            'This does not load Python or blingfire DLLs on Windows.\n\n'
            'Important: inference is usage-metered, not unlimited free. '
            'No other chatbot or alternate voice mode runs in Jarvis. '
            'Opening the Cloud dashboard does NOT start a voice call. '
            'Any call begun in the browser can use LiveKit credits; end it '
            'in that browser tab. Jarvis STOP and its local timer CANNOT '
            'end a browser call.\n\n'
            'The typed command box is local, not another chatbot. Voice conversation cannot execute desktop actions, '
            'access private files or use your Windows login.'
        )
        tk.Label(self.window, text=description, bg=PANEL, fg=TEXT,
                 font=('Segoe UI', 10), justify='left', wraplength=660,
                 padx=17, pady=13).pack(fill='x', padx=20, pady=4)

        self.noise_enhancement = tk.BooleanVar(master=self.window, value=False)
        tk.Checkbutton(
            self.window,
            text='AI-Coustics (optional · extra install/download, possibly billed)',
            variable=self.noise_enhancement, bg=BG, fg=MUTED, selectcolor=PANEL,
            activebackground=BG, activeforeground=TEXT,
        ).pack(anchor='w', padx=26, pady=(5, 3))

        cap = tk.Frame(self.window, bg=BG)
        cap.pack(fill='x', padx=25, pady=(2, 7))
        tk.Label(cap, text='Automatically STOP after:', bg=BG, fg=TEXT,
                 font=('Segoe UI', 10)).pack(side='left')
        self.max_minutes = tk.StringVar(master=self.window, value='10')
        ttk.Combobox(cap, textvariable=self.max_minutes, values=['5', '10', '15'],
                     width=4, state='readonly').pack(side='left', padx=12)
        tk.Label(cap, text='minutes · a time limit, not a money cap',
                 bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='left')

        links = tk.Frame(self.window, bg=BG)
        links.pack(fill='x', padx=23, pady=(0, 8))
        self._button('Get LiveKit API key ↗',
                     lambda: webbrowser.open(LIVEKIT_DASHBOARD)).pack(side='left', padx=3)
        self._button('Key instructions ↗',
                     lambda: webbrowser.open(LIVEKIT_KEYS_GUIDE)).pack(side='left', padx=3)
        self._button('LiveKit pricing ↗',
                     lambda: webbrowser.open(LIVEKIT_PRICING)).pack(side='left', padx=3)

        self.setup_button = self._button('1  Install / repair LiveKit voice tools', self.install)
        self.setup_button.pack(fill='x', padx=25, pady=5)
        self.credentials_button = self._button('2  Open LOCAL API key + secret file',
                                               self.edit_credentials)
        self.credentials_button.pack(fill='x', padx=25, pady=5)
        self.start_button = self._button('● Talk Live · Browser Agent Console (recommended)',
                                         self.start, primary=True)
        self.start_button.pack(fill='x', padx=25, pady=5)
        self.local_start_button = self._button(
            'Advanced · Local Python console (can be blocked by Windows)', self.start_local)
        self.local_start_button.pack(fill='x', padx=25, pady=4)
        self.stop_button = self._button('STOP LiveKit realtime voice', self.stop)
        self.stop_button.pack(fill='x', padx=25, pady=5)
        self._button('View last LiveKit error / diagnostic log', self.open_diagnostics).pack(
            fill='x', padx=25, pady=4)

        tk.Label(self.window, textvariable=self.status, bg=BG, fg=CYAN,
                 wraplength=655, font=('Segoe UI', 10), justify='left').pack(
                     anchor='w', padx=25, pady=(10, 3))
        self.refresh()
        self.window.after(1000, self._tick)

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
        active = self.console.is_running()
        remaining = self.console.remaining_seconds() if active else 0
        if active:
            minutes, seconds = divmod(remaining, 60)
            phrase = f'LOCAL LIVE · GPT-Live-1 / marin · auto STOP in {minutes}:{seconds:02d}'
            self.start_button.configure(state='disabled')
            self.local_start_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
        else:
            if self.browser_opened:
                phrase = ('BROWSER CONSOLE OPENED · call status unknown here; '
                          'end any voice call in LiveKit browser tab')
            elif self.setup_issue:
                phrase = ('LOCAL SDK ISSUE · ' + self.setup_issue +
                          ' · Browser Talk Live works without that DLL')
            elif self.console.last_error:
                phrase = 'LOCAL VOICE EXITED · ' + self.console.last_error
            else:
                phrase = 'BROWSER LIVEKIT READY · Talk Live opens official Cloud Agent Console'
            self.start_button.configure(state='normal')
            self.local_start_button.configure(state='normal')
            self.stop_button.configure(state='disabled')
        if hasattr(self.host, 'livekit_voice_state'):
            self.host.livekit_voice_state.set(phrase)
        button = getattr(self.host, 'livekit_primary_button', None)
        if button is not None:
            button.configure(text='■ End Live Voice' if active else '● Talk Live')
        if not self.busy:
            self.status.set(phrase)

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
        """Launch official deployed Agent Console without local DLLs or API secrets.

        This only opens the user's browser: the user signs in and explicitly
        starts any potentially billed LiveKit session there. There is no
        browser session state or stop control in the Windows dashboard.
        """
        if self.closed or self.busy:
            return False
        if self.console.is_running():
            self.window.deiconify()
            messagebox.showwarning(
                'Local voice already active',
                'Pehle local LiveKit session STOP karo taake do metered '
                'conversations ek saath na chalain.', parent=self.window)
            return False
        if not messagebox.askyesno(
            'Open LiveKit Cloud Agent Console?',
            'Browser mein LiveKit Cloud khulegi. Project select karo, '
            'Agents > training-2057 > Launch Console dabao aur mic allow karo. '
            'Web page khulne se call automatically START nahi hoti.\n\n'
            'Jab browser mein voice call shuru karoge to Cloud credits use '
            'ho sakte hain. IMPORTANT: Jarvis STOP aur 5/10/15 min auto '
            'timer browser call ko band NAHI kar sakte. Browser mein khud '
            'End Call dabana zaroori hai. Continue?',
            parent=self.window
        ):
            return False
        try:
            opened = webbrowser.open(LIVEKIT_DASHBOARD, new=2)
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            self.status.set('Browser open nahi hua; Chrome mein https://cloud.livekit.io/ kholo.')
            messagebox.showerror('Browser unavailable',
                                 'Browser nahi khula. https://cloud.livekit.io/ manually kholo.',
                                 parent=self.window)
            return False
        self.browser_opened = True
        self.refresh()
        # The browser takes foreground; Jarvis never claims a cloud call
        # has started, nor can it terminate browser sessions.
        self.window.withdraw()
        return True

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
        self.refresh()

    def close(self):
        if self.closed:
            return
        self.console.stop()
        self.closed = True
        self.window.destroy()
