# JARVIS — LiveKit-only AI for Windows 11

Created by **Haseeb Crafts**.

**The only active AI conversation provider is LiveKit Inference
(`openai/gpt-live-1`, `marin` voice).** Jarvis no longer launches a Puter
account relay, a sandbox chatbot, local Ollama, alternate AI chat providers,
AI-generated action plans or a second voice-chat provider. The dashboard
retains its animated orb, local notes, tasks, direct desktop commands,
screen-action review, emergency STOP and GitHub updates.

## Start LiveKit conversation

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

## Local desktop commands (not AI chat)

The text box now accepts *reviewed local commands only*. Typed general
questions are **never forwarded to an alternate chatbot** and are answered
with a local command-help notice. Examples:

| Command | Local action |
| --- | --- |
| `calculator kholo`, `notepad kholo` | Launch an allowlisted app |
| `windows`, `inspect: Notepad` | List and inspect accessible windows |
| `button: Calculator \\| Nine` | Reviewed accessible control invocation |
| `folder banao: Client Work`, `note: Meeting Monday` | Create local files in a chosen workspace |
| `screenshot`, `find: invoice` | Screenshot preview and bounded local search |
| `volume up`, `play pause` | Allowlisted system controls |
| `shortcut: name` | Run an existing saved shortcut with review |

Local desktop commands **do not come from the LiveKit voice agent**: the voice
agent currently has *no* desktop-control tools or filesystem access. You
cannot voice-control Windows apps through LiveKit until a separate,
permission-reviewed tool integration is developed.

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

The old chatbot and free-TTS source files are intentionally left in the
**reviewed source bundle solely for compatibility with already-installed
updaters and their offline migration tests**. They are not imported,
initialized, connected or exposed as providers by the native Jarvis UI.
No old Puter account service is automatically connected; Jarvis does not
uninstall unrelated Windows software or delete model files on your computer.

## Verification

Windows CI validates the desktop dashboard, legacy-disabled runtime behavior,
safe local controls, source ZIP, installer and Windows EXE startup without
using your personal LiveKit credentials. These tests **do not prove** real
LiveKit account connectivity, voice quality, latency or billable usage on your PC.
You have to consent to and run a live device test yourself.

Unsigned development EXEs may be blocked by Windows Smart App Control; keep
Defender and Smart App Control enabled.
