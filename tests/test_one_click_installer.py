"""Safe Windows installer tests: never install dependencies or touch host shortcuts."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jarvis_installer", ROOT / "tools" / "install_windows.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class OneClickInstallerTests(unittest.TestCase):
    def test_no_files_copied_when_user_declines(self):
        with patch.object(installer.os, "name", "nt"), \
             patch.object(installer.sys, "version_info", (3, 12)), \
             patch.object(installer, "target_directory", return_value=Path("C:/Temp/Jarvis")), \
             patch("builtins.input", return_value="NO"), \
             patch.object(installer, "copy_source") as copier:
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                installer.install()
            copier.assert_not_called()

    def test_source_copy_only_allowlisted_items(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "JarvisApp"
            copied = installer.copy_source(destination)
            self.assertGreater(copied, 10)
            self.assertTrue((destination / "app.py").is_file())
            self.assertTrue((destination / "dashboard.py").is_file())
            self.assertTrue((destination / "INSTALL-JARVIS.cmd").is_file())
            self.assertFalse((destination / "Jarvis.exe").exists())
            self.assertFalse((destination / ".env").exists())

    def test_local_runtime_test_selection_does_not_run_store_or_release_audits(self):
        patterns = installer.LOCAL_RUNTIME_TESTS
        self.assertIn("test_core.py", patterns)
        self.assertIn("test_desktop_voice_memory.py", patterns)
        self.assertTrue(all("store" not in item for item in patterns))
        self.assertTrue(all("source_package" not in item for item in patterns))
        self.assertTrue(all("one_click_installer" not in item for item in patterns))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            for name in patterns:
                (root / "tests" / name).write_text("import unittest\\n", encoding="utf-8")
            with patch.object(installer, "run") as runner:
                installer.run_local_tests(Path("python.exe"), root)
            self.assertEqual(runner.call_count, len(patterns))
            for call in runner.call_args_list:
                self.assertEqual(call.args[0:6], ("python.exe", "-m", "unittest", "discover", "-s", "tests"))
                self.assertIn(call.args[7], patterns)

    def test_missing_runtime_test_fails_without_creating_shortcuts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            with patch.object(installer, "run") as runner:
                with self.assertRaises(FileNotFoundError):
                    installer.run_local_tests(Path("python.exe"), root)
                runner.assert_not_called()

    def test_shortcuts_created_by_venv_python_not_installer_python(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "JarvisApp"
            (destination / "tools").mkdir(parents=True)
            (destination / "tools" / "create_shortcuts.py").write_text("# helper", encoding="utf-8")
            scripts = destination / ".venv" / "Scripts"
            scripts.mkdir(parents=True)
            (scripts / "pythonw.exe").write_bytes(b"test stub")
            desktop = Path(directory) / "desktop"
            programs = Path(directory) / "programs"
            with patch.object(installer, "run") as run:
                def create_fakes(*_args, **_kwargs):
                    desktop.mkdir(exist_ok=True)
                    programs.mkdir(exist_ok=True)
                    (desktop / (installer.APP_NAME + ".lnk")).write_bytes(b"test fake")
                    (programs / (installer.APP_NAME + ".lnk")).write_bytes(b"test fake")
                run.side_effect = create_fakes
                result = installer.create_shortcuts(destination, scripts / "python.exe", desktop, programs)
            self.assertEqual(len(result), 2)
            invoked = run.call_args.args
            self.assertEqual(invoked[0], str(scripts / "python.exe"))
            self.assertEqual(invoked[1], str(destination / "tools" / "create_shortcuts.py"))
            self.assertEqual(invoked[2], str(destination))
            self.assertEqual(invoked[3], str(scripts / "pythonw.exe"))

    def test_runtime_uses_virtual_environment_not_unsigned_exe(self):
        path = Path("C:/Jarvis")
        self.assertEqual(installer.installed_python(path), path / ".venv" / "Scripts" / "python.exe")


if __name__ == "__main__":
    unittest.main()
