"""Python GUI source setup tests — no packages or shortcuts are installed."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jarvis_gui_installer", ROOT / "START-JARVIS-GUI.pyw")
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


class GUISetupTests(unittest.TestCase):
    def test_pythonw_prefers_python_console_subprocess(self):
        with patch.object(gui.sys, "executable", "C:/Python312/pythonw.exe"):
            self.assertEqual(gui.official_python_binary().name, "python.exe")
        with patch.object(gui.sys, "executable", "C:/Python312/python.exe"):
            self.assertEqual(gui.official_python_binary().name, "python.exe")

    def test_executable_shell_execution_not_used(self):
        with patch.object(gui, "ROOT", Path("C:/Jarvis")):
            self.assertFalse(hasattr(gui, "disable_smart_app_control"))
        source = (ROOT / "START-JARVIS-GUI.pyw").read_text(encoding="utf-8")
        self.assertIn("shell=False", source)
        self.assertNotIn("Set-MpPreference", source)
        self.assertNotIn("Unblock-File", source)
        self.assertNotIn("Set-ExecutionPolicy", source)
        self.assertIn("self.agreed.get()", source)

    def test_gui_entrypoint_does_not_require_unsigned_exe(self):
        source = (ROOT / "START-JARVIS-GUI.pyw").read_text(encoding="utf-8")
        self.assertIn('tools" / "install_windows.py', source)
        self.assertNotIn('"Jarvis.exe"', source)


if __name__ == "__main__":
    unittest.main()
