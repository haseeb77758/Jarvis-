# Jarvis — ElevenLabs voice setup

1. Update Jarvis, then close and reopen it.
2. Open **Voices** below chat, or **••• → Voice / ElevenLabs**.
3. Select **ElevenLabs**. Open **API keys** to create/copy your own key in your account.
   Give the key Text to Speech access. Do not paste it into GitHub or chat.
4. Copy a voice ID from your ElevenLabs account into **Voice ID**. The included
   example ID is from ElevenLabs' official SDK README; account access can vary.
5. Language: `auto` for mixed text, `ur` for Urdu, `en` for English. The integration
   uses Eleven v3. Use Urdu script with an appropriate voice/accent for clearer
   Urdu; Roman Urdu pronunciation depends on the model and selected voice.
6. Accept the spoken-text disclosure, click **Save settings**, then **Test voice**.
   This sends the test sentence to ElevenLabs and can use account credits.
7. Enable **Speak replies**. Main chat and Sandbox use these settings. The Sandbox
   has its own Speak replies checkbox. Mic recognition remains local and reviewed.

## Credentials and playback

- Internet, an account API key and available credits are required. The GitHub SDK
  is open source; this does not make the hosted voice API unlimited or free.
- **Remember key** uses Windows DPAPI for the current Windows user. Without it,
  the key lasts only in the running app. No key is stored in preferences or code.
- **Forget key** deletes this app's saved credential. Revoke at ElevenLabs if you
  want to invalidate the key itself. Windows speech is available without a key.
- Only spoken reply text (up to 1,800 characters per reply) is sent, not raw mic
  audio, screenshots or the full chat history. Generated audio stays in memory.
- STOP cancels local playback and discards pending audio. It cannot undo a request
  already received by the provider. No automatic retry spends more credits.
- Errors appear as a safe notice in chat: check API key/permissions, voice ID,
  credits/rate limits or internet, depending on the notice. Key values and raw
  provider errors are not written to chat/activity logs.
- Readiness shows **Configured, not verified** for a saved cloud configuration.
  A real **Test voice** with your key is needed to verify account access and audio.

## Official references

- https://github.com/elevenlabs/elevenlabs-python
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- https://elevenlabs.io/docs/overview/models
- https://elevenlabs.io/docs/help-center/other/what-languages-do-you-support
