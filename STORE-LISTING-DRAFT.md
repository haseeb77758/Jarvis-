# HASEEB AI Jarvis — Microsoft Store listing draft (English)

**State:** Draft for the future Microsoft Partner Center submission. No public listing, pricing, certification, or installability is claimed.

## App name

Preferred: **HASEEB AI Jarvis**

Reserve and confirm availability in Partner Center first. Do not assume the name is available.

## Short description

A local Windows 11 desktop assistant for reviewed voice commands, app shortcuts, notes and simple automation.

## Description

HASEEB AI Jarvis helps you perform supported tasks on your Windows PC using text commands and opt-in microphone transcription. Its three-panel desktop dashboard combines conversation, quick shortcuts, local notes and a record of completed actions.

**What you can do**
- Open supported local applications such as Notepad, Calculator, Paint, Edge, Chrome and File Explorer, or register an installed app.
- Open secure websites and search Google or YouTube in your browser.
- Inspect, focus and wait for named Windows windows and interact with supported accessible buttons.
- Save explicit preferences, reviewed action shortcuts and text notes locally.
- Control media play/pause, volume and next/previous tracks.
- Use an optional local language model through Ollama for AI chat and proposed multi-step actions.
- Record up to six seconds of microphone audio only after pressing Mic; review recognized speech before acting.
- Stop a pending action using the built-in STOP control.

**How controls stay safer**
Actions are limited to a supported allowlist. Screen typing and clicking require an opt-in and review. There is no automatic sending of WhatsApp messages, arbitrary shell execution or unrestricted file deletion.

**Important setup**
Local AI chat requires a separate optional Ollama runtime and downloaded language model. An Internet connection may be needed to obtain optional model files, browse websites or open third-party services. Performance depends on your PC's hardware. Jarvis is not a continuous-listening or fully autonomous computer operator.

## Suggested Store metadata

- **Category:** Productivity (verify available categories)
- **Pricing:** Free for the personal test submission (select in Partner Center)
- **Primary language:** English (US); Roman Urdu command support described in app, not a full Urdu UI localization
- **Age rating:** Complete Microsoft's real questionnaire; do not assume an age classification
- **Target devices:** Windows desktop, x64; Windows 11 testing priority
- **Visibility:** Private audience for personal testing, if selectable for the app
- **Publisher:** Individual account's actual verified identity; do not falsely represent Haseeb Crafts as a registered corporation
- **Privacy policy URL:** REQUIRED BEFORE SUBMISSION — publish the reviewed draft from `STORE-PRIVACY-DRAFT.md` at a stable public HTTPS URL and insert that URL
- **Support contact:** REQUIRED IF APPLICABLE — enter a legitimate address owned by the publisher, not a placeholder
- **Screenshot:** REQUIRED — use a real in-app capture, at least 1366 × 768 PNG; do not submit a conceptual mockup

## Screenshot caption drafts

1. **Assistant dashboard** — Access reviewed Windows shortcuts, conversation and activity history in one workspace.
2. **Local voice workflow** — Tap Mic, review the transcript and approve the intended computer action.
3. **Notes and shortcuts** — Manage explicit local preferences and saved, reviewed action sequences.

These captions are prospective; upload only screenshots of functionality actually verified on the release candidate.

## Certification notes to reviewer

HASEEB AI Jarvis is a local Windows desktop application. It uses a full-trust packaged desktop process because it interacts with supported installed application windows. It requests microphone access for explicit six-second, user-initiated speech transcription; audio is processed by a locally downloaded/bundled Whisper model. Screen input is opt-in and reviewed; the app cannot silently delete files or transmit screenshots. Local AI chat is optional through the Ollama service on localhost, with additional model downloads initiated by the user. The Store package does not contain a general remote desktop-control server.

Please test the local app shortcuts, microphone opt-in, review controls and emergency STOP. Offline functionality is available for some commands without setting up a language model. Browser links and optional model downloads need internet connectivity.

## Release readiness review

Before submission, the publisher must confirm app/store policies, user-facing screenshots, privacy policy public URL, final package identity/publisher strings, and successful installation on a Windows 11 device. Microsoft may request changes.

Official Store listing guidance: https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/create-app-submission
