"""Explicit cloud speech configuration; keys never enter chat or activity logs."""
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from cloud_voice import VoiceError


class VoiceSettingsWindow:
    def __init__(self, host):
        from dashboard import BG, PANEL, TEXT, MUTED, CYAN, btn, label
        self.host = host
        self.closed = False
        self.window = tk.Toplevel(host.root)
        self.window.title('Jarvis · Voice / ElevenLabs')
        self.window.configure(bg=BG)
        self.window.geometry('690x640')
        self.window.minsize(620, 620)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        settings = host.voice_settings
        self.provider = tk.StringVar(master=self.window, value=settings.provider)
        self.voice_id = tk.StringVar(master=self.window, value=settings.voice_id)
        self.language = tk.StringVar(master=self.window, value=settings.language)
        self.api_key = tk.StringVar(master=self.window, value='')
        self.remember = tk.BooleanVar(master=self.window, value=settings.key_path.is_file())
        self.consent = tk.BooleanVar(master=self.window, value=settings.provider == 'ElevenLabs')
        self.status = tk.StringVar(master=self.window, value='Key loaded on this PC' if settings.key else 'No API key configured')
        label(self.window, 'VOICE / ELEVENLABS', 18, CYAN, True, bg=BG).pack(anchor='w', padx=22, pady=(18, 5))
        label(self.window, 'Choose how Jarvis speaks its replies', 10, MUTED, bg=BG).pack(anchor='w', padx=22)
        form = tk.Frame(self.window, bg=PANEL)
        form.pack(fill='x', padx=20, pady=14)
        for title, variable, choices in (
            ('Provider', self.provider, ['Windows', 'ElevenLabs']),
            ('Language (auto / Urdu / English)', self.language, ['auto', 'ur', 'en']),
        ):
            label(form, title, 10, TEXT).pack(anchor='w', padx=13, pady=(9, 3))
            ttk.Combobox(form, textvariable=variable, values=choices, state='readonly').pack(fill='x', padx=13)
        label(form, 'Voice ID (copy from your ElevenLabs account)', 10, TEXT).pack(anchor='w', padx=13, pady=(10, 3))
        tk.Entry(form, textvariable=self.voice_id).pack(fill='x', padx=13)
        label(form, 'API key (blank keeps current key)', 10, TEXT).pack(anchor='w', padx=13, pady=(10, 3))
        self.key_entry = tk.Entry(form, textvariable=self.api_key, show='•')
        self.key_entry.pack(fill='x', padx=13)
        tk.Checkbutton(form, text='Remember key on this Windows account (encrypted)', variable=self.remember,
                       bg=PANEL, fg=TEXT, selectcolor=BG, activebackground=PANEL,
                       activeforeground=TEXT).pack(anchor='w', padx=9, pady=(8, 0))
        label(form, '', 9, MUTED, textvariable=self.status).pack(anchor='w', padx=13, pady=(2, 10))
        tk.Checkbutton(self.window, text='Send spoken reply text to ElevenLabs; account credits apply',
                       variable=self.consent, bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=TEXT).pack(anchor='w', padx=19)
        label(self.window,
              'Eleven v3 · Urdu & English · Internet and your own API key required.\n'
              'Only spoken reply text is sent; mic transcription stays local. Up to 1,800 characters per reply.\n'
              'STOP cancels local playback. A request already sent may still consume credits.\n'
              'For clearer Urdu pronunciation, use Urdu script and a matching voice/accent.',
              9, MUTED, bg=BG, wraplength=635, justify='left').pack(anchor='w', padx=22, pady=(10, 8))
        actions = tk.Frame(self.window, bg=BG)
        actions.pack(fill='x', padx=18, pady=5)
        btn(actions, 'Save settings', self.save, True, True).pack(side='left', padx=3)
        btn(actions, 'Test voice', self.test, compact=True).pack(side='left', padx=3)
        btn(actions, 'STOP', self.stop_speech, compact=True).pack(side='left', padx=3)
        btn(actions, 'Forget key', self.forget, compact=True).pack(side='left', padx=3)
        links = tk.Frame(self.window, bg=BG)
        links.pack(fill='x', padx=18, pady=5)
        btn(links, 'API keys ↗', lambda: webbrowser.open('https://elevenlabs.io/app/settings/api-keys'), compact=True).pack(side='left', padx=3)
        btn(links, 'Voice library ↗', lambda: webbrowser.open('https://elevenlabs.io/app/voice-library'), compact=True).pack(side='left', padx=3)
        tk.Checkbutton(links, text='Speak replies', variable=host.speak_enabled,
                       bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                       activeforeground=TEXT).pack(side='left', padx=8)

    def stop_speech(self):
        self.host.speaker.stop()
        sandbox = getattr(self.host, 'sandbox_window', None)
        if sandbox is not None and not sandbox.closed:
            sandbox.speaker.stop()

    def save(self, quiet=False):
        if self.provider.get() == 'ElevenLabs' and not self.consent.get():
            messagebox.showwarning('Enable ElevenLabs', 'ElevenLabs ko spoken reply text bhejne ka checkbox tick karein.', parent=self.window)
            return False
        try:
            self.stop_speech()
            key = self.api_key.get().strip() or self.host.voice_settings.key
            self.host.voice_settings.save(self.provider.get(), self.voice_id.get().strip(),
                                          self.language.get(), key, self.remember.get())
        except VoiceError as exc:
            messagebox.showerror('Voice settings', str(exc), parent=self.window)
            return False
        except OSError:
            messagebox.showerror('Voice settings', 'Settings save nahi hui. User folder access check karein.', parent=self.window)
            return False
        self.api_key.set('')
        self.status.set(self.provider.get() + ' selected · press Test voice to verify')
        if not quiet:
            self.host.say('VOICE', self.provider.get() + ' selected. Speak replies tick karein; Test voice se awaaz check karein.')
        return True

    def test(self):
        if self.host.stop.is_set():
            self.status.set('Jarvis stopped hai. Main window mein Resume dabayein.')
            return
        if not self.save(quiet=True):
            return
        text = 'السلام علیکم حسیب! میں جاروس ہوں، آپ کا اسسٹنٹ۔' if self.language.get() == 'ur' else 'Hello Haseeb. Jarvis voice is ready. How can I help you today?'
        self.host.speaker.speak(text)
        self.status.set('Voice test requested · errors appear in chat · STOP cancels playback')

    def forget(self):
        try:
            self.stop_speech()
            self.host.voice_settings.forget()
        except OSError:
            messagebox.showerror('Forget key', 'Stored key remove nahi hui. User folder access check karein.', parent=self.window)
            return
        self.api_key.set('')
        self.remember.set(False)
        self.status.set('API key removed from this app and stored credentials')

    def close(self):
        self.closed = True
        self.api_key.set('')
        self.window.destroy()
