"""Optional Jarvis realtime voice agent adapted from training-2057.zip.

Runs in its own opt-in Python environment. No desktop control tools are exposed.
LiveKit Inference uses a billed cloud model; regular Jarvis remains unchanged.
"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

# The user's explicit, locally saved project must override any stale parent
# environment values. Never print credentials or place them in command args.
credential_file = os.environ.get("JARVIS_LIVEKIT_ENV_FILE")
if credential_file:
    load_dotenv(credential_file, override=True)


def configure_diagnostics():
    """Capture SDK warnings and exceptions locally without transcripts or keys."""
    destination = os.environ.get("JARVIS_LIVEKIT_LOG_PATH")
    if not destination:
        return
    try:
        log = Path(destination)
        log.parent.mkdir(parents=True, exist_ok=True)
        secrets = [
            os.environ.get("LIVEKIT_API_KEY", ""),
            os.environ.get("LIVEKIT_API_SECRET", ""),
            os.environ.get("LIVEKIT_URL", ""),
        ]

        class RedactingFormatter(logging.Formatter):
            def format(self, record):
                result = super().format(record)
                for secret in secrets:
                    if secret:
                        result = result.replace(secret, "[REDACTED]")
                return result

        handler = RotatingFileHandler(
            log, maxBytes=256_000, backupCount=0, encoding="utf-8"
        )
        handler.setLevel(logging.WARNING)
        handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        if root.level > logging.WARNING:
            root.setLevel(logging.WARNING)
    except (OSError, ValueError):
        # Log setup must not block voice startup.
        pass


configure_diagnostics()
logger = logging.getLogger("jarvis-livekit")

try:
    from livekit.agents import (  # noqa: E402
        Agent, AgentServer, AgentSession, JobContext, cli, inference, room_io,
    )
except Exception:
    logger.exception("LiveKit SDK import failed; repair the isolated LiveKit installation")
    raise

SPEECH_INSTRUCTIONS = (
    "You are Jarvis, the practical personal voice assistant created by Haseeb Crafts. "
    "This is a real-time voice conversation, not a coaching roleplay. "
    "Speak naturally and clearly, in conversational Pakistani Urdu when the user speaks Urdu, "
    "or in English when the user speaks English. Avoid robotic, overly formal phrases. "
    "Keep ordinary replies short: one to three sentences. Be friendly but precise. "
    "Respond to the point without repeating the question. "
    "Pronounce people's names carefully; if unsure, ask once. "
    "Do not read code blocks, markdown, web links, or symbols aloud. "
    "If asked to use or control the computer, clearly explain that this LiveKit voice "
    "test does not have desktop tools and has not performed any desktop action. "
    "Never pretend to have opened a file or changed a setting. "
    "Do not solicit passwords or secrets. Follow safety restrictions. "
    "You can be interrupted; continue conversationally."
)


class JarvisLiveVoice(Agent):
    def __init__(self):
        super().__init__(instructions=SPEECH_INSTRUCTIONS)

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="Say a short natural greeting, then ask what the user wants to do.",
            allow_interruptions=True,
        )


server = AgentServer()


@server.rtc_session(agent_name="jarvis-voice-2057")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        llm=inference.DuplexModel(model="openai/gpt-live-1", voice="marin"),
    )
    session_options = {"agent": JarvisLiveVoice(), "room": ctx.room}
    # Optional: ai-coustics Voice Focus can add cloud usage charges.
    if os.environ.get("JARVIS_LIVEKIT_AI_COUSTICS") == "1":
        from livekit.plugins import ai_coustics  # optional, never imported by default
        session_options["room_options"] = room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        )
    try:
        await session.start(**session_options)
    except Exception:
        logger.exception("LiveKit session failed before voice conversation started")
        raise


if __name__ == "__main__":
    try:
        cli.run_app(server)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            logger.error("LiveKit CLI exited before normal completion; status=%s", exc.code)
        raise
    except BaseException:
        logger.exception("LiveKit console terminated unexpectedly")
        raise
