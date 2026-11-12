"""Explicit local preferences and reviewed shortcuts, never executable self-modification."""
import json
import os
from pathlib import Path
import tempfile
from core import validate, MODEL, CHAT_MODELS


class PreferenceStore:
    def __init__(self, directory=None):
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share'))
        self.directory = Path(directory) if directory else base / 'HaseebCrafts/Jarvis'
        self.path = self.directory / 'preferences.json'
        self.facts = []
        self.shortcuts = {}
        self.apps = {}
        self.chat_model = MODEL
        self.load()

    def load(self):
        if not self.path.is_file():
            return
        try:
            if self.path.stat().st_size > 100000:
                raise ValueError('preferences too large')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            facts = data.get('facts', [])
            if not isinstance(facts, list) or len(facts) > 20 or any(not isinstance(x, str) or not 1 <= len(x) <= 500 for x in facts):
                raise ValueError('bad preferences')
            shortcuts = data.get('shortcuts', {})
            if not isinstance(shortcuts, dict) or len(shortcuts) > 20:
                raise ValueError('bad shortcuts')
            verified = {}
            for name, actions in shortcuts.items():
                if not isinstance(name, str) or not 1 <= len(name) <= 60 or not isinstance(actions, list) or not 1 <= len(actions) <= 8:
                    raise ValueError('bad shortcut')
                verified[name] = [validate(a) for a in actions]
            apps = data.get('apps', {})
            if not isinstance(apps, dict) or len(apps) > 20:
                raise ValueError('bad app registry')
            import re
            for alias, path in apps.items():
                if not re.fullmatch(r'[a-z0-9][a-z0-9 -]{0,39}', alias) or not isinstance(path, str) or not Path(path).is_absolute() or Path(path).suffix.lower() != '.exe':
                    raise ValueError('bad app path')
            selected = data.get('chat_model', MODEL)
            if selected not in CHAT_MODELS:
                raise ValueError('unsupported AI model preference')
            self.facts, self.shortcuts, self.apps = facts, verified, apps
            self.chat_model = selected
        except (ValueError, OSError, TypeError, AttributeError):
            # Do not run partially validated persisted actions.
            self.facts, self.shortcuts, self.apps = [], {}, {}
            self.chat_model = MODEL

    def save(self):
        payload = json.dumps({'version': 1, 'facts': self.facts, 'shortcuts': self.shortcuts, 'apps': self.apps, 'chat_model': self.chat_model}, ensure_ascii=False, indent=2)
        if len(payload.encode('utf-8')) > 100000:
            raise ValueError('Memory size limit reached. Kuch entries remove karein.')
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='prefs-', suffix='.json', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(payload)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def remember(self, fact):
        if not isinstance(fact, str) or not 1 <= len(fact.strip()) <= 500:
            raise ValueError('Preference 1–500 characters ki honi chahiye.')
        fact = fact.strip()
        if fact not in self.facts:
            if len(self.facts) >= 20:
                raise ValueError('20 preferences saved hain. Memory se koi remove karein.')
            self.facts.append(fact)
            self.save()

    def shortcut(self, name, actions):
        name = name.strip().casefold()
        if not 1 <= len(name) <= 60 or not 1 <= len(actions) <= 8:
            raise ValueError('Short naam aur 1–8 actions chahiye.')
        if name in self.shortcuts:
            raise ValueError('Is naam ka shortcut pehle se hai. Memory mein remove karke dobara save karein.')
        if len(self.shortcuts) >= 20:
            raise ValueError('Maximum 20 shortcuts.')
        self.shortcuts[name] = [validate(a) for a in actions]
        self.save()

    def register_app(self, alias, path):
        import re
        alias = alias.strip().casefold()
        executable = Path(path).resolve()
        if not re.fullmatch(r'[a-z0-9][a-z0-9 -]{0,39}', alias) or not executable.is_file() or executable.suffix.lower() != '.exe':
            raise ValueError('Simple English alias aur existing .exe file choose karein.')
        if alias in self.apps:
            raise ValueError('Alias pehle se saved hai. Memory mein remove karke dobara add karein.')
        if len(self.apps) >= 20:
            raise ValueError('Maximum 20 custom apps.')
        self.apps[alias] = str(executable)
        self.save()
