"""Browser UI integration tests with an explicitly mocked AI provider."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MOCK = r'''
window.mockCalls = [];
let signed = false;
window.puter = {
  auth: {
    isSignedIn: () => signed,
    signIn: async () => { signed = true; },
    signOut: async () => { signed = false; }
  },
  ai: {
    chat: async (messages, options) => {
      window.mockCalls.push(messages);
      const text = messages[messages.length - 1].content;
      if (text === 'FAIL') throw {code: 429};
      if (text === 'WAIT') {
        return new Promise((resolve, reject) => {
          options.signal.addEventListener('abort', () => reject(new DOMException('Stopped', 'AbortError')));
        });
      }
      return {message: {content: 'Mock AI response: ' + text}};
    }
  }
};
'''


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'web')))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.route('https://js.puter.com/v2/', lambda route: route.fulfill(content_type='application/javascript', body=MOCK))
        self.page.goto(self.base)
        self.page.get_by_text('Connect AI to start chatting', exact=True).wait_for()

    def tearDown(self):
        self.page.close()

    def send(self, text):
        self.page.get_by_label('Message', exact=True).fill(text)
        self.page.get_by_role('button', name='Send ↗', exact=True).click()

    def connect(self):
        self.page.get_by_role('button', name='Connect AI', exact=True).click()
        self.page.get_by_role('button', name='Disconnect AI', exact=True).wait_for()

    def test_auth_gate_context_reset_and_safe_rendering(self):
        self.send('Hello')
        self.page.get_by_text('Pehle upar Connect AI dabayein.', exact=False).wait_for()
        self.assertEqual(self.page.evaluate('window.mockCalls.length'), 0)
        self.connect()
        self.send('<img src=x onerror=alert(1)>')
        self.page.get_by_text('Mock AI response: <img src=x onerror=alert(1)>', exact=True).wait_for()
        self.assertEqual(self.page.locator('#chat img').count(), 0)
        self.send('Follow up')
        self.page.get_by_text('Mock AI response: Follow up', exact=True).wait_for()
        calls = self.page.evaluate('window.mockCalls')
        self.assertEqual(len(calls[-1]), 4)
        self.page.get_by_role('button', name='＋ New conversation', exact=True).click()
        self.send('Fresh')
        self.page.get_by_text('Mock AI response: Fresh', exact=True).wait_for()
        self.assertEqual(len(self.page.evaluate('window.mockCalls').pop()), 2)
        self.page.get_by_role('button', name='Disconnect AI', exact=True).click()
        self.page.get_by_role('button', name='Connect AI', exact=True).wait_for()

    def test_quota_failure_restores_message_and_supports_retry(self):
        self.connect()
        self.send('FAIL')
        self.page.get_by_text('Free allowance ya rate limit poori ho gayi.', exact=False).wait_for()
        self.assertEqual(self.page.get_by_label('Message', exact=True).input_value(), 'FAIL')
        self.assertTrue(self.page.get_by_role('button', name='Send ↗', exact=True).is_enabled())
        self.send('Retry')
        self.page.get_by_text('Mock AI response: Retry', exact=True).wait_for()

    def test_abort_mobile_layout_and_suggestion(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.get_by_role('button', name='Website ka hero copy likho', exact=True).click()
        self.assertEqual(self.page.get_by_label('Message', exact=True).input_value(), 'Website ka hero copy likho')
        self.connect()
        self.send('WAIT')
        self.page.get_by_role('button', name='Stop', exact=True).click()
        self.page.get_by_text('Reply rok di ya timeout hua.', exact=False).wait_for()
        self.assertTrue(self.page.get_by_role('button', name='Send ↗', exact=True).is_enabled())
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)


if __name__ == '__main__':
    unittest.main(verbosity=2)
