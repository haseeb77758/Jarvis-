# Jarvis primary voice — LiveKit GPT-Live-1

LiveKit GPT-Live-1 (voice `marin`) is Jarvis's **only active AI
conversation provider**, following the user's successful test of
`training-2057.zip`. Puter account chat, AI plans, Ollama and the other voice
chat modes are no longer initialized or exposed by native Jarvis. The typed
composer now accepts **local reviewed desktop commands only**; it cannot send
general questions to the LiveKit voice model.

**What "primary" means:** a big **Talk Live** button on the main Jarvis
dashboard launches the user-tested separate LiveKit console. The animated
dashboard stays available, shows the session's remaining time, and its button
becomes **End Live Voice** while running. This is a native dashboard shortcut,
not a fully embedded voice waveform/transcript player. The LiveKit agent has
**no desktop-control tools** and does not execute spoken PC commands.

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

## How to speak after updating Jarvis

1. On Windows 11, open Jarvis and run **Update Jarvis**; restart the app.
2. For first setup only, click **LiveKit setup** → **Install / repair LiveKit
   voice tools**. This uses a separate Python 3.12 environment and internet.
3. Add LiveKit Cloud credentials in the **LOCAL** file described above.
4. On the main Jarvis chat bar, click **● Talk Live**.
5. Confirm the cloud usage prompt for this specific session. The familiar
   LiveKit voice console opens while the dashboard remains available.
6. Click **■ End Live Voice**, use Jarvis global STOP / Ctrl+Alt+F12, or
   close Jarvis to terminate the session.

**Talk Live** is the only AI conversation button. There is no other
chatbot, free voice fallback or separate model chooser in the native UI.
The legacy speech and chatbot source modules remain in the reviewable source
only so already-installed older updaters can verify and migrate successfully.
Their providers are not constructed or connected in the current runtime.

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
