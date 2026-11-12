"""Real browser + native loopback integration, with an explicitly mocked Puter SDK."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sys
import threading
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from account_chat import AccountChat
from core import ChatAI

MOCK = r'''
let signed = false;
window.calls = [];
window.aborted = false;
window.puter = {
 auth:{isSignedIn:()=>signed,signIn:async()=>{signed=true;},signOut:async()=>{signed=false;}},
 ai:{chat:async(messages,options)=>{
  window.calls.push(messages);
  const text=messages[messages.length-1].content;
  if(text==='QUOTA') throw {code:429};
  if(text==='WAIT') return new Promise((resolve,reject)=>{
   options.signal.addEventListener('abort',()=>{window.aborted=true;reject(new DOMException('Stopped','AbortError'));});
  });
  return {message:{content:'Useful mocked answer for '+text}};
 }}
};
'''


class AccountBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel=os.environ.get('JARVIS_BROWSER_CHANNEL') or None)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.bridge = AccountChat()
        self.pool = ThreadPoolExecutor(2)
        self.page = self.browser.new_page()
        self.page.route('https://js.puter.com/**', lambda route: route.fulfill(status=200, content_type='application/javascript', body=MOCK))
        self.page.goto(self.bridge.start())

    def tearDown(self):
        self.bridge.close()
        self.page.close()
        self.pool.shutdown(wait=True)

    def connect(self):
        self.page.locator('#consent').check()
        self.page.locator('#connect').click()
        self.page.wait_for_function("document.getElementById('status').textContent.includes('Connected.')")
        self.assertEqual(self.bridge.status(),'ready')

    def test_consent_signin_native_history_disconnect(self):
        self.page.locator('#connect').click()
        self.assertIn('Tick',self.page.locator('#status').inner_text())
        self.assertEqual(self.bridge.status(),'sign_in')
        self.assertEqual(self.page.evaluate('window.calls.length'),0)
        self.connect()
        ai = ChatAI(bridge=self.bridge)
        future = self.pool.submit(ai.ask,[{'role':'user','content':'website idea'}])
        self.page.wait_for_function('window.calls.length === 1')
        self.page.wait_for_function("document.getElementById('status').textContent.includes('Connected.')")
        # Pump browser events until the response POST reaches the native thread.
        self.page.wait_for_timeout(200)
        self.assertIn('Useful mocked answer',future.result(timeout=3))
        self.page.locator('#disconnect').click()
        self.page.wait_for_function("document.getElementById('status').textContent.includes('Disconnected')")
        self.assertEqual(self.bridge.status(),'sign_in')
        self.assertEqual(self.page.evaluate('window.calls.length'),1)

    def test_quota_no_retry_or_paid_fallback(self):
        self.connect()
        future = self.pool.submit(self.bridge.complete,{'messages':[{'role':'user','content':'QUOTA'}]})
        self.page.wait_for_function('window.calls.length === 1')
        self.page.wait_for_timeout(200)
        with self.assertRaisesRegex(RuntimeError,'allowance'):
            future.result(timeout=3)
        self.assertEqual(self.page.evaluate('window.calls.length'),1)

    def test_native_stop_aborts_browser_and_discards_late_answer(self):
        self.connect()
        stop = threading.Event()
        future = self.pool.submit(self.bridge.complete,{'messages':[{'role':'user','content':'WAIT'}]},stop)
        self.page.wait_for_function('window.calls.length === 1')
        stop.set()
        with self.assertRaisesRegex(RuntimeError,'stopped'):
            future.result(timeout=3)
        self.page.wait_for_function('window.aborted === true',timeout=5000)
        self.assertFalse(self.bridge.tasks)
        self.assertEqual(self.page.evaluate('window.calls.length'),1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
