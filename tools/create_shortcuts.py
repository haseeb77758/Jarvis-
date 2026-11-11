"""Create Jarvis Desktop and Start Menu shortcuts with the *installed venv*.

This script must run via .venv/Scripts/python.exe because win32com is installed
inside that environment, not necessarily in the Python install manager runtime.
No administrator privileges or Windows Security changes are required.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


APP_NAME = "HASEEB AI - Jarvis"


def create_shortcuts(
    destination: Path,
    pythonw: Path,
    desktop: Path | None = None,
    programs: Path | None = None,
) -> list[Path]:
    if os.name != "nt":
        raise RuntimeError("Windows shortcuts require Windows.")
    import win32com.client
    from win32com.shell import shell, shellcon

    destination = destination.resolve(strict=True)
    pythonw = pythonw.resolve(strict=True)
    script = destination / "app.py"
    if not script.is_file() or pythonw.name.lower() != "pythonw.exe":
        raise FileNotFoundError("Installed Jarvis script or Python GUI runtime is missing.")
    if desktop is None:
        desktop = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0))
    if programs is None:
        programs = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAMS, None, 0))
    paths = [desktop / (APP_NAME + ".lnk"), programs / (APP_NAME + ".lnk")]
    wsh = win32com.client.Dispatch("WScript.Shell")
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        shortcut = wsh.CreateShortcut(str(path))
        shortcut.TargetPath = str(pythonw)
        shortcut.Arguments = '"' + str(script) + '"'
        shortcut.WorkingDirectory = str(destination)
        shortcut.Description = "Haseeb AI - Windows desktop assistant (Python source edition)"
        shortcut.WindowStyle = 1
        shortcut.Save()
        if not path.is_file():
            raise RuntimeError("Windows did not create shortcut: " + str(path))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("pythonw", type=Path)
    parser.add_argument("--desktop", type=Path, help="Override for isolated Windows CI testing")
    parser.add_argument("--programs", type=Path, help="Override for isolated Windows CI testing")
    args = parser.parse_args()
    if (args.desktop is None) != (args.programs is None):
        parser.error("--desktop and --programs must be specified together")
    for path in create_shortcuts(args.destination, args.pythonw, args.desktop, args.programs):
        print("SHORTCUT: " + str(path))


if __name__ == "__main__":
    main()
