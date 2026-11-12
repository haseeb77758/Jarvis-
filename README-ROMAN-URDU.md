# HASEEB AI / JARVIS — LiveKit-only voice assistant

Created by Haseeb Crafts.

## Ab sirf LiveKit chatbot / voice AI hai

Jarvis mein ab **Puter Connect AI, Sandbox, AI Chat, Ollama aur alternate
voice-chat UI** nahi chalengi. Jarvis ke main dashboard par **Talk Live**
hi ek AI conversation option hai: `GPT-Live-1`, `marin` voice.
AI agent abhi alag LiveKit console mein bolta hai; Jarvis orb aur
dashboard session status/STOP ko control karte hain.

**Important:** LiveKit GPT-Live-1 usage-based billed provider hai. Free
unlimited nahi. Session har dafa tumhari permission se start hogi.

## Windows par chalane ke steps

1. Jarvis mein **Update Jarvis** chalao, verification pass hone par restart karo.
2. **LiveKit setup** kholo. Pehli dafa ho to **Install / repair LiveKit voice tools**
   click karo.
3. `https://cloud.livekit.io/` par apna project kholo, **Manage API keys**
   se project key aur secret lo; project ka `wss://...` URL bhi copy karo.
4. **Open LOCAL API key + secret file** mein ye values PC par enter karo:
   `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`. Secret chat ya
   screenshot mein expose mat karna.
5. Main dashboard par **Talk Live** click karo. Billing/usage prompt approve
   karo. Voice session shuru hogi.
6. **End Live Voice**, STOP ya Ctrl+Alt+F12 se session band karo.
   5, 10 ya 15 minute local auto STOP milta hai; ye paison ki cap nahi.

Detailed help: [LIVEKIT-VOICE.md](LIVEKIT-VOICE.md).

## Purane chatbot ka kya hua?

Purana Puter browser sign-in, Sandbox, AI action plans, free Edge TTS aur
Whisper mic **Jarvis native dashboard se remove/disable** hain. Koi
background alternate chatbot connect nahi hoga. Code ke kuch purane
compatibility modules sirf installed older updater ke verification ke liye
source mein hain, use karne ke liye visible nahi hain. Jarvis Windows
se unrelated installed software/data khud se delete nahi karta.

## Local desktop commands alag hain

Text input ab **local desktop command box** hai, general AI chat nahi.
Yahan `calculator kholo`, `notepad kholo`, `windows`,
`inspect: Notepad`, `screenshot`, `volume up`, `note: meeting`
jaise supported commands chalenge. Unknown text kisi remote AI ko nahi
bheja jayega; local help milegi.

Screen click/type par permission aur review zaroori rehta hai. **LiveKit
voice agent abhi desktop apps control nahi karta**: voice se Windows
commands execute karne ke liye alag safe tool integration chahiye.

## Installation

Official Python 3.12 aur Windows 11 chahiye. Complete source ZIP extract
karke `START-JARVIS-GUI.pyw` chalao. Windows Defender/Smart App Control
disable mat karo. Existing user memory, apps aur LiveKit keys safe rehengi.

CI tests passing hone ka matlab actual PC par LiveKit Cloud connection
test nahi hua; apni credentials ke saath voice session tumhe test karni hai.
