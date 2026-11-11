"""Produce a reviewable, executable-free Jarvis source ZIP for Windows 11.

This distribution does not alter Smart App Control, Defender, execution policy,
or Windows trust settings. It deliberately excludes local data, secrets, venvs,
and PyInstaller outputs.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FOLDER = "Jarvis-Source-Windows"
FILES = (
    "app.py", "core.py", "dashboard.py", "desktop.py", "memory.py", "voice.py",
    "RUN-JARVIS.py", "START-JARVIS.cmd", "INSTALL-JARVIS.cmd", "SETUP.bat", "START.bat",
    "SETUP-LOCAL-AI.bat", "requirements.txt", "README.md",
    "README-ROMAN-URDU.md", "DESKTOP-FIRST.md", "SMART-APP-CONTROL.md",
)
PATTERNS = ("tests/test_*.py", "tools/*.py", "tools/*.ps1",
            "web/*.html", "web/*.css", "web/*.js")


def source_files(root: Path = ROOT) -> list[Path]:
    """Strict allowlist; never package .env, git history, local files or binaries."""
    found: set[Path] = {Path(name) for name in FILES}
    for pattern in PATTERNS:
        found.update(p.relative_to(root) for p in root.glob(pattern))
    if not found:
        raise RuntimeError("No source files found.")
    ordered = sorted(found, key=lambda item: item.as_posix())
    for relative in ordered:
        path = root / relative
        if (relative.is_absolute() or ".." in relative.parts or
                path.is_symlink() or not path.is_file() or
                not path.resolve().is_relative_to(root.resolve())):
            raise ValueError("Invalid package entry: " + str(relative))
    return ordered


def make_zip(destination: Path, root: Path = ROOT) -> Path:
    destination = Path(destination)
    files = source_files(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = [
        "JARVIS — HASEEB AI  |  Reviewable Windows Python source",
        "This manifest checks contents, not publisher identity or malware safety.",
        "These files do not include Jarvis.exe. Do not disable Smart App Control.",
        "Official Python required: https://www.python.org/downloads/windows/",
        "First step: README-START-HERE.txt, then py -3 RUN-JARVIS.py",
        "",
        "SHA256   RELATIVE PATH",
    ]
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for item in files:
            data = (root / item).read_bytes()
            archive.writestr(f"{FOLDER}/{item.as_posix()}", data)
            manifest.append(f"{hashlib.sha256(data).hexdigest()}   {item.as_posix()}")
        help_text = (
            "HASEEB AI / JARVIS — SOURCE EDITION FOR WINDOWS 11\n\n"
            "1. This package contains source files, not an unsigned Jarvis.exe.\n"
            "2. Extract the complete ZIP into a normal folder.\n"
            "3. Install official Python 3.10+ with tkinter from:\n"
            "   https://www.python.org/downloads/windows/\n"
            "4. Open Terminal in the extracted Jarvis-Source-Windows folder.\n"
            "5. Run: py -3 RUN-JARVIS.py --check\n"
            "6. Run: py -3 RUN-JARVIS.py\n"
            "7. Type YES only if you approve installing the dependencies listed\n"
            "   in requirements.txt. The launcher runs tests before starting Jarvis.\n"
            "8. Later, use the same command, or START-JARVIS.cmd if allowed.\n\n"
            "IMPORTANT: Running Python source does not guarantee that Windows\n"
            "security policy will permit all components. Do not disable system\n"
            "protections. Do not run Jarvis as Administrator.\n"
            "For errors and publisher signing, read SMART-APP-CONTROL.md.\n"
        )
        archive.writestr(f"{FOLDER}/README-START-HERE.txt", help_text)
        archive.writestr(f"{FOLDER}/PACKAGE-MANIFEST.txt", "\n".join(manifest) + "\n")
    print(f"Created {destination}: {len(files)} allowlisted source files.")
    print(f"Archive SHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "Jarvis-Source-Windows.zip")
    arguments = parser.parse_args()
    make_zip(arguments.output)
