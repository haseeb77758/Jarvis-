## NEW (13 Nov 2026) — Gemini Free API chat

Jarvis mein Gemini AI chat ab separate optional text mode hai. Pehle
https://aistudio.google.com/api-keys se **Free Tier** project ki key banao.
Key ChatGPT/GitHub mein share mat karna. Jarvis ke **Gemini API setup** mein
paste karke Save dabao. Phir chat dropdown mein **Gemini AI chat** select
karke 'Salam Jarvis' send karo. Default free-tier text model
**gemini-3.5-flash-lite** hai. Agar project access 404 aaye, settings
mein **gemini-3.1-flash-lite** try kar sakte ho.

Ye **text chat only** hai; Gemini voice aur desktop control automatically
nahi karta. **Computer commands** mode mein Windows ke approved commands
chalenge. **Talk Live** alag LiveKit voice option hai. Google Free Tier
prompts product improvement ke liye use kar sakta hai—confidential client
data mat bhejo. Detailed steps: [GEMINI-SETUP.md](GEMINI-SETUP.md).

---

# HASEEB AI / JARVIS — LiveKit-only voice assistant

Created by Haseeb Crafts.

## Naya direct desktop LiveKit — current setup

**Talk Live ab seedha Jarvis ki dedicated desktop voice window kholta hai,**
LiveKit Cloud Console ka round-trip nahi. Existing training-2057 agent
se WebRTC par connection hota hai. Local Python blingfire DLL ki zaroorat
nahi; native Windows Smart App Control ko disable mat karo.

Ek dafa **LiveKit setup -> One-time LiveKit project keys** mein project
wss URL, API key aur API secret save karo. Phir Talk Live dabao, Cloud
credits consent approve karo, aur mic permission allow karo.

**Voice se apps/files ke liye:** LIVEKIT-DIRECT-DESKTOP.md ke mutabiq
Builder mein desktop_command Client Tool ek dafa configure karke Deploy
karna lazmi hai. Agent uske baghair voice requests ko desktop actions mein
convert nahi karega. Har action native Jarvis confirmation se guzarta hai.
No shell, delete ya unrestricted screen access. Desktop STOP aur auto
10-minute timer Cloud room ko end karne ki koshish karte hain; network
failures mein provider session check karna zaroori hai.

## Purani Cloud Console instructions (superseded)

Jarvis mein ab **Puter Connect AI, Sandbox, AI Chat, Ollama aur alternate
voice-chat UI** nahi chalengi. Jarvis ke main dashboard par **Talk Live**
hi ek AI conversation option hai: `GPT-Live-1`, `marin` voice.
Ab Talk Live **official LiveKit Cloud Agent Console browser** mein kholta hai.
Windows `blingfire` native DLL block hone par bhi ye browser route chal sakta hai.
Jarvis **browser ki call ko STOP ya 5/10/15-minute timer se band nahi kar sakta**.
Call ko browser mein khud End Call/Disconnect karna hoga.

**Important:** LiveKit GPT-Live-1 usage-based billed provider hai. Free
unlimited nahi. Session har dafa tumhari permission se start hogi.

## Windows par chalane ke steps (recommended browser mode)

1. Jarvis mein **Update Jarvis** chalao aur verified update ke baad restart karo.
2. Dashboard mein **Talk Live** click karo. Official LiveKit Cloud browser mein
   khulegi; **local Python DLL, pip repair, API secret file ki zaroorat nahi**.
3. LiveKit Cloud login karke apna project kholo, **Agents** mein jao,
   **training-2057** select karo aur **Launch Console** dabao.
4. Browser ko microphone permission do aur wahan se voice conversation start
   karo. LiveKit Cloud credits/usage apply ho sakti hai.
5. **Browser mein End Call/Disconnect zaroor dabao**. Jarvis STOP aur local
   5/10/15 minute timer browser call ko band nahi kar sakte.

**Advanced local Python mode** alag option rahega; woh Windows Application
Control mein `blingfire` DLL block hone ki wajah se fail ho sakta hai.
Windows security disable na karo. Browser mode mein local project API keys
store karne ki bhi zaroorat nahi.

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
