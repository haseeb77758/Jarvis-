"""Mocked Gemini integration tests; no real API keys, billing, network or PC actions."""
from __future__ import annotations

from datetime import date
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import gemini_chat as gm


class GeminiProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = gm.GeminiStore(self.tmp.name)
        self.key = "AIzaDummyKeyForOfflineUnitTests1234567890"
        self.crypt = patch.object(gm, "_protect", side_effect=lambda v: b"DPAPI-ENCRYPTED:" + v[::-1])
        self.uncrypt = patch.object(gm, "_unprotect", side_effect=lambda v: v.split(b":", 1)[1][::-1])
        self.crypt.start()
        self.uncrypt.start()
        self.addCleanup(self.crypt.stop)
        self.addCleanup(self.uncrypt.stop)

    def test_key_is_encrypted_at_rest_and_removable(self):
        self.store.save_key(self.key)
        self.assertTrue(self.store.configured())
        disk = self.store.secret.read_bytes()
        self.assertNotIn(self.key.encode(), disk)
        self.assertEqual(self.store.get_key(), self.key)
        self.store.delete_key()
        self.assertFalse(self.store.configured())
        with self.assertRaises(gm.GeminiError):
            self.store.get_key()

    def test_key_never_saved_if_not_protected(self):
        with patch.object(gm, "_protect", side_effect=gm.GeminiError("DPAPI unavailable")):
            with self.assertRaisesRegex(gm.GeminiError, "DPAPI"):
                self.store.save_key(self.key)
        self.assertFalse(self.store.secret.exists())

    def test_invalid_keys_and_models_are_rejected(self):
        for value in ("", "short", "API KEY WITH SPACES", "a" * 300, "bad\nkey"):
            with self.subTest(value=value[:8]), self.assertRaises(gm.GeminiError):
                self.store.save_key(value)
        self.assertEqual(self.store.model(), gm.DEFAULT_MODEL)
        with self.assertRaises(gm.GeminiError):
            self.store.set_model("gemini-paid-model")
        self.store.set_model("gemini-3.1-flash-lite")
        self.assertEqual(self.store.model(), "gemini-3.1-flash-lite")

    def test_usage_guard_limits_locally_without_starting_cloud_billing(self):
        self.assertEqual(self.store.consume_request(), 1)
        for _ in range(gm.DAILY_REQUEST_LIMIT - 1):
            self.store.consume_request()
        with self.assertRaisesRegex(gm.GeminiError, "30 daily"):
            self.store.consume_request()
        self.assertEqual(json.loads(self.store.usage.read_text())["used"], 30)

    def test_payload_is_text_only_bounded_and_separates_system_instructions(self):
        data = json.loads(gm._payload("Jarvis apna intro do", [
            {"role": "user", "content": "Salam"},
            {"role": "assistant", "content": "Walaikum salam"},
        ]))
        self.assertEqual(data["contents"][0]["role"], "user")
        self.assertEqual(data["contents"][1]["role"], "model")
        self.assertEqual(data["contents"][-1]["parts"][0]["text"], "Jarvis apna intro do")
        self.assertNotIn("tools", data)
        self.assertNotIn("function_call", json.dumps(data))
        self.assertIn("TEXT CHAT ONLY", data["system_instruction"]["parts"][0]["text"])
        for bad in ("", "x" * 4001):
            with self.assertRaises(gm.GeminiError):
                gm._payload(bad, [])

    def _response(self, value=None):
        reply = Mock()
        reply.read.return_value = json.dumps(value or {
            "candidates": [{"content": {"parts": [{"text": "Walaikum salam!"}]}}]
        }).encode()
        reply.__enter__ = Mock(return_value=reply)
        reply.__exit__ = Mock(return_value=None)
        return reply

    def test_request_goes_only_to_fixed_google_endpoint_with_header_key(self):
        self.store.save_key(self.key)
        reply = self._response()
        with patch.object(gm, "urlopen", return_value=reply) as opened:
            response = gm.GeminiClient(self.store).ask("Salam", [])
        self.assertEqual(response, "Walaikum salam!")
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url,
                         gm.API_URL + gm.DEFAULT_MODEL + ":generateContent")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-goog-api-key"), self.key)
        self.assertNotIn(self.key, request.full_url)
        self.assertNotIn(self.key.encode(), request.data)
        self.assertEqual(opened.call_args.kwargs["timeout"], 22)

    def test_no_key_means_no_network_or_usage(self):
        with patch.object(gm, "urlopen") as opened:
            with self.assertRaisesRegex(gm.GeminiError, "key missing"):
                gm.GeminiClient(self.store).ask("Salam")
        opened.assert_not_called()
        self.assertFalse(self.store.usage.exists())

    def test_stop_prevents_send_and_discards_finished_response(self):
        self.store.save_key(self.key)
        stop = threading.Event()
        stop.set()
        with patch.object(gm, "urlopen") as opened, self.assertRaisesRegex(gm.GeminiError, "Stopped"):
            gm.GeminiClient(self.store).ask("Salam", stop=stop)
        opened.assert_not_called()
        stop.clear()
        response = self._response()
        def stop_during_request(*_args, **_kwargs):
            stop.set()
            return response
        with patch.object(gm, "urlopen", side_effect=stop_during_request):
            with self.assertRaisesRegex(gm.GeminiError, "discard"):
                gm.GeminiClient(self.store).ask("Salam", stop=stop)

    def test_safe_http_errors_never_print_key_or_provider_body(self):
        self.store.save_key(self.key)
        for status, expected in ((403, "permission"), (404, "model"),
                                 (429, "rate limit"), (400, "request")):
            with self.subTest(status=status):
                http = HTTPError("https://example.invalid", status, 
                                 "SECRET " + self.key, {}, BytesIO(b"bad"))
                with patch.object(gm, "urlopen", side_effect=http):
                    with self.assertRaises(gm.GeminiError) as raised:
                        gm.GeminiClient(self.store).ask("Salam")
                self.assertIn(expected, str(raised.exception))
                self.assertNotIn(self.key, str(raised.exception))

    def test_invalid_json_and_network_failures_do_not_expose_credentials(self):
        self.store.save_key(self.key)
        with patch.object(gm, "urlopen", side_effect=URLError("SECRET " + self.key)):
            with self.assertRaises(gm.GeminiError) as raised:
                gm.GeminiClient(self.store).ask("Salam")
        self.assertNotIn(self.key, str(raised.exception))
        with patch.object(gm, "urlopen", return_value=self._response({"candidates": []})):
            with self.assertRaisesRegex(gm.GeminiError, "valid text"):
                gm.GeminiClient(self.store).ask("Salam")


if __name__ == "__main__":
    unittest.main()
