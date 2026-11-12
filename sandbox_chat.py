"""Chat-only account conversation; cloud output never executes desktop actions."""
from __future__ import annotations

from collections import deque
from datetime import datetime
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from chat_ui import ChatComposer, on_return, preset_prompt
from core import ChatAI, MODEL, CHAT_MODELS
from voice import Speaker, listen

BG = "#070e16"
SIDE = "#0c1926"
PANEL = "#101f2d"
LAYER = "#142838"
LINE = "#274256"
LIGHT = "#e7f6fb"
MUTED = "#8faab8"
CYAN = "#42dfd5"
GOLD = "#d7b785"
USER = "#174854"


class SandboxSession:
    """Volatile conversation, independently bounded from desktop command history."""

    def __init__(self, max_messages=8):
        self._messages = deque(maxlen=max_messages)

    @property
    def history(self):
        return list(self._messages)

    def conversation_for(self, text):
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > 4000:
            raise ValueError("Message 1 se 4000 characters ka hona chahiye.")
        return self.history + [{"role": "user", "content": text.strip()}]

    def commit(self, text, answer):
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Chatbot ka jawab khali hai.")
        self._messages.extend((
            {"role": "user", "content": text.strip()},
            {"role": "assistant", "content": answer.strip()},
        ))

    def clear(self):
        self._messages.clear()


def sandbox_reply(ai, session, message):
    """Read-only chat endpoint; intentionally never parse computer commands."""
    return ai.ask(session.conversation_for(message), plan=False)


class SandboxWindow:
    """Tkinter chat UI; all widgets update on the main Tk thread via event queue."""

    def __init__(self, parent, host, session=None):
        self.parent = parent
        self.host = host
        self.session = session if session is not None else SandboxSession()
        self.selected_model = tk.StringVar(master=parent, value=host.store.chat_model)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.ai = ChatAI(bridge=host.chat_bridge, cancel=self.cancel)
        self.generation = 0
        self.busy = False
        self.listening = False
        self.closed = False
        self.speaker = Speaker(lambda notice: self.events.put(("speech_notice", notice)), settings=host.voice_settings,
                               prepare_speech=self.ai.prepare_speech)
        self.speak_replies = tk.BooleanVar(master=parent, value=False)
        self.status = tk.StringVar(master=parent, value="ACCOUNT AI · SIGN IN")
        self.activity = tk.StringVar(master=parent, value="Chat only  •  No desktop actions")
        self.window = tk.Toplevel(parent)
        self.window.title("HASEEB AI  |  CONVERSATION SANDBOX")
        self.window.geometry("1050x720")
        self.window.minsize(790, 570)
        self.window.configure(bg=BG)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build()
        self._welcome()
        self._restore_messages()
        self.window.after(120, self._poll)
        self.window.after(300, self.refresh_status)
        self.entry.focus_set()

    def _button(self, parent, text, command, primary=False, width=None):
        b = tk.Button(
            parent, text=text, command=command,
            bg=CYAN if primary else LAYER, fg=BG if primary else LIGHT,
            activebackground="#a0fff4" if primary else "#1d3b4e",
            activeforeground=BG if primary else LIGHT,
            highlightthickness=1, highlightbackground=LINE if not primary else CYAN,
            relief="flat", bd=0, padx=15, pady=10, cursor="hand2",
            font=("Segoe UI", 10, "bold" if primary else "normal"),
            width=width,
        )
        return b

    def _build(self):
        header = tk.Frame(self.window, bg=SIDE, height=78)
        header.pack(fill="x")
        header.pack_propagate(False)
        identity = tk.Frame(header, bg=SIDE)
        identity.pack(side="left", padx=22, pady=13)
        tk.Label(identity, text="◉   H A S E E B    A I", fg=CYAN, bg=SIDE,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(identity, text="JARVIS / CONVERSATION SANDBOX",
                 fg=MUTED, bg=SIDE, font=("Segoe UI", 9)).pack(anchor="w")
        self._button(header, "Close", self.close).pack(side="right", padx=(4, 17), pady=15)
        self._button(header, "Connect AI", self.host.setup_ai).pack(side="right", padx=4, pady=15)
        self._button(header, "New chat", self.new_chat).pack(side="right", padx=4, pady=15)

        content = tk.Frame(self.window, bg=BG)
        content.pack(fill="both", expand=True, padx=15, pady=14)
        side = tk.Frame(content, bg=SIDE, width=230,
                        highlightthickness=1, highlightbackground=LINE)
        side.pack(side="left", fill="y", padx=(0, 12))
        side.pack_propagate(False)
        tk.Label(side, text="AI   /   SANDBOX", fg=GOLD, bg=SIDE,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=17, pady=(21, 9))
        orbit = tk.Canvas(side, bg=SIDE, highlightthickness=0, width=210, height=160)
        orbit.pack(pady=(0, 8))
        cx, cy = 105, 78
        for radius, tone in ((68, "#1b4251"), (49, "#25616b"), (28, "#37958f")):
            orbit.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline=tone, width=1)
        orbit.create_oval(cx-18, cy-18, cx+18, cy+18,
                          fill="#0d3e47", outline=CYAN, width=2)
        orbit.create_text(cx, cy, text="AI", fill=LIGHT, font=("Segoe UI", 13, "bold"))
        tk.Label(side, textvariable=self.status, fg=CYAN, bg=SIDE,
                 font=("Segoe UI", 9, "bold"), wraplength=192,
                 justify="left").pack(anchor="w", padx=17, pady=(2, 9))
        tk.Label(side, text="CHAT MODEL", fg=GOLD, bg=SIDE, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=17, pady=(10, 4)
        )
        self.model_picker = ttk.Combobox(side, textvariable=self.selected_model, state="readonly",
                                         values=CHAT_MODELS, width=17)
        self.model_picker.pack(fill="x", padx=15, pady=4)
        self.model_picker.bind("<<ComboboxSelected>>", self.on_model_change)
        tk.Label(side, text="Online account model · no local download", fg=MUTED, bg=SIDE,
                 font=("Segoe UI", 8), wraplength=192, justify="left").pack(
            anchor="w", padx=17, pady=(1, 7))
        self._button(side, "Refresh connection", self.refresh_status).pack(fill="x", padx=15, pady=4)
        tk.Frame(side, bg=LINE, height=1).pack(fill="x", padx=15, pady=17)
        tk.Label(side, text="THIS IS A CHAT-ONLY SPACE", fg=GOLD, bg=SIDE,
                 font=("Segoe UI", 9, "bold"), wraplength=200,
                 justify="left").pack(anchor="w", padx=17)
        tk.Label(side, text="Chat messages and recent context go to Puter/model provider. No auto-run, file edits, shell commands or screen control.",
                 fg=MUTED, bg=SIDE, font=("Segoe UI", 9), justify="left",
                 wraplength=190).pack(anchor="w", padx=17, pady=(8, 14))
        self._button(side, "Stop response", self.stop).pack(fill="x", padx=15, pady=(0, 6))

        main = tk.Frame(content, bg=BG, highlightthickness=1, highlightbackground=LINE)
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=PANEL, height=57)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="Conversation with Jarvis", fg=LIGHT, bg=PANEL,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=19, pady=14)
        tk.Label(top, textvariable=self.selected_model, fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 9)).pack(side="right", padx=17)

        transcript = tk.Frame(main, bg=BG)
        transcript.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(transcript, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(transcript, command=self.canvas.yview, orient="vertical")
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.messages = tk.Frame(self.canvas, bg=BG)
        self._canvas_item = self.canvas.create_window(0, 0, window=self.messages, anchor="nw")
        self.messages.bind("<Configure>", lambda _event: self._sync_scroll())
        self.canvas.bind("<Configure>", self._resize_messages)

        bottom = tk.Frame(main, bg=PANEL)
        bottom.pack(side="bottom", fill="x", padx=1, pady=1)
        tk.Label(bottom, textvariable=self.activity, fg=MUTED, bg=PANEL,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(10, 3))
        chips = tk.Frame(bottom, bg=PANEL)
        chips.pack(fill="x", padx=12)
        for name, prompt in (
            ("Salam", "Salam Jarvis, tum kaise ho?"),
            ("Website idea", "Mere liye ek professional business website ka idea do."),
            ("Video script", "Haseeb Crafts ke liye 15 second ki cinematic video script do."),
        ):
            self._button(chips, name, lambda p=prompt: preset_prompt(self.entry, p)).pack(
                side="left", padx=3, pady=3
            )
        compose = tk.Frame(bottom, bg=PANEL)
        compose.pack(fill="x", padx=12, pady=(7, 4))
        self.entry = ChatComposer(
            compose, bg=SIDE, fg=LIGHT, insertbackground=CYAN,
            highlightthickness=1, highlightbackground=LINE,
            highlightcolor=CYAN, relief="flat", bd=0, height=3,
            padx=12, pady=10, font=("Segoe UI", 11), wrap="word"
        )
        self.entry.pack(side="left", fill="both", expand=True)
        self.entry.bind("<Return>", lambda event: on_return(event, self.send))
        self.send_button = self._button(compose, "SEND", self.send, primary=True, width=8)
        self.send_button.pack(side="right", padx=(9, 0))
        speak = tk.Frame(bottom, bg=PANEL)
        speak.pack(fill="x", padx=14, pady=(0, 9))
        self.mic_button = self._button(speak, "Mic · 6 seconds", self.start_mic)
        self.mic_button.pack(side="left", padx=(0, 7))
        tk.Checkbutton(speak, text="Speak replies", variable=self.speak_replies,
                       fg=LIGHT, bg=PANEL, selectcolor=SIDE,
                       activebackground=PANEL, activeforeground=LIGHT).pack(side="left")
        tk.Label(speak, text="Enter: send    Shift+Enter: new line",
                 fg=MUTED, bg=PANEL, font=("Segoe UI", 9)).pack(side="right")

    def _resize_messages(self, event):
        self.canvas.itemconfigure(self._canvas_item, width=event.width)

    def _sync_scroll(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(1.0)

    def _bubble(self, who, body, historic=False):
        mine = who == "YOU"
        row = tk.Frame(self.messages, bg=BG)
        row.pack(fill="x", padx=18, pady=(8, 5))
        holder = tk.Frame(row, bg=USER if mine else PANEL, highlightthickness=1,
                          highlightbackground="#2c7080" if mine else LINE)
        holder.pack(side="right" if mine else "left", padx=4)
        display = "YOU" if mine else "JARVIS · ACCOUNT AI"
        stamp = datetime.now().strftime("%H:%M")
        tk.Label(holder, text=display + "   •   " + stamp, fg=CYAN if mine else GOLD,
                 bg=USER if mine else PANEL,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        tk.Label(holder, text=body, fg=LIGHT, bg=USER if mine else PANEL,
                 font=("Segoe UI", 11), justify="left", anchor="w",
                 wraplength=480).pack(anchor="w", padx=14, pady=(0, 12))
        if not historic:
            self._sync_scroll()

    def _welcome(self):
        self._bubble("JARVIS", "Assalamualaikum! Main Jarvis hoon, aapka account-connected AI assistant. Roman Urdu mein baat kar sakte hain. Yeh chat-only sandbox hai — yahan se computer commands execute nahi hotin.", True)

    def _restore_messages(self):
        for item in self.session.history:
            self._bubble("YOU" if item["role"] == "user" else "JARVIS", item["content"], True)

    def _set_busy(self, value, message="Ready to chat"):
        self.busy = value
        if not self.closed:
            self.send_button.configure(state="disabled" if value else "normal")
            self.mic_button.configure(state="disabled" if value else "normal")
            self.activity.set(message)

    def on_model_change(self, _event=None):
        self.selected_model.set(MODEL)

    def refresh_status(self):
        if self.closed:
            return
        state = self.host.chat_bridge.status()
        self.status.set('● ACCOUNT CONNECTED' if state == 'ready' else '● CONNECT AI / SIGN IN')
        self.window.after(3000, self.refresh_status)

    def send(self):
        if self.closed or self.busy:
            return
        text = self.entry.get().strip()
        if not text:
            return
        try:
            messages = self.session.conversation_for(text)
        except ValueError as exc:
            messagebox.showerror("Message invalid", str(exc), parent=self.window)
            return
        self.entry.delete(0, "end")
        self._bubble("YOU", text)
        self.ai.model = self.selected_model.get()
        self._set_busy(True, "Jarvis is thinking online (" + self.ai.model + ")...")
        self.cancel.clear()
        generation = self.generation
        def work():
            try:
                response = self.ai.ask(messages, plan=False)
                self.events.put(("reply", (generation, text, response, None)))
            except Exception as exc:
                self.events.put(("reply", (generation, text, None, str(exc))))
        threading.Thread(target=work, daemon=True).start()

    def start_mic(self):
        if self.closed or self.busy:
            return
        self.cancel.clear()
        generation = self.generation
        self.listening = True
        self._set_busy(True, "Listening for 6 seconds (local microphone)...")
        def work():
            try:
                transcript = listen(self.cancel, "auto",
                                    notify=lambda msg: self.events.put(("voice_status", (generation, msg))))
                self.events.put(("voice", (generation, transcript, None)))
            except Exception as exc:
                self.events.put(("voice", (generation, None, str(exc))))
        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        self.cancel.set()
        self.generation += 1
        self.speaker.stop()
        # The cloud request cannot always be interrupted. We discard its
        # result if stopped, and wait for it to finish before enabling Send.
        self.activity.set("Stopped · pending answer will be discarded")

    def new_chat(self):
        if self.busy:
            messagebox.showinfo("Finish current reply",
                                "Pehle current request finish hone dein ya Stop dabayein.",
                                parent=self.window)
            return
        self.speaker.stop()
        self.session.clear()
        for widget in self.messages.winfo_children():
            widget.destroy()
        self._welcome()
        self.entry.delete(0, "end")
        self.activity.set("Fresh local conversation · No saved transcript")

    def _poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "voice_status":
                    generation, notice = data
                    if generation == self.generation:
                        self.activity.set(notice)
                elif kind == "speech_notice":
                    self.activity.set(data)
                elif kind == "voice":
                    generation, transcript, error = data
                    self.listening = False
                    self._set_busy(False, "Voice transcript ready to review")
                    if generation != self.generation:
                        continue
                    if error:
                        self.activity.set(error)
                    else:
                        preset_prompt(self.entry, transcript)
                        if messagebox.askyesno(
                            "Review recorded voice",
                            "Recognized text:\n\n" + transcript + "\n\nSend to account chat?",
                            parent=self.window
                        ):
                            self.send()
                elif kind == "reply":
                    generation, question, answer, error = data
                    self._set_busy(False)
                    if generation != self.generation:
                        continue
                    if error:
                        self._bubble("JARVIS", "AI response error: " + error)
                        self.activity.set("Check account connection or press Connect AI")
                    else:
                        self.session.commit(question, answer)
                        self._bubble("JARVIS", answer)
                        self.activity.set("Reply received · conversation stays local")
                        if self.speak_replies.get():
                            self.speaker.speak(answer)
        except queue.Empty:
            pass
        if not self.closed and self.window.winfo_exists():
            self.window.after(120, self._poll)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel.set()
        self.generation += 1
        self.speaker.stop()
        self.window.destroy()

