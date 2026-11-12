"""Direct LiveKit WebRTC desktop companion, no native LiveKit Python imports.

Local-only HTTP token broker + bounded command bridge. Project API secrets
stay in LOCALAPPDATA and never reach the browser. No network port is exposed.
Voice sessions are dispatched to the user's existing LiveKit Builder agent.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from livekit_bridge import credentials_path, LiveKitSetupError

AGENT_NAME = "training-2057"
MAX_SECONDS = 10 * 60
ASSETS = {
    "/": ("text/html; charset=utf-8", "jarvis_live.html"),
    "/jarvis_live.css": ("text/css; charset=utf-8", "jarvis_live.css"),
    "/jarvis_live.js": ("application/javascript; charset=utf-8", "jarvis_live.js"),
}
REVIEWED_ACTIONS = frozenset({"launch", "find", "folder", "note", "clock", "windows"})
STATIC_ROOT = Path(__file__).resolve().parent / "web"


def encode_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jwt_sign(claims, key, secret):
    """HS256 only, using Python stdlib; no blingfire or third-party Python."""
    if not key or not secret or len(secret) < 10:
        raise LiveKitSetupError("LiveKit Cloud API key/secret invalid.")
    header = b64url(encode_json({"alg": "HS256", "typ": "JWT"}))
    payload = b64url(encode_json(claims))
    unsigned = header + "." + payload
    signature = b64url(hmac.new(secret.encode("utf-8"), unsigned.encode("ascii"),
                                hashlib.sha256).digest())
    return unsigned + "." + signature


def get_project_settings(path=None):
    path = Path(path) if path else credentials_path()
    if not path.is_file() or path.stat().st_size > 8192:
        raise LiveKitSetupError(
            "Direct voice ke liye LiveKit project URL/key/secret LOCAL file mein save karo. "
            "LiveKit setup > Advanced 2 (edit local credentials)."
        )
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            field, value = line.split("=", 1)
            values[field.strip()] = value.strip().strip("'\"")
    url = values.get("LIVEKIT_URL", "")
    parsed = urlsplit(url)
    if (parsed.scheme != "wss" or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise LiveKitSetupError("LIVEKIT_URL ko project ke wss://....livekit.cloud URL se set karo.")
    if any(not values.get(key) or values[key].startswith("YOUR_") for key in
           ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")):
        raise LiveKitSetupError("LiveKit LOCAL file mein asli Cloud credentials chahiye.")
    return values


def make_client_token(settings, room, now=None):
    now = int(now if now is not None else time.time())
    identity = "jarvis-" + secrets.token_hex(7)
    claims = {
        "iss": settings["LIVEKIT_API_KEY"], "sub": identity,
        "iat": now, "nbf": now - 1, "exp": now + 90,
        "name": "Jarvis Desktop",
        "video": {
            "room": room, "roomJoin": True, "canPublish": True,
            "canSubscribe": True, "canPublishData": True,
            "canPublishSources": ["microphone"],
        },
        # Explicit dispatch names the EXISTING Builder production agent.
        "roomConfig": {"agents": [{"agentName": AGENT_NAME}]},
    }
    return jwt_sign(claims, settings["LIVEKIT_API_KEY"],
                    settings["LIVEKIT_API_SECRET"])


def make_admin_token(settings, room):
    now = int(time.time())
    return jwt_sign({
        "iss": settings["LIVEKIT_API_KEY"], "sub": "jarvis-desktop-admin",
        "iat": now, "nbf": now - 1, "exp": now + 60,
        "video": {"room": room, "roomAdmin": True},
    }, settings["LIVEKIT_API_KEY"], settings["LIVEKIT_API_SECRET"])


def delete_room(settings, room):
    """Server-side end-call/timeout backstop; never gives admin token to JS."""
    parsed = urlsplit(settings["LIVEKIT_URL"])
    url = "https://" + parsed.netloc + "/twirp/livekit.RoomService/DeleteRoom"
    token = make_admin_token(settings, room)
    req = Request(url, method="POST", data=encode_json({"room": room}),
                  headers={"Content-Type": "application/json",
                           "Authorization": "Bearer " + token})
    try:
        with urlopen(req, timeout=8) as response:
            return 200 <= response.status < 300
    except HTTPError as exc:
        # A nonexistent room has already ended.
        if exc.code == 404:
            return True
        raise RuntimeError("Cloud room end request failed (HTTP " + str(exc.code) + ")") from None
    except (OSError, URLError) as exc:
        raise RuntimeError("Cloud room end request unavailable: " +
                           type(exc).__name__) from None


def check_action(data):
    """Strict shape and content limits before any Tk review/Controller.execute."""
    from core import validate
    if not isinstance(data, dict) or not 1 <= len(data) <= 4:
        raise ValueError("Invalid command payload.")
    action = data.get("action")
    if action not in REVIEWED_ACTIONS:
        raise ValueError("Unsupported voice action. Screen automation and deletion are disabled.")
    permitted = {
        "launch": {"action", "app"},
        "folder": {"action", "name"},
        "note": {"action", "name", "text"},
        "find": {"action", "query"},
        "windows": {"action"},
        "clock": {"action"},
    }[action]
    if set(data) != permitted:
        raise ValueError("Unexpected or missing tool arguments.")
    for value in data.values():
        if isinstance(value, str) and (len(value) > 1400 or "\x00" in value):
            raise ValueError("Tool argument too long or invalid.")
    return validate(data)


@dataclass
class VoiceToolRequest:
    action: dict
    event: threading.Event
    result: str = "DENIED: No approval."


class DirectVoiceService:
    def __init__(self, command_queue, on_state=None, max_seconds=MAX_SECONDS,
                 asset_root=STATIC_ROOT):
        import queue
        self.command_queue = command_queue if command_queue is not None else queue.Queue()
        self.on_state = on_state
        self.max_seconds = max_seconds
        self.asset_root = Path(asset_root)
        self.nonce = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.active_room = None
        self.room_settings = None
        self.started_at = None
        self.stop_requested = False
        self.state = "OFF"
        self.timer = None
        self.httpd = None
        self.url = None

    def start(self):
        if self.httpd is not None:
            return self.url
        server = self
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *args):
                pass  # Never log bearer tokens, path fragments or room IDs.

            def valid_host(self):
                host = self.headers.get("Host", "")
                return host == "127.0.0.1:" + str(server.httpd.server_port)

            def authorized(self):
                return (
                    self.headers.get("Authorization") == "Bearer " + server.nonce
                    and self.headers.get("Origin", "") ==
                    "http://127.0.0.1:" + str(server.httpd.server_port)
                )

            def reply(self, code, body, mime="application/json; charset=utf-8"):
                payload = body if isinstance(body, bytes) else encode_json(body)
                self.send_response(code)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Permissions-Policy", "microphone=(self), camera=()")
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                if mime.startswith("text/html"):
                    self.send_header(
                        "Content-Security-Policy",
                        "default-src 'none'; script-src 'self' https://cdn.jsdelivr.net; "
                        "style-src 'self'; connect-src 'self' https: wss:; "
                        "media-src 'self' blob:; img-src 'self' data:; "
                        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                    )
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                if not self.valid_host():
                    return self.reply(403, {"error": "Untrusted host"})
                route = self.path.split("?", 1)[0]
                if route in ASSETS:
                    mime, name = ASSETS[route]
                    try:
                        contents = (server.asset_root / name).read_bytes()
                    except OSError:
                        return self.reply(404, {"error": "Missing local UI asset"})
                    return self.reply(200, contents, mime)
                return self.reply(404, {"error": "No such endpoint"})

            def do_POST(self):
                if not self.valid_host() or not self.authorized():
                    return self.reply(403, {"error": "Local session authorization required"})
                if self.path not in ("/api/connect", "/api/disconnect", "/api/state",
                                     "/api/action", "/api/status"):
                    return self.reply(404, {"error": "Unknown API"})
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                    if not 0 <= length <= 4096:
                        return self.reply(413, {"error": "Invalid payload size"})
                    raw = self.rfile.read(length)
                    data = json.loads(raw) if raw else {}
                    if not isinstance(data, dict):
                        return self.reply(400, {"error": "Expected JSON object"})
                    if self.path == "/api/connect":
                        result = server.connect()
                    elif self.path == "/api/disconnect":
                        result = server.disconnect()
                    elif self.path == "/api/status":
                        result = server.status()
                    elif self.path == "/api/state":
                        result = server.update_state(data)
                    else:
                        result = server.request_action(data)
                    return self.reply(200, result)
                except (ValueError, LiveKitSetupError) as exc:
                    return self.reply(400, {"error": str(exc)[:500]})
                except Exception:
                    return self.reply(503, {"error": "Local bridge operation failed; retry or open diagnostics."})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.httpd.timeout = 0.5
        self.url = "http://127.0.0.1:" + str(self.httpd.server_port) + "/#" + self.nonce
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self.url

    def connect(self):
        with self.lock:
            if self.active_room:
                raise ValueError("Already in a session. Disconnect first.")
            settings = get_project_settings()
            room = "jarvis-" + secrets.token_hex(14)
            token = make_client_token(settings, room)
            self.active_room = room
            self.room_settings = settings
            self.started_at = time.monotonic()
            self.stop_requested = False
            self.state = "CONNECTING"
            self.timer = threading.Timer(self.max_seconds, self.disconnect)
            self.timer.daemon = True
            self.timer.start()
            return {"url": settings["LIVEKIT_URL"], "token": token,
                    "room": room, "agent": AGENT_NAME,
                    "maxSeconds": self.max_seconds}

    def update_state(self, data):
        state = data.get("state")
        if not isinstance(state, str) or state not in {
            "CONNECTED", "AGENT JOINED", "AGENT LEFT", "LISTENING",
            "SPEAKING", "DISCONNECTED", "FAILED",
        }:
            raise ValueError("Invalid voice state")
        with self.lock:
            if not self.active_room:
                return {"stopped": True}
            self.state = state
        if self.on_state:
            try:
                self.on_state(state)
            except Exception:
                pass
        return self.status()

    def status(self):
        with self.lock:
            return {
                "state": self.state,
                "active": bool(self.active_room),
                "stopRequested": self.stop_requested,
                "remainingSeconds": max(0, int(self.max_seconds -
                    (time.monotonic() - self.started_at))) if self.started_at else 0,
            }

    def request_action(self, data):
        with self.lock:
            if not self.active_room or self.stop_requested:
                raise ValueError("Voice session not active.")
        action = check_action(data)
        if not self.command_queue:
            raise ValueError("No desktop review handler.")
        req = VoiceToolRequest(action=action, event=threading.Event())
        self.command_queue.put(req)
        if not req.event.wait(timeout=20):
            return {"ok": False, "result": "DENIED: Native desktop approval timed out."}
        return {"ok": req.result.startswith("DONE:"), "result": req.result[:1800]}

    def disconnect(self):
        with self.lock:
            room = self.active_room
            settings = self.room_settings
            timer = self.timer
            self.stop_requested = True
            self.timer = None
            self.active_room = None
            self.room_settings = None
            self.started_at = None
            self.state = "DISCONNECT REQUESTED"
        if timer:
            timer.cancel()
        if room and settings:
            try:
                ended = delete_room(settings, room)
                return {"ok": ended, "message": "Cloud room ended" if ended else "End not confirmed"}
            except RuntimeError as exc:
                return {"ok": False, "message": str(exc)[:250]}
        return {"ok": True, "message": "No active voice room"}

    def close(self):
        self.disconnect()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
