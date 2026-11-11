"""Safe Stonic-video inspired media, navigation and draft commands."""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Controller, parse_command, validate


class VideoFeaturesTests(unittest.TestCase):
    def test_natural_navigation(self):
        self.assertEqual(parse_command('youtube kholo'), {'action': 'website', 'url': 'https://www.youtube.com'})
        self.assertEqual(parse_command('whatsapp kholo'), {'action': 'website', 'url': 'https://web.whatsapp.com'})
        self.assertEqual(parse_command('google par search karo: Haseeb Crafts'),
                         {'action': 'web_search', 'query': 'Haseeb Crafts'})
        self.assertEqual(parse_command('youtube par dhoondo: CSS tutorial'),
                         {'action': 'youtube_search', 'query': 'CSS tutorial'})

    def test_media_commands_are_allowlisted(self):
        for text, command in [('play pause', 'play_pause'), ('next song', 'next'),
                              ('previous song', 'previous'), ('agla gana', 'next')]:
            self.assertEqual(parse_command(text), {'action': 'media', 'command': command})
        for command in ('shutdown', 'launch', 'delete'):
            with self.assertRaises(ValueError):
                validate({'action': 'media', 'command': command})

    def test_media_controller_uses_media_key_only(self):
        fake = Mock()
        with patch('core.os.name', 'nt'), patch.dict(sys.modules, {'pyautogui': fake}):
            Controller('.').execute({'action': 'media', 'command': 'play_pause'})
        fake.press.assert_called_once_with('playpause')
        fake.hotkey.assert_not_called()

    def test_whatsapp_is_draft_only_never_autosend(self):
        self.assertEqual(parse_command('whatsapp draft: Hello Haseeb'),
                         {'action': 'whatsapp_draft', 'text': 'Hello Haseeb'})
        for text in ('', 'hello\nworld', 'a' * 501):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                validate({'action': 'whatsapp_draft', 'text': text})
        with patch('core.os.name', 'nt'), patch('webbrowser.open', return_value=True) as browser:
            result = Controller('.').execute({'action': 'whatsapp_draft', 'text': 'Hello & salaam'})
        self.assertIn('Send khud', result)
        browser.assert_called_once_with('https://wa.me/?text=Hello+%26+salaam')

    def test_destructive_commands_remain_unsupported(self):
        for text in ('delete all files', 'shutdown computer', 'send WhatsApp automatically'):
            self.assertIsNone(parse_command(text))
        for kind in ('shutdown', 'shell', 'delete', 'send_whatsapp'):
            with self.assertRaises(ValueError):
                validate({'action': kind})


if __name__ == '__main__':
    unittest.main()
