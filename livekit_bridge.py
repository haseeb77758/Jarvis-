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
from urllib.parse import urlsplit

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


def session_log_path():
    """Local-only diagnostic log, never included in GitHub source or updates."""
    return app_data_root() / "last-session.log"


def _redact_secrets(content):
    """Redact locally configured LiveKit URL/key/secret from human-readable logs."""
    try:
        path = credentials_path()
        if not path.is_file() or path.stat().st_size > 8192:
            return content
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            name, value = line.split("=", 1)
            if name.strip() in ENV_KEYS:
                secret = value.strip().strip("'\"")
                if secret:
                    content = content.replace(secret, "[REDACTED]")
    except (OSError, ValueError, UnicodeError):
        pass
    return content


def safe_log_tail(limit=1500):
    """Return a small, redacted excerpt, without uploading local log contents."""
    try:
        path = session_log_path()
        if not path.is_file() or path.stat().st_size > 1_000_000:
            return ""
        with path.open("rb") as src:
            src.seek(max(0, path.stat().st_size - 16_000))
            result = src.read().decode("utf-8", "replace")[-limit:]
        return _redact_secrets(result)
    except (OSError, UnicodeError, ValueError):
        return ""

def credential_issue():
    """Validate the local URL shape without making any network request."""
    if not configured():
        return "LiveKit credentials missing: URL, API key aur secret local file mein save karein."
    try:
        entries = {}
        for line in credentials_path().read_text(encoding="utf-8-sig").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            entries[key.strip()] = value.strip().strip("'\"")
        address = urlsplit(entries["LIVEKIT_URL"])
        if address.scheme != "wss" or not address.hostname or address.username or address.password or address.query or address.fragment:
            return "LIVEKIT_URL must be a wss:// project URL, not the project ID or dashboard URL."
        if any(entries[key].upper().startswith(("YOUR_", "PLACEHOLDER")) for key in ENV_KEYS):
            return "Demo placeholders hata kar asli LiveKit project credentials save karo."
    except (ValueError, KeyError, OSError, UnicodeError):
        return "LiveKit local credentials file invalid hai."
    return None


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


def _write_install_error(stage, details):
    """Keep a bounded, redacted Windows-local installer error for diagnosis."""
    try:
        path = session_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        detail = details.decode("utf-8", "replace") if isinstance(details, bytes) else str(details)
        path.write_text(
            "LiveKit setup failure at " + stage + ":\n" + _redact_secrets(detail)[-5500:] + "\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError, ValueError):
        pass


def _install_command(command, root, stage, timeout=360):
    """Run an allowlisted Python command, never a shell or a cloud session."""
    try:
        result = subprocess.run(
            command, cwd=str(root), check=False, capture_output=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _write_install_error(stage, type(exc).__name__ + ": " + str(exc))
        raise LiveKitSetupError(
            "LiveKit " + stage + " timeout/fail hua. View last LiveKit error kholo."
        ) from None
    if result.returncode:
        details = (result.stderr or b"") + b"\n" + (result.stdout or b"")
        _write_install_error(stage, details)
        raise LiveKitSetupError(
            "LiveKit " + stage + " fail hua (code " + str(result.returncode) +
            "). View last LiveKit error / diagnostic log kholo."
        )


def ensure_venv_pip(python=None, root=None):
    """Repair a pre-existing isolated venv that was created without pip.

    `venv\\Scripts\\python.exe` existing is NOT proof `pip` is installed.
    Use Python's bundled ensurepip only when needed; never delete the venv,
    download an unofficial bootstrap script, or touch LiveKit credentials.
    """
    root = root if root is not None else app_data_root()
    python = python if python is not None else environment_python()
    check = [str(python), "-m", "pip", "--version"]
    try:
        result = subprocess.run(
            check, cwd=str(root), capture_output=True, check=False, timeout=35,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _write_install_error("pip detection", type(exc).__name__ + ": " + str(exc))
        raise LiveKitSetupError(
            "LiveKit Python/pip check fail hua. View last LiveKit error kholo."
        ) from None
    if result.returncode == 0:
        return False
    # Python 3.12's standard library bundles ensurepip. Do this entirely
    # inside the existing LiveKit venv; existing packages stay untouched.
    try:
        _install_command(
            [str(python), "-m", "ensurepip", "--upgrade", "--default-pip"],
            root, "pip bootstrap (ensurepip)", 180,
        )
    except LiveKitSetupError:
        raise LiveKitSetupError(
            "LiveKit pip missing tha aur ensurepip repair fail hui. "
            "Official Python 3.12 installer se Python/pip repair karo; "
            "View last LiveKit error mein exact reason hai."
        ) from None
    _install_command(check, root, "pip verification after bootstrap", 35)
    return True


def preflight_runtime(noise_enhancement=False):
    """Check realtime SDK imports offline; no mic, model download or Cloud charge."""
    python = environment_python()
    if not python.is_file():
        raise LiveKitSetupError("LiveKit runtime missing hai. Install / repair LiveKit voice tools dabao.")
    check = ("from dotenv import load_dotenv; "
             "from livekit.agents import Agent, AgentServer, AgentSession, inference, room_io; "
             "import sounddevice")
    if noise_enhancement:
        check += "; from livekit.plugins import ai_coustics"
    try:
        completed = subprocess.run(
            [str(python), "-c", check],
            cwd=str(app_data_root()), capture_output=True, timeout=35, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _write_install_error("SDK preflight", type(exc).__name__ + ": " + str(exc))
        raise LiveKitSetupError("LiveKit Python preflight fail. Install / repair dobara chalao.") from None
    if completed.returncode:
        _write_install_error("SDK preflight", completed.stderr or b"")
        if noise_enhancement:
            raise LiveKitSetupError(
                "AI-Coustics extra missing/broken hai. Enhancement OFF karke test karo "
                "ya checkbox ON rakh kar Install / repair dobara chalao."
            )
        raise LiveKitSetupError(
            "LiveKit Python imports fail ho rahe hain. Install / repair dabao "
            "aur View last LiveKit error kholo."
        )
    return True


def install_optional(noise_enhancement=False):
    """Install minimal Cloud voice runtime; only requested noise models are extra."""
    if os.name != "nt":
        raise LiveKitSetupError("LiveKit desktop setup abhi Windows 11 ke liye hai.")
    if type(noise_enhancement) is not bool:
        raise LiveKitSetupError("LiveKit enhancement choice invalid.")
    if not agent_path().is_file() or not dependencies_path().is_file():
        raise LiveKitSetupError("Jarvis LiveKit files missing hain. Jarvis update karein.")
    root = app_data_root()
    root.mkdir(parents=True, exist_ok=True)
    python = environment_python()
    if not python.is_file():
        _install_command(python_command() + ["-m", "venv", str(root / ".venv")],
                         root, "Python virtual environment", 180)
    if not python.is_file():
        _write_install_error("Python environment", "venv was not created")
        raise LiveKitSetupError("LiveKit Python environment nahi bani. View last LiveKit error kholo.")

    # Some existing Windows venvs were created with --without-pip or
    # interrupted before pip bootstrap. Auto-repair before pip install.
    ensure_venv_pip(python=python, root=root)

    _install_command(
        [str(python), "-m", "pip", "--disable-pip-version-check",
         "install", "--no-input", "-r", str(dependencies_path())],
        root, "pip install", 450,
    )

    if noise_enhancement:
        # Only an explicitly selected extra requires local enhancement assets.
        _install_command(
            [str(python), "-m", "pip", "--disable-pip-version-check",
             "install", "--no-input", "livekit-plugins-ai-coustics~=0.2"],
            root, "optional AI-Coustics install", 360,
        )
        _install_command(
            [str(python), str(agent_path()), "download-files"],
            root, "optional AI-Coustics model download", 360,
        )

    # GPT-Live-1/marin is Cloud inference: no local voice/STT/turn
    # detector models need to be downloaded in the default configuration.
    preflight_runtime(noise_enhancement=noise_enhancement)
    try:
        session_log_path().write_text(
            "LiveKit runtime verified locally. No Cloud voice session started.\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    if noise_enhancement:
        return "LiveKit installed + optional AI-Coustics ready. Talk Live ab test karo."
    return "LiveKit realtime voice installed and verified. No extra model download needed."


class LiveKitConsole:
    def __init__(self):
        self.process = None
        self.started_at = None
        self.max_minutes = None
        self._stop_timer = None
        self.last_error = ""
        self.last_exit_code = None

    def is_running(self):
        process = self.process
        if process is None:
            return False
        code = process.poll()
        if code is None:
            return True
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None
        self.last_exit_code = code
        elapsed = (time.monotonic() - self.started_at) if self.started_at is not None else 0
        if elapsed < 30 or code != 0:
            self.last_error = (
                f"LiveKit voice stopped unexpectedly after {int(elapsed)}s "
                f"(exit code {code}). Open diagnostic log for the exact reason."
            )
        else:
            self.last_error = "LiveKit voice session ended. No cloud voice is running."
        self.process = None
        self.started_at = None
        self.max_minutes = None
        return False

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
        issue = credential_issue()
        if issue:
            raise LiveKitSetupError(issue)
        python, agent = environment_python(), agent_path()
        if not python.is_file():
            raise LiveKitSetupError("Pehle Install LiveKit Voice dabayein.")
        if not agent.is_file():
            raise LiveKitSetupError("LiveKit agent file missing. Jarvis update karein.")
        environment = os.environ.copy()
        environment["JARVIS_LIVEKIT_ENV_FILE"] = str(credentials_path())
        log = session_log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("Jarvis LiveKit session starting. Local diagnostics only.\n", encoding="utf-8")
        environment["JARVIS_LIVEKIT_LOG_PATH"] = str(log)
        self.last_error = ""
        self.last_exit_code = None
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
