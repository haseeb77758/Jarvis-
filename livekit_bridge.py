"""Windows-only, opt-in LiveKit voice console controller for Jarvis.

It never imports LiveKit into the regular app, starts cloud work automatically,
or puts credentials into Git, the UI log, or the source distribution.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ENV_KEYS = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")


class LiveKitSetupError(RuntimeError):
    pass


def app_data_root():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise LiveKitSetupError("Windows LOCALAPPDATA folder nahi mila.")
    return Path(base) / "HaseebCrafts" / "Jarvis" / "LiveKitVoice"


def credentials_path():
    return app_data_root() / ".env.local"


def environment_python():
    return app_data_root() / ".venv" / "Scripts" / "python.exe"


def package_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def agent_path():
    return package_root() / "livekit_agent.py"


def dependencies_path():
    return package_root() / "livekit_requirements.txt"


def create_credentials_template():
    """Create a private, blank file; never overwrite existing credentials."""
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("x", encoding="utf-8") as out:
            for key in ENV_KEYS:
                out.write(key + "=\n")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path


def configured():
    """Only check nonempty fields. Never disclose values or attempt a login."""
    path = credentials_path()
    try:
        if not path.is_file() or path.stat().st_size > 8192:
            return False
        entries = {}
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            clean = line.strip()
            if clean.startswith("#") or "=" not in clean:
                continue
            key, val = clean.split("=", 1)
            key, val = key.strip(), val.strip().strip("'\"")
            if key in ENV_KEYS:
                entries[key] = val
        return all(entries.get(key) for key in ENV_KEYS)
    except (OSError, UnicodeError):
        return False


def python_command():
    """Return an explicitly identified Python runtime, never Jarvis.exe."""
    if not getattr(sys, "frozen", False):
        path = Path(sys.executable)
        if path.name.lower() in ("python.exe", "pythonw.exe"):
            candidate = path.with_name("python.exe")
            if candidate.is_file():
                return [str(candidate)]
    py = shutil.which("py")
    if py and os.name == "nt":
        return [py, "-3.12"]
    python = shutil.which("python")
    if python and not getattr(sys, "frozen", False):
        return [python]
    raise LiveKitSetupError(
        "Python 3.12 missing hai. Official Python 3.12 install karke dobara try karein."
    )


def install_optional():
    """Explicit opt-in only: install separate dependencies, not regular Jarvis deps."""
    if os.name != "nt":
        raise LiveKitSetupError("LiveKit desktop setup abhi Windows 11 ke liye hai.")
    if not agent_path().is_file() or not dependencies_path().is_file():
        raise LiveKitSetupError("Jarvis LiveKit files missing hain. Jarvis update karein.")
    root = app_data_root()
    root.mkdir(parents=True, exist_ok=True)
    python = environment_python()
    if not python.is_file():
        command = python_command() + ["-m", "venv", str(root / ".venv")]
        try:
            subprocess.run(command, check=True, cwd=str(root), capture_output=True, timeout=180)
        except (OSError, subprocess.SubprocessError) as exc:
            raise LiveKitSetupError("LiveKit ke liye isolated Python environment nahi bana.") from None
    try:
        subprocess.run(
            [str(python), "-m", "pip", "--disable-pip-version-check", "install",
             "--no-input", "-r", str(dependencies_path())],
            check=True, cwd=str(root), capture_output=True, timeout=360,
        )
        # Download only the agent's declared noise processing model files.
        subprocess.run(
            [str(python), str(agent_path()), "download-files"],
            check=True, cwd=str(package_root()),
            capture_output=True, timeout=360,
        )
    except (OSError, subprocess.SubprocessError):
        raise LiveKitSetupError(
            "LiveKit dependencies/model download nahi hui. Internet aur available disk space check karein."
        ) from None
    return "LiveKit voice environment installed. Credentials locally set karna baqi hai."


class LiveKitConsole:
    def __init__(self):
        self.process = None
        self.started_at = None
        self.max_minutes = None
        self._stop_timer = None

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def start(self, *, consent=False, noise_enhancement=False, max_minutes=10):
        """Start a separate console only with explicit cost consent."""
        if not consent:
            raise LiveKitSetupError("LiveKit cloud-usage consent required hai.")
        if type(max_minutes) is not int or max_minutes not in (5, 10, 15):
            raise LiveKitSetupError("Voice safety limit 5, 10 ya 15 minutes hona chahiye.")
        if os.name != "nt":
            raise LiveKitSetupError("Windows console mode only.")
        if self.is_running():
            raise LiveKitSetupError("LiveKit voice already running hai.")
        if not configured():
            raise LiveKitSetupError(
                "LiveKit URL, API key aur secret local credentials file mein enter karein."
            )
        python, agent = environment_python(), agent_path()
        if not python.is_file():
            raise LiveKitSetupError("Pehle Install LiveKit Voice dabayein.")
        if not agent.is_file():
            raise LiveKitSetupError("LiveKit agent file missing. Jarvis update karein.")
        environment = os.environ.copy()
        environment["JARVIS_LIVEKIT_ENV_FILE"] = str(credentials_path())
        environment["JARVIS_LIVEKIT_AI_COUSTICS"] = "1" if noise_enhancement else "0"
        # Never embed API credentials in command line arguments.
        self.process = subprocess.Popen(
            [str(python), str(agent), "console"],
            cwd=str(agent.parent),
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            close_fds=True,
        )
        self.started_at = time.monotonic()
        self.max_minutes = max_minutes
        # Hard local runtime cap even if the Tk dashboard is hidden or stalled.
        # This caps session duration, not the provider's monetary charges.
        self._stop_timer = threading.Timer(max_minutes * 60, self.stop)
        self._stop_timer.daemon = True
        self._stop_timer.start()
        return self.process

    def remaining_seconds(self):
        if not self.is_running() or self.started_at is None or self.max_minutes is None:
            return 0
        return max(0, int(self.max_minutes * 60 - (time.monotonic() - self.started_at)))

    def stop(self):
        timer = self._stop_timer
        self._stop_timer = None
        if timer is not None:
            timer.cancel()
        process = self.process
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    # A stalled console must not keep cloud audio billed.
                    process.kill()
                    process.wait(timeout=4)
        except (OSError, subprocess.TimeoutExpired):
            # The process may have exited between poll and terminate.
            pass
        finally:
            self.process = None
            self.started_at = None
            self.max_minutes = None
