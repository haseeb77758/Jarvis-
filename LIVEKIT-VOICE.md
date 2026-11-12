# Jarvis primary voice — LiveKit GPT-Live-1

LiveKit GPT-Live-1 (voice `marin`) is now Jarvis's **primary spoken conversation
mode**, following the user's successful test of the original
`training-2057.zip` agent. The regular Windows/Edge voice and local Whisper
microphone remain a **Free Mic fallback**; text/chat and reviewed desktop
controls are unchanged.

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

The former **Mic** button is now labelled **Free Mic**. The existing
**Voices** button still configures the free Edge Neural TTS provider. Use these
if you don't want to spend LiveKit Cloud credits.

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
- A local virtualenv and downloaded models remain installed between restarts;
  the agent doesn't download models at every Talk Live click.

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
