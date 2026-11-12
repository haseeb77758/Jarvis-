"""Ephemeral browser relay for Puter account chat. No account tokens on Python.

Only text requests/responses cross this loopback bridge. It exposes no desktop
commands, files, screen, shell or microphone APIs. Cloud output is untrusted text.
"""
from collections import deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit
import sys

MAX_BODY = 128_000
ASSETS = {'/': ('connect.html', 'text/html; charset=utf-8'),
          '/connect.js': ('connect.js', 'text/javascript; charset=utf-8'),
          '/connect.css': ('connect.css', 'text/css; charset=utf-8')}


@dataclass
class Task:
    payload: dict
    done: threading.Event = field(default_factory=threading.Event)
    response: dict | None = None
    error: str | None = None


class AccountChat:
    def __init__(self):
        self.secret = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.tasks = {}
        self.waiting = deque()
        self.signed_in = False
        self.last_seen = 0
        self.server = None
        self.closed = False

    def start(self):
        with self.lock:
            if self.closed:
                raise RuntimeError('Chat connection closed. Jarvis restart karein.')
            if self.server is None:
                bridge = self
                class Handler(BaseHTTPRequestHandler):
                    def log_message(self, *_args):
                        pass

                    def setup(self):
                        super().setup()
                        self.connection.settimeout(5)

                    def send_json(self, status, value):
                        data = json.dumps(value).encode('utf-8')
                        self.send_bytes(status, data, 'application/json')

                    def send_bytes(self, status, data, mime):
                        self.send_response(status)
                        self.send_header('Content-Type', mime)
                        self.send_header('Content-Length', str(len(data)))
                        self.send_header('Cache-Control', 'no-store')
                        self.send_header('Referrer-Policy', 'no-referrer')
                        self.send_header('X-Frame-Options', 'DENY')
                        self.send_header('X-Content-Type-Options', 'nosniff')
                        self.send_header('Content-Security-Policy', "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
                        self.end_headers()
                        self.wfile.write(data)

                    def trusted_host(self):
                        return self.headers.get('Host') == bridge.host

                    def authorized(self):
                        origin = self.headers.get('Origin')
                        token = self.headers.get('Authorization', '')
                        return (self.trusted_host() and origin in (None, bridge.origin) and
                                token.isascii() and secrets.compare_digest(token, 'Bearer ' + bridge.secret))

                    def do_GET(self):
                        if not self.trusted_host():
                            self.send_json(403, {'error': 'host'})
                            return
                        path = urlsplit(self.path).path
                        if path in ASSETS:
                            file, mime = ASSETS[path]
                            root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'web'
                            self.send_bytes(200, (root / file).read_bytes(), mime)
                        elif path == '/next' and self.authorized():
                            self.send_json(200, bridge.next_task())
                        else:
                            self.send_json(403, {'error': 'not authorized'})

                    def do_POST(self):
                        if not self.authorized():
                            self.send_json(403, {'error': 'not authorized'})
                            return
                        try:
                            size = int(self.headers.get('Content-Length', '0'))
                            if not 1 <= size <= MAX_BODY or self.headers.get('Transfer-Encoding'):
                                raise ValueError()
                            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                                raise ValueError()
                            data = json.loads(self.rfile.read(size))
                            if not isinstance(data, dict):
                                raise ValueError()
                            if self.path == '/connection':
                                if type(data.get('signed_in')) is not bool:
                                    raise ValueError()
                                bridge.connection(data['signed_in'])
                                active = data.get('active_id')
                                with bridge.lock:
                                    task = bridge.tasks.get(active) if isinstance(active, str) else None
                                    alive = task is not None and not task.done.is_set()
                                self.send_json(200, {'ok': True, 'active': alive})
                            elif self.path == '/result':
                                accepted = bridge.result(data)
                                self.send_json(200 if accepted else 409, {'ok': accepted})
                            else:
                                self.send_json(404, {'error': 'unknown route'})
                        except (ValueError, TypeError, UnicodeError):
                            self.send_json(400, {'error': 'invalid request'})

                self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
                self.server.daemon_threads = True
                self.host = '127.0.0.1:' + str(self.server.server_port)
                self.origin = 'http://' + self.host
                threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self.origin + '/#' + self.secret

    def status(self):
        with self.lock:
            return 'ready' if self.signed_in and time.monotonic() - self.last_seen < 12 else 'sign_in'

    def connection(self, signed_in):
        with self.lock:
            self.signed_in = signed_in
            self.last_seen = time.monotonic()
            if not signed_in:
                for task in self.tasks.values():
                    task.error = 'AI disconnected. Connect AI se browser mein sign in karein.'
                    task.done.set()

    def next_task(self):
        with self.lock:
            if not self.signed_in:
                return {'task': None}
            self.last_seen = time.monotonic()
            while self.waiting:
                ident = self.waiting.popleft()
                task = self.tasks.get(ident)
                if task is not None and not task.done.is_set():
                    return {'task': {'id': ident, **task.payload}}
        return {'task': None}

    def result(self, data):
        ident = data.get('id')
        if not isinstance(ident, str):
            return False
        with self.lock:
            task = self.tasks.get(ident)
            if task is None or task.done.is_set():
                return False
            text = data.get('text')
            if isinstance(text, str) and 0 < len(text.strip()) <= 16000:
                task.response = {'message': {'content': text.strip()}}
            else:
                # Only known error codes cross into native logs, never provider data.
                task.error = {
                    'quota': 'Account allowance/rate limit poori ho gayi. Koi paid upgrade automatic nahi hui.',
                    'sign_in': 'Pehle Connect AI se Puter account sign-in karein.',
                    'stopped': 'Chat request stopped or timed out.',
                }.get(data.get('error'), 'AI reply nahi mili. Browser connection aur internet check karein.')
            task.done.set()
            return True

    def complete(self, payload, cancel=None, timeout=95):
        if cancel is not None and cancel.is_set():
            raise RuntimeError('Chat request stopped.')
        if self.status() != 'ready':
            raise RuntimeError('Pehle Connect AI dabayein, browser mein sign in karein aur connection tab khula rakhein.')
        encoded = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        if len(encoded) > MAX_BODY - 1000:
            raise ValueError('Conversation bohat lambi hai. New chat shuru karein.')
        task = Task(payload)
        ident = secrets.token_urlsafe(18)
        with self.lock:
            if self.closed or len(self.tasks) >= 4:
                raise RuntimeError('Chat busy/closed hai. Dobara connect karke try karein.')
            self.tasks[ident] = task
            self.waiting.append(ident)
        deadline = time.monotonic() + timeout
        try:
            while not task.done.wait(0.05):
                if self.closed or (cancel is not None and cancel.is_set()):
                    raise RuntimeError('Chat request stopped. Late answer discarded.')
                if time.monotonic() > deadline:
                    raise RuntimeError('Chat timeout. Browser connection tab aur internet check karein.')
            if cancel is not None and cancel.is_set():
                raise RuntimeError('Chat request stopped. Late answer discarded.')
            if task.error:
                raise RuntimeError(task.error)
            return task.response
        finally:
            with self.lock:
                self.tasks.pop(ident, None)
                try:
                    self.waiting.remove(ident)
                except ValueError:
                    pass

    def close(self):
        self.closed = True
        self.connection(False)
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
