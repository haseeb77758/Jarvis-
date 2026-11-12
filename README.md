# JARVIS — Haseeb AI for Windows 11

Created by **Haseeb Crafts**.

Jarvis combines a native animated dashboard, account-based AI chat, opt-in voice,
local notes/memory and reviewed Windows controls. **No API key or local language
model is required for chat.** Internet, a Puter account sign-in and available
account allowance are required. This is limited free usage, not unlimited free
inference. The app does not buy credits or upgrade plans.

## Start on Windows

Install official Python 3.12, extract the complete source ZIP, and open
**START-JARVIS-GUI.pyw** with Python. Approve the dependency installation, wait for
runtime checks, and use the installed **HASEEB AI - Jarvis** shortcut. See
[the local install guide](LOCAL-TEST-NO-ID.md). Existing preferences are preserved.

Unsigned EXE/CMD distributions may be blocked by Windows Smart App Control. Keep
Windows security enabled. See [Smart App Control](SMART-APP-CONTROL.md) and the
[trusted release guide](TRUSTED-WINDOWS-RELEASE.md). A successful CI build does not
make an unsigned executable trusted or prove installation on your laptop.

## Connect AI — account sign-in, no API key

1. Open Jarvis and click **Connect AI**.
2. Accept opening the connection page. In the browser, tick the chat-data
   disclosure and click **Sign in & connect**.
3. Sign in to your own Puter account and return to the desktop dashboard.
4. Keep the connection tab open while using main chat, Sandbox or AI action plans.
5. Click Disconnect in that tab to sign out, or close Jarvis to stop the relay.

Puter provides a free monthly allowance, subject to account/model limits. Exact
message counts vary with model, context and reply length. Use a free account and
check its usage view. Existing paid account entitlements are controlled by the
provider; Jarvis does not automatically subscribe, purchase or switch providers.
Quota errors are shown in chat. [Connection details and limits](ACCOUNT-CHAT.md).

Chat messages, recent context and saved response preferences are sent to
Puter/model providers after opt-in. User-selected code review sends the selected
file text only after its additional disclosure. No automatic screenshots or raw
microphone audio are attached. Authentication is managed by the browser SDK;
Jarvis never asks for an account API key, password or manually copied token.

The previous local chat runtime is retired: no service checks, launches, model
pulls or chat requests use it. Already-installed software/model files on your PC
are not uninstalled or deleted. Voice recognition still uses a separate small
local transcription model.

## Free voice replies

Open **Voices → Edge Neural (free online)**, choose **Asad/Uzma** for Urdu or
Ryan/Sonia/Guy/Jenny for English, accept sending spoken text, save and test.
Enable **Speak replies**. No API key is required by this client, but internet and
service availability are required. Urdu script gives clearer Urdu pronunciation;
Roman Urdu replies now use a **local Roman Urdu → Urdu script** speech copy by default; text chat stays Roman Urdu. This removes the separate AI conversion request, though unusual names and mixed English words may still sound incorrect. The same free neural service is used; live latency depends on the provider and network. Incoming MP3 audio is now decoded and played while subsequent audio is still arriving. [Voice setup](FREE-VOICES.md).

Windows speech is available offline. The previously added ElevenLabs provider is
optional and requires its own key/credits; it is never a fallback for free chat or
free speech. Do not select it for free-only usage. [Optional setup](ELEVENLABS-VOICE.md).

Mic recording starts only after pressing **Mic**, ends after a short speech pause
(with a six-second hard limit), transcribes locally, and asks for transcript review
before running a command. A noisy room can prevent early stopping; the six-second
limit still applies. The readiness/response timings are shown in the status bar.
There is no always-on recording. Use **Readiness** for device/configuration hints;
a live device test is needed to verify permission, voice quality and audible output.

## Optional LiveKit realtime voice (separately billed)

The **LiveKit Voice** button opens an optional, independent voice console based
on the user's uploaded `training-2057.zip`. It uses GPT-Live-1 through
LiveKit Inference. Unlike the normal free speech path, this model requires
LiveKit Cloud credentials and **can incur usage charges**. The button shows
explicit confirmation before launching cloud audio; the dependencies install
only after separate permission. It does **not** connect to Jarvis desktop
controls or ordinary chat history. The original voice remains the default.
See [LiveKit Voice setup and safety](LIVEKIT-VOICE.md).

## Reviewed desktop controls

| Command | Supported action |
| --- | --- |
| `chrome kholo`, `notepad kholo`, `calculator kholo` | Launch a supported installed app |
| `windows`, `inspect: Notepad` | List/inspect named app windows |
| `focus: Notepad`, `wait: Notepad` | Target an exact titled window |
| `write: Notepad \| Hello Haseeb` | Reviewed targeted text input |
| `button: Calculator \| Nine` | Invoke an exact accessible control after inspection |
| `folder banao: Client Work`, `note: Meeting Monday` | Create workspace folder/note without overwriting |
| `find: invoice`, `screenshot` | Bounded workspace filename search or local screenshot preview |
| `volume up`, `play pause`, `youtube kholo` | Allowlisted media/site controls |
| `remember: Reply in short Roman Urdu`, `shortcut: work` | Explicit local preferences/reviewed saved plans |

Select **Computer commands** for direct controls or **AI action plan** for a
proposed bounded plan. AI output never directly calls desktop functions. Each
plan is validated, screen input requires opt-in, and actions are reviewed.
Unsupported requests, elevated/UAC windows, arbitrary shell execution and
unrestricted autonomous PC operation are not supported.

STOP: app button, app-focused Esc, global Ctrl+Alt+F12 when registered, or the
PyAutoGUI corner fail-safe during input. Cloud requests already submitted can
still consume account allowance, but cancelled/late answers are discarded.

## Network and packaging

Connect AI starts a temporary authenticated relay on **127.0.0.1** at a random
port. It exposes only chat request/response/connection endpoints, not file access
or desktop-control routes. No public listener, remote-control tunnel, autostart
or background monitoring is installed. [Toolkit](JARVIS-TOOLKIT.md).

The separate **web/** browser edition also supports Puter sign-in with no desktop
bridge. Preview with `python -m http.server 8000 --directory web`. Private GitHub
Codespaces/Pages and build artifacts depend on your GitHub account/plan settings;
no repository visibility, paid plan or public deployment is changed automatically.

Actions → **Windows test and build** produces the source archive and unsigned
Windows executable. Source and dependency notices are included; free speech
client source/license/rebuild information is in THIRD-PARTY-NOTICES.txt.

## Validation

`python -m unittest discover -s tests -v` checks native behavior and boundaries.
Windows CI tests UI geometry, reviewed synthetic window input, installation,
voice codecs and EXE startup. Browser CI tests the real loopback relay with
explicitly mocked Puter sign-in/model replies, including quotas and STOP.

A passing mock test does **not** verify real account sign-in, account allowance,
or a real model reply. Those need your signed-in connection page on the target
PC. Live free-speech sample generation is a separate optional CI step; inspect
its own result before calling it verified. [Desktop smoke guide](DESKTOP-FIRST.md).
