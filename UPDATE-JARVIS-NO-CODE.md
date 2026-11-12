# HASEEB AI Jarvis — Update Jarvis (no repeated ZIP downloads)

After installing the upgraded Windows source edition **once**, Jarvis can check its official GitHub repository for a new `main` commit. You do **not** need to download and extract a new ZIP for each future update.

## Fix: "Invalid package entry: livekit_voice\\agent.py"

Older Jarvis versions downloaded updates with an allowlist that accepted files
at repository root, plus known `tools/`, `tests/`, and `web/` folders.
It silently skipped the new `livekit_voice/` folder. The reviewable package
then failed its own verification and safely preserved the existing Jarvis.

The current source keeps the LiveKit startup code in `livekit_agent.py` and
`livekit_requirements.txt` at repository root, so **the already-installed
old updater can stage the complete update without reinstalling**. The
LiveKit account credential file under your Windows LOCALAPPDATA directory is
not touched. A regression test now reconstructs the legacy updater's
archive filtering and validates the complete staged package.

To recover: close other active Jarvis instances, reopen your currently
installed Jarvis, click **Connect GitHub** if your session expired, and
click **Update Jarvis** again. Once it reports success, restart Jarvis.
Do not disable Defender or remove your old user data to fix this error.

## Private GitHub repository — first-time account connection

Your `haseeb77758/Jarvis-` repository is **private**. This is why the original updater showed "GitHub update check failed" even when the internet worked: it called GitHub as an anonymous visitor. You do **not** need to make the repo public.

1. Install the new Jarvis source edition **once** from your signed-in GitHub page (Code → Download ZIP → Extract All → `START-JARVIS-GUI.pyw` → INSTALL & OPEN JARVIS). The old updater cannot fetch its own fix anonymously.
2. In Jarvis click **Connect GitHub**. If the official **GitHub CLI** is missing, Jarvis offers https://cli.github.com/ for installation. Install it from the official website, then restart Jarvis.
3. Click **Connect GitHub** again, approve the official CLI browser/device login and sign in to the GitHub account **haseeb77758** that has access to the repository. Complete only the official GitHub browser flow; **do not paste passwords or GitHub tokens into Jarvis or ChatGPT**.
4. Click **Update Jarvis**. The app asks GitHub CLI for an existing logged-in credential held outside Jarvis and uses it in memory to read the private repo over HTTPS. Any downloaded source is pinned to the exact commit you approve. The app does not put tokens in config files or logs.

GitHub CLI's account permissions may be broader than Jarvis's read-only operations; only authenticate a trusted local Jarvis installation and protect your GitHub account with 2FA. The updater never uploads or pushes your repo.

## First time only

Your older installed Jarvis has no updater. Download the new ZIP at https://github.com/haseeb77758/Jarvis- (Code → Download ZIP), extract it, open `START-JARVIS-GUI.pyw`, and approve the normal per-user install. Existing local memory remains stored separately. Once installed, start Jarvis with the desktop shortcut.

## Future updates

1. Jarvis checks the authenticated private GitHub repository **once shortly after the window opens**; no files are updated just by checking.
2. If there is a newer commit, Jarvis displays **GitHub update available · Update Jarvis** in the system status.
3. Click **Update Jarvis** in the title bar (or click it manually anytime to check).
4. Review the exact short commit ID, repository and important limitations, and choose **Yes** to approve. Select **No** to leave installed code unchanged.
5. Jarvis downloads source from GitHub at that approved commit, verifies the archive structure, rejects unsafe file types and path traversal, keeps updates inside its installed source directory, installs declared Python requirements (if any), runs runtime unit tests and a GUI self-test, then applies the update.
6. On success, **close Jarvis and reopen its desktop shortcut**; that is when the new version runs. No automatic restart or self-modifying desktop-control commands.

## Safety and practical limits

- No background silent **installation**; only a small background update **check**. Code changes require a real click and confirmation.
- This updater trusts code published to **your GitHub repository's `main` branch**. If the repo or GitHub account is compromised, the updater could execute malicious code. Review what you merge to `main`, protect the GitHub account with 2FA and protect the branch. It is not a code-signing or independent malware-verification mechanism.
- Sources are fetched through GitHub's authenticated HTTPS API with default certificate verification and a fixed repository URL. The exact approved commit is used for the download; no arbitrary external URL or local shell command is accepted.
- Only safe allowlisted source file types inside the app/tests/tools/web folders may be updated. `.venv`, saved user preferences, local model files, user notes, secrets, and unrelated user files are not copied or deleted.
- If code promotion or the installed-app test fails, changed **code files** are rolled back. However, Python packages installed or upgraded from `requirements.txt` cannot be automatically rolled back, so dependencies may need manual repair if their installation fails.
- Windows Defender and Smart App Control remain enabled. The updater cannot bypass Windows restrictions.
- Internet access is required to check/download changes. Jarvis still runs normally offline.
- Updates to the updater itself are applied only by the next launch after a successful update.
- This does not promise live desktop testing on your specific laptop; GitHub's Windows CI is additional validation.
