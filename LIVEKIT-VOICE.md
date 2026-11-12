# Jarvis LiveKit Voice — optional test mode

This integration was adapted from the user's `training-2057.zip` LiveKit Agent Builder export.

## What this changes

Jarvis now offers a separate **LiveKit Voice** button alongside its ordinary
**Voices** button. The new mode starts a realtime two-way voice session using
LiveKit Inference, `openai/gpt-live-1` and `marin` voice. It supports
interruptions, voice turn-taking and AI-Coustics audio enhancement.

**AI-Coustics voice isolation is OFF by default** to avoid extra metered audio\nprocessing. Turn it on only with the explicit checkbox if needed.\n\nThis is NOT the regular Jarvis Mic, and it is NOT a PC-control interface:
LiveKit voice is a separate console conversation window with **no desktop,
filesystem or browser automation tools**. The original free Edge Neural,
Whisper mic and account chat remain available and unchanged.

## Price and credentials

This specific model is billed by the LiveKit Cloud project, with delegated
reasoning/tool usage potentially billed separately. This cannot be promised as
an unlimited free service. Installing the optional library does not start a
cloud session or subscribe to a plan. **Start** requires a separate explicit
billing-consent confirmation every time.

You must have your own LiveKit Cloud project and its credentials. These never
belong in the GitHub repository or ChatGPT conversation. Open the generated
private `.env.local` from the LiveKit Voice screen, then fill:

    LIVEKIT_URL=wss://your-livekit-project
    LIVEKIT_API_KEY=...
    LIVEKIT_API_SECRET=...

Saved path: `%LOCALAPPDATA%\HaseebCrafts\Jarvis\LiveKitVoice\.env.local`.
This is a local plaintext credential file, protected by your Windows account's
file permissions. Keep the machine/user account secure; don't share the file.

## Windows 11 steps (no coding)

1. Update Jarvis from GitHub and restart.
2. Click **LiveKit Voice** beside the existing **Voices** button.
3. Click **Install separate LiveKit voice tools** and consent to internet
   package/model downloads. This uses a separate Python 3.12 environment
   under your Windows user folder, not the regular Jarvis environment.
4. Click **Open private LiveKit credentials file**. Fill and save your
   own LiveKit Cloud URL, API key and API secret.
5. Review your LiveKit Cloud billing/usage limits. Click
   **Start metered LiveKit conversation** only if you accept the costs.
   A separate voice console opens. Allow microphone access when prompted.
6. End the conversation with **STOP LiveKit voice session**, or close
   the LiveKit Voice dialog / Jarvis. The controller terminates the
   session process it created.

No desktop applications are launched from voice prompts, and no system
permissions are expanded. No service is automatically started on Windows boot.

## Quality and latency expectations

- GPT-Live-1 supports concurrent listening and speaking, including model
  driven interruptions. For quick conversations it can reduce the need for
  separate audio-to-text, LLM and text-to-speech requests.
- `marin` is not a verified authentic Pakistani Urdu accent, and bilingual
  pronunciation depends on the model. Test names, Urdu and English separately.
- Latency depends on LiveKit Cloud routing, network, model response and audio
  devices. This optional mode has not been live-tested on the user's computer.
- No guarantees for free quotas, unlimited voice, or millisecond latency.

## Technical boundaries

Only `livekit_voice/requirements.txt` is installed when you opt in.
The exported `training-2057.zip` is a template, not a complete packaged
Windows client; its original Dockerfile referenced a missing `uv.lock`.
We adapt its working agent structure instead of copying that Dockerfile.
The normal Windows CI tests statically test the optional launcher and
safety boundaries without making real cloud connections. A credentialed,
human-approved Windows microphone smoke test is still required for full
validation.

Official reference:
- https://docs.livekit.io/agents/models/realtime/gpt-live/
- https://docs.livekit.io/agents/server/startup-modes/
- https://docs.livekit.io/agents/models/inference/
