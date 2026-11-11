"""Real Windows venv shortcut smoke test, using only temporary directories.

Validates the exact venv import and shortcut creation path that failed on the
user's laptop. No real Desktop/Start Menu shortcut or user data is touched.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("This smoke test must run on Windows.")
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="jarvis-shortcut-smoke-") as directory:
        folder = Path(directory)
        installed = folder / "JarvisApp"
        installed.mkdir()
        shutil.copy2(root / "app.py", installed / "app.py")
        (installed / "tools").mkdir()
        shutil.copy2(root / "tools" / "create_shortcuts.py", installed / "tools" / "create_shortcuts.py")
        subprocess.run([sys.executable, "-m", "venv", str(installed / ".venv")], check=True, shell=False)
        python = installed / ".venv" / "Scripts" / "python.exe"
        pythonw = installed / ".venv" / "Scripts" / "pythonw.exe"
        subprocess.run([str(python), "-m", "pip", "install", "pywin32>=306"], check=True, shell=False)
        subprocess.run([str(python), "-c", "import win32com.client; import win32com.shell"], check=True, shell=False)
        desktop = folder / "mock-desktop"
        programs = folder / "mock-start-menu"
        subprocess.run([
            str(python), str(installed / "tools" / "create_shortcuts.py"),
            str(installed), str(pythonw), "--desktop", str(desktop),
            "--programs", str(programs),
        ], check=True, shell=False)
        import win32com.client
        wsh = win32com.client.Dispatch("WScript.Shell")
        for shortcut in (desktop / "HASEEB AI - Jarvis.lnk",
                         programs / "HASEEB AI - Jarvis.lnk"):
            assert shortcut.is_file(), str(shortcut)
            link = wsh.CreateShortcut(str(shortcut))
            assert Path(link.TargetPath).resolve() == pythonw.resolve(), link.TargetPath
            assert Path(link.Arguments.strip('"')).resolve() == (installed / "app.py").resolve(), link.Arguments
            assert Path(link.WorkingDirectory).resolve() == installed.resolve(), link.WorkingDirectory
        print("PASS: actual installed venv imports win32com and creates valid Windows .lnk files in isolated directories")
