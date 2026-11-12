# Jarvis free neural voices

Jarvis uses [rany2/edge-tts](https://github.com/rany2/edge-tts), an open-source
client for Microsoft's **online** Edge speech service. This option needs no API
key or paid account in the client. It is not a downloaded/offline voice model,
and service/voice availability is controlled by the provider.

## Use it

1. Update Jarvis and restart the app.
2. Open **Voices** below chat or **••• → Voices / Free neural / ElevenLabs**.
3. Choose **Edge Neural (free online)**.
4. Choose your voice:

| Voice | Language | Voice ID |
| --- | --- | --- |
| Asad | Urdu male | ur-PK-AsadNeural |
| Uzma | Urdu female | ur-PK-UzmaNeural |
| Ryan | British English male | en-GB-RyanNeural |
| Sonia | British English female | en-GB-SoniaNeural |
| Guy | American English male | en-US-GuyNeural |
| Jenny | American English female | en-US-JennyNeural |

5. Start with **−5%** speed for a slightly calmer delivery; change to **+0%** for
   normal speed. Speed does not guarantee a particular speaking style or accent.
6. Tick the disclosure to send spoken reply text to Microsoft, then **Save**.
7. Press **Test voice**, then enable **Speak replies**. Sandbox has its own
   Speak replies checkbox and uses the shared provider/voice settings.

For spoken Roman Urdu, keep **FAST Urdu accent** enabled (default). Jarvis
now converts the spoken copy locally to Urdu script using `urdunlp`; chat text
stays Roman Urdu. No extra account AI request or quota is used by this step.
Free neural speech is streamed: MP3 frames begin playing as they arrive,
rather than waiting for the entire generated audio. The first reply may spend
additional time loading the local language tables. The Microsoft online
speech service still requires internet, consent and availability.

If a name or English technical word is read incorrectly, you can turn FAST
off and leave **AI Urdu conversion** enabled. That existing mode may improve
pronunciation for some sentences, but it uses an additional account AI call,
takes longer, and may also introduce errors. With both FAST and AI checked,
FAST takes precedence. Using English voices for full English text is best.
Neither mode guarantees human-quality pronunciation; listen on your PC.

English-only messages and existing Urdu-script messages are not locally
retransliterated. Markdown, URLs and fenced code are removed from the
spoken copy, while visible chat content is unchanged.

## Data and cancellation

Only the spoken reply text (up to 1,800 characters per reply) goes to the speech
service. Mic recognition remains local. The app keeps returned MP3/PCM in memory
for playback; it does not save chat audio. No ElevenLabs key is sent by this
provider. Windows speech remains available offline; ElevenLabs remains optional.

STOP cancels the pending network task and local playback, but cannot unsend text
already received by the service. Unavailable network/service errors appear in
chat without automatically switching to a paid provider. No promise of unlimited
access, uptime, or commercial service rights is made by this integration.

## Verification and source

Unit tests mock the service and exercise cancellation, size limits and provider
routing. A Windows test creates and decodes a synthetic MP3 without a network or
speakers. The optional live Windows CI step generates short Urdu/English samples
and uploads **Jarvis-Free-Voice-Samples** only when the service succeeds. Check
that step's own outcome: it is optional and does not determine the whole build's
success. Laptop audio output, voice quality and local network still need testing.

This integration uses unmodified edge-tts 7.3.1. See THIRD-PARTY-NOTICES.txt,
EDGE-TTS-LICENSE.txt and GPL-3.0.txt for license/source/rebuild details. No
Microsoft voice model weights or recordings are redistributed as app assets.

Official client source: https://github.com/rany2/edge-tts/tree/7.3.1
