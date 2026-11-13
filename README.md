# JARVIS — Gemini Text Chat + LiveKit Voice for Windows 11

Created by **Haseeb Crafts**.

**Two opt-in modes**: Gemini Free-Tier **text chat**, and separate LiveKit
Inference **voice** (`openai/gpt-live-1`, `marin` voice). Normal typed
desktop commands remain local and reviewed. Jarvis does not launch the
retired Puter relay, Ollama or other chatbots. It keeps the animated orb,
local notes, tasks, desktop controls, STOP and GitHub updates.

## Current: Gemini Free API text chat (optional)

Open **Gemini API setup** in Jarvis and save your key privately on Windows.
The key is encrypted using Windows DPAPI and never goes to GitHub. Select
**Gemini AI chat** in the dropdown for natural Roman Urdu/English replies.
Press Send to call the fixed official Gemini HTTPS endpoint. Switch back to
**Computer commands** for Windows tools. Gemini output is **text only** and
cannot run desktop actions automatically.

The initial model is `gemini-3.5-flash-lite`, with a reviewed optional
`gemini-3.1-flash-lite` selection. Both currently list Free Tier API text
pricing, subject to Google account/project availability and limits.
Jarvis enforces a local 30 attempted requests/day precaution, **not** a
financial cap. Google Free Tier data may be used to improve its products;
do not send confidential client content. No auto-retry or background calls.
Full setup: [Gemini Windows setup](GEMINI-SETUP.md).


## Current: Direct Jarvis desktop WebRTC voice

Jarvis Talk Live now opens a dedicated Chrome/Edge app-mode desktop window,
not the LiveKit Cloud Agent Console. A loopback-only Python standard-library
server mints short-lived tokens from your saved LiveKit Cloud project
credentials; Windows' blocked native blingfire DLL is not imported.

**One-time**: Save LiveKit project URL, API key and secret locally via
LiveKit setup -> One-time LiveKit project keys. Then click **Talk Live**,
approve the Cloud credits notice, and the desktop voice window connects to
the existing **training-2057** agent. Browser mic permission may be needed
on first use. End via Disconnect / desktop STOP. The local backend also
requests room deletion after ten minutes; it is **not** a spending cap.

**Voice-control apps/files:** A restricted desktop_command client RPC is now
implemented in the browser/local Jarvis bridge. You must additionally add
and Deploy that Client Tool once in your existing private LiveKit Builder;
GitHub updates cannot modify your Builder agent. Every action requires
separate native Jarvis approval. See [Direct Voice setup](LIVEKIT-DIRECT-DESKTOP.md).

**Security:** No arbitrary shell, deletion or unrestricted file reads; only
approved apps and workspace file operations. LiveKit project secrets never
enter the browser. Voice sessions need internet/Cloud usage and a pinned
LiveKit WebRTC SDK CDN. No offline voice is promised.

## Historical browser-console instructions (superseded)

1. Update Jarvis and restart.
2. Click **Talk Live** to open the **official LiveKit Cloud Agent Console** in your browser. Sign in, choose your existing project and deployed `training-2057` agent, then click **Launch Console**.
3. Allow the microphone and explicitly start the conversation inside the browser; LiveKit Cloud usage may be billed.
4. **End Call/Disconnect in your browser** to stop: Jarvis STOP and the 5/10/15-minute local timer **cannot control browser voice sessions**.

**Browser LiveKit needs no local Python, `blingfire` DLL, or API keys stored in Jarvis.** It works around Windows Application Control blocks without disabling security. **Advanced** local Python mode still exists for systems whose native libraries are allowed by Windows policy; only there do the local timer and process STOP apply.

**This is usage-metered cloud inference, not an unlimited free AI.** Check
[LiveKit pricing](https://livekit.com/pricing/inference) and project usage.
No billable voice session is started on Jarvis launch, update, or opening
the settings window. AI-Coustics remains opt-in.

See [LiveKit setup, keys, privacy and safety](LIVEKIT-VOICE.md).

## Local desktop commands (separate from Gemini chat)

When the dropdown is set to **Computer commands**, the text box accepts
*reviewed local commands only*; unknown text is not sent online.
Choose **Gemini AI chat** to send a message explicitly to Gemini. Examples:

| Command | Local action |
| --- | --- |
| `calculator kholo`, `notepad kholo` | Launch an allowlisted app |
| `windows`, `inspect: Notepad` | List and inspect accessible windows |
| `button: Calculator \\| Nine` | Reviewed accessible control invocation |
| `folder banao: Client Work`, `note: Meeting Monday` | Create local files in a chosen workspace |
| `screenshot`, `find: invoice` | Screenshot preview and bounded local search |
| `volume up`, `play pause` | Allowlisted system controls |
| `shortcut: name` | Run an existing saved shortcut with review |

Gemini text replies **do not execute desktop tools**. LiveKit voice desktop
actions require an explicit `desktop_command` Client Tool deployed in
the owner's private LiveKit Builder and a separate native Jarvis approval
for each supported action. See [Direct Voice setup](LIVEKIT-DIRECT-DESKTOP.md).

Screen input requires user permission and individual review. STOP via the
app button, focused Esc or global Ctrl+Alt+F12 (if registered).
Never disable Windows security or enable unrestricted shell commands.

## Installation and updates

Install official Python 3.12, extract the reviewed
`Jarvis-Source-Windows.zip` from the authenticated repository's GitHub Actions
artifacts and open `START-JARVIS-GUI.pyw`. The installer uses a per-user venv
and keeps local preferences and LiveKit credentials across updates. See
[Windows installation](LOCAL-TEST-NO-ID.md) and
[updating Jarvis](UPDATE-JARVIS-NO-CODE.md).

The old chatbot and free-TTS source files remain in the reviewed source
bundle for legacy updater compatibility and offline migration tests.
They are not activated as additional chat providers. Gemini is separately
implemented without the retired Puter account relay.
No old Puter account service is automatically connected; Jarvis does not
uninstall unrelated Windows software or delete model files on your computer.

## Verification

Windows CI validates the dashboard, mocked Gemini REST/key safety,
local commands, source ZIP, installer and EXE launch without your private
Gemini/LiveKit credentials. These tests **do not prove** real Gemini key
access, LiveKit Cloud voice quality, latency or usage on your PC.
You have to consent to and run a live device test yourself.

Unsigned development EXEs may be blocked by Windows Smart App Control; keep
Defender and Smart App Control enabled.
