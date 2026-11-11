"""Consent-based source updater for the installed Windows Jarvis application.

Reads an approved private GitHub repository over authenticated HTTPS. Never disables
Windows Security, downloads executables, updates preferences or changes startup.
A new snapshot is tested before promotion; local code changes are rolled back
if promotion or the installed-app smoke test fails.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from zipfile import ZipFile, BadZipFile

REPOSITORY = "haseeb77758/Jarvis-"
LATEST_URL = "https://api.github.com/repos/" + REPOSITORY + "/commits/main"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
STATE_FILE = ".jarvis-update.json"
MAX_ARCHIVE_BYTES = 20_000_000
MAX_SOURCE_BYTES = 12_000_000
MAX_SINGLE_FILE = 1_000_000
MAX_FILES = 250
REQUIRED = frozenset({
    "app.py", "chat_ui.py", "sandbox_chat.py", "core.py", "dashboard.py", "memory.py", "voice.py",
    "requirements.txt", "tools/install_windows.py", "tools/create_shortcuts.py",
    "tools/update_windows.py", "tests/test_core.py", "tests/test_chat_ui.py",
    "tests/test_updater.py",
})
LOCAL_TESTS = (
    "test_sandbox_chat.py",
    "test_chat_ui.py", "test_core.py", "test_desktop_voice_memory.py",
    "test_safety_regressions.py", "test_stonic_tools.py",
    "test_stonic_volume.py", "test_video_desktop_features.py",
    "test_updater.py",
)


class UpdateError(RuntimeError):
    pass


class GitHubAuthenticationRequired(UpdateError):
    """Private repo requires a GitHub account with explicit repo access."""


def github_cli():
    """Only GitHub's official CLI, never execute a downloaded unreviewed script."""
    found = shutil.which("gh.exe") or shutil.which("gh")
    if found and Path(found).is_file():
        return str(found)
    candidates = []
    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(key)
        if root:
            candidates.append(Path(root) / "GitHub CLI" / "gh.exe")
            candidates.append(Path(root) / "Programs" / "GitHub CLI" / "gh.exe")
    return next((str(p) for p in candidates if p.is_file()), None)


def github_auth_token() -> str:
    """Read the user's GitHub CLI login *into memory only*; never print/store it.

    The GitHub CLI owns OS credential storage and account login. This app makes
    only read-only GitHub API calls, but CLI's granted scope can be broader.
    """
    executable = github_cli()
    if not executable:
        raise GitHubAuthenticationRequired(
            "PRIVATE GITHUB ACCESS: GitHub CLI install nahi hai. "
            "Jarvis mein Connect GitHub dabayein, official GitHub CLI install karein."
        )
    try:
        result = subprocess.run([executable, "auth", "token", "--hostname", "github.com"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=12, shell=False, check=False, text=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitHubAuthenticationRequired(
            "PRIVATE GITHUB ACCESS: GitHub CLI login read nahi ho raha. "
            "Connect GitHub dabayein."
        ) from exc
    token = result.stdout.strip() if result.returncode == 0 else ""
    if not 8 <= len(token) <= 1024 or any(char.isspace() for char in token):
        raise GitHubAuthenticationRequired(
            "PRIVATE GITHUB ACCESS: GitHub account sign in nahi hai. "
            "Jarvis mein Connect GitHub dabayein aur browser se login karein."
        )
    return token


def launch_github_login() -> None:
    """Start the official GitHub device/browser login in a visible console.

    No credentials are passed to Jarvis or placed on a command line.
    """
    if os.name != "nt":
        raise UpdateError("GitHub browser login button is for Windows.")
    executable = github_cli()
    if not executable:
        raise GitHubAuthenticationRequired(
            "PRIVATE GITHUB ACCESS: Pehle https://cli.github.com/ se official "
            "GitHub CLI install karein, phir Jarvis restart karein."
        )
    try:
        subprocess.Popen(
            [executable, "auth", "login", "--hostname", "github.com",
             "--git-protocol", "https", "--web"],
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            shell=False,
        )
    except OSError as exc:
        raise UpdateError(
            "GitHub login window open nahi hui. GitHub CLI reinstall karein."
        ) from exc


class SafeGitHubRedirect(HTTPRedirectHandler):
    """Do not send private bearer tokens to redirected archive hosts."""
    SAFE_HOSTS = frozenset({"api.github.com", "codeload.github.com"})

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination = urlparse(newurl)
        original = urlparse(req.full_url)
        if destination.scheme != "https" or destination.hostname not in self.SAFE_HOSTS:
            raise UpdateError("GitHub archive redirect went to an untrusted host.")
        rewritten = super().redirect_request(req, fp, code, msg, headers, newurl)
        if rewritten is not None and original.hostname != destination.hostname:
            rewritten.remove_header("Authorization")
            rewritten.unredirected_hdrs.pop("Authorization", None)
        return rewritten


def _request(url: str, limit: int, timeout: int) -> bytes:
    """Read-only authenticated private GitHub access, never log tokens."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        raise UpdateError("Only the official GitHub HTTPS API is supported.")
    token = github_auth_token()
    request = Request(url, headers={
        "User-Agent": "HASEEB-Jarvis-Source-Updater/2.0",
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
    })
    client = build_opener(SafeGitHubRedirect())
    chunks, total = [], 0
    try:
        with client.open(request, timeout=timeout) as response:
            while True:
                data = response.read(131072)
                if not data:
                    break
                total += len(data)
                if total > limit:
                    raise UpdateError("GitHub update exceeds the safe download size.")
                chunks.append(data)
    except HTTPError as exc:
        if exc.code in (401, 403, 404):
            raise GitHubAuthenticationRequired(
                "PRIVATE GITHUB ACCESS: GitHub ne repository access reject kiya "
                "(HTTP " + str(exc.code) + "). Connect GitHub se "
                "haseeb77758 account login karein, aur repo permission check karein."
            ) from exc
        raise UpdateError("GitHub server returned HTTP " + str(exc.code) + ".") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise UpdateError(
            "GitHub network connection fail hui. Internet, DNS ya firewall check karein."
        ) from exc
    return b"".join(chunks)


def latest_commit() -> str:
    """Fetch main branch SHA from the user's authenticated private repository."""
    try:
        payload = json.loads(_request(LATEST_URL, 300_000, 12))
        sha = payload["sha"]
    except (KeyError, ValueError, TypeError) as exc:
        raise UpdateError("GitHub response mein valid main commit nahi mila.") from exc
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise UpdateError("GitHub returned an invalid commit identifier.")
    return sha


def installed_commit(destination: Path) -> str | None:
    state = Path(destination) / STATE_FILE
    if not state.is_file() or state.is_symlink():
        return None
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
        sha = data.get("sha")
        return sha if isinstance(sha, str) and SHA_RE.fullmatch(sha) else None
    except (OSError, UnicodeError, ValueError, TypeError):
        return None


def check_update(destination: Path) -> tuple[str, bool]:
    """Return (remote SHA, whether a reviewed install is available)."""
    sha = latest_commit()
    return sha, sha != installed_commit(destination)


def _safe_source_path(path: PurePosixPath) -> bool:
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} or part.startswith(".")
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", part)
        or part.split(".")[0].upper() in {
            "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))
        }
        for part in path.parts
    ):
        return False
    if len(path.parts) == 1:
        return path.suffix.lower() in {".py", ".pyw", ".md", ".txt", ".bat", ".cmd"} or path.name == "requirements.txt"
    if len(path.parts) == 2 and path.parts[0] == "tools":
        return path.suffix.lower() in {".py", ".ps1"}
    if len(path.parts) == 2 and path.parts[0] == "tests":
        return path.name.startswith("test_") and path.suffix.lower() == ".py"
    if len(path.parts) == 2 and path.parts[0] == "web":
        return path.suffix.lower() in {".html", ".css", ".js"}
    return False


def snapshot_sources(archive: bytes) -> dict[str, bytes]:
    """Accept only a bounded, safe source-file subset; never extract ZIP paths."""
    files: dict[str, bytes] = {}
    try:
        with ZipFile(io.BytesIO(archive)) as z:
            entries = [entry for entry in z.infolist() if not entry.is_dir()]
            if not entries or len(entries) > 600:
                raise UpdateError("GitHub archive contains too many entries.")
            top = set()
            total = 0
            for entry in entries:
                name = PurePosixPath(entry.filename)
                if (name.is_absolute() or "\\" in entry.filename
                        or ":" in entry.filename or any(p in {"", ".", ".."} for p in name.parts)):
                    raise UpdateError("Invalid archive path.")
                if len(name.parts) < 2:
                    raise UpdateError("Unexpected archive layout.")
                top.add(name.parts[0])
                if len(top) != 1:
                    raise UpdateError("Unexpected multiple archive roots.")
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise UpdateError("ZIP links are not permitted.")
                relative = PurePosixPath(*name.parts[1:])
                if not _safe_source_path(relative):
                    continue
                if entry.file_size > MAX_SINGLE_FILE:
                    raise UpdateError("Update source file is unexpectedly large.")
                total += entry.file_size
                if total > MAX_SOURCE_BYTES or len(files) >= MAX_FILES:
                    raise UpdateError("Update contains too much source code.")
                key = relative.as_posix()
                if key in files:
                    raise UpdateError("Duplicate update source path.")
                data = z.read(entry)
                if len(data) != entry.file_size:
                    raise UpdateError("Archive entry size mismatch.")
                files[key] = data
    except (BadZipFile, OSError, EOFError) as exc:
        raise UpdateError("GitHub source archive could not be verified.") from exc
    missing = REQUIRED - files.keys()
    if missing:
        raise UpdateError("Incomplete official Jarvis source: " + ", ".join(sorted(missing)))
    return files


def _run(command: list[str], cwd: Path, timeout: int = 240) -> None:
    try:
        result = subprocess.run(command, cwd=str(cwd), check=False, shell=False,
                                capture_output=True, text=True, errors="replace",
                                timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("Jarvis update verification timed out or could not start.") from exc
    if result.returncode:
        details = (result.stdout + "\n" + result.stderr)[-1800:]
        raise UpdateError("Update failed its verification; existing Jarvis files were preserved.\n" + details)


def _safe_target(destination: Path, rel: str) -> Path:
    path = destination / Path(rel)
    current = destination
    for part in Path(rel).parts[:-1]:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise UpdateError("Update folder contains an unsafe link.")
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise UpdateError("Update target is an unsafe link.")
    return path


def _write_version(destination: Path, sha: str) -> None:
    state = destination / STATE_FILE
    if state.is_symlink():
        raise UpdateError("Update state path is an unsafe link.")
    temporary = destination / (STATE_FILE + ".tmp")
    if temporary.is_symlink():
        raise UpdateError("Update temporary state is an unsafe link.")
    temporary.write_text(json.dumps({"sha": sha, "repository": REPOSITORY}) + "\n", encoding="utf-8")
    os.replace(temporary, state)


def install_update(destination: Path, sha: str, *, archive: bytes | None = None,
                   run_checks: bool = True) -> str:
    """Apply an explicitly approved commit. Running Jarvis must be restarted.

    archive is injectable for offline unit tests, not exposed by the GUI.
    """
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise UpdateError("Invalid approved GitHub commit.")
    destination = Path(destination).resolve(strict=True)
    python = destination / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        raise UpdateError("Installed Jarvis Python environment missing. Run setup once first.")
    if archive is None:
        # Authenticate this *same approved SHA* via GitHub's private-repo API.
        url = "https://api.github.com/repos/" + REPOSITORY + "/zipball/" + sha
        archive = _request(url, MAX_ARCHIVE_BYTES, 60)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise UpdateError("Update archive too large.")
    files = snapshot_sources(archive)
    with tempfile.TemporaryDirectory(prefix="jarvis-reviewed-update-") as tmp:
        stage = Path(tmp) / "stage"
        stage.mkdir()
        for name, data in files.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if run_checks:
            _run([str(python), "-m", "pip", "install", "-r",
                  str(stage / "requirements.txt")], destination, timeout=900)
            for test_name in LOCAL_TESTS:
                if not (stage / "tests" / test_name).is_file():
                    raise UpdateError("Runtime verification test missing: " + test_name)
                _run([str(python), "-m", "unittest", "discover", "-s", "tests",
                      "-p", test_name, "-v"], stage, timeout=120)
        originals: dict[str, bytes | None] = {}
        changed: list[str] = []
        try:
            for name, data in files.items():
                target = _safe_target(destination, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                original = target.read_bytes() if target.is_file() else None
                if original == data:
                    continue
                originals[name] = original
                pending = target.with_name(target.name + ".jarvis-new")
                if pending.is_symlink():
                    raise UpdateError("Unsafe pending update file.")
                pending.write_bytes(data)
                os.replace(pending, target)
                changed.append(name)
            if run_checks:
                _run([str(python), str(destination / "app.py"), "--self-test"],
                     destination, timeout=90)
            _write_version(destination, sha)
        except Exception:
            for name in reversed(changed):
                target = _safe_target(destination, name)
                previous = originals[name]
                if previous is None:
                    target.unlink(missing_ok=True)
                else:
                    pending = target.with_name(target.name + ".jarvis-new")
                    pending.write_bytes(previous)
                    os.replace(pending, target)
            raise
    return ("Jarvis updated from GitHub main (" + sha[:9] +
            "). Restart Jarvis to load the new code. User preferences and Ollama models were not touched.")
