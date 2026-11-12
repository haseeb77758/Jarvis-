# Jarvis desktop smoke test

Created by Haseeb Crafts. Keep Windows security enabled. Use the Python-source
installation route if unsigned EXE/CMD files are blocked on the target machine.

## 1. Direct supported desktop controls

Start the app and select Computer commands. Try `notepad kholo`, `windows`,
`inspect: Notepad`, and a reviewed targeted write to your synthetic/test document.
Use a separate workspace for notes/folders. No AI account is required for these
commands. Screen input is opt-in and reviewed; STOP must cancel pending input.

## 2. Account chatbot (no local model download)

Click Connect AI, accept opening the connection page, tick the chat-data disclosure
and sign in to Puter. Return to the native dashboard, keeping the tab open. Send
a short Roman Urdu question and verify a useful reply. Use New chat to reset.

Internet and account allowance are required. Free allowance is limited; no fixed
message count is promised. No automatic plan/credit purchase is implemented.
Disconnect in the browser and verify the app status returns to SIGN IN. Quota
errors must be shown without paid-provider switching. The app does not install,
start or call a local chatbot service, and does not delete previously installed
software or model files.

## 3. Voice

Voices → Edge Neural (free online) → Asad/Uzma for Urdu, or an English voice →
accept spoken-text transfer → Save → Test voice. Enable Speak replies. Test Urdu
with Urdu script. Verify actual audible output on the laptop. Windows offline
speech is available. Mic is explicit six-second local recording/transcription;
review the transcript before sending/running it. There is no continuous listening.

## 4. Memory and reviewed plans

Save a non-sensitive response preference using `remember:` and confirm it persists.
Saved preferences can be sent with account chat. Try a small supported AI action
plan, inspect it, approve one step and cancel the remainder. AI output is not a
trusted tool call. No arbitrary shell, silent deletion or automatic self-upgrade.

## Stop / limitations

STOP/Esc and global Ctrl+Alt+F12 (when registered) stop native waiting and input.
The browser aborts cancelled SDK requests when noticed; a provider may still
count an already-sent request. Keep the browser connection tab open for account
chat. Its temporary authenticated relay binds only to 127.0.0.1 and exposes text
chat endpoints, never computer-control/file endpoints. See ACCOUNT-CHAT.md.

Windows/browser CI uses synthetic windows and mocked account AI. It cannot prove
real account sign-in, allowance, model quality, target-PC mic permission or sound.
