# HASEEB AI Jarvis — Ollama Chat Setup (No Coding)

This enables **local chatbot answers** on the Windows 11 Jarvis dashboard. It does **not** install a remote-control service, grant autonomous desktop access, or make Jarvis a cloud chatbot.

1. Install the official **Ollama for Windows** app from https://ollama.com/download/windows and open Ollama from the Windows Start menu. No programming required.
2. Open the **HASEEB AI - Jarvis** Desktop shortcut and locate **Setup AI** in the top bar.
3. If the top status says **OLLAMA · INSTALL REQUIRED**, install Ollama using its official installer, then reopen Jarvis and click Setup AI.
4. If the status says **OLLAMA · OPEN APP**, start Ollama from the Windows Start menu, then click Setup AI again. A dialog can ask to launch the local server, only after your confirmation.
5. If the status says **OLLAMA · MODEL NEEDED**, press Setup AI, approve the **qwen2.5:1.5b** download (approximately 1 GB, plus extra storage and RAM needed) and keep an internet connection while it completes.
6. Once model verification succeeds, Jarvis selects **Local AI chat** automatically. Type **Salam Jarvis, mera naam kya hai?** or **Mujhe website design ke 3 ideas do** and press Send. The model only knows details the user shares or saves; it does not know private facts by default.
7. To control Windows apps, switch back to **Computer commands**; to generate reviewable action plans, choose **AI action plan**. The chat mode itself does not automatically control the computer.

The **Local AI** request uses only `127.0.0.1:11434` with proxy disabled. This is a local HTTP request on your own device. No ChatGPT/OpenAI or third-party hosted API is required to answer via Ollama. Browser search commands are separate and can open public sites.

**Important:** The 1.5B model is deliberately small to fit modest 8 GB Windows PCs. It will be slower on a CPU-only computer and will make mistakes. It does not know current live news without an additional source. Long downloads, Windows antivirus restrictions, model loading and first response can take time. The exact performance and installation must be verified on the user's own laptop; passing GitHub tests does not confirm that local model answers worked on the laptop.

If you see **OLLAMA · READY** but chat fails, open Ollama in Start menu, use Jarvis Setup AI again, and report just the error text (no secrets). There is no need to disable Smart App Control or Defender.

Official docs: https://docs.ollama.com/windows and https://docs.ollama.com/api/chat
