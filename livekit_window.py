"""Optional LiveKit voice mode UI. Does not replace the free Jarvis voice."""
import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox

from livekit_bridge import (
    LiveKitConsole, LiveKitSetupError, configured, create_credentials_template,
    install_optional,
)

BG, PANEL, TEXT, MUTED, CYAN = '#080e17', '#101c2b', '#eff7fa', '#9ab1c0', '#4ce2d2'


class LiveKitVoiceWindow:
    def __init__(self, host):
        self.host = host
        self.closed = False
        self.busy = False
        self.console = LiveKitConsole()
        self.window = tk.Toplevel(host.root)
        self.window.title('Jarvis · LiveKit realtime voice (optional)')
        self.window.geometry('700x520')
        self.window.minsize(640, 470)
        self.window.configure(bg=BG)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.status = tk.StringVar(
            master=self.window, value='Cloud voice is OFF · no charges started.'
        )

        tk.Label(self.window, text='LIVEKIT · REALTIME VOICE', font=('Segoe UI', 18, 'bold'),
                 bg=BG, fg=CYAN).pack(anchor='w', padx=22, pady=(20, 8))
        description = (
            'Tumhare training-2057 LiveKit agent ka Jarvis version. This uses GPT-Live-1 '
            'and Marin voice for natural, interruptible conversations. It runs in a '
            'separate Windows voice console, NOT inside the main Mic/chat window.\n\n'
            'IMPORTANT: LiveKit Cloud inference is usage-billed. This is not an '
            'unlimited free voice service. No subscription or payment is initiated '
            'by Jarvis; the model uses your own configured LiveKit Cloud account. '
            'Regular Jarvis free voice and desktop review safeguards stay unchanged.\n\n'
            'This test has no access to desktop control, files or passwords.'
        )
        tk.Label(self.window, text=description, bg=PANEL, fg=TEXT,
                 font=('Segoe UI', 10), justify='left', wraplength=620,
                 padx=17, pady=15).pack(fill='x', padx=20, pady=6)

        self.noise_enhancement = tk.BooleanVar(master=self.window, value=False)
        tk.Checkbutton(
            self.window,
            text='AI-Coustics noise enhancement (optional, can cost extra)',
            variable=self.noise_enhancement, bg=BG, fg=MUTED, selectcolor=PANEL,
            activebackground=BG, activeforeground=TEXT,
        ).pack(anchor='w', padx=26, pady=(3, 0))

        self.setup_button = self._button('1  Install separate LiveKit voice tools',
                                         self.install)
        self.setup_button.pack(fill='x', padx=25, pady=6)
        self.credentials_button = self._button('2  Open private LiveKit credentials file',
                                               self.edit_credentials)
        self.credentials_button.pack(fill='x', padx=25, pady=6)
        self.start_button = self._button('3  Start metered LiveKit conversation',
                                         self.start, primary=True)
        self.start_button.pack(fill='x', padx=25, pady=6)
        self.stop_button = self._button('STOP LiveKit voice session',
                                        self.stop)
        self.stop_button.pack(fill='x', padx=25, pady=6)

        tk.Label(self.window, textvariable=self.status, bg=BG, fg=CYAN,
                 wraplength=630, font=('Segoe UI', 10), justify='left').pack(
                     anchor='w', padx=25, pady=(10, 0))
        self.refresh()

    def _button(self, text, command, primary=False):
        return tk.Button(
            self.window, text=text, command=command,
            bg=CYAN if primary else PANEL, fg=BG if primary else TEXT,
            activebackground='#a0fff4' if primary else '#204052',
            activeforeground=BG if primary else TEXT, font=('Segoe UI', 10),
            relief='flat', bd=0, padx=14, pady=9, cursor='hand2')

    def refresh(self):
        if self.closed:
            return
        if not self.busy:
            self.status.set(
                'Voice active in separate console · STOP to end billed session.'
                if self.console.is_running()
                else ('Credentials present · ready for user-approved cloud session.'
                      if configured() else
                      'Cloud voice OFF · set credentials in your private file first.')
            )

    def edit_credentials(self):
        try:
            path = create_credentials_template()
            if os.name != 'nt':
                raise LiveKitSetupError('Open this file with your text editor on Windows.')
            subprocess.Popen(['notepad.exe', str(path)])
            self.status.set(
                'Credentials file open · save URL/API key/secret, then return. '
                'Never paste credentials into chat or GitHub.'
            )
        except (OSError, LiveKitSetupError) as exc:
            messagebox.showerror('LiveKit credentials', str(exc), parent=self.window)

    def install(self):
        if self.busy:
            return
        if not messagebox.askyesno(
            'Install optional voice components?',
            'This installs LiveKit packages in a SEPARATE Python environment and '
            'downloads speech-processing models. Requires internet and disk space. '
            'It does NOT start paid cloud voice. Continue?',
            parent=self.window
        ):
            return
        self.busy = True
        self.setup_button.configure(state='disabled')
        self.status.set('Installing optional voice packages; regular Jarvis remains usable.')
        def job():
            try:
                result, error = install_optional(), None
            except Exception as exc:
                result, error = None, str(exc) if isinstance(exc, LiveKitSetupError) else (
                    'Optional voice installation failed; check Python/internet.')
            def finished():
                if self.closed:
                    return
                self.busy = False
                self.setup_button.configure(state='normal')
                if error:
                    self.status.set(error)
                else:
                    self.status.set(result)
            try:
                self.window.after(0, finished)
            except tk.TclError:
                pass
        threading.Thread(target=job, daemon=True).start()

    def start(self):
        if self.busy:
            return
        if not messagebox.askyesno(
            'Start billable LiveKit session?',
            'GPT-Live-1 usage and delegated backend operations can incur '
            'charges against YOUR LiveKit Cloud account. Use it only if you '
            'understand and accept your provider plan, limits and charges. '
            'Proceed with one voice session?',
            parent=self.window
        ):
            return
        try:
            self.console.start(consent=True)
            self.status.set('Voice console launched. Close/STOP to end session.')
        except (OSError, LiveKitSetupError) as exc:
            messagebox.showerror('LiveKit voice', str(exc), parent=self.window)

    def stop(self):
        self.console.stop()
        self.refresh()

    def close(self):
        if self.closed:
            return
        self.console.stop()
        self.closed = True
        self.window.destroy()
