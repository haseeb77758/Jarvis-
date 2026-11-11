# Jarvis: desktop first, then chatbot and voice

Created by Haseeb Crafts.

## 1. Desktop smoke test on your Windows 11 PC

Download the latest successful `Jarvis-Single-EXE-Windows-x64` artifact, extract and run Jarvis.exe. The EXE includes application libraries and the multilingual tiny voice model; no Python or `_internal` folder is required. It is larger and first startup needs time to extract files. Local chat still needs the separate Ollama runtime/model.

Use an empty test folder first. Run these commands:

1. `calculator kholo` — inspect the real Calculator window.
2. `windows` — check the actual title list.
3. `inspect: Calculator` — view exposed non-edit UI labels. Some apps do not expose usable UI Automation controls.
4. Enable mouse/keyboard controls. `focus: Calculator` switches to a specific window after review/countdown.
5. `notepad kholo`, then `wait: Notepad`. If more than one Notepad window exists, use the specific title from `windows`.
6. `write: Notepad | Hello Haseeb` types into the focused field in that named window after review. Target-window validation happens again immediately before input. It does not press Enter.
7. `press: Notepad | ctrl+s` sends a reviewed shortcut. Interact with the real Save dialog yourself as needed.
8. `button: Calculator | Nine` invokes the exact button only if your locale/app actually exposes that accessible name. Run `inspect` to learn names first. Missing or ambiguous targets stop with an error; there is no blind coordinate fallback.
9. STOP, app-focused Esc or Ctrl+Alt+F12 cancels pending actions. During mouse/keyboard injection, a screen corner is also a PyAutoGUI fail-safe.

Apps such as Adobe software can be added through **Add app**: choose the installed .exe, give a simple alias and approve the path. Then use `open photoshop` or that alias. No command-line arguments/scripts are registered. An app may launch successfully yet expose few accessible controls; that does not imply full automation support.

## 2. Local chatbot and bounded action plans

**Setup local AI** opens the official Ollama installer if needed, then downloads the selected local model. In **Local AI chat**, messages stay local through Ollama and produce text only. **AI action plan** can propose up to eight allowed actions. Each proposed action is displayed for review; a failed step stops the remaining plan.

Example planning request: `Open Notepad, wait for its window, and type Hello Haseeb in it.`

The small model may misunderstand Roman Urdu or complex requests. Unsupported tasks are not silently converted to shell code. There is no unrestricted coding agent, browser account agent or guaranteed handling of every desktop app. Exact user commands are more predictable than generated plans.

## 3. Voice output and microphone commands

- **Test voice** uses a Windows installed SAPI voice. **Speak replies** reads result/error/chat replies aloud. Urdu/Roman Urdu pronunciation depends on installed voices and may not sound natural.
- **Mic · 6 seconds** records only after you press it. Choose Auto, Urdu or English. Recording and Whisper transcription happen locally; microphone audio is not uploaded.
- After model preparation, a short beep and Listening now status mark the start of the six-second recording. A transcript appears for review before execution. Cancel lets you edit it. Example English: `Open calculator.` Common Urdu examples include `کروم کھول دو` and `رک جاؤ`.
- Complex voice instructions use the selected mode. Select AI action plan for generated multi-step actions; select Local AI chat for conversation. The same permission/approval controls apply to spoken commands.
- No wake word or continuous listening is active. Use the physical/global stop controls while a voice recognition job is busy; saying stop is only recognized during an explicit recording.
- Tiny Whisper has limited accuracy, especially with noise, accents or mixed Urdu/English. Live-mic and Urdu quality must be tested on your laptop. The build's English test uses synthetic speech, not your microphone.
- Windows must allow desktop microphone access and have a working default input device. TTS needs an installed SAPI voice/output device.

## 4. Learn preferences without rewriting its own code

`remember: mujhe Roman Urdu mein short jawab do` saves an explicitly reviewed preference. The local chatbot receives these as response preferences, never as new system permissions.

**Save last plan** creates a named local shortcut from validated actions. Run it with `shortcut: work`. Every run is validated again and still requires action review. **Memory** shows/removes preferences, shortcuts and registered apps. These are stored under `%LOCALAPPDATA%\HaseebCrafts\Jarvis\preferences.json` and survive EXE updates.

It does not learn a new programming skill or retrain itself from every sentence. It does not rewrite, download or replace its executable automatically. **Updates ↗** opens the repository's tested builds for a deliberate update.

## Practical boundaries

Normal user privileges only; no UAC bypass, hidden monitoring, credential extraction or automatic financial/message submission. Primary-monitor pixel input only. The window/control features depend on the target app's UI Automation support. File writes remain within the selected workspace and never overwrite existing notes. User-requested screenshots can contain private content, so save them deliberately.

Large AI models, high-quality Urdu voice output, browser login flows and complex Adobe workflows would be separate, app-specific work. The existing GitHub browser version remains chat only; desktop controls live in the Windows EXE.
