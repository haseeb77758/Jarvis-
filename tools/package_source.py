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
    "app.py", "account_chat.py", "adaptive_capture.py", "roman_urdu_speech.py", "free_voice.py", "cloud_voice.py", "voice_settings_ui.py", "diagnostics.py", "chat_ui.py", "sandbox_chat.py", "core.py", "dashboard.py", "desktop.py", "memory.py", "voice.py",
    "enhanced_tools.py", "enhanced_ui.py", "livekit_bridge.py", "livekit_window.py", "direct_livekit.py",
    "livekit_agent.py", "livekit_requirements.txt",
    "RUN-JARVIS.py", "START-JARVIS-GUI.pyw", "START-JARVIS.cmd", "INSTALL-JARVIS.cmd", "SETUP.bat", "START.bat",
    "requirements.txt", "README.md", "ACCOUNT-CHAT.md",
    "README-ROMAN-URDU.md", "ELEVENLABS-VOICE.md", "FREE-VOICES.md", "LIVEKIT-VOICE.md", "LIVEKIT-DIRECT-DESKTOP.md",
    "EDGE-TTS-LICENSE.txt", "GPL-3.0.txt", "THIRD-PARTY-NOTICES.txt", "DESKTOP-FIRST.md", "SMART-APP-CONTROL.md",
    "UPDATE-JARVIS-NO-CODE.md", "JARVIS-TOOLKIT.md",
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
        "First step: README-START-HERE.txt, then open START-JARVIS-GUI.pyw using official Python 3.12",
        "",
        "SHA256   RELATIVE PATH",
    ]
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for item in files:
            data = (root / item).read_bytes()
            archive.writestr(f"{FOLDER}/{item.as_posix()}", data)
            manifest.append(f"{hashlib.sha256(data).hexdigest()}   {item.as_posix()}")
        help_text = (
            "HASEEB AI / JARVIS — WINDOWS 11 PYTHON GUI SETUP\n\n"
            "1. Extract the complete ZIP (do not launch files inside the ZIP).\n"
            "2. Open the Jarvis-Source-Windows folder.\n"
            "3. Install official Python 3.12 (including tkinter).\n"
            "4. Double-click START-JARVIS-GUI.pyw in the extracted folder.\n"
            "   Select Python if Windows asks which application should open it.\n"
            "5. Tick the install-permission box, then click INSTALL & OPEN JARVIS.\n"
            "6. After setup, use HASEEB AI - Jarvis on your Desktop.\n"
            "7. In LiveKit setup, save local project URL/API keys once, then Talk Live opens direct Jarvis WebRTC.\n\n"
            "IMPORTANT: This GUI setup does NOT disable Windows\n"
            "Smart App Control or Defender, and contains no unsigned Jarvis.exe.\n"
            "Windows policies may still block a component or installation.\n"
            "Never disable protections or run as Administrator to force it.\n"
            "Read SMART-APP-CONTROL.md if your PC refuses the installation.\n"
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

