# RETIRED — Legacy Puter account chatbot

**This file is a migration notice, not current setup instructions.**

Jarvis now uses **only LiveKit GPT-Live-1** for AI conversation.
The old Puter account sign-in, Sandbox window, AI Chat tab and AI action
plans have been disconnected from the Windows desktop app. No account
relay is created at startup and no text commands are sent to Puter.
Use **Talk Live** for voice conversation instead.

The old `account_chat.py`, `sandbox_chat.py`, `web/connect.*` and their
offline regression tests are temporarily still shipped for **compatibility
with previously installed GitHub self-updaters**. Those older updaters
verify a fixed list of files and tests *before* installing the new
version. Removing files right now would break safe updates and strand
existing Windows users. They are not imported, instantiated, or exposed
by the new Jarvis native app.

Your original Puter account itself is not deleted, and separately
installed software or downloaded models on your computer are not
uninstalled. The retired browser demo under `web/` is not wired to
native Jarvis; do not use it for new Jarvis conversations.

See [LiveKit-only setup](LIVEKIT-VOICE.md).
