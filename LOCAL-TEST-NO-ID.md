# HASEEB AI Jarvis — personal local testing, no Microsoft Store account

**Goal:** test the existing local Windows desktop Jarvis without using the blocked unsigned `Jarvis.exe` or downloaded `.cmd` installer. No Windows protections are disabled. This method is not guaranteed on every Smart App Control configuration.

## Only these steps

1. Install **official Python 3.12 for Windows** from https://www.python.org/downloads/windows/ . The installation should include **tkinter** and associate `.pyw` files with Python. Do not download Python from advertisements, mirrors or unverified sources.
2. Sign in to your own private GitHub repository: https://github.com/haseeb77758/Jarvis-
3. Choose **Code → Download ZIP**. Download the **repository source ZIP**, **not** a GitHub Actions EXE artifact.
4. In File Explorer right-click the downloaded ZIP → **Extract All**. Open the extracted project folder, the one containing `app.py`, `requirements.txt` and `START-JARVIS-GUI.pyw`.
5. Double-click **START-JARVIS-GUI.pyw**. If Windows asks you to choose an app, select the official Python 3.12 or Python Launcher installed in step 1. Do not open any CMD/BAT/EXE installer from the downloaded project.
6. In the graphical installer, read the dependency notice, tick the consent checkbox and click **INSTALL & OPEN JARVIS**. Jarvis dependencies will be installed in a private Windows user directory, then the existing Windows unit tests will run. First setup requires internet.
7. After setup succeeds, use the **HASEEB AI - Jarvis** Desktop or Start Menu shortcut. The GUI will also request to open the application once.

## What should work

Supported local commands such as `notepad kholo`, `calculator kholo`, `chrome kholo`, `youtube kholo`, `windows`, `screenshot` and `play pause`. AI chat is a separate optional **Ollama** model setup. Voice transcription requires a local voice model setup if not already present. Desktop input is opt-in, reviewed and cancellable.

## If Windows still blocks the GUI file

Do **not** disable Smart App Control or Defender. Do not use the `Unblock` trick to evade security policy and do not run as administrator. Capture the full Windows blocking message and the exact file name. The project cannot make a guarantee about local Windows policy or the reputation of a downloaded Python source. If this route is blocked, a legitimately signed app or Microsoft-approved Store release remains the trusted route.

## Diagnostics without coding

- **No window appears:** confirm Python **3.12** is installed, that the file was extracted, and try **Open with → Python**.
- **Setup error in GUI:** the last lines in its error log identify the failing dependency or test. Copy the **error text only** (no passwords).
- **Install succeeds but application doesn't open:** use the Desktop shortcut and share the exact error or screenshot.
- **Performance:** the tiny local transcription model and optional small Ollama AI model may be slow on an 8 GB machine.

These steps require only File Explorer and mouse interactions. They do not publish Jarvis on the Internet or require Microsoft Partner Center identity verification.
