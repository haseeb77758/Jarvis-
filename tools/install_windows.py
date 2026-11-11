"""Install HASEEB AI to a stable per-user Windows folder; no administrator or EXE.

The installer uses only official Python, pip dependencies from requirements.txt,
and explicit user approval. It never modifies Smart App Control or Defender.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_source import source_files

APP_NAME = "HASEEB AI - Jarvis"

# These suites exercise desktop/voice/safety behavior. Store publishing, GitHub
# packaging and release tests require repository-only documents and CI files;
# those must stay in GitHub Actions, not block a user's local installation.
LOCAL_RUNTIME_TESTS = (
    "test_core.py",
    "test_desktop_voice_memory.py",
    "test_safety_regressions.py",
    "test_stonic_tools.py",
    "test_stonic_volume.py",
    "test_video_desktop_features.py",
)


def target_directory() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if os.name != "nt" or not local:
        raise RuntimeError("This installer requires a Windows user profile.")
    return Path(local) / "HaseebCrafts" / "JarvisApp"


def installed_python(root: Path) -> Path:
    return root / ".venv" / "Scripts" / "python.exe"


def run(*args: str, cwd: Path, capture: bool = False):
    return subprocess.run(args, cwd=str(cwd), check=True, shell=False,
                          text=True, capture_output=capture)


def copy_source(destination: Path) -> int:
    """Copy only allowlisted source files; never overwrite stored user memory."""
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for relative in source_files(ROOT):
        origin = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
        copied += 1
    return copied


def run_local_tests(python: Path, destination: Path) -> None:
    """Validate installed Jarvis runtime without unrelated Store/CI release tests."""
    for test_file in LOCAL_RUNTIME_TESTS:
        if not (destination / "tests" / test_file).is_file():
            raise FileNotFoundError("Required Jarvis runtime test missing: " + test_file)
        run(str(python), "-m", "unittest", "discover", "-s", "tests",
            "-p", test_file, "-v", cwd=destination)
    print("PASS: All local Jarvis runtime checks completed.")


def create_shortcuts(destination: Path, pythonw: Path) -> list[Path]:
    """Native Windows shortcuts using existing pywin32 dependency."""
    import win32com.client
    from win32com.shell import shell, shellcon

    desktop = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0))
    programs = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAMS, None, 0))
    programs.mkdir(parents=True, exist_ok=True)
    script = destination / "app.py"
    if not script.is_file() or not pythonw.is_file():
        raise FileNotFoundError("Required Jarvis source/runtime not found for shortcut.")
    paths = [desktop / (APP_NAME + ".lnk"), programs / (APP_NAME + ".lnk")]
    wsh = win32com.client.Dispatch("WScript.Shell")
    for path in paths:
        shortcut = wsh.CreateShortcut(str(path))
        shortcut.TargetPath = str(pythonw)
        shortcut.Arguments = '"' + str(script) + '"'
        shortcut.WorkingDirectory = str(destination)
        shortcut.Description = "Haseeb AI - Windows desktop assistant (Python source edition)"
        shortcut.WindowStyle = 1
        shortcut.Save()
    return paths


def install(agree: bool = False) -> Path:
    if os.name != "nt" or sys.version_info[:2] != (3, 12):
        raise RuntimeError("Official Python 3.12 on Windows is required.")
    destination = target_directory()
    print("Jarvis installation directory:", destination)
    print("Official source directory:", ROOT)
    print("This will install Python dependencies from requirements.txt into a local virtual environment.")
    print("Desktop and Start Menu shortcuts will be created; your existing local memory is not deleted.")
    print("No Windows security protection will be disabled or modified.")
    if not agree and input("Do you approve? Type YES: ").strip() != "YES":
        raise RuntimeError("Installation cancelled before copying or installing files.")

    count = copy_source(destination)
    print(f"Copied {count} reviewed source files.")
    python = installed_python(destination)
    if not python.is_file():
        run(sys.executable, "-m", "venv", str(destination / ".venv"), cwd=destination)
    run(str(python), "-m", "pip", "install", "-r", str(destination / "requirements.txt"), cwd=destination)
    print("Running Jarvis runtime tests before installing shortcuts (Store publishing tests stay in GitHub CI)...")
    run_local_tests(python, destination)
    # Check the application compiles before a shortcut could launch it.
    import compileall
    if not compileall.compile_file(str(destination / "app.py"), quiet=1):
        raise RuntimeError("Jarvis source compile check failed.")
    pythonw = python.with_name("pythonw.exe")
    shortcuts = create_shortcuts(destination, pythonw)
    for shortcut in shortcuts:
        print("Shortcut ready:", shortcut)
    print("INSTALLATION COMPLETE.")
    print("Use the HASEEB AI - Jarvis desktop shortcut to launch.")
    return destination


if __name__ == "__main__":
    try:
        install()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("INSTALLATION FAILED:", exc, file=sys.stderr)
        raise SystemExit(1) from exc
