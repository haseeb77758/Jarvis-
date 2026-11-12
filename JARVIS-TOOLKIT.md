# HASEEB AI Jarvis — Safe Toolkit (Stonic-inspired ideas)

This is an independent implementation of useful Stonic-style capabilities for
the existing Windows 11 Tkinter desktop application. It does **not** install
or execute the third-party Stonic repository.

## No-code usage

1. Start **HASEEB AI Jarvis** using the existing Desktop shortcut.
2. Select **Toolbox** in the top bar (or **AI toolkit & schedule** in the sidebar).
3. Choose a capability. Its dialog explains the scope and asks for confirmation
   before paid cloud requests or sensitive system operations.
4. **AI Sandbox** remains chat-only: typed messages do not execute desktop
   actions, shell commands, or system operations.
5. For voice, the existing **Mic** button records an opt-in 6-second snippet,
   locally transcribes it and asks you to review the command before running it.
   It is not always listening and it is not a LiveKit real-time voice session.

## What works

- **Voice AI**: existing offline Whisper transcription + Windows SAPI speech.
  Microphone access is opt-in; quality and supported languages depend on the
  available model and installed Windows voices.
- **Desktop control**: existing reviewed app launching, window focus,
  screenshot, mouse/keyboard, media and volume with STOP/permissions.
- **Internet**: existing Google and YouTube searches; new weather search
  opens live Google results in your default browser. Jarvis does not claim to
  have fetched live weather itself.
- **Code review / generation**: Code Studio reads one explicitly selected,
  small (up to 3,000 characters) code file and sends explicitly selected text to account AI after disclosure. Code Generator drafts
  code in the chat. **Neither executes, saves nor self-upgrades code**.
- **Image generation**: optional OpenAI Images API, with your own key and API
  billing (separate from ChatGPT), user approval per request, 1024x1024 PNG,
  and selected local output directory. Key is never stored in preferences.
  The local 3B text model cannot generate images.
- **System operations**: Windows lock, shutdown in 60 seconds, restart in
  60 seconds, or cancel a pending shutdown. These are only clickable after
  an explicit confirmation dialog. Never model-executed.
- **Sleep mode**: the main Jarvis window can pause processing of ordinary
  chat/desktop commands. Enter **Wake up Jarvis** to resume. This is not
  microphone hotword detection. Chat-only AI Sandbox is separate.
- **Schedule / timetable**: local dated entries in
  `%LOCALAPPDATA%\HaseebCrafts\Jarvis\schedule.csv` (outside source code).
  Add, view and delete are supported; **no background reminders or notifications**.
- **Dashboard**: the existing Windows Tkinter dashboard adds a clearly
  organized Toolbox entry. No Flask server or remote control port is installed.

## Security and limits

- Never paste passwords or API keys into Jarvis chat or GitHub issues.
- Do not use unknown code without reviewing it. Generated code is untested
  and must be inspected before running in a separate development environment.
- The image API uses the fixed official HTTPS endpoint, no redirects, one
  image per action, and no stored key. A failed API request may still be
  billable by the provider depending on their policy.
- Weather, image API and GitHub updates require internet; account chat,
  schedule, basic desktop actions and optional local speech run on your PC.
- Real-time LiveKit cloud voice, hand-camera gesture detection, image editing,
  automatic software self-updates, arbitrary shell execution and scheduled
  notifications are **not** included in this toolkit release. Adding these
  requires separate design, consent, testing and possibly hardware/API budgets.
- Existing Windows Security settings must stay enabled; no elevated
  privileges or security-control bypass is required for the provided features.

