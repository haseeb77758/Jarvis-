"""Reviewed Windows controls and account-chat prompts; chat cannot execute tools."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import threading
import time
from urllib.parse import urlparse, urlencode
from datetime import datetime

MODEL = 'Puter account default'
CHAT_MODELS = (MODEL,)
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


def _looks_like_echo(user_text, answer):
    """Detect short near-verbatim replies rather than penalizing normal conversation."""
    import difflib
    import re
    def compact(value):
        return " ".join(re.findall(r"\w+", value.casefold()))
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


def _has_urdu_script(text):
    """Detect Arabic-script glyphs in generated text, including Urdu-specific letters."""
    return any(
        0x0600 <= ord(char) <= 0x06FF
        or 0x0750 <= ord(char) <= 0x077F
        or 0x08A0 <= ord(char) <= 0x08FF
        for char in text
    )


def _roman_urdu_required(user_text):
    """Roman Urdu is the default, except when another script/language was requested."""
    lowered = user_text.casefold()
    if "roman urdu" in lowered or "roman-urdu" in lowered:
        return True
    if _has_urdu_script(user_text):
        return False  # Respect explicitly Urdu-script prompts.
    return not any(phrase in lowered for phrase in (
        "in english", "english mein", "english me", "write english",
        "reply in english", "respond in english", "answer in english",
        "urdu script", "urdu font", "urdu alphabet", "urdu mein likho",
        "urdu me likho", "french mein", "in french", "in spanish",
        "in arabic", "in hindi", "in persian",
    ))


def _asks_jarvis_intro(text):
    """A small, explicit check for requests about Jarvis's own identity."""
    normalized = text.casefold()
    return any(phrase in normalized for phrase in (
        'apna introduction', 'apna intro', 'apne bare mein batao',
        'apne baare mein batao', 'introduce yourself',
        'who are you', 'tum kaun ho',
    ))


def _verified_jarvis_intro(text):
    """Return an accurate, reviewed local self-introduction for simple Roman Urdu requests.

    A small model may produce plausible but nonsensical self-descriptions. This
    narrow identity FAQ uses fixed truthful text; other requests use the connected account model.
    """
    if not isinstance(text, str) or len(text) > 450:
        return None
    if not _asks_jarvis_intro(text) or not _roman_urdu_required(text):
        return None
    lowered = text.casefold()
    # Do not swallow additional substantive tasks attached to an intro request.
    if any(phrase in lowered for phrase in (
        'translate', 'tarjuma', 'comparison', 'compare', 'code likho',
        'website banao', 'video script likho', 'script banao',
        'essay', 'story likho', 'kahani likho', 'debug',
    )):
        return None
    # One to three sentences, with the requested identity and capabilities.
    identity = 'Main Jarvis hoon, Haseeb Crafts ka AI assistant.'
    capabilities = ('Main website ideas, video scripts, content planning aur '
                    'sawalon ke jawab dene mein madad kar sakta hoon.')
    closing = 'Batao, tumhe kis kaam mein madad chahiye?'
    is_greeting = 'salam' in lowered or 'salaam' in lowered
    sentences = (['Wa alaikum assalam!', identity, capabilities] if is_greeting
                 else [identity, capabilities, closing])
    count_match = re.search(r'\b([123])\s+(?:simple\s+)?(?:roman\s+urdu\s+)?(?:sentences?|jumlay?|lines?)\b', lowered)
    requested = int(count_match.group(1)) if count_match else 3
    if requested == 1:
        return (('Wa alaikum assalam, ' if is_greeting else '')
                + 'main Jarvis hoon, Haseeb Crafts ka AI assistant, '
                'jo website ideas, video scripts aur planning mein madad karta hai.')
    if requested == 2 and is_greeting:
        return 'Wa alaikum assalam! Main Jarvis hoon, Haseeb Crafts ka AI assistant jo ideas aur planning mein madad karta hai.'
    return ' '.join(sentences[:requested])


def _answers_jarvis_intro(text):
    """A greeting alone does not answer a requested self-introduction."""
    normalized = text.casefold()
    return ('jarvis' in normalized or 'haseeb ai' in normalized) and any(
        phrase in normalized for phrase in (
            'assistant', 'ai', 'madad', 'help', 'sawal', 'kaam', 'created',
        )
    )


CHAT_SYSTEM = (
    'You are Jarvis, a friendly, practical AI conversation partner created by Haseeb Crafts. '
    'Have a natural back-and-forth chat in Roman Urdu unless the user requests another language. '
    'When using Roman Urdu, write ONLY with Latin letters (A-Z); do not use Urdu, Arabic, or Persian script in any part of the reply. Keep it to 1-3 clear, friendly sentences for casual chat. '
    'Write natural Pakistan-style Roman Urdu with correct common phrases. Prefer simple conversational words; avoid broken literal translations, nonsense phrases and overly formal English. '
    'For salam use: "Wa alaikum assalam! Main theek hoon, tum sunao?" Never say "hai. Kya hai ab?". '
    'When unsure of a fact, say so briefly rather than guessing. '
    'IMPORTANT: Never merely repeat, rephrase or translate the user message. Actually respond to it. '
    'For a greeting, reply warmly and ask a short follow-up question. '
    'If the user asks for both a greeting AND your introduction, fulfill both; never answer only the greeting. '
    'If asked for your introduction in 3 Roman Urdu sentences, clearly say: 1) your name and creator, 2) what you can help with, 3) a relevant friendly closing. '
    'Example for introduction: "Wa alaikum assalam! Main Jarvis, Haseeb Crafts ka AI assistant hoon. Main sawalon, ideas aur planning mein madad kar sakta hoon; tumhe kis cheez mein madad chahiye?" '
    'For small talk such as "aur sunao", say something conversational and invite the user to continue. '
    'For a specific question, give a useful and accurate answer instead of restating the question. '
    'Remember earlier turns in this chat but do not invent personal details or claim to know private information. '
    'Keep responses concise and clear unless the user asks for detail. '
    'You cannot control the computer from this chat and must never claim an action was performed. '
    'Examples: User: "Assalam u alaikum Jarvis" Assistant: "Wa alaikum assalam! Main theek hoon, tum sunao?"; '
    'User: "aur sunao" Assistant: "Bas sab theek! Tum sunao, aaj kis cheez par baat karein?"'
)


class ChatAI:
    def __init__(self, model=MODEL, bridge=None, cancel=None):
        from account_chat import AccountChat
        self.model = MODEL
        self.bridge = bridge if bridge is not None else AccountChat()
        self.cancel = cancel

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
        # The verified self-introduction prevents nonsense for this narrow FAQ.
        # In particular, it never touches desktop action-planning JSON mode.
        if not plan:
            prepared_intro = _verified_jarvis_intro(latest_user)
            if prepared_intro is not None:
                return prepared_intro
        roman_required = not plan and _roman_urdu_required(latest_user)
        problem = None
        # Retry once for an echoed answer or an answer that breaks Roman Urdu script.
        # Never retry desktop-action JSON plans or silently rewrite Urdu-script requests.
        for attempt in range(1 if plan else 2):
            instruction = system
            if attempt and problem == 'script':
                instruction += ('\nIMPORTANT CORRECTION: The previous reply wrongly used Urdu or Arabic script. '
                                'Rewrite your answer entirely in Latin-letter Roman Urdu only. '
                                'No Urdu/Arabic letters, no direct translation to Urdu script. '
                                'Use short, grammatically simple conversational sentences.')
            elif attempt and problem == 'intro':
                instruction += ('\nIMPORTANT CORRECTION: The user asked for YOUR introduction. '
                                'The previous answer only greeted them. Explicitly say your name Jarvis, '
                                'that you are Haseeb Crafts AI assistant, and what you can help with. '
                                'If the user requested three sentences, give three complete sentences. '
                                'Keep Roman Urdu natural, without Urdu script.')
            elif attempt:
                instruction += ('\nYour previous draft echoed the incoming message instead of answering. '
                                'Reply freshly and conversationally, with at least one new, helpful statement. '
                                'Do not quote the user or say what they said.')
            selected = messages[-8:]
            if any(not isinstance(item, dict) or item.get('role') not in ('user', 'assistant')
                   or not isinstance(item.get('content'), str) or len(item['content']) > 4000 for item in selected):
                raise ValueError('Chat messages invalid hain ya bohat lambay hain.')
            body = {'messages': [{'role': 'system', 'content': instruction}] + selected, 'plan': bool(plan)}
            if sum(len(item['content']) for item in body['messages']) > 24000:
                raise ValueError('Conversation lambi hai. New chat shuru karein.')
            data = self.bridge.complete(body, cancel=self.cancel)
            content = data.get('message', {}).get('content')
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError('AI chatbot ne khali reply diya. Direct command try karein.')
            content = content.strip()
            if plan:
                return content
            if roman_required and _has_urdu_script(content):
                problem = 'script'
                continue
            if _looks_like_echo(latest_user, content):
                problem = 'echo'
                continue
            if _asks_jarvis_intro(latest_user) and not _answers_jarvis_intro(content):
                problem = 'intro'
                continue
            return content
        if problem == 'intro':
            raise RuntimeError(
                'Chat model ne apna introduction dene ka hissa chhor diya. '
                'New chat mein sirf "Jarvis apna introduction do" likh kar try karein.'
            )
        if problem == 'script':
            raise RuntimeError(
                'AI chatbot ne Roman Urdu ke bajaye Urdu script likhi. '
                'New chat se dobara try karein ya chhota aur seedha sawal poochhein. '
                'Selected model ' + self.model + ' se correct Roman Urdu guarantee nahi hoti.'
            )
        raise RuntimeError(
            'AI chatbot aapki baat repeat kar raha hai. '
            'New chat se retry karein ya thora detailed sawal poochhein; '
            'Sawal dobara saaf alfaaz mein poochhein.'
        )

