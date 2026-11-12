"""Voice configuration with explicit online-text consent and masked credentials."""
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from cloud_voice import VoiceError
from free_voice import PROVIDER, VOICES, RATES


class VoiceSettingsWindow:
    def __init__(self, host):
        from dashboard import BG, PANEL, TEXT, MUTED, CYAN, btn, label
        self.host = host
        self.closed = False
        self.window = tk.Toplevel(host.root)
        self.window.title('Jarvis · Voices / Free neural')
        self.window.configure(bg=BG)
        self.window.geometry('690x640')
        self.window.minsize(620, 620)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        settings = host.voice_settings
        self.provider = tk.StringVar(master=self.window, value=settings.provider)
        self.voice_id = tk.StringVar(master=self.window, value=settings.voice_id)
        self.language = tk.StringVar(master=self.window, value=settings.language)
        self.free_voice = tk.StringVar(master=self.window, value=next(name for name, value in VOICES.items() if value == settings.free_voice))
        self.free_rate = tk.StringVar(master=self.window, value=settings.free_rate)
        self.api_key = tk.StringVar(master=self.window, value='')
        self.remember = tk.BooleanVar(master=self.window, value=settings.key_path.is_file())
        self.consent = tk.BooleanVar(master=self.window, value=settings.provider != 'Windows')
        self.status = tk.StringVar(master=self.window, value='Choose a provider, then Test voice')
        self.disclosure = tk.StringVar(master=self.window)
        self.explanation = tk.StringVar(master=self.window)
        label(self.window, 'JARVIS VOICES', 18, CYAN, True, bg=BG).pack(anchor='w', padx=22, pady=(18, 5))
        label(self.window, 'Free neural voices · Windows offline · ElevenLabs optional', 10, MUTED, bg=BG).pack(anchor='w', padx=22)
        form = tk.Frame(self.window, bg=PANEL)
        form.pack(fill='x', padx=20, pady=14)
        label(form, 'Provider', 10, TEXT).pack(anchor='w', padx=13, pady=(9, 3))
        self.provider_box = ttk.Combobox(form, textvariable=self.provider,
                                       values=[PROVIDER, 'Windows', 'ElevenLabs'], state='readonly')
        self.provider_box.pack(fill='x', padx=13, pady=(0, 10))
        self.provider_box.bind('<<ComboboxSelected>>', self.on_provider_change)

        self.free_form = tk.Frame(form, bg=PANEL)
        label(self.free_form, 'Free voice (no API key)', 10, TEXT).pack(anchor='w', padx=13, pady=(4, 3))
        ttk.Combobox(self.free_form, textvariable=self.free_voice, values=list(VOICES), state='readonly').pack(fill='x', padx=13)
        label(self.free_form, 'Speaking speed (−5%: slightly calmer)', 10, TEXT).pack(anchor='w', padx=13, pady=(10, 3))
        ttk.Combobox(self.free_form, textvariable=self.free_rate, values=RATES, state='readonly').pack(fill='x', padx=13, pady=(0, 12))

        self.paid_form = tk.Frame(form, bg=PANEL)
        for title, variable in [('Language (auto / Urdu / English)', self.language)]:
            label(self.paid_form, title, 10, TEXT).pack(anchor='w', padx=13, pady=(4, 3))
            ttk.Combobox(self.paid_form, textvariable=variable, values=['auto', 'ur', 'en'], state='readonly').pack(fill='x', padx=13)
        label(self.paid_form, 'ElevenLabs voice ID', 10, TEXT).pack(anchor='w', padx=13, pady=(8, 3))
        tk.Entry(self.paid_form, textvariable=self.voice_id).pack(fill='x', padx=13)
        label(self.paid_form, 'API key (blank keeps current key)', 10, TEXT).pack(anchor='w', padx=13, pady=(8, 3))
        self.key_entry = tk.Entry(self.paid_form, textvariable=self.api_key, show='•')
        self.key_entry.pack(fill='x', padx=13)
        tk.Checkbutton(self.paid_form, text='Remember key on this Windows account (encrypted)', variable=self.remember,
                       bg=PANEL, fg=TEXT, selectcolor=BG, activebackground=PANEL,
                       activeforeground=TEXT).pack(anchor='w', padx=9, pady=(5, 0))
        paid_links = tk.Frame(self.paid_form, bg=PANEL)
        paid_links.pack(fill='x', padx=10, pady=(4, 8))
        btn(paid_links, 'API keys ↗', lambda: webbrowser.open('https://elevenlabs.io/app/settings/api-keys'), compact=True).pack(side='left', padx=2)
        btn(paid_links, 'Voice library ↗', lambda: webbrowser.open('https://elevenlabs.io/app/voice-library'), compact=True).pack(side='left', padx=2)
        btn(paid_links, 'Forget key', self.forget, compact=True).pack(side='left', padx=2)
        self.consent_box = tk.Checkbutton(self.window, textvariable=self.disclosure, variable=self.consent,
                                          bg=BG, fg=TEXT, selectcolor=PANEL,
                                          activebackground=BG, activeforeground=TEXT)
        self.consent_box.pack(anchor='w', padx=19)
        label(self.window, '', 9, MUTED, bg=BG, textvariable=self.explanation,
              wraplength=635, justify='left').pack(anchor='w', padx=22, pady=(10, 8))
        actions = tk.Frame(self.window, bg=BG)
        actions.pack(fill='x', padx=18, pady=5)
        self.save_button = btn(actions, 'Save settings', self.save, True, True)
        self.save_button.pack(side='left', padx=3)
        self.test_button = btn(actions, 'Test voice', self.test, compact=True)
        self.test_button.pack(side='left', padx=3)
        btn(actions, 'STOP', self.stop_speech, compact=True).pack(side='left', padx=3)
        tk.Checkbutton(actions, text='Speak replies', variable=host.speak_enabled,
                       bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                       activeforeground=TEXT).pack(side='left', padx=8)
        label(self.window, '', 9, CYAN, bg=BG, textvariable=self.status,
              wraplength=630, justify='left').pack(anchor='w', padx=22, pady=(10, 5))
        label(self.window, 'Free voice client: rany2/edge-tts · LGPLv3 · third-party service',
              8, MUTED, bg=BG).pack(anchor='w', padx=22, pady=5)
        self.update_provider_form()

    def on_provider_change(self, _event=None):
        self.consent.set(False)
        self.update_provider_form()

    def update_provider_form(self):
        selected = self.provider.get()
        self.free_form.pack_forget()
        self.paid_form.pack_forget()
        if selected == PROVIDER:
            self.free_form.pack(fill='x')
            self.disclosure.set('Send spoken reply text to Microsoft for free online speech')
            self.explanation.set('No API key or paid subscription is required by this client. Internet required.\n'
                                 'Choose Asad/Uzma for Urdu or a matching English voice. Urdu script gives clearer Urdu.\n'
                                 'Only spoken reply text is sent; mic recognition stays local. STOP cancels playback.\n'
                                 'Service availability and voice quality can vary; no unlimited-service guarantee.')
        elif selected == 'ElevenLabs':
            self.paid_form.pack(fill='x')
            self.disclosure.set('Send spoken reply text to ElevenLabs; account credits apply')
            self.explanation.set('Eleven v3 · your API key and available credits required. Internet required.\n'
                                 'Only spoken reply text is sent; mic recognition stays local. Up to 1,800 characters.\n'
                                 'STOP cancels local playback; an already-sent request may still consume credits.')
        else:
            self.disclosure.set('Online speech disabled for Windows provider')
            self.explanation.set('Windows speech runs locally without an API key. Voice quality depends on installed voices.\n'
                                 'Choose Edge Neural (free online) for online Urdu/English neural voices.')
        self.consent_box.configure(state='disabled' if selected == 'Windows' else 'normal')

    def stop_speech(self):
        self.host.speaker.stop()
        sandbox = getattr(self.host, 'sandbox_window', None)
        if sandbox is not None and not sandbox.closed:
            sandbox.speaker.stop()

    def save(self, quiet=False):
        if self.provider.get() != 'Windows' and not self.consent.get():
            messagebox.showwarning('Enable online speech', 'Selected provider ko spoken reply text bhejne ka checkbox tick karein.', parent=self.window)
            return False
        try:
            self.stop_speech()
            key = self.api_key.get().strip() or self.host.voice_settings.key
            self.host.voice_settings.save(self.provider.get(), self.voice_id.get().strip(),
                                          self.language.get(), key, self.remember.get(),
                                          free_voice=VOICES[self.free_voice.get()], free_rate=self.free_rate.get())
        except (VoiceError, KeyError) as exc:
            messagebox.showerror('Voice settings', str(exc) if isinstance(exc, VoiceError) else 'List se free voice select karein.', parent=self.window)
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
        urdu = VOICES[self.free_voice.get()].startswith('ur-') if self.provider.get() == PROVIDER else self.language.get() == 'ur'
        text = 'السلام علیکم حسیب! میں جاروس ہوں، آپ کا اسسٹنٹ۔' if urdu else 'Hello Haseeb. Jarvis voice is ready. How can I help you today?'
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
        self.status.set('ElevenLabs key removed from this app and stored credentials')

    def close(self):
        self.closed = True
        self.api_key.set('')
        self.window.destroy()
