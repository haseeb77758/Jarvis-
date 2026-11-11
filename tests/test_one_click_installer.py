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

    def test_runtime_uses_virtual_environment_not_unsigned_exe(self):
        path = Path("C:/Jarvis")
        self.assertEqual(installer.installed_python(path), path / ".venv" / "Scripts" / "python.exe")


if __name__ == "__main__":
    unittest.main()
