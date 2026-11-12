"""No real Puter login: validate a fake browser relay, cancellation and boundaries."""
import http.client
import json
import queue
import threading
import time
import unittest
from unittest.mock import Mock, patch

from account_chat import AccountChat
from core import ChatAI


class AccountChatTests(unittest.TestCase):
    def setUp(self):
        self.bridge = AccountChat()
        self.addCleanup(self.bridge.close)
        self.url = self.bridge.start()

    def http(self, method, path, data=None, auth=True, origin=None, host=None):
        conn = http.client.HTTPConnection(self.bridge.host, timeout=3)
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers['Authorization'] = 'Bearer ' + self.bridge.secret
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        encoded = json.dumps(data) if data is not None else None
        conn.request(method, path, body=encoded, headers=headers)
        response = conn.getresponse()
        result = (response.status, response.read(), dict(response.getheaders()))
        conn.close()
        return result

    def begin(self, stop=None, timeout=2):
        result = queue.Queue()
        def work():
            try:
                result.put(self.bridge.complete({'messages':[{'role':'user','content':'hello'}]}, stop, timeout))
            except Exception as exc:
                result.put(exc)
        thread = threading.Thread(target=work)
        thread.start()
        self.addCleanup(lambda: thread.join(3))
        return result

    def next(self):
        for _ in range(40):
            status, data, _ = self.http('GET', '/next')
            task = json.loads(data)['task']
            if task:
                return task
            time.sleep(0.01)
        self.fail('No queued native request')

    def test_random_loopback_fragment_not_secret_query_or_remote_host(self):
        self.assertTrue(self.url.startswith('http://127.0.0.1:'))
        self.assertIn('/#', self.url)
        self.assertNotIn('?', self.url)
        self.assertEqual(self.bridge.server.server_address[0], '127.0.0.1')
        self.assertGreaterEqual(len(self.bridge.secret), 32)

    def test_initial_signin_gate_sends_nothing(self):
        with self.assertRaisesRegex(RuntimeError, 'Connect AI'):
            self.bridge.complete({'messages':[]})
        self.assertFalse(self.bridge.tasks)
        self.assertFalse(self.bridge.waiting)

    def test_private_routes_reject_missing_auth_host_and_foreign_origin(self):
        for kwargs in ({'auth':False}, {'origin':'https://evil.example'}, {'host':'evil.example'}):
            self.assertEqual(self.http('GET','/next',**kwargs)[0], 403)
        self.assertEqual(self.http('POST','/connection',{'signed_in':True},auth=False)[0],403)

    def test_static_page_exposes_no_secret_and_no_cors(self):
        status, body, headers = self.http('GET','/',auth=False)
        self.assertEqual(status,200)
        self.assertNotIn(self.bridge.secret.encode(),body)
        self.assertNotIn('Access-Control-Allow-Origin',headers)
        self.assertIn(b'free monthly allowance',body)
        self.assertEqual(self.http('GET','/../../core.py')[0],403)
        self.assertEqual(self.http('POST','/execute',{'action':'launch'})[0],404)

    def test_signin_roundtrip_delivers_only_untrusted_text_once(self):
        self.assertEqual(self.http('POST','/connection',{'signed_in':True})[0],200)
        result = self.begin()
        task = self.next()
        self.assertEqual(task['messages'][0]['content'],'hello')
        self.assertIsNone(json.loads(self.http('GET','/next')[1])['task'])
        self.assertEqual(self.http('POST','/result',{'id':task['id'],'text':'A useful answer'})[0],200)
        self.assertEqual(result.get(timeout=2), {'message':{'content':'A useful answer'}})
        self.assertEqual(self.http('POST','/result',{'id':task['id'],'text':'duplicate'})[0],409)

    def test_quota_error_stops_without_any_retry_or_upgrade(self):
        self.bridge.connection(True)
        result = self.begin()
        task = self.next()
        self.http('POST','/result',{'id':task['id'],'error':'quota'})
        error = result.get(timeout=2)
        self.assertIsInstance(error,RuntimeError)
        self.assertIn('allowance',str(error))
        self.assertFalse(self.bridge.waiting)

    def test_cancel_discards_late_response_and_reports_inactive_to_browser(self):
        self.bridge.connection(True)
        stop = threading.Event()
        result = self.begin(stop)
        task = self.next()
        stop.set()
        self.assertIn('stopped',str(result.get(timeout=2)).lower())
        status, body, _ = self.http('POST','/connection',{'signed_in':True,'active_id':task['id']})
        self.assertFalse(json.loads(body)['active'])
        self.assertEqual(self.http('POST','/result',{'id':task['id'],'text':'late'})[0],409)

    def test_disconnect_cancels_pending_request(self):
        self.bridge.connection(True)
        result = self.begin()
        self.next()
        self.bridge.connection(False)
        self.assertIn('disconnected',str(result.get(timeout=2)))
        self.assertEqual(self.bridge.status(),'sign_in')

    def test_timeout_cleans_queue_and_does_not_requeue_paid_work(self):
        self.bridge.connection(True)
        with self.assertRaisesRegex(RuntimeError,'timeout'):
            self.bridge.complete({'messages':[]},timeout=0.02)
        self.assertFalse(self.bridge.tasks)
        self.assertFalse(self.bridge.waiting)

    def test_expired_tab_is_not_reported_as_connected(self):
        self.bridge.connection(True)
        self.bridge.last_seen -= 20
        self.assertEqual(self.bridge.status(),'sign_in')

    def test_invalid_json_shape_cannot_mark_signed_in(self):
        for data in ([],{'signed_in':'yes'}, {'signed_in':1}):
            self.assertEqual(self.http('POST','/connection',data)[0],400)
        self.assertEqual(self.bridge.status(),'sign_in')

    def test_legacy_setup_entry_points_to_livekit_not_puter(self):
        from app import App
        host = Mock()
        with patch('app.webbrowser.open') as browser:
            App.setup_ai(host)
        host.open_livekit_voice.assert_called_once()
        host.worker.assert_not_called()
        browser.assert_not_called()

    def test_native_ai_uses_same_account_bridge(self):
        ai = ChatAI(bridge=self.bridge)
        self.assertIs(ai.bridge,self.bridge)
        self.assertEqual(ai.model,'Puter account default')


if __name__ == '__main__':
    unittest.main()
