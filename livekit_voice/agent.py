"""Optional Jarvis realtime voice agent adapted from training-2057.zip.

Runs in its own opt-in Python environment. No desktop control tools are exposed.
LiveKit Inference uses a billed cloud model; regular Jarvis remains unchanged.
"""
import logging
import os

from dotenv import load_dotenv

# Credentials live in the Windows user's application-data folder, never in Git.
credential_file = os.environ.get("JARVIS_LIVEKIT_ENV_FILE")
if credential_file:
    load_dotenv(credential_file, override=False)

from livekit.agents import (  # noqa: E402
    Agent, AgentServer, AgentSession, JobContext, cli, inference, room_io,
)
from livekit.plugins import ai_coustics  # noqa: E402

logger = logging.getLogger("jarvis-livekit")

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
    await session.start(
        agent=JarvisLiveVoice(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
