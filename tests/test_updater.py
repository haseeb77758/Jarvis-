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

    def test_legacy_updater_stages_complete_livekit_package(self):
        """Regression for previously shipped updater that rejects new directories.

        Windows users still run the OLD updater until a new snapshot is
        verified. It only accepts root-level .py/.txt files plus tools, tests
        and web. The old LiveKit layout passed GitHub CI but failed on the
        user's PC because livekit_voice/agent.py was filtered out.
        """
        from tools.package_source import ROOT, source_files

        # Reproduce the exact path-shape rules from the installed updater:
        # arbitrary new top-level directories are silently skipped.
        def accepted_by_old_updater(path):
            p = PurePosixPath(path)
            if len(p.parts) == 1:
                return p.suffix.lower() in {
                    '.py', '.pyw', '.md', '.txt', '.bat', '.cmd'
                } or p.name == 'requirements.txt'
            if len(p.parts) != 2:
                return False
            return ((p.parts[0] == 'tools' and p.suffix.lower() in {'.py', '.ps1'}) or
                    (p.parts[0] == 'tests' and p.name.startswith('test_') and p.suffix == '.py') or
                    (p.parts[0] == 'web' and p.suffix.lower() in {'.html', '.css', '.js'}))

        published = {p.as_posix(): (ROOT / p).read_bytes()
                     for p in source_files(ROOT)}
        # The repository may keep its original LiveKit training reference,
        # but user updates must not depend on that filtered directory.
        for name in ('livekit_voice/agent.py', 'livekit_voice/requirements.txt'):
            original = ROOT / name
            if original.is_file():
                published[name] = original.read_bytes()
        self.assertFalse(accepted_by_old_updater('livekit_voice/agent.py'))
        for required in ('livekit_agent.py', 'livekit_requirements.txt'):
            self.assertIn(required, published)
            self.assertTrue(accepted_by_old_updater(required))

        archived = io.BytesIO()
        with ZipFile(archived, 'w') as zipfile:
            for name, value in published.items():
                zipfile.writestr('Jarvis-legacy-check/' + name, value)
        with ZipFile(io.BytesIO(archived.getvalue())) as archive:
            legacy_files = {}
            for entry in archive.infolist():
                relative = '/'.join(PurePosixPath(entry.filename).parts[1:])
                if accepted_by_old_updater(relative):
                    legacy_files[relative] = archive.read(entry)

        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp) / 'stage'
            stage.mkdir()
            for name, value in legacy_files.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
            # This used to throw "Invalid package entry: livekit_voice\\agent.py".
            staged = {p.as_posix() for p in source_files(stage)}
            self.assertEqual(staged, {p.as_posix() for p in source_files(ROOT)})
            for required in ('livekit_agent.py', 'livekit_requirements.txt',
                             'livekit_bridge.py', 'livekit_window.py'):
                self.assertTrue((stage / required).is_file())

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
