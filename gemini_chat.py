"""Optional Gemini text chat for Jarvis, isolated from desktop commands.

Only explicit user Chat mode sends a request. No server process, autonomous
tool calls, retries, paid-tier auto-upgrade, or background requests.
API keys are encrypted for the current Windows user with DPAPI.
"""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MODELS = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
DAILY_REQUEST_LIMIT = 30
MAX_USER_CHARS = 4000
MAX_HISTORY_TURNS = 8
MAX_RESPONSE_BYTES = 65536
SYSTEM_INSTRUCTIONS = (
    "You are Jarvis, a helpful personal AI assistant by Haseeb Crafts. "
    "Reply in clear, natural Roman Urdu when the user speaks Roman Urdu, "
    "and English when the user writes English. Keep normal answers concise. "
    "Be factual, and admit uncertainty. Never claim that you opened Windows "
    "apps, changed PC settings, browsed the web, or completed desktop actions. "
    "You are TEXT CHAT ONLY. Desktop tools are separate and require native user "
    "approval. Never ask for passwords or API keys."
)


class GeminiError(RuntimeError):
    """Safe to display: never contains credential, prompts or provider payloads."""


def _protect(value: bytes) -> bytes:
    if os.name != "nt":
        raise GeminiError("Gemini key Windows 11 par DPAPI mein save hoti hai.")
    try:
        import win32crypt
        return win32crypt.CryptProtectData(value, "Haseeb Jarvis Gemini", None, None, None, 0)
    except Exception:
        raise GeminiError("Windows secure credential storage available nahi.") from None


def _unprotect(value: bytes) -> bytes:
    if os.name != "nt":
        raise GeminiError("Gemini key Windows 11 par hi unlock hoti hai.")
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(value, None, None, None, 0)[1]
    except Exception:
        raise GeminiError("Windows account se Gemini key unlock nahi ho rahi. Key dobara save karein.") from None


def data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        root = str(Path.home() / "AppData" / "Local")
    return Path(root) / "HaseebCrafts" / "Jarvis" / "Gemini"


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temp file in same directory; never use a generic world-readable temp path.
    fd, name = tempfile.mkstemp(prefix=".gemini-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class GeminiStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else data_dir()
        self.secret = self.directory / "key.dpapi"
        self.preference = self.directory / "settings.json"
        self.usage = self.directory / "usage.json"
        self._lock = threading.Lock()

    def configured(self) -> bool:
        return self.secret.is_file()

    def save_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise GeminiError("Valid Gemini API key paste karein.")
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", key):
            raise GeminiError("Invalid key format. AI Studio se nayi API key copy karein.")
        _atomic_write(self.secret, _protect(key.encode("utf-8")))

    def get_key(self) -> str:
        if not self.configured():
            raise GeminiError("Gemini API key missing. Pehle Gemini setup kholo.")
        try:
            key = _unprotect(self.secret.read_bytes()).decode("utf-8")
        except (OSError, UnicodeDecodeError):
            raise GeminiError("Saved Gemini key read nahi ho rahi. Dobara save karein.") from None
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", key):
            raise GeminiError("Saved Gemini key invalid hai. Dobara save karein.")
        return key

    def delete_key(self) -> None:
        try:
            self.secret.unlink(missing_ok=True)
        except OSError:
            raise GeminiError("Gemini key delete nahi hui. Windows file permission check karein.") from None

    def model(self) -> str:
        try:
            value = json.loads(self.preference.read_text(encoding="utf-8"))
            model = value.get("model")
            return model if model in MODELS else DEFAULT_MODEL
        except (OSError, ValueError, TypeError, AttributeError):
            return DEFAULT_MODEL

    def set_model(self, model: str) -> None:
        if model not in MODELS:
            raise GeminiError("Sirf reviewed Gemini free-tier text models allowed hain.")
        _atomic_write(self.preference, json.dumps({"model": model}).encode("utf-8"))

    def consume_request(self) -> int:
        """Local precaution, not a cloud billing limit; one count per attempted call."""
        with self._lock:
            today = date.today().isoformat()
            try:
                value = json.loads(self.usage.read_text(encoding="utf-8"))
                used = int(value.get("used", 0)) if value.get("date") == today else 0
            except (OSError, ValueError, TypeError, AttributeError):
                used = 0
            used = max(0, used)
            if used >= DAILY_REQUEST_LIMIT:
                raise GeminiError("Jarvis ki 30 daily Gemini requests limit complete. Kal try karein.")
            _atomic_write(self.usage, json.dumps({"date": today, "used": used + 1}).encode("utf-8"))
            return used + 1


def _payload(text: str, history) -> bytes:
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_USER_CHARS:
        raise GeminiError("Message 1 se 4,000 characters tak rakhein.")
    turns = []
    for item in list(history)[-MAX_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = {"user": "user", "assistant": "model"}.get(item.get("role"))
        body = item.get("content")
        if role and isinstance(body, str) and 0 < len(body) <= MAX_USER_CHARS:
            turns.append({"role": role, "parts": [{"text": body}]})
    # Only include alternating valid history, and start with a user turn.
    clean = []
    for item in turns:
        if not clean and item["role"] != "user":
            continue
        if clean and clean[-1]["role"] == item["role"]:
            clean[-1] = item
        else:
            clean.append(item)
    if clean and clean[-1]["role"] == "user":
        clean.pop()
    clean.append({"role": "user", "parts": [{"text": text.strip()}]})
    return json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
        "contents": clean,
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.6},
    }, ensure_ascii=False).encode("utf-8")


class GeminiClient:
    def __init__(self, store: GeminiStore):
        self.store = store

    def ask(self, text: str, history=(), stop=None) -> str:
        body = _payload(text, history)
        if stop is not None and stop.is_set():
            raise GeminiError("Stopped. Gemini request nahi bheji.")
        key = self.store.get_key()
        model = self.store.model()  # allowlist, never a user-supplied URL
        self.store.consume_request()
        request = Request(
            API_URL + model + ":generateContent",
            data=body,
            headers={"Content-Type": "application/json",
                     "User-Agent": "HaseebCrafts-Jarvis/1.0"},
            method="POST",
        )
        # Do not forward the credential if a remote server sends a redirect.
        request.add_unredirected_header("x-goog-api-key", key)
        try:
            with urlopen(request, timeout=22, context=ssl.create_default_context()) as reply:
                raw = reply.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise GeminiError("Gemini key/permission reject hui. AI Studio project aur API key check karein.") from None
            if exc.code == 404:
                raise GeminiError("Is project ko selected Gemini model access nahi. Settings mein doosra free model select karein.") from None
            if exc.code == 429:
                raise GeminiError("Gemini free tier rate limit poori ho gayi. Baad mein try karein.") from None
            if exc.code == 400:
                raise GeminiError("Gemini request reject hui. Key/model configuration check karein.") from None
            raise GeminiError("Gemini service ne HTTP " + str(exc.code) + " return kiya.") from None
        except (OSError, URLError, TimeoutError):
            raise GeminiError("Gemini connection timeout/network issue. Internet check karein.") from None
        if stop is not None and stop.is_set():
            raise GeminiError("Stopped. Cloud result discard kar diya.")
        if len(raw) > MAX_RESPONSE_BYTES:
            raise GeminiError("Gemini reply size limit se bari hai.")
        try:
            response = json.loads(raw)
            parts = response["candidates"][0]["content"]["parts"]
            answer = "".join(part["text"] for part in parts if isinstance(part.get("text"), str)).strip()
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise GeminiError("Gemini se valid text reply nahi aayi; safety filters ya service issue ho sakta hai.") from None
        if not answer:
            raise GeminiError("Gemini ne khali reply di; content policy ya availability check karein.")
        return answer[:6500]


def open_settings(parent, store: GeminiStore):
    """User-initiated dialog, no automatic paid calls or secret display."""
    window = tk.Toplevel(parent)
    window.title("Jarvis | Gemini Free API setup")
    window.geometry("600x485")
    window.configure(bg="#0b1827")
    window.transient(parent)
    window.grab_set()
    fg, muted = "#eaf7ff", "#a5bdcb"
    def label(value, color=fg):
        tk.Label(window, text=value, fg=color, bg="#0b1827",
                 wraplength=510, justify="left").pack(anchor="w", padx=22, pady=(12, 2))
    label("GEMINI AI CHAT · Optional free-tier text brain", "#44e1d6")
    label("Get key: https://aistudio.google.com/api-keys")
    tk.Button(window, text="Open Google AI Studio", command=lambda: webbrowser.open(
        "https://aistudio.google.com/api-keys")).pack(anchor="w", padx=22, pady=4)
    label("Key stays encrypted to this Windows user (DPAPI), never in GitHub or chat.",
          muted)
    label("Paste new API key (masked; saved key is never shown):")
    key_input = tk.Entry(window, show="●", width=48)
    key_input.pack(anchor="w", padx=22, pady=4)
    label("Text model (supported Free Tier, subject to project availability):")
    selected = tk.StringVar(window, store.model())
    chooser = ttk.Combobox(window, textvariable=selected, values=MODELS,
                           state="readonly", width=30)
    chooser.pack(anchor="w", padx=22, pady=3)
    result = tk.StringVar(window, "Configured" if store.configured() else "Key not set")
    label("Free-tier requests may be used by Google to improve products. Do not send private client data.", muted)
    tk.Label(window, textvariable=result, bg="#0b1827", fg="#53e5a1",
             wraplength=510, justify="left").pack(anchor="w", padx=22, pady=4)

    def save():
        try:
            if key_input.get().strip():
                store.save_key(key_input.get())
            elif not store.configured():
                raise GeminiError("Pehle Gemini API key paste karein.")
            store.set_model(selected.get())
            key_input.delete(0, "end")
            result.set("Gemini key saved securely. Chat mode select karke 'Salam' send karein.")
        except GeminiError as exc:
            result.set(str(exc))

    def delete():
        if messagebox.askyesno("Remove Gemini key",
                               "Sirf is Windows PC ki saved Gemini API key delete karein?",
                               parent=window):
            try:
                store.delete_key()
                key_input.delete(0, "end")
                result.set("Saved Gemini API key removed.")
            except GeminiError as exc:
                result.set(str(exc))

    buttons = tk.Frame(window, bg="#0b1827")
    buttons.pack(fill="x", padx=19, pady=13)
    tk.Button(buttons, text="Save key / model", command=save).pack(side="left", padx=4)
    tk.Button(buttons, text="Remove key", command=delete).pack(side="left", padx=4)
    tk.Button(buttons, text="Close", command=window.destroy).pack(side="right", padx=4)
    return window
