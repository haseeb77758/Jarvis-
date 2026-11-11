# JARVIS — Haseeb AI for Windows 11

Created by **Haseeb Crafts**.

A Windows desktop assistant with local controls, optional free local AI chat, and action-by-action approval. This repository contains the working Python source and an automatic Windows executable build.

## Download the Windows app

1. Open this repository's **Actions → Windows test and build**.
2. Open the latest successful run and download **Jarvis-Windows-x64** from Artifacts.
3. Extract the complete ZIP and run **Jarvis.exe**. Keep the `_internal` folder next to the EXE.
4. For offline AI, run **SETUP-LOCAL-AI.bat** once. It opens the official Ollama installer if missing, then downloads `qwen2.5:1.5b` (about 986 MB).

You must be signed in to GitHub to download artifacts from this private repository. Artifacts are retained for 14 days; a new push or manual workflow run rebuilds the package. If no successful build exists yet, use the source setup below. This build is unsigned and contains no bundled AI model.

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

`python -m unittest discover -s tests -v` runs the local integration/validation suite. The Windows workflow installs dependencies, runs these tests, creates the UI and captures only runner screen dimensions in a smoke test, builds with PyInstaller and checks the resulting EXE's `--self-test` exit code before uploading it.

Windows CI success demonstrates a hosted Windows runner, not successful installation or AI performance on your own laptop. Run the guide's smoke test on the target PC.
