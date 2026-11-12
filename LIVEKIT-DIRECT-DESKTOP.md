# JARVIS + LiveKit Direct Voice and Desktop Tools

Created by Haseeb Crafts. Windows 11 / Python 3.12. LiveKit deployed agent: training-2057.

## One-time setup: no more Agent Console navigation

1. Update Jarvis from its reviewed GitHub main branch and restart.
2. Open LiveKit setup and select One-time project API keys (local file).
   Save the project's LIVEKIT_URL (wss://...), LIVEKIT_API_KEY and
   LIVEKIT_API_SECRET, from https://cloud.livekit.io/ > Manage API keys.
   The plaintext local file is under Windows LOCALAPPDATA /
   HaseebCrafts / Jarvis / LiveKitVoice / .env.local.
   Never send the secret in chat or commit it to GitHub.
3. On the main Jarvis dashboard click Talk Live and approve metered Cloud
   usage once for this session. A standalone Chrome/Edge app-mode desktop
   window opens at 127.0.0.1 (not the LiveKit Console).
4. Allow microphone access in the browser window on the first use.
   The WebRTC client connects directly to training-2057 through LiveKit.
5. Click Disconnect in that window, or Jarvis End Live Voice / STOP.
   A 10-minute timer and server-side RoomService DeleteRoom request provide
   a backstop. Network outages may delay Cloud confirmation; check project
   Sessions/Usage if needed. This is NOT a monetary spending cap.

The standalone browser app-mode window is launched by Jarvis and has its
own connection controls. It is not an embedded Tkinter WebView.

## Required once: configure voice desktop Client Tool in LiveKit Builder

The user's existing private Builder agent CANNOT be automatically modified
by this GitHub update. Without this one-time Builder tool configuration,
normal voice conversation works, but the agent will NOT call desktop tools.

Go to https://cloud.livekit.io/, select jarvis project, open Agents >
training-2057 > Builder > Actions > Add Client Tool.

- Tool name / RPC method: desktop_command (exact, including underscore)
- Description: "Use this client tool only when the user explicitly requests
  a Windows desktop action. The native Jarvis app must approve every action.
  Never run arbitrary commands, delete files or claim success before the
  returned tool result. If user denies, explain the denial."
- Parameters: action (required string); app, name, text, query
  (optional strings). Set only fields relevant to the selected action.
- action=launch, app=notepad/calculator/paint/explorer/chrome/edge
- action=folder, name=Clients (simple folder name, in Jarvis workspace)
- action=note, name=Meeting.txt, text=meeting details
- action=find, query=invoice (bounded search only in Jarvis workspace)
- action=clock (no other fields)
- action=windows (no other fields)
- Sample result: {"ok":true,"result":"DONE: Launch request bhej di: calculator"}
- Silent OFF, so Jarvis can speak results.
- Deploy the Builder changes to production. Keep training-2057 agent name.

Tool parameters/name in Builder UI can change. This is the one step that
requires access to the owner's LiveKit account; the desktop app's command
handler cannot force deployment from GitHub. It must be tested on the owner's
real Cloud deployment before claiming voice-based PC control is working.

## Security policy

Local tools are validated by a local-only HTTP service and every tool
request requires a real native Jarvis confirmation. File creation and
search are restricted to the user's chosen Jarvis workspace. No blind
typing, shell, PowerShell, deletions, arbitrary file reads or uncontrolled
mouse/keyboard input are exposed. STOP rejects further tool calls.

A tool result may be sent to your LiveKit Cloud agent after you approve it.
Do not approve actions containing sensitive information you don't want to
share with the Cloud provider.

LiveKit project API keys NEVER reach the browser, the agent or GitHub. A
short-lived room-scoped token is signed in Python stdlib using the locally
stored project secret. The HTTP server binds only to 127.0.0.1, validates
Origin/Host plus a random bearer secret, and has no permissive CORS. The
client SDK is pinned to LiveKit 2.23.0 via jsDelivr (internet needed).

The 10-minute STOP calls LiveKit's server-side RoomService DeleteRoom using
a separate short-lived roomCreate-scoped token (LiveKit DeleteRoom requirement) that stays on the local backend.
That stop can fail during network outages; the UI must not claim confirmed
Cloud termination when LiveKit is unreachable.

## Evidence, integration limits and docs

Windows CI tests local auth/CSRF, JWT dispatch, allowed/denied native
desktop actions, session timer, source/EXE packaging and GUI startup.
It cannot test the owner's microphone, private Cloud billing account, or
configure the Builder on the user's behalf. A final end-to-end test is
required after the user saves credentials and deploys the Client Tool.

https://docs.livekit.io/frontends/build/authentication/
https://docs.livekit.io/agents/server/agent-dispatch/
https://docs.livekit.io/transport/data/rpc/
https://docs.livekit.io/agents/start/builder/
https://docs.livekit.io/reference/other/roomservice-api/
