"""Jarvis Windows source launcher. Does not disable or bypass Windows protections.

Usage: py -3 RUN-JARVIS.py [--check] [--setup]
Dependencies are installed only after an explicit interactive confirmation.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def python_ok() -> None:
    if os.name != "nt":
        raise SystemExit("Jarvis desktop needs Windows 11/10.")
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ required. Download from python.org.")
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:
        raise SystemExit("This Python installation lacks tkinter.") from exc


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True, shell=False)


def setup() -> None:
    if not VENV_PYTHON.is_file():
        run(sys.executable, "-m", "venv", str(ROOT / ".venv"))
    print("Installing Jarvis dependencies from requirements.txt using pip.")
    run(str(VENV_PYTHON), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt"))
    print("Running unit tests before first launch...")
    run(str(VENV_PYTHON), "-m", "unittest", "discover", "-s", "tests", "-v")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Jarvis from reviewed Python source.")
    parser.add_argument("--check", action="store_true", help="Check source prerequisites without installing or running.")
    parser.add_argument("--setup", action="store_true", help="Set up local environment after approval.")
    args = parser.parse_args()
    python_ok()
    if args.check:
        print("Python:", sys.version.split()[0])
        print("Source:", ROOT)
        print("Local environment:", "ready" if VENV_PYTHON.is_file() else "not installed")
        print("No applications started or system settings changed.")
        return
    if args.setup or not VENV_PYTHON.is_file():
        print("This will create a local Python environment and install third-party Python packages.")
        if input("Continue? Type YES: ").strip() != "YES":
            raise SystemExit("Cancelled. No dependencies installed.")
        setup()
    print("Starting Jarvis from local Python source...")
    run(str(VENV_PYTHON), str(ROOT / "app.py"))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit("Jarvis setup/launch failed at step: " + " ".join(map(str, exc.cmd)) + " (exit " + str(exc.returncode) + ")") from exc
