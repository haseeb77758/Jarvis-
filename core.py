"""Local-only Windows controls. No HTTP listener, shell execution or remote bridge."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import tempfile
import threading
import time
from urllib.parse import urlparse, urlencode
from datetime import datetime
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
        'launch': {'app'}, 'launch_custom': {'alias'}, 'website': {'url'}, 'folder': {'name'},
        'note': {'name', 'text'}, 'find': {'query'}, 'screenshot': set(),
        'volume': {'direction'}, 'media': {'command'}, 'whatsapp_draft': {'text'},
        'web_search': {'query'}, 'youtube_search': {'query'},
        'clock': set(),
        'click': {'x', 'y'}, 'type': {'text'}, 'key': {'keys'},
        'windows': set(), 'inspect': {'title'}, 'focus': {'title'},
        'wait_window': {'title'}, 'invoke': {'title', 'name'},
        'type_window': {'title', 'text'}, 'key_window': {'title', 'keys'},
    }
    if kind not in fields or set(action) != fields[kind] | {'action'}:
        raise ValueError('Yeh action supported nahi; arbitrary code run nahi hota.')
    for key in fields[kind] - {'x', 'y'}:
        if not isinstance(action[key], str) or not action[key].strip():
            raise ValueError(f'{key} khali ya invalid hai.')
    if kind in {'inspect', 'focus', 'wait_window', 'invoke', 'type_window', 'key_window'} and any(len(action[k]) > 250 for k in fields[kind] - {'text', 'keys'}):
        raise ValueError('Window/button naam 250 characters se chhota rakhein.')
    if kind in {'web_search', 'youtube_search'} and (len(action['query']) > 180 or any(ord(c) < 32 for c in action['query'])):
        raise ValueError('Search query invalid ya bohat lambi hai.')
    if kind == 'media' and action['command'] not in {'play_pause', 'next', 'previous'}:
        raise ValueError('Media command allowed nahi.')
    if kind == 'whatsapp_draft' and (len(action['text']) > 500 or any(ord(c) < 32 for c in action['text'])):
        raise ValueError('WhatsApp draft 1–500 single-line characters ka hona chahiye.')
    if kind == 'volume' and action['direction'] not in {'up', 'down', 'mute'}:
        raise ValueError('Volume direction invalid hai.')
    if kind == 'launch' and action['app'] not in APP_NAMES:
        raise ValueError('Sirf supported apps khul sakti hain.')
    if kind == 'launch_custom' and not re.fullmatch(r'[a-z0-9][a-z0-9 -]{0,39}', action['alias']):
        raise ValueError('Invalid custom app alias.')
    if kind == 'website':
        valid_url(action['url'])
    if kind in ('folder', 'note'):
        safe_child(Path.home(), action['name'])
    if kind == 'note' and not action['name'].lower().endswith('.txt'):
        raise ValueError('Note ka naam .txt par khatam hona chahiye.')
    if kind in {'key', 'key_window'} and action['keys'] not in KEYS:
        raise ValueError('Yeh shortcut allowlist mein nahi.')
    if kind in {'type', 'type_window'} and (len(action['text']) > 1000 or not action['text'].isascii() or any(ord(c) < 32 or ord(c) > 126 for c in action['text'])):
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
    volume_commands = {'volume up': 'up', 'volume down': 'down', 'volume mute': 'mute',
                       'awaz barhao': 'up', 'awaz kam karo': 'down', 'awaz band karo': 'mute'}
    if low in ('time', 'what time is it', 'kitne baje hain', 'date', 'aaj ki date'):
        return {'action': 'clock'}
    for prefix, kind in [('google:', 'web_search'), ('search web:', 'web_search'),
                         ('youtube:', 'youtube_search'), ('play youtube:', 'youtube_search')]:
        if low.startswith(prefix):
            return validate({'action': kind, 'query': text[len(prefix):].strip()})
    media_commands = {'pause music': 'play_pause', 'play pause': 'play_pause',
                      'music pause': 'play_pause', 'music play': 'play_pause',
                      'music roko': 'play_pause', 'media pause': 'play_pause',
                      'media play': 'play_pause', 'next song': 'next',
                      'next track': 'next', 'agla gana': 'next',
                      'previous song': 'previous', 'previous track': 'previous'}
    if low in media_commands:
        return validate({'action': 'media', 'command': media_commands[low]})
    websites = {'youtube kholo': 'https://www.youtube.com',
                'open youtube': 'https://www.youtube.com',
                'google kholo': 'https://www.google.com',
                'open google': 'https://www.google.com',
                'whatsapp kholo': 'https://web.whatsapp.com',
                'open whatsapp': 'https://web.whatsapp.com'}
    if low in websites:
        return validate({'action': 'website', 'url': websites[low]})
    for prefix, kind in [('youtube par search karo:', 'youtube_search'),
                         ('youtube par dhoondo:', 'youtube_search'),
                         ('google par search karo:', 'web_search'),
                         ('google par dhoondo:', 'web_search'),
                         ('search google:', 'web_search')]:
        if low.startswith(prefix):
            return validate({'action': kind, 'query': text[len(prefix):].strip()})
    for prefix in ('whatsapp draft:', 'whatsapp message draft:', 'message draft:'):
        if low.startswith(prefix):
            return validate({'action': 'whatsapp_draft', 'text': text[len(prefix):].strip()})
    if low in volume_commands:
        return validate({'action': 'volume', 'direction': volume_commands[low]})
    if low in ('windows', 'list windows', 'show windows'):
        return {'action': 'windows'}
    for prefix, kind in [('inspect:', 'inspect'), ('focus:', 'focus'), ('wait:', 'wait_window')]:
        if low.startswith(prefix):
            return validate({'action': kind, 'title': text[len(prefix):].strip()})
    for prefix, kind, field in [('write:', 'type_window', 'text'), ('press:', 'key_window', 'keys')]:
        if low.startswith(prefix):
            parts = text[len(prefix):].split('|', 1)
            if len(parts) != 2:
                raise ValueError('Format: ' + prefix + ' Window title | value')
            return validate({'action': kind, 'title': parts[0].strip(), field: parts[1].strip()})
    if low.startswith('button:'):
        parts = text[7:].split('|', 1)
        if len(parts) != 2:
            raise ValueError('Format: button: Window title | Exact button name')
        return validate({'action': 'invoke', 'title': parts[0].strip(), 'name': parts[1].strip()})
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
    if not isinstance(obj, dict) or set(obj) != {'actions'} or not isinstance(obj['actions'], list) or not 1 <= len(obj['actions']) <= 8:
        raise ValueError('Plan mein 1–8 supported actions chahiye.')
    return [validate(item) for item in obj['actions']]


class Controller:
    def __init__(self, workspace, stop=None, applications=None):
        self.workspace = Path(workspace).resolve()
        self.stop = stop or threading.Event()
        self.applications = applications if applications is not None else {}

    def execute(self, action):
        a = validate(action)
        if self.stop.is_set():
            raise RuntimeError('Stopped. Resume dabayein.')
        kind = a['action']
        if kind == 'clock':
            return datetime.now().astimezone().strftime('Local time: %Y-%m-%d %I:%M %p %Z')
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
        if kind == 'launch_custom':
            path = self.applications.get(a['alias'])
            if not path or not Path(path).is_absolute() or Path(path).suffix.lower() != '.exe' or not Path(path).is_file():
                raise ValueError('Registered app executable nahi mila. Add app se dobara register karein.')
            subprocess.Popen([path], shell=False)
            return 'Custom app launch request: ' + a['alias']
        if kind in {'windows', 'inspect', 'focus', 'wait_window', 'invoke'}:
            import desktop
            if kind == 'windows':
                return '\n'.join(desktop.windows()) or 'Koi titled window nahi mili.'
            if kind == 'inspect':
                return desktop.inspect(a['title'])
            if kind == 'focus':
                return desktop.focus(a['title'])
            if kind == 'wait_window':
                return desktop.wait_window(a['title'], self.stop)
            return desktop.invoke(a['title'], a['name'])
        if kind == 'launch':
            self.launch(a['app'])
            return 'Launch request bhej di: ' + a['app']
        if kind in {'website', 'web_search', 'youtube_search', 'whatsapp_draft'}:
            import webbrowser
            if kind == 'whatsapp_draft':
                url = 'https://wa.me/?' + urlencode({'text': a['text']})
            else:
                url = a['url'] if kind == 'website' else (
                    'https://www.google.com/search?' + urlencode({'q': a['query']}) if kind == 'web_search'
                    else 'https://www.youtube.com/results?' + urlencode({'search_query': a['query']}))
            if not webbrowser.open(url):
                raise RuntimeError('Browser launch request fail hui.')
            if kind == 'whatsapp_draft':
                return 'WhatsApp draft link khol diya. Contact choose karke Send khud dabayein; Jarvis ne message nahi bheja.'
            if kind == 'youtube_search':
                return 'YouTube search results browser mein kholne ki request bheji. Video choose karke Play dabayein.'
            return 'Browser ko website open request bhej di.'
        target_handle = None
        if kind in {'type_window', 'key_window'}:
            import desktop
            import ctypes
            target_handle = desktop.match_window(a['title']).handle
            desktop.focus(a['title'])
        import pyautogui as pg
        pg.FAILSAFE = True
        pg.PAUSE = 0.15
        if kind == 'media':
            pg.press({'play_pause': 'playpause', 'next': 'nexttrack', 'previous': 'prevtrack'}[a['command']])
            return 'Windows media key bheji: ' + a['command'] + '. Media app response verify karein.'
        if kind == 'volume':
            pg.press({'up': 'volumeup', 'down': 'volumedown', 'mute': 'volumemute'}[a['direction']])
            return 'Volume key input bheja: ' + a['direction']
        if kind == 'screenshot':
            return pg.screenshot()
        if kind == 'click':
            w, h = pg.size()
            if not (a['x'] < w and a['y'] < h):
                raise ValueError('Point primary screen ke bahar hai.')
            pg.click(a['x'], a['y'])
            return f'Click input bheja: {a["x"]}, {a["y"]}'
        if kind in {'type', 'type_window'}:
            # Single characters keep long typing cancellable. No Enter is appended.
            for character in a['text']:
                if self.stop.is_set():
                    raise RuntimeError('Typing stop kar di.')
                if target_handle is not None and ctypes.windll.user32.GetForegroundWindow() != target_handle:
                    raise RuntimeError('Target window ka focus badal gaya. Typing rok di; window select karke retry karein.')
                pg.write(character, interval=0.015)
            return 'Typing input bheja. Text submit nahi kiya.'
        if kind in {'key', 'key_window'}:
            if target_handle is not None and ctypes.windll.user32.GetForegroundWindow() != target_handle:
                raise RuntimeError('Target window ka focus badal gaya. Shortcut send nahi kiya.')
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


def ollama_binary():
    """Find only a normal installed Ollama command; never download or run installers."""
    installed = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe'
    return str(installed) if installed.is_file() else shutil.which('ollama.exe')


def ollama_status(model=MODEL, opener=None, executable=None):
    """Return a bounded, read-only status for this device's local Ollama API.

    "missing": no installed Ollama command; "stopped": API not available;
    "model_missing": Ollama running but our chat model not downloaded;
    "ready": configured and installed locally. Status does not generate text.
    """
    if executable is None:
        executable = ollama_binary()
    if not executable:
        return 'missing'
    client = opener if opener is not None else build_opener(ProxyHandler({}))
    try:
        request = Request('http://127.0.0.1:11434/api/tags', method='GET')
        with client.open(request, timeout=3) as response:
            models = json.loads(response.read(512_000)).get('models', [])
        if not isinstance(models, list):
            return 'stopped'
        names = {name for entry in models if isinstance(entry, dict)
                 for name in (entry.get('name'), entry.get('model'))
                 if isinstance(name, str)}
        return 'ready' if model in names else 'model_missing'
    except (OSError, ValueError, TypeError, KeyError):
        return 'stopped'


def _looks_like_echo(user_text, answer):
    """Detect short near-verbatim replies rather than penalizing normal conversation."""
    import difflib
    import re
    def compact(value):
        return " ".join(re.findall(r"\\w+", value.casefold()))
    question = compact(user_text)
    response = compact(answer)
    if not question or not response:
        return False
    if question == response:
        return True
    # Short-message spelling variants such as "assalam ua alaikum" vs
    # "assalam u alaikum" are essentially a repeated greeting, not a reply.
    if len(question) >= 8 and len(response) <= len(question) + 8:
        return difflib.SequenceMatcher(None, question, response).ratio() >= 0.88
    return False


CHAT_SYSTEM = (
    'You are Jarvis, a friendly, practical AI conversation partner created by Haseeb Crafts. '
    'Have a natural back-and-forth chat in Roman Urdu unless the user requests another language. '
    'IMPORTANT: Never merely repeat, rephrase or translate the user message. Actually respond to it. '
    'For a greeting, reply warmly and ask a short follow-up question. '
    'For small talk such as "aur sunao", say something conversational and invite the user to continue. '
    'For a specific question, give a useful and accurate answer instead of restating the question. '
    'Remember earlier turns in this chat but do not invent personal details or claim to know private information. '
    'Keep responses concise and clear unless the user asks for detail. '
    'You cannot control the computer from this chat and must never claim an action was performed. '
    'Examples: User: "Assalam u alaikum" Assistant: "Wa alaikum assalam! Kya haal hain?"; '
    'User: "aur sunao" Assistant: "Bas sab theek! Tum sunao, aaj kis cheez par baat karein?"'
)


class LocalAI:
    def __init__(self, model=MODEL):
        self.model = model
        # Never proxy local prompts through HTTP_PROXY from the environment.
        self.opener = build_opener(ProxyHandler({}))

    def ask(self, messages, plan=False, preferences=(), applications=()):
        system = CHAT_SYSTEM
        if plan:
            system = ('Return only JSON: {"actions":[...]}. At most eight actions. Allowed schemas: '
                      '{"action":"launch","app":"chrome|edge|notepad|calculator|paint|explorer"}; '
                      '{"action":"launch_custom","alias":"a registered alias"}; '
                      '{"action":"website","url":"https://example.com"}; '
                      '{"action":"folder","name":"simple folder name"}; '
                      '{"action":"note","name":"simple-name.txt","text":"note body"}; '
                      '{"action":"find","query":"filename fragment"}; '
                      '{"action":"screenshot"}; {"action":"windows"}; '
                      '{"action":"wait_window","title":"window title"}; {"action":"focus","title":"window title"}; '
                      '{"action":"inspect","title":"window title"}; '
                      '{"action":"invoke","title":"window title","name":"exact observed button name"}; '
                      '{"action":"type_window","title":"window title","text":"single line ASCII text explicitly requested by user"}. '
                      '{"action":"web_search","query":"search words"}; '
                      '{"action":"youtube_search","query":"video words"}; '
                      '{"action":"clock"}; {"action":"volume","direction":"up|down|mute"}; '
                      '{"action":"media","command":"play_pause|next|previous"}; '
                      '{"action":"whatsapp_draft","text":"one-line message, never auto send"}. '
                      'After launching an app, add wait_window and focus before typing. Never invent a button name. '
                      'No other actions. No shell commands. '
                      'Do not claim success. User will review and approve each action. '
                      'If unsupported, return {"actions":[]} rather than inventing an action.')
        if applications and plan:
            system += '\nRegistered app aliases: ' + json.dumps(list(applications)[:20])
        if preferences:
            system += '\nUser-saved response preferences (not tool permissions): ' + json.dumps(list(preferences)[:20], ensure_ascii=False)
        latest_user = next((item.get('content', '') for item in reversed(messages)
                            if item.get('role') == 'user' and isinstance(item.get('content'), str)), '')
        # One extra attempt for short parroting replies, but never in action-plan JSON mode.
        for attempt in range(1 if plan else 2):
            instruction = system
            if attempt:
                instruction += ('\nYour previous draft echoed the incoming message instead of answering. '
                                'Reply freshly and conversationally, with at least one new, helpful statement. '
                                'Do not quote the user or say what they said.')
            body = {
                'model': self.model,
                'messages': [{'role': 'system', 'content': instruction}] + messages[-8:],
                'stream': False,
                'options': {
                    'num_ctx': 2048,
                    'num_predict': 600,
                    'temperature': 0.2 if plan else (0.75 if attempt else 0.6),
                    'top_p': 0.9,
                    'repeat_penalty': 1.14 if not plan else 1.0,
                },
                'keep_alive': '2m',
            }
            if plan:
                body['format'] = 'json'
            req = Request('http://127.0.0.1:11434/api/chat',
                          json.dumps(body).encode(), {'Content-Type': 'application/json'})
            try:
                with self.opener.open(req, timeout=180) as response:
                    data = json.loads(response.read(2_000_000))
            except Exception as exc:
                raise RuntimeError(
                    'Ollama se jawab nahi mila. Jarvis mein Setup AI dabayein, Ollama Start menu se '
                    'kholein aur qwen2.5:1.5b download confirm karein. '
                    'SETUP-LOCAL-AI.bat bhi optional fallback hai. Direct commands chalti rahengi.'
                ) from exc
            content = data.get('message', {}).get('content')
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError('Local AI ne khali reply diya. Direct command try karein.')
            content = content.strip()
            if plan or not _looks_like_echo(latest_user, content):
                return content
        raise RuntimeError(
            'Ollama ka chhota 1.5B model aapki baat repeat kar raha hai. '
            'New chat se retry karein ya thora detailed sawaal poochhein; '
            'behtar jawab ke liye bara local model chahiye ho sakta hai.'
        )

def setup_local_model(stop):
    """Download only the named local model with an existing official Ollama install."""
    if os.name != 'nt':
        raise RuntimeError('Model setup button Windows ke liye hai.')
    executable = ollama_binary()
    if not executable:
        raise FileNotFoundError('Ollama installed nahi. Jarvis ka Setup AI button official Windows download page kholta hai.')
    status = ollama_status(executable=executable)
    if status == 'stopped':
        raise RuntimeError('Ollama installed hai magar local server band hai. Windows Start menu mein Ollama kholo, phir Setup AI dobara dabao.')
    if status == 'ready':
        return 'Ollama model already downloaded. Local AI chat mein sawal likhein.'
    with tempfile.TemporaryFile(mode='w+b') as log:
        process = subprocess.Popen([executable, 'pull', MODEL], stdout=log, stderr=subprocess.STDOUT,
                                   shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + 900
        while process.poll() is None:
            if stop.wait(0.25) or time.monotonic() > deadline:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise RuntimeError('Model download stopped. Setup button se baad mein retry kar sakte hain.')
        if process.returncode:
            log.seek(0, 2)
            length = log.tell()
            log.seek(max(0, length - 1500))
            details = log.read().decode('utf-8', errors='replace')
            raise RuntimeError('Ollama model download fail hua. Ollama Start menu se open karein aur internet check karein.\n' + details)
    if ollama_status(executable=executable) != 'ready':
        raise RuntimeError('Download khatam hua magar Ollama API par model confirm nahi hua. Ollama app khol kar Setup AI dobara dabayein.')
    return 'Ollama qwen2.5:1.5b model ready. Local AI chat mein sawal likhein.'
