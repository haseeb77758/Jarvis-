# JARVIS — Haseeb AI for Windows 11

Created by **Haseeb Crafts**.

A Windows desktop assistant with local controls, optional free local AI chat, and action-by-action approval. This repository contains the working Python source and an automatic Windows executable build.

## Option 2 — Browser chat from this repository

The standalone browser app is in **web/**. It uses Puter sign-in and the user's free monthly allowance, with no API key. Browser chat cannot control Windows. The external provider may prompt for more credits when the allowance is exhausted; there is no unlimited-free claim.

- **Private GitHub preview:** Open **Code → Codespaces → Create codespace on main**. The devcontainer starts the static server on port 8000 and opens the browser preview. If needed, use **Ports → 8000 → Open in Browser**. Codespaces uses the account's included development allowance; stop it after use. Creating a codespace has not been done automatically in this session.
- **GitHub Pages publishing:** The `Publish browser chat to GitHub Pages` workflow is ready but manual. GitHub Free cannot publish Pages from a private repository. A Pro account may publish from a private repo; otherwise changing repository visibility is an explicit owner decision. First configure **Settings → Pages → Source: GitHub Actions**, then run that workflow. No public URL is claimed before successful publishing.
- **Immediate existing cloud chat:** https://haseeb-ai-4ybb30.v2.appdeploy.ai/ (separate hosted version, not GitHub Pages).
- **Local browser preview:** `python -m http.server 8000 --directory web`, then open http://localhost:8000.

## Option 3 — One Windows EXE

1. Open **Actions → Windows test and build**, then the latest successful run.
2. Download **Jarvis-Single-EXE-Windows-x64** from Artifacts and extract it.
3. Run **Jarvis.exe**. No `_internal` folder or Python install is required for this build.
4. Use the app's **Setup local AI** button once for optional free offline AI. If Ollama is missing, it opens the official installer page. After installation, press the button again to download `qwen2.5:1.5b` (about 986 MB). The model/runtime are separate downloads, not embedded in the EXE.

The app is unsigned. One-file packaging extracts bundled application libraries into a temporary folder while running; it does not mean an AI model is embedded or that no temporary files are used. You must sign in to GitHub to download private-repository artifacts. Artifacts are retained for 14 days. No repository visibility or billing setting was changed.

## Run from source

Extract/clone the repository and double-click **SETUP.bat**. It checks Python 3.10+, creates a local environment, installs dependencies and runs tests. Later, use **START.bat**. Read [the Roman Urdu guide](README-ROMAN-URDU.md) for setup and machine-specific checks.

## What works

| Command / mode | Function |
| --- | --- |
| `chrome kholo`, `edge kholo`, `notepad kholo` | Launch an installed supported app |
| `calculator kholo`, `paint kholo`, `explorer kholo` | Launch Windows utilities |
| `open https://example.com` | Open an HTTPS website |
| `folder banao: Client Work` | Create a folder inside the selected workspace |
| `find: invoice` | Bounded filename search in the selected workspace |
| `note: Client meeting Monday` | Save a unique text note without overwriting files |
| `screenshot` | Preview the primary screen locally and optionally select a click point |
| `type: Hello Haseeb`, `key: ctrl+s`, `click: 300,400` | Reviewed keyboard/mouse input after opt-in and a countdown |
| Local AI chat | Chat with a downloaded model through local Ollama |
| AI action plan | Review and approve a limited plan before each action |

**Stop:** STOP button, app-focused Esc, global Ctrl+Alt+F12 when registered, or PyAutoGUI's screen-corner fail-safe during input.

## Scope and cost

- Local commands need no AI/API key. Local AI uses your hardware and the downloaded model; no per-message cloud API bill. It can be slow on an 8 GB laptop and is less capable than large hosted models.
- Cloud chat opens the existing hosted Haseeb AI app; its free monthly allowance applies and it does not control your PC.
- This is a limited desktop helper, not unrestricted autonomous control. Voice input, visual AI screen understanding, UAC/elevated windows and multi-monitor control are not included.
- Screenshots, file listings and file contents are not automatically uploaded. No inbound server, arbitrary shell command execution, autostart or background monitoring.
- Mouse/keyboard input is disabled by default. Review the actual target before approving click/Enter; input does not understand financial or messaging context.
- GitHub Actions consumes the repository owner's included build allowance. No billing upgrade or paid plan is configured by this repository.

## Validation

`python -m unittest discover -s tests -v` runs the local integration/validation suite. The Windows workflow installs dependencies, runs these tests, creates the UI and verifies a runner-only screenshot in a smoke test, builds with PyInstaller and checks the resulting EXE's `--self-test` exit code before uploading it.

Windows CI success demonstrates a hosted Windows runner, not successful installation or AI performance on your own laptop. Run the guide's smoke test on the target PC.


## Browser test coverage

The separate browser-check workflow tests sign-in gating, conversation context, new-chat reset, safe text rendering, quota errors/retry, abort and mobile layout with an explicitly mocked Puter provider. It does not claim a real Puter model reply or account sign-in was verified. That needs a user-signed-in browser.
