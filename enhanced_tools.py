"""Safe, opt-in extensions for HASEEB AI Jarvis; no remote control or shell.

Keep the desktop toolkit separate from the chat-only sandbox. A model response
never directly calls system actions, network image APIs, or file writes.
"""
from __future__ import annotations

import base64
import csv
from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from uuid import uuid4

IMAGE_API_URL = "https://api.openai.com/v1/images/generations"
IMAGE_MODEL = "gpt-image-1-mini"
SCHEDULE_HEADERS = ("date", "time", "title")
CODE_EXTENSIONS = frozenset({
    ".py", ".html", ".css", ".js", ".jsx", ".ts", ".tsx",
    ".php", ".json", ".java", ".cpp", ".cs", ".md", ".txt",
})


def weather_search_url(city: str) -> str:
    """A browser search, not an invented forecast or an undisclosed geolocation."""
    if not isinstance(city, str) or not 1 <= len(city.strip()) <= 80:
        raise ValueError("Weather ke liye shehar ka naam dein (1-80 characters).")
    if any(ord(ch) < 32 for ch in city):
        raise ValueError("Weather city mein control characters allowed nahi.")
    return "https://www.google.com/search?" + urlencode({"q": "weather " + city.strip()})


def read_code_for_review(path: str | Path) -> str:
    """Explicit file selection only; never read .env, keys or whole folders."""
    item = Path(path)
    if item.is_symlink() or item.suffix.lower() not in CODE_EXTENSIONS:
        raise ValueError("Sirf known code/text file types review ho sakti hain.")
    if not item.is_file() or not 1 <= item.stat().st_size <= 25_000:
        raise ValueError("Code file 1 se 25 KB ke darmiyan honi chahiye.")
    try:
        return item.read_text(encoding="utf-8")
    except (UnicodeError, OSError) as exc:
        raise ValueError("Code file UTF-8 text nahi hai ya read nahi ho saki.") from exc


class ScheduleStore:
    """Explicitly saved local CSV agenda. No background watcher or notifications."""

    def __init__(self, data_directory: str | Path):
        self.directory = Path(data_directory)
        self.path = self.directory / "schedule.csv"

    @staticmethod
    def verify(date: str, time: str, title: str) -> dict[str, str]:
        if not isinstance(date, str) or not isinstance(time, str) or not isinstance(title, str):
            raise ValueError("Date, time aur title text honay chahiye.")
        try:
            datetime.strptime(date, "%Y-%m-%d")
            datetime.strptime(time, "%H:%M")
        except ValueError as exc:
            raise ValueError("Date YYYY-MM-DD aur time HH:MM (24h) format mein dein.") from exc
        if len(date) != 10 or len(time) != 5:
            raise ValueError("Date/time format invalid hai.")
        if not 1 <= len(title.strip()) <= 120 or any(ord(x) < 32 for x in title):
            raise ValueError("Schedule title 1-120 characters ka single line text ho.")
        return {"date": date, "time": time, "title": title.strip()}

    def list_items(self) -> list[dict[str, str]]:
        if not self.path.is_file():
            return []
        if self.path.is_symlink() or self.path.stat().st_size > 65_536:
            raise ValueError("Schedule file unsafe ya bohat bari hai.")
        with self.path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != SCHEDULE_HEADERS:
                raise ValueError("Schedule CSV header invalid hai.")
            result = []
            for row in reader:
                if len(result) >= 200 or set(row) != set(SCHEDULE_HEADERS):
                    raise ValueError("Schedule CSV mein unsupported rows hain.")
                result.append(self.verify(row["date"], row["time"], row["title"]))
        return sorted(result, key=lambda value: (value["date"], value["time"], value["title"]))

    def add(self, date: str, time: str, title: str):
        item = self.verify(date, time, title)
        records = self.list_items()
        if len(records) >= 200:
            raise ValueError("Maximum 200 schedule entries allowed.")
        if item in records:
            raise ValueError("Yeh schedule entry pehle se saved hai.")
        records.append(item)
        records.sort(key=lambda value: (value["date"], value["time"], value["title"]))
        self._write(records)

    def delete(self, index: int):
        items = self.list_items()
        if type(index) is not int or not 0 <= index < len(items):
            raise ValueError("Valid schedule item select karein.")
        removed = items.pop(index)
        self._write(items)
        return removed

    def _write(self, records):
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.directory.is_symlink() or self.path.is_symlink():
            raise ValueError("Schedule symlink par write allowed nahi.")
        fd, tmp = tempfile.mkstemp(prefix=".schedule-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=SCHEDULE_HEADERS)
                writer.writeheader()
                writer.writerows(records)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


def system_action(mode: str):
    """Never called by Ollama directly. UI enforces explicit user review."""
    if mode not in {"lock", "shutdown", "restart", "cancel"}:
        raise ValueError("System action allowlist mein nahi.")
    if os.name != "nt":
        raise RuntimeError("System power controls sirf Windows par available hain.")
    if mode == "lock":
        import ctypes
        if not ctypes.windll.user32.LockWorkStation():
            raise RuntimeError("Windows session lock nahi hui.")
        return "Windows ko lock karne ka command bheja."
    system_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32"
    exe = system_dir / "shutdown.exe"
    if not exe.is_file():
        raise RuntimeError("Windows shutdown.exe nahi mila.")
    flags = {
        "shutdown": ["/s", "/t", "60"],
        "restart": ["/r", "/t", "60"],
        "cancel": ["/a"],
    }[mode]
    subprocess.Popen([str(exe), *flags], shell=False)
    if mode == "cancel":
        return "Pending Windows power action cancel karne ki request bhej di."
    return ("Windows " + mode + " 60 seconds baad scheduled hai. "
            "Unsaved work save karein ya Toolkit se Cancel Power dabayein.")


def generate_cloud_image(prompt: str, api_key: str, output_directory: str | Path, opener=None) -> Path:
    """Optional paid OpenAI Images API; only after separate UI approval.

    The only network destination is the fixed official HTTPS endpoint. Never
    persist/log an API key; never rewrite an existing image file.
    """
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 1500:
        raise ValueError("Image prompt 1-1500 characters ka hona chahiye.")
    if not isinstance(api_key, str) or not 10 <= len(api_key) <= 250 or any(ch.isspace() for ch in api_key):
        raise ValueError("Valid OpenAI API key dein. ChatGPT subscription se API credit alag hota hai.")
    body = json.dumps({
        "model": IMAGE_MODEL,
        "prompt": prompt.strip(),
        "n": 1,
        "size": "1024x1024",
        "quality": "low",
        "output_format": "png",
    }).encode("utf-8")
    request = Request(IMAGE_API_URL, body, headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }, method="POST")
    class BlockRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("Image provider redirect denied; API key never forwarded.")

    client = opener if opener is not None else build_opener(ProxyHandler({}), BlockRedirect())
    try:
        with client.open(request, timeout=150) as response:
            raw = response.read(24_000_001)
        if len(raw) > 24_000_000:
            raise ValueError("Image service ka response bohat bara hai.")
        payload = json.loads(raw)
        encoded = payload["data"][0]["b64_json"]
        if not isinstance(encoded, str) or len(encoded) > 23_000_000:
            raise ValueError("Image response format invalid.")
        image = base64.b64decode(encoded, validate=True)
        if not image.startswith(b"\x89PNG\r\n\x1a\n") or not 100 <= len(image) <= 16_000_000:
            raise ValueError("Image service ne valid PNG output nahi diya.")
    except (KeyError, IndexError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError("Image generate nahi hui. API access, credits aur network check karein.") from exc
    destination = Path(output_directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    name = "HaseebAI-" + uuid4().hex + ".png"
    target = destination / name
    with target.open("xb") as file:
        file.write(image)
    return target
