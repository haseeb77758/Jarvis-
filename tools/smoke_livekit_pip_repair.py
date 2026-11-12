"""Actual Windows smoke test: repair a Python venv created WITHOUT pip.

Runs only in CI; no LiveKit Cloud requests, project credentials or paid inference.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

import livekit_bridge as lk


def main():
    with tempfile.TemporaryDirectory(prefix="jarvis-pip-repair-") as folder:
        root = Path(folder)
        venv = root / ".venv"
        subprocess.run(
            [sys.executable, "-m", "venv", "--without-pip", str(venv)],
            check=True, timeout=180, capture_output=True,
        )
        python = venv / "Scripts" / "python.exe"
        assert python.is_file(), "Fresh Windows venv has no Python executable"
        before = subprocess.run(
            [str(python), "-m", "pip", "--version"],
            timeout=35, capture_output=True,
        )
        assert before.returncode != 0, "Test setup error: venv unexpectedly has pip"
        assert b"No module named pip" in before.stderr, before.stderr[-1500:]
        with patch.object(lk, "app_data_root", return_value=root):
            changed = lk.ensure_venv_pip(python=python, root=root)
            assert changed, "Missing pip was not repaired"
            after = subprocess.run(
                [str(python), "-m", "pip", "--version"],
                timeout=35, capture_output=True,
            )
            assert after.returncode == 0, after.stderr[-1500:]
            assert b"pip" in after.stdout.lower(), after.stdout[-1500:]
            assert lk.ensure_venv_pip(python=python, root=root) is False, (
                "Healthy pip incorrectly requires a reinstall"
            )
            print("PASS: Windows LiveKit venv missing pip repaired via ensurepip")
            print(after.stdout.decode("utf-8", "replace").strip())


if __name__ == "__main__":
    main()
