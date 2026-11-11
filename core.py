"""Local-only Windows controls. No HTTP listener, shell execution or remote bridge."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler

MODEL = 'qwen2.5:1.5b'
CLOUD_URL = 'https://haseeb-ai-4ybb30.v2.appdeploy.ai/'
APP_NAMES = ('chrome', 'edge', 'notepad', 'calculator', 'paint', 'explorer')
KEYS = {'ctrl+c': ('ctrl', 'c'), 'ctrl+v': ('ctrl', 'v'),
        'ctrl+a': ('ctrl', 'a'), 'ctrl+s': ('ctrl', 's'),
        'alt+tab': ('alt', 'tab'), 'win+d': ('win', 'd'),
        'enter': ('enter',), 'tab': ('tab',), 'esc': ('esc',),
        'up': ('up',), 'down': ('down',), 'left': ('left',), 'right': ('right',)}


def valid_url(value):
    u = urlparse(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or any(c.isspace() for c in value):
        raise ValueError('Sirf plain https:// website address use karein.')
    return value


def safe_child(root, name):
    """Only simple names, never paths, device names, alternate data streams or traversal."""
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError('Naam 1–100 characters ka hona chahiye.')
    if name != name.strip() or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith(('.', ' ')):
        raise ValueError('Simple naam dein; slash, colon aur path allowed nahi.')
    if name in ('.', '..') or name.split('.')[0].upper() in {
        'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))
    }:
        raise ValueError('Yeh Windows reserved naam hai.')
    base = Path(root).resolve()
    target = base / name
    # Existing links are not followed for writes.
    if target.is_symlink() or target.resolve().parent != base:
        raise ValueError('Workspace se bahar write allowed nahi.')
    return target


def validate(action):
    if not isinstance(action, dict) or not isinstance(action.get('action'), str):
        raise ValueError('Action invalid hai.')
    kind = action['action']
    fields = {
        'launch': {'app'}, 'website': {'url'}, 'folder': {'name'},
        'note': {'name', 'text'}, 'find': {'query'}, 'screenshot': set(),
        'click': {'x', 'y'}, 'type': {'text'}, 'key': {'keys'},
    }
    if kind not in fields or set(action) != fields[kind] | {'action'}:
        raise ValueError('Yeh action supported nahi; arbitrary code run nahi hota.')
    for key in fields[kind] - {'x', 'y'}:
        if not isinstance(action[key], str) or not action[key].strip():
            raise ValueError(f'{key} khali ya invalid hai.')
    if kind == 'launch' and action['app'] not in APP_NAMES:
        raise ValueError('Sirf supported apps khul sakti hain.')
    if kind == 'website':
        valid_url(action['url'])
    if kind in ('folder', 'note'):
        safe_child(Path.home(), action['name'])
    if kind == 'note' and not action['name'].lower().endswith('.txt'):
        raise ValueError('Note ka naam .txt par khatam hona chahiye.')
    if kind == 'key' and action['keys'] not in KEYS:
        raise ValueError('Yeh shortcut allowlist mein nahi.')
    if kind == 'type' and (len(action['text']) > 1000 or not action['text'].isascii() or any(ord(c) < 32 or ord(c) > 126 for c in action['text'])):
        raise ValueError('Type action: single-line English/Roman Urdu, max 1,000 characters.')
    if kind == 'note' and len(action['text']) > 20000:
        raise ValueError('Note bohat lamba hai.')
    if kind == 'find' and len(action['query']) > 100:
        raise ValueError('Search query chhoti rakhein.')
    if kind == 'click' and any(type(action[k]) is not int or not 0 <= action[k] <= 20000 for k in ('x', 'y')):
        raise ValueError('Click coordinates invalid hain.')
    return dict(action)


def parse_command(text):
    text = text.strip()
    low = text.lower()
    if low in ('screenshot', 'screen dekhao', 'screen dikhao'):
        return {'action': 'screenshot'}
    for app in APP_NAMES:
        if low in (f'{app} kholo', f'open {app}', f'launch {app}'):
            return {'action': 'launch', 'app': app}
    if low.startswith('open https://'):
        return validate({'action': 'website', 'url': text[5:]})
    for prefix in ('folder banao:', 'folder:', 'create folder:'):
        if low.startswith(prefix):
            return validate({'action': 'folder', 'name': text[len(prefix):].strip()})
    for prefix in ('find:', 'file dhoondo:', 'search:'):
        if low.startswith(prefix):
            return validate({'action': 'find', 'query': text[len(prefix):].strip()})
    if low.startswith('type:'):
        return validate({'action': 'type', 'text': text[5:].strip()})
    if low.startswith('key:'):
        return validate({'action': 'key', 'keys': text[4:].strip().lower()})
    m = re.fullmatch(r'click:\s*(\d+)\s*,\s*(\d+)', low)
    if m:
        return validate({'action': 'click', 'x': int(m[1]), 'y': int(m[2])})
    if low.startswith('note:'):
        return validate({'action': 'note', 'name': 'Haseeb-Note-' + str(time.time_ns()) + '.txt', 'text': text[5:].strip()})
    return None


def parse_plan(raw):
    try:
        obj = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError('AI ka plan valid JSON nahi tha. Direct command use karein.') from exc
    if not isinstance(obj, dict) or set(obj) != {'actions'} or not isinstance(obj['actions'], list) or not 1 <= len(obj['actions']) <= 5:
        raise ValueError('Plan mein 1–5 supported actions chahiye.')
    return [validate(item) for item in obj['actions']]


class Controller:
    def __init__(self, workspace, stop=None):
        self.workspace = Path(workspace).resolve()
        self.stop = stop or threading.Event()

    def execute(self, action):
        a = validate(action)
        if self.stop.is_set():
            raise RuntimeError('Stopped. Resume dabayein.')
        kind = a['action']
        if kind == 'folder':
            p = safe_child(self.workspace, a['name'])
            p.mkdir(exist_ok=False)
            return f'Folder bana: {p}'
        if kind == 'note':
            p = safe_child(self.workspace, a['name'])
            with p.open('x', encoding='utf-8') as f:
                f.write(a['text'])
            return f'Note save hua: {p}'
        if kind == 'find':
            return self.find(a['query'])
        if os.name != 'nt':
            raise RuntimeError('Yeh control Windows par chalta hai.')
        if kind == 'launch':
            self.launch(a['app'])
            return 'Launch request bhej di: ' + a['app']
        if kind == 'website':
            import webbrowser
            if not webbrowser.open(a['url']):
                raise RuntimeError('Browser launch request fail hui.')
            return 'Browser ko website open request bhej di.'
        import pyautogui as pg
        pg.FAILSAFE = True
        pg.PAUSE = 0.15
        if kind == 'screenshot':
            return pg.screenshot()
        if kind == 'click':
            w, h = pg.size()
            if not (a['x'] < w and a['y'] < h):
                raise ValueError('Point primary screen ke bahar hai.')
            pg.click(a['x'], a['y'])
            return f'Click input bheja: {a["x"]}, {a["y"]}'
        if kind == 'type':
            # Single characters keep long typing cancellable. No Enter is appended.
            for character in a['text']:
                if self.stop.is_set():
                    raise RuntimeError('Typing stop kar di.')
                pg.write(character, interval=0.015)
            return 'Typing input bheja. Text submit nahi kiya.'
        if kind == 'key':
            pg.hotkey(*KEYS[a['keys']])
            return 'Keyboard input bheja: ' + a['keys']
        raise ValueError('Action not implemented.')

    def find(self, query):
        results = []
        deadline = time.monotonic() + 12
        visited = 0
        for root, dirs, files in os.walk(self.workspace, followlinks=False):
            dirs[:] = [d for d in dirs if d not in {'.git', '.venv', 'node_modules', 'AppData', '$Recycle.Bin'}
                       and not (Path(root) / d).is_symlink()
                       and not (hasattr(Path(root) / d, 'is_junction') and (Path(root) / d).is_junction())]
            for name in dirs + files:
                visited += 1
                if self.stop.is_set():
                    return 'Search stopped.\n' + '\n'.join(results)
                if query.casefold() in name.casefold():
                    results.append(str(Path(root) / name))
                if len(results) >= 50 or time.monotonic() > deadline or visited > 50000:
                    return 'Search bounded (50 results / 12 seconds / 50k entries):\n' + '\n'.join(results)
        return '\n'.join(results) if results else 'Is workspace mein matching naam nahi mila.'

    @staticmethod
    def launch(app):
        win = Path(os.environ.get('WINDIR', r'C:\Windows'))
        system = win / 'System32'
        fixed = {'notepad': system / 'notepad.exe', 'calculator': system / 'calc.exe',
                 'paint': system / 'mspaint.exe', 'explorer': win / 'explorer.exe'}
        if app in fixed:
            exe = fixed[app]
        else:
            relative = 'Google/Chrome/Application/chrome.exe' if app == 'chrome' else 'Microsoft/Edge/Application/msedge.exe'
            candidates = [Path(os.environ.get(v, '')) / relative for v in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA') if os.environ.get(v)]
            exe = next((p for p in candidates if p.is_file()), None)
            if not exe:
                raise FileNotFoundError(f'{app} installed location nahi mili.')
        if not Path(exe).is_file():
            raise FileNotFoundError('App executable nahi mila: ' + str(exe))
        subprocess.Popen([str(exe)], shell=False)


class LocalAI:
    def __init__(self, model=MODEL):
        self.model = model
        # Never proxy local prompts through HTTP_PROXY from the environment.
        self.opener = build_opener(ProxyHandler({}))

    def ask(self, messages, plan=False):
        system = ('You are HASEEB AI, created by Haseeb Crafts. Answer in concise Roman Urdu or the language requested. '
                  'You cannot control the computer from chat. Never claim an action was performed. ')
        if plan:
            system = ('Return only JSON: {"actions":[...]}. At most five actions. Allowed schemas: '
                      '{"action":"launch","app":"chrome|edge|notepad|calculator|paint|explorer"}; '
                      '{"action":"website","url":"https://example.com"}; '
                      '{"action":"folder","name":"simple folder name"}; '
                      '{"action":"note","name":"simple-name.txt","text":"note body"}; '
                      '{"action":"find","query":"filename fragment"}; '
                      '{"action":"screenshot"}. No other actions. No shell commands. '
                      'Do not claim success. User will review and approve each action. '
                      'If unsupported, return {"actions":[]} rather than inventing an action.')
        body = {'model': self.model, 'messages': [{'role': 'system', 'content': system}] + messages[-8:],
                'stream': False, 'options': {'num_ctx': 2048, 'num_predict': 600, 'temperature': 0.2}, 'keep_alive': '2m'}
        if plan:
            body['format'] = 'json'
        req = Request('http://127.0.0.1:11434/api/chat', json.dumps(body).encode(), {'Content-Type': 'application/json'})
        try:
            with self.opener.open(req, timeout=180) as r:
                data = json.loads(r.read(2_000_000))
        except Exception as exc:
            raise RuntimeError('Local AI ready nahi ya timeout hua. SETUP-LOCAL-AI.bat chalayein; Ollama running aur model downloaded hona chahiye. Direct commands phir bhi chalti hain.') from exc
        content = data.get('message', {}).get('content')
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError('Local AI ne khali reply diya. Direct command try karein.')
        return content
