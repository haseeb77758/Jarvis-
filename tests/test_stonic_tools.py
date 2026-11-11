"""Stonic-inspired safe search, media and clock tools."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Controller, parse_command, parse_plan, validate

class StonicToolsTests(unittest.TestCase):
    def test_command_parsing(self):
        self.assertEqual(parse_command('google: weather in Lahore'), {'action':'web_search','query':'weather in Lahore'})
        self.assertEqual(parse_command('youtube: python tutorial'), {'action':'youtube_search','query':'python tutorial'})
        self.assertEqual(parse_command('kitne baje hain'), {'action':'clock'})
    def test_search_validation(self):
        for action in ('web_search','youtube_search'):
            for query in ('', 'x'*181, 'hi\\nbye'):
                with self.subTest(action=action,query=query), self.assertRaises(ValueError):
                    validate({'action':action,'query':query})
        with self.assertRaises(ValueError):
            validate({'action':'shutdown'})
    def test_url_encoding_and_no_shell(self):
        with patch('core.os.name','nt'), patch('webbrowser.open',return_value=True) as browser:
            Controller('.').execute({'action':'youtube_search','query':'python & AI'})
            self.assertEqual(browser.call_args.args[0], 'https://www.youtube.com/results?search_query=python+%26+AI')
    def test_clock_and_plans(self):
        self.assertIn('Local time:', Controller('.').execute({'action':'clock'}))
        self.assertEqual(parse_plan('{"actions":[{"action":"clock"}]}'),[{'action':'clock'}])

if __name__ == '__main__':
    unittest.main()
