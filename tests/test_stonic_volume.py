"""Stonic-inspired volume integration: no unsafe system commands."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Controller, parse_command, validate

class VolumeIntegrationTests(unittest.TestCase):
    def test_voice_style_commands(self):
        for command, direction in [('volume up','up'),('volume down','down'),('volume mute','mute'),('awaz barhao','up'),('awaz kam karo','down'),('awaz band karo','mute')]:
            self.assertEqual(parse_command(command), {'action':'volume','direction':direction})
    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):
            validate({'action':'volume','direction':'shutdown'})
        with self.assertRaises(ValueError):
            validate({'action':'volume','direction':'up','shell':'cmd'})
    def test_windows_key_is_allowlisted(self):
        fake=Mock()
        with patch('core.os.name','nt'), patch.dict(sys.modules,{'pyautogui':fake}):
            self.assertIn('up',Controller('.').execute({'action':'volume','direction':'up'}))
        fake.press.assert_called_once_with('volumeup')

if __name__ == '__main__':
    unittest.main()
