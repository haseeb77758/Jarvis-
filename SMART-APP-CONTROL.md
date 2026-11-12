# Windows Smart App Control: Safe Jarvis launch

**Problem:** An unsigned PyInstaller `Jarvis.exe` may be blocked by Windows 11 Smart App Control. A successful GitHub Windows test does not establish Microsoft publisher trust. No setting in this repository disables, bypasses, or creates an exception for Smart App Control.

## Recommended source launch (no unsigned Jarvis.exe)

1. Download this repository's source ZIP from GitHub **Code → Download ZIP**, or clone it. Extract it completely to a normal folder.
2. Install an official Python 3.10+ for Windows with tkinter and the `py` launcher from https://www.python.org/downloads/windows/
3. Open Terminal in the extracted repository folder.
4. Check without any changes: `py -3 RUN-JARVIS.py --check`.
5. Start: `py -3 RUN-JARVIS.py`. On first run, review the install notice and type `YES` to install packages in a local `.venv`. It runs tests, then starts the desktop app.
6. Later: `py -3 RUN-JARVIS.py`. The `--setup` option forces a confirmed dependency refresh and test run.

This is a source-run alternative, not a promise that Windows will trust every dependency or that local security policy permits every action. Python packages are fetched from the configured pip package index. Review `requirements.txt` first. Never run as Administrator or disable security protections to make it work.

## Permanent distribution fix

For a distributable `.exe` that is more likely to be trusted, use a legitimate trusted code-signing certificate issued to your verified publisher identity and sign **the final EXE after building it**. Keep the certificate/private key outside the GitHub repository. Signed apps can still be blocked by security checks; code-signing is not a malware clearance or guaranteed approval.

Official Microsoft guidance: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control

## Important

Account AI uses **Connect AI** → Puter browser sign-in, with internet and limited account allowance; no local chatbot model download. Voice transcription setup remains separate. See ACCOUNT-CHAT.md.
- A computer-control agent still needs explicit permission; existing review, STOP, and screen corner fail-safe mechanisms remain in place.
- A source-run success is not identical to a successful signed Windows deployment.

