"""Offline safety/flow tests for the direct LiveKit desktop WebRTC companion."""
import base64
import json
import queue
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import direct_livekit as lk


EXAMPLE_SETTINGS = {
    "LIVEKIT_URL": "wss://sample-project.livekit.cloud",
    "LIVEKIT_API_KEY": "api-key-example",
    "LIVEKIT_API_SECRET": "test-secret-should-never-leave-backend",
}


def decode_payload(token):
    segment = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


class DirectLivekitUnitTests(unittest.TestCase):
    def test_issues_signed_short_lived_room_token_with_builder_dispatch(self):
        token = lk.make_client_token(EXAMPLE_SETTINGS, "jarvis-test123", now=10000)
        data = decode_payload(token)
        self.assertEqual(data["iss"], "api-key-example")
        self.assertEqual(data["exp"], 10090)
        self.assertEqual(data["video"]["room"], "jarvis-test123")
        self.assertTrue(data["video"]["roomJoin"])
        self.assertFalse(data["video"].get("roomAdmin", False))
        self.assertEqual(data["roomConfig"]["agents"][0]["agentName"], "training-2057")
        self.assertNotIn("LIVEKIT_API_SECRET", json.dumps(data))
        self.assertNotIn(EXAMPLE_SETTINGS["LIVEKIT_API_SECRET"], token)

    def test_project_credentials_only_accepted_as_local_private_file(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / ".env.local"
            with self.assertRaises(lk.LiveKitSetupError):
                lk.get_project_settings(file)
            file.write_text(
                "LIVEKIT_URL=wss://sample-project.livekit.cloud\n"
                "LIVEKIT_API_KEY=api-key-example\n"
                "LIVEKIT_API_SECRET=test-secret-should-never-leave-backend\n",
                encoding="utf-8")
            self.assertEqual(lk.get_project_settings(file), EXAMPLE_SETTINGS)
            file.write_text(
                "LIVEKIT_URL=https://cloud.livekit.io/projects/jarvis\n"
                "LIVEKIT_API_KEY=key\nLIVEKIT_API_SECRET=secretsecret\n",
                encoding="utf-8")
            with self.assertRaisesRegex(lk.LiveKitSetupError, "wss://"):
                lk.get_project_settings(file)

    def test_strict_tool_allowlist_blocks_unsafe_operations(self):
        for action in (
            {"action": "delete", "path": "Documents"},
            {"action": "key", "keys": "ctrl+enter"},
            {"action": "click", "x": 50, "y": 50},
            {"action": "launch", "app": "powershell"},
            {"action": "launch", "app": "notepad", "shell": True},
            {"action": "note", "name": "../secrets.txt", "text": "x"},
            {"action": "folder", "name": "..\\secrets"},
            {"action": "find", "query": "\x00"},
        ):
            with self.subTest(action=action):
                with self.assertRaises((ValueError, TypeError, KeyError)):
                    lk.check_action(action)
        self.assertEqual(lk.check_action(
            {"action": "launch", "app": "notepad"}), {"action":"launch","app":"notepad"})
        self.assertEqual(lk.check_action(
            {"action":"find","query":"invoice"}), {"action":"find","query":"invoice"})

    def test_admin_room_end_is_separate_private_token_and_fixed_https_url(self):
        with patch("direct_livekit.urlopen") as request:
            request.return_value.__enter__.return_value.status = 200
            self.assertTrue(lk.delete_room(EXAMPLE_SETTINGS, "jarvis-test"))
            sent = request.call_args.args[0]
            self.assertEqual(sent.full_url,
                             "https://sample-project.livekit.cloud/twirp/livekit.RoomService/DeleteRoom")
            self.assertEqual(json.loads(sent.data), {"room": "jarvis-test"})
            self.assertEqual(sent.get_method(), "POST")
            token = sent.get_header("Authorization").split("Bearer ", 1)[1]
            claims = decode_payload(token)
            self.assertTrue(claims["video"]["roomAdmin"])
            self.assertNotIn("roomConfig", claims)

    def test_browser_assets_serve_no_secret_and_pinned_sdk(self):
        root = Path(__file__).resolve().parents[1] / "web"
        html = (root / "jarvis_live.html").read_text(encoding="utf-8")
        js = (root / "jarvis_live.js").read_text(encoding="utf-8")
        self.assertIn("livekit-client@2.23.0", html)
        self.assertIn("registerRpcMethod", js)
        self.assertIn("desktop_command", js)
        self.assertIn("/api/disconnect", js)
        self.assertIn("/api/connect", js)
        self.assertNotIn("LIVEKIT_API_SECRET", js)
        self.assertNotIn("cloud.livekit.io/projects", js)


class DirectLivekitHttpTests(unittest.TestCase):
    def setUp(self):
        self.queue = queue.Queue()
        self.server = lk.DirectVoiceService(self.queue)
        self.url = self.server.start()
        self.base = self.url.split("/#",1)[0]
        self.headers = {
            "Authorization": "Bearer " + self.server.nonce,
            "Origin": self.base,
            "Content-Type": "application/json",
        }
        self.room_delete = patch("direct_livekit.delete_room", return_value=True)
        self.room_delete.start()
        self.addCleanup(self.room_delete.stop)
        self.addCleanup(self.server.close)

    def post(self, endpoint, payload=None, headers=None):
        req = Request(self.base + endpoint, method="POST",
                      data=json.dumps(payload or {}).encode("utf-8"),
                      headers=headers if headers is not None else self.headers)
        with urlopen(req, timeout=4) as result:
            return json.loads(result.read())

    def test_local_server_has_strict_host_origin_and_no_cors(self):
        self.assertIn("127.0.0.1", self.base)
        with urlopen(self.base + "/", timeout=3) as resp:
            self.assertIn("frame-ancestors 'none'",
                          resp.headers["Content-Security-Policy"])
            self.assertNotIn("Access-Control-Allow-Origin", dict(resp.headers))
        for headers in (
            {"Origin": "https://evil.test"},
            {"Authorization": "Bearer " + self.server.nonce,
             "Origin": "https://evil.test"},
            {"Authorization": "Bearer wrong", "Origin": self.base},
        ):
            with self.subTest(headers=headers):
                with self.assertRaises(HTTPError) as err:
                    self.post("/api/connect", headers=headers)
                self.assertEqual(err.exception.code, 403)

    def test_connect_dispatch_token_is_scoped_and_one_session_only(self):
        with patch("direct_livekit.get_project_settings", return_value=EXAMPLE_SETTINGS):
            response = self.post("/api/connect")
            self.assertEqual(response["url"], EXAMPLE_SETTINGS["LIVEKIT_URL"])
            self.assertEqual(response["agent"], "training-2057")
            self.assertNotIn("LIVEKIT_API_SECRET", str(response))
            self.assertNotIn(EXAMPLE_SETTINGS["LIVEKIT_API_SECRET"], str(response))
            self.assertEqual(decode_payload(response["token"])["video"]["room"],
                             response["room"])
            with self.assertRaises(HTTPError) as err:
                self.post("/api/connect")
            self.assertEqual(err.exception.code, 400)
            ended = self.post("/api/disconnect")
            self.assertTrue(ended["ok"])

    def test_disallowed_voice_action_never_enters_review_queue(self):
        with patch("direct_livekit.get_project_settings", return_value=EXAMPLE_SETTINGS):
            self.post("/api/connect")
            for command in (
                {"action":"delete","name":"important"},
                {"action":"click","x":1,"y":2},
                {"action":"launch","app":"cmd"},
            ):
                with self.assertRaises(HTTPError):
                    self.post("/api/action", command)
            self.assertTrue(self.queue.empty())

    def test_approved_native_action_returns_only_after_review(self):
        with patch("direct_livekit.get_project_settings", return_value=EXAMPLE_SETTINGS):
            self.post("/api/connect")
            done = {}
            def worker():
                done["result"] = self.post(
                    "/api/action", {"action":"launch", "app":"calculator"})
            thread = threading.Thread(target=worker)
            thread.start()
            req = self.queue.get(timeout=2)
            self.assertEqual(req.action, {"action":"launch","app":"calculator"})
            self.assertNotIn("result", done)
            req.result = "DONE: calculator opened"
            req.event.set()
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertTrue(done["result"]["ok"])

    def test_native_denial_is_not_success(self):
        with patch("direct_livekit.get_project_settings", return_value=EXAMPLE_SETTINGS):
            self.post("/api/connect")
            done = {}
            def worker():
                done["result"] = self.post("/api/action",
                                           {"action":"find","query":"invoice"})
            thread = threading.Thread(target=worker)
            thread.start()
            req = self.queue.get(timeout=2)
            req.result = "DENIED: User declined"
            req.event.set()
            thread.join(3)
            self.assertFalse(done["result"]["ok"])

    def test_stop_state_blocks_further_actions_and_reconnect_is_explicit(self):
        with patch("direct_livekit.get_project_settings", return_value=EXAMPLE_SETTINGS):
            self.post("/api/connect")
            self.post("/api/state", {"state":"CONNECTED"})
            self.assertTrue(self.post("/api/status")["active"])
            self.post("/api/disconnect")
            stopped = self.post("/api/status")
            self.assertTrue(stopped["stopRequested"])
            self.assertFalse(stopped["active"])
            with self.assertRaises(HTTPError):
                self.post("/api/action", {"action":"launch","app":"notepad"})
            self.post("/api/connect")
            self.assertTrue(self.post("/api/status")["active"])

    def test_session_timeout_requests_cloud_room_end(self):
        self.server.max_seconds = 0.12
        with patch("direct_livekit.get_project_settings", return_value=EXAMPLE_SETTINGS):
            self.post("/api/connect")
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                if not self.post("/api/status")["active"]:
                    break
                time.sleep(.04)
            self.assertFalse(self.post("/api/status")["active"])
            self.assertTrue(self.post("/api/status")["stopRequested"])


if __name__ == "__main__":
    unittest.main()
