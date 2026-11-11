"""Offline regression tests for optional GitHub Jarvis source updates."""
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools import update_windows as u


def fake_zip(override=None, extra=None):
    files = {name: b"# validated source\n" for name in u.REQUIRED}
    files["requirements.txt"] = b"# requirements\n"
    files.update(override or {})
    files.update(extra or {})
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as z:
        for path, contents in files.items():
            z.writestr("Jarvis-abcdef123/" + path, contents)
    return buffer.getvalue()


def _incomplete_zip():
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("Jarvis-abc/app.py", "only one file")
    return buffer.getvalue()


def _incomplete_zip():
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("Jarvis-abc/app.py", "only one file")
    return buffer.getvalue()


class UpdateTests(unittest.TestCase):
    def test_archive_allowlist_prevents_code_outside_owned_source(self):
        data = fake_zip(extra={
            "secrets/password.txt": b"do not copy",
            "random.exe": b"EXE",
            ".env": b"TOKEN=hidden",
            "assets/private.json": b"secret",
        })
        files = u.snapshot_sources(data)
        self.assertIn("app.py", files)
        for name in ("secrets/password.txt", "random.exe", ".env", "assets/private.json"):
            self.assertNotIn(name, files)

    def test_missing_required_files_are_rejected(self):
        with self.assertRaisesRegex(u.UpdateError, "Incomplete"):
            u.snapshot_sources(_incomplete_zip())

    def test_zip_traversal_or_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = fake_zip(extra={"tools/../../app.py": b"bad"})
            with self.assertRaises(u.UpdateError):
                u.snapshot_sources(archive)

    def test_windows_path_separator_and_device_name_rejected(self):
        # Windows ZIP writer normalizes backslashes to forward slashes before
        # archiving, so check raw untrusted names in the pathname validator.
        for value in (r"tools\..\app.py", r"tools\file.py", "CON.py", "tools/COM1.py"):
            with self.subTest(value=value):
                if chr(92) in value:
                    self.assertFalse(u._safe_source_path(PurePosixPath(value)))
                else:
                    self.assertNotIn(value, u.snapshot_sources(fake_zip(extra={value: b"malicious"})))

    def test_commit_version_saved_and_compared(self):
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(u.installed_commit(root))
            u._write_version(root, sha)
            self.assertEqual(u.installed_commit(root), sha)
            with patch.object(u, "latest_commit", return_value=sha):
                self.assertEqual(u.check_update(root), (sha, False))
            with patch.object(u, "latest_commit", return_value="b"*40):
                self.assertEqual(u.check_update(root), ("b"*40, True))

    def test_update_requires_a_valid_commit_and_installed_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(u.UpdateError, "Invalid"):
                u.install_update(root, "main", archive=fake_zip())
            with self.assertRaisesRegex(u.UpdateError, "environment missing"):
                u.install_update(root, "a"*40, archive=fake_zip())

    def test_successful_reviewed_install_preserves_user_memory(self):
        sha = "b"*40
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"fake python")
            prefs = root / "preferences.json"
            prefs.write_text("private user saved data", encoding="utf-8")
            previous = root / "app.py"
            previous.write_text("previous local app", encoding="utf-8")
            result = u.install_update(root, sha,
                                      archive=fake_zip({"app.py": b"new app"}), run_checks=False)
            self.assertEqual(previous.read_bytes(), b"new app")
            self.assertEqual(prefs.read_text(encoding="utf-8"), "private user saved data")
            self.assertIn("Restart", result)
            self.assertEqual(u.installed_commit(root), sha)

    def test_rollback_restores_old_application_if_state_write_fails(self):
        sha = "c"*40
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = root / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"fake python")
            old = root / "app.py"
            old.write_bytes(b"original app")
            with patch.object(u, "_write_version", side_effect=u.UpdateError("simulated disk failure")):
                with self.assertRaisesRegex(u.UpdateError, "simulated"):
                    u.install_update(root, sha, archive=fake_zip({"app.py": b"replacement app"}),
                                     run_checks=False)
            self.assertEqual(old.read_bytes(), b"original app")
            self.assertIsNone(u.installed_commit(root))


if __name__ == "__main__":
    unittest.main()
