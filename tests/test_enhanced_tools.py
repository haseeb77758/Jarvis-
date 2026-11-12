"""Offline tests for the optional Stonic-inspired HASEEB AI toolkit."""
from __future__ import annotations

import base64
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enhanced_tools import (
    IMAGE_API_URL, IMAGE_MODEL, ScheduleStore, generate_cloud_image,
    read_code_for_review, system_action, weather_search_url,
)
from tools.package_source import source_files
from tools.update_windows import LOCAL_TESTS, REQUIRED


class EnhancedToolkitTests(unittest.TestCase):
    def test_weather_uses_browser_search_not_fake_api(self):
        self.assertEqual(weather_search_url("Rawalpindi"),
                         "https://www.google.com/search?q=weather+Rawalpindi")
        for value in ("", "x" * 81, "Rawalpindi\nunsafe"):
            with self.assertRaises(ValueError):
                weather_search_url(value)

    def test_schedule_is_local_sorted_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ScheduleStore(folder)
            self.assertEqual(store.list_items(), [])
            store.add("2026-12-12", "10:20", "Second meeting")
            store.add("2026-11-13", "09:00", "First project")
            entries = ScheduleStore(folder).list_items()
            self.assertEqual([x["title"] for x in entries], ["First project", "Second meeting"])
            self.assertEqual(store.delete(0)["title"], "First project")
            self.assertEqual(len(ScheduleStore(folder).list_items()), 1)
            with self.assertRaisesRegex(ValueError, "pehle"):
                store.add("2026-12-12", "10:20", "Second meeting")

    def test_schedule_input_rejects_invalid_dates_and_titles(self):
        for item in (
            ("2026-02-30", "13:00", "Impossible date"),
            ("2026-12-01", "25:00", "Impossible hour"),
            ("2026-12-01", "08:20", "Newline\nunsafe"),
            ("2026-12-01", "08:20", "x" * 130),
        ):
            with self.subTest(item=item), self.assertRaises(ValueError):
                ScheduleStore.verify(*item)

    def test_schedule_refuses_symlink_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            target = base / "other.csv"
            target.write_text("untouched", encoding="utf-8")
            link = base / "schedule.csv"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                return
            with self.assertRaises(ValueError):
                ScheduleStore(base).add("2026-12-12", "12:00", "Test")
            self.assertEqual(target.read_text(), "untouched")

    def test_code_review_requires_explicit_small_code_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "demo.py"
            p.write_text("print('hello')", encoding="utf-8")
            self.assertEqual(read_code_for_review(p), "print('hello')")
            key = Path(folder) / "secrets.env"
            key.write_text("PRIVATE_KEY=test", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_code_for_review(key)
            p.write_text("z" * 25001, encoding="utf-8")
            with self.assertRaises(ValueError):
                read_code_for_review(p)

    def test_system_commands_allowlisted_and_never_shell(self):
        with self.assertRaises(ValueError):
            system_action("delete")
        with self.assertRaises(ValueError):
            system_action("format")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            exe = root / "System32" / "shutdown.exe"
            exe.parent.mkdir(parents=True)
            exe.touch()
            with patch("enhanced_tools.os.name", "nt"), patch.dict(
                "os.environ", {"WINDIR": str(root)}
            ), patch("enhanced_tools.subprocess.Popen") as popen:
                result = system_action("shutdown")
                self.assertIn("60 seconds", result)
                popen.assert_called_once_with([str(exe), "/s", "/t", "60"], shell=False)

    def test_image_generation_fixed_https_and_not_in_sandbox(self):
        with tempfile.TemporaryDirectory() as folder:
            fake_png = b"\x89PNG\r\n\x1a\n" + b"1" * 110
            payload = {"data": [{"b64_json": base64.b64encode(fake_png).decode()}]}
            opener = Mock()
            response = Mock()
            response.__enter__ = Mock(return_value=BytesIO(json.dumps(payload).encode()))
            response.__exit__ = Mock(return_value=False)
            opener.open.return_value = response
            file = generate_cloud_image("An original illustrated sun", "sk-valid-example-key", folder, opener)
            self.assertTrue(file.is_file())
            self.assertEqual(file.read_bytes(), fake_png)
            req = opener.open.call_args.args[0]
            self.assertEqual(req.full_url, IMAGE_API_URL)
            self.assertEqual(req.get_method(), "POST")
            self.assertTrue(IMAGE_API_URL.startswith("https://api.openai.com/"))
            self.assertEqual(json.loads(req.data)["model"], IMAGE_MODEL)
            self.assertTrue(req.get_header("Authorization").startswith("Bearer "))
            self.assertEqual(len(list(Path(folder).glob("*.png"))), 1)

    def test_image_api_errors_do_not_save_files(self):
        with tempfile.TemporaryDirectory() as folder:
            opener = Mock()
            opener.open.side_effect = ConnectionError("no network")
            with self.assertRaisesRegex(RuntimeError, "Image generate nahi"):
                generate_cloud_image("An original diagram", "sk-valid-example-key", folder, opener)
            self.assertEqual(list(Path(folder).glob("*.png")), [])
            with self.assertRaises(ValueError):
                generate_cloud_image("x", "short", folder, opener)
            opener.open.assert_called_once()

    def test_updater_and_source_package_include_new_toolkit(self):
        items = [p.as_posix() for p in source_files()]
        for filename in ("enhanced_ui.py", "enhanced_tools.py"):
            self.assertIn(filename, items)
            self.assertIn(filename, REQUIRED)
        self.assertIn("test_enhanced_tools.py", LOCAL_TESTS)


if __name__ == "__main__":
    unittest.main()
