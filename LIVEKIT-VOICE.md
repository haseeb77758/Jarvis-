# Jarvis primary voice — LiveKit GPT-Live-1

LiveKit GPT-Live-1 (voice `marin`) is Jarvis's **only active AI
conversation provider**, following the user's successful test of
`training-2057.zip`. Puter account chat, AI plans, Ollama and the other voice
chat modes are no longer initialized or exposed by native Jarvis. The typed
composer now accepts **local reviewed desktop commands only**; it cannot send
general questions to the LiveKit voice model.

**What "primary" means:** the dashboard's **Talk Live** button now opens
the **official LiveKit Cloud Agent Console in your normal web browser**.
This is the recommended route on Windows systems where Application Control
blocks the LiveKit Python native DLL. The voice agent runs in LiveKit Cloud;
no local Python SDK, native DLL, installed local speech models, or local
`LIVEKIT_API_SECRET` is required for the browser conversation. Sign in to
LiveKit Cloud and select your deployed agent `training-2057`.

**Crucial difference:** Jarvis **cannot see, stop or automatically time-limit**
the browser voice conversation. The browser's **End Call/Disconnect** button
must be used to end it. Jarvis's 5/10/15-minute local timer, global STOP,
and End Live Voice button control **only the optional local Python console**.
Opening a browser page does not itself start a billable voice session.
The agent has **no desktop-control tools**, so it cannot execute Windows
commands by voice.

## CURRENT — Direct Jarvis desktop WebRTC mode

Latest Jarvis **Talk Live** opens a private, dedicated Chrome/Edge app-mode
voice window served from 127.0.0.1, connects to the deployed training-2057
via an on-device short-lived token broker, and does not import native
LiveKit Python modules or launch the LiveKit Cloud Agent Console.

Save LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET once through
LiveKit setup > One-time LiveKit project keys. They stay local, are never
forwarded to the browser/agent. Browser gets only a 90-second room JWT.

Use direct voice Connect/Disconnect or the Jarvis main Talk Live/STOP.
The backend requests Cloud room deletion when ending or on the 10-minute
timer. This is a safety backstop, **not a guaranteed cash cap**, and
network failures can delay confirmation. Each tool request is reviewed
through a native Jarvis popup. Enable the desktop_command Client Tool
once in your LiveKit Builder to activate spoken app/file actions.

See **LIVEKIT-DIRECT-DESKTOP.md** for the one-time Builder configuration,
restricted actions and privacy details. The below Cloud Console instructions
are kept for historical context only, not the current default workflow.

## Historical Cloud Console option (superseded)

1. Update Jarvis from GitHub and restart.
2. On the main Jarvis dashboard press **Talk Live**. Confirm the browser
   disclosure. The official `https://cloud.livekit.io/` page opens.
3. Sign in to **the same LiveKit Cloud account** that owns your deployed agent.
4. Select your project (the one where **training-2057** is RUNNING), open
   **Agents** and select **training-2057**.
5. Click **Launch Console**, allow microphone access in the browser, then
   start the voice conversation. Credits/usage can accrue once the session
   is actually started.
6. **End Call/Disconnect in the browser** to stop the session. Closing the
   Jarvis dashboard or pressing Jarvis STOP is **not** a reliable way to
   end a browser session, and its local auto-STOP timer does **not** apply.

**Do NOT select Install/repair or edit LOCAL API keys for browser mode.**
Those controls are exclusively for the optional, advanced Python console.
The browser mode needs normal LiveKit Cloud sign-in, not project secrets
in Jarvis. This is still **LiveKit-only** and still billed/limited by
your LiveKit Cloud project. The official Agent Console is supported for
deployed agents, including Agent Builder deployments.

## Windows Application Control DLL block

If the previous local setup log shows:

```text
from livekit import blingfire
ImportError: DLL load failed while importing _native:
An Application Control policy has blocked this file.
```

**Windows Code Integrity / Application Control is refusing to load native
Python code.** The error can appear under an "optional AI-Coustics model
download" heading simply because that step tried importing `livekit.agents`,
which also imports `blingfire`; this does NOT prove the noise plugin is
the cause. Re-running `pip install`, deleting/recreating the venv, or
turning off AI-Coustics alone might not make the native module trusted.
Jarvis now recognizes the exact policy error and directs you to the
browser agent. **Do not disable Windows security, use an unofficial DLL
download, or bypass your organization's policies.**

If you eventually want to use local Python mode, the publisher/administrator
must resolve the blocked library under the applicable Windows App Control
policy (for example by obtaining trusted signed binaries or deploying
through an authorized managed installer). The browser mode is the practical
working alternative and does not attempt any security bypass.

## API keys — official pages

- **Create an account / open your project:** https://cloud.livekit.io/
- **LiveKit API key documentation:** https://docs.livekit.io/reference/api/projects/keys/
- **GPT-Live-1 setup docs:** https://docs.livekit.io/agents/models/realtime/gpt-live/
- **Current inference prices:** https://livekit.com/pricing/inference

After LiveKit Cloud sign-in, select your project, then navigate to its
**Settings → API Keys / Keys** section. Create a new key and keep the secret
immediately: LiveKit only shows it on creation.

You need **three LiveKit Cloud values** for Jarvis:

```dotenv
LIVEKIT_URL=wss://YOUR-PROJECT.livekit.cloud
LIVEKIT_API_KEY=YOUR_PROJECT_KEY
LIVEKIT_API_SECRET=YOUR_PROJECT_SECRET
```

These are *example placeholders*, not credentials. You do **not** need an
additional OpenAI API key for the tested LiveKit Inference mode.

In Jarvis, open **LiveKit setup** then click **Open LOCAL API key + secret
file** and save the real three values there. The file is stored under
`%LOCALAPPDATA%\HaseebCrafts\Jarvis\LiveKitVoice\.env.local`, separate
from source code and GitHub. It is Windows-user-readable **plaintext**, so
use a private Windows account and never share its contents or upload it.

Existing project credentials and the separately installed voice environment
are kept when you update Jarvis; updates don't overwrite the credentials
file. Never paste the API secret into ChatGPT or commit it to a repository.

## Optional advanced: local Python console

Use **Advanced 1 / 2 / 3** in the LiveKit setup window only if native
Python modules are permitted by your Windows Application Control policy.
This mode uses your local `.env.local` project credentials, opt-in
separate Python installation, and user-selected 5/10/15-minute local
automatic STOP. If DLL loading is blocked, prefer the official browser
Console above rather than retrying or disabling security.

**Talk Live on the main dashboard always opens the browser** and never
automatically installs local packages, starts a local process, or forwards
local secrets. Cloud conversation occurs only after you start it in
LiveKit Agent Console.
### Safety and ongoing expenses

- There is **no automatic cloud voice start** on Windows boot, app opening,
  or chat send. A new voice session needs **explicit user consent**, every time.
- By default, a LiveKit session **automatically stops after 10 minutes**.
  You can select **5 / 10 / 15 minutes** in LiveKit setup before starting.
  This local timer is a safety backstop, **not a monetary cost cap**.
- LiveKit Inference is **usage-metered**. The free Build plan may include a
  limited credit allowance, but *this is not unlimited free*. Check live
  pricing, quota and account usage. Even a short session can consume credits.
- AI-Coustics enhancement is **OFF by default**, and can add separate usage
  charges when selected.
- LiveKit agent speech is **separate from desktop control**. It cannot
  automatically launch Windows applications, access files or execute commands.
  The reviewed desktop controls elsewhere in Jarvis retain their approval
  checks, permissions and STOP behavior.
- **STOP** ends the local LiveKit console process; an already-billed portion
  or a provider-side session close delay cannot be reversed.
- A local virtualenv and installed SDK remain across restarts. The normal
  GPT-Live-1/marin Cloud mode does **not need local downloadable speech
  model files** and does not download any on the default Install/repair path.
  AI-Coustics optional extra, when deliberately enabled, may need its own
  plugin and assets. This is not required to speak to Jarvis.

## Fix: `No module named pip` during LiveKit setup

If the diagnostics show:

```text
LiveKit setup failure at pip install:
...\\LiveKitVoice\\.venv\\Scripts\\python.exe: No module named pip
```

this is a **broken or incomplete per-user virtual environment**, **not** a
LiveKit Cloud API-key error. The `.venv\\Scripts\\python.exe` file can exist
without the Python package installer `pip`. Earlier Jarvis only checked that
the Python executable existed.

The updated **Install / repair LiveKit voice tools** button now:
- Checks `python.exe -m pip --version` in the actual LiveKit virtualenv.
- If pip is missing, runs Python's bundled
  `python.exe -m ensurepip --upgrade --default-pip` automatically inside
  **that same virtualenv**.
- Verifies that pip is working before installing minimal LiveKit packages,
  without downloading unrelated models or launching a paid Cloud session.
- Leaves `%LOCALAPPDATA%\\HaseebCrafts\\Jarvis\\LiveKitVoice\\.env.local`
  and previously installed packages untouched.
- Saves the exact failure stage in the redacted local diagnostics if the
  underlying Python installation also lacks `ensurepip`. In that case use
  the official Python 3.12 Repair installer, not an arbitrary online
  bootstrap script, and run Install / repair again.

**No-code recovery:** Update Jarvis from GitHub, restart it, open
**LiveKit setup**, leave AI-Coustics OFF and click
**Install / repair LiveKit voice tools**. Do not delete the LiveKitVoice
folder, passwords, virtualenv or Jarvis app. Choose **Talk Live** only after
the installation reports success and you accept the metered Cloud session.

## Fix: "LiveKit dependencies/model download nahi hui"

Older installers ran `python livekit_agent.py download-files` **for every
LiveKit GPT-Live-1 setup**, even with AI-Coustics enhancement unchecked. This
attempted to fetch optional models/assets that the normal realtime Cloud
voice does not use. A failure in either pip installation or the unrelated
model download produced the same vague message, so the earlier screenshot
does **not** identify which step actually failed.

The corrected installer now:

1. Installs only `livekit-agents` and `python-dotenv` in a separate Windows
   Python 3.12 environment; previously installed packages are not deleted.
2. Skips `download-files` in the recommended normal GPT-Live-1/marin voice
   path. **Leave AI-Coustics unchecked** for the first successful test.
3. Downloads optional AI-Coustics packages/assets only if you explicitly
   check that option and approve the separate installation.
4. Runs an offline import check of LiveKit, `sounddevice` and its SDK after
   the install. It never starts a paid cloud session during setup.
5. If installation fails, displays the failed stage (e.g. `pip install`,
   `optional AI-Coustics model download`, or `SDK preflight`) and writes
   its redacted error under `last-session.log` for **View last LiveKit
   error / diagnostic log**. Do not share unredacted files or credentials.
6. After setup failure, blocks the metered session prompt until **Install /
   repair** succeeds.

**Recovery:** Click **No** on the metered-session popup in the old version,
update Jarvis from GitHub and restart. Open **LiveKit setup**, keep the
AI-Coustics checkbox OFF, then click **Install / repair LiveKit voice tools**.
When READY appears, select the 5-minute limit and click **Talk Live**.
If pip fails because internet or disk space is unavailable, inspect the
redacted local error and address that specific issue instead of repeatedly
clicking Start.

## Windows issue: Talk Live opens and then closes in seconds

If **Talk Live** flashes a Windows voice terminal and the session stops after
a few seconds, that is **not** a successful conversation. Older Jarvis versions
showed the misleading `READY` indicator immediately after the process died.

Current Jarvis now:

- Runs an **offline LiveKit SDK import preflight** before launching billable
  voice; a missing/broken Python environment becomes a setup error instead
  of a silently closed terminal.
- Checks the local project URL is an actual `wss://...` connection URL, not
  `https://cloud.livekit.io/projects/...` or a project ID.
- Uses the saved local LiveKit credentials even if an old environment variable
  points to a different project.
- Displays `VOICE EXITED` and the console exit code if a short session ends
  unexpectedly, instead of pretending that LiveKit is ready/connected.
- Writes warning and Python exception diagnostics to
  `%LOCALAPPDATA%\\HaseebCrafts\\Jarvis\\LiveKitVoice\\last-session.log`.
  The **View last LiveKit error / diagnostic log** button opens a locally
  redacted text copy. Do not share unredacted logs or API secrets.

**Troubleshooting:** Update Jarvis and restart, then open **LiveKit setup**.
Click **Install / repair LiveKit voice tools** if the preflight reports missing
SDK packages. Check your `LIVEKIT_URL` (`wss://...`) and project usage.
Click **Talk Live**, explicitly confirm the metered session, and speak after
the voice console opens. If the session exits, inspect the new local log for
the specific error. The fix cannot guarantee LiveKit Cloud quotas, network
access, or a working physical microphone without a local device test.

If the header says **Global stop unavailable**, Windows declined that
particular system-wide hotkey registration (often because another app owns
the shortcut). The Jarvis **STOP / Esc** button and app-focused Escape
remain available; don't disable Windows security to fix hotkey conflicts.

## Verification and limitations

GitHub Windows CI verifies the dashboard, controlled process start/stop, safe
credential paths, local time-limit logic, packaging and executable startup
**without requiring any personal API credentials**. The original user has
reported that the live console audio sounds good on their device. Future
latency/accuracy still depends on the LiveKit network and account limits.
There is no guarantee of a fully offline voice or zero delay.

The source is an adaptation of a user-provided LiveKit Agent Builder export.
It is not a cloud deployment. For a fully embedded audio/chat UI or
voice-initiated desktop tool approvals, additional integration work and
explicit permission design would be required.
