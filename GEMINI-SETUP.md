# Gemini Free API for Jarvis — Windows 11

This is **optional text chat**, independent of LiveKit realtime voice. It does not give the AI direct permission to execute Windows actions.

## One-time setup (no coding)

1. Open https://aistudio.google.com/api-keys
2. Sign in with Google and select/create a **Free Tier** project. Check its actual billing tier in AI Studio; do not upgrade to paid merely for initial Jarvis testing.
3. Create an API key. **Do not paste it into ChatGPT or GitHub.**
4. Update/restart Jarvis on Windows 11.
5. In Jarvis select **Gemini API setup**.
6. Paste the key in the masked field and select **Save key / model**.
   Default: gemini-3.5-flash-lite. Alternate: gemini-3.1-flash-lite.
7. Select **Gemini AI chat** from the chat-mode dropdown and send: Salam Jarvis.
   Switch back to **Computer commands** for local Windows actions.

If a request returns 404, check whether the selected model is available to
your Google project and try the alternate approved model. If 429 appears,
check the project-specific rate limits in Google AI Studio.

## Cost and consent

- Google advertises Free Tier pricing for these text models, subject to
  availability, project tier and rate limits. A **paid Google project is not
  automatically free** because the same model has a free tier.
- Gemini text chat sends requests **only** when Send is pressed in Gemini
  AI chat mode. Jarvis never automatically sends screenshots, files, notes,
  saved preferences, passwords or local computer commands.
- On the Free Tier, Google may use submitted data to improve its products.
  Do not send confidential client information or secrets.
- Jarvis caps attempted requests at **30 per local day**, limits context
  and answer length, and does not retry failed requests automatically.
  This is **not** a financial spending cap: provider billing and quotas are
  authoritative.
- No API traffic begins just from app startup, settings or mode selection.

## Key security

- The key is stored under:
  %LOCALAPPDATA%\HaseebCrafts\Jarvis\Gemini\key.dpapi
- It is encrypted with Windows DPAPI for the current Windows user.
- It is never written to GitHub, passed in a URL, logged or placed in
  the assistant transcript. Settings allow you to remove it.
- Switching Windows accounts or computers may require saving a new key.
- The fixed Google HTTPS endpoint receives an x-goog-api-key HTTP header.
- Gemini replies are text only. No Gemini response can directly invoke
  Windows tools, PowerShell, mouse, keyboard or file writes. Manually
  switch to Computer commands for reviewed actions.
- STOP discards a pending response. An already-sent request may finish on
  Google's side and still count toward usage.

## Modes

**Gemini AI chat**: Roman Urdu or English conversational text. Recent chat
history is sent as context only after pressing Send. It remains in RAM
until Clear activity or app close. No Gemini voice engine is added.

**Computer commands**: Existing local reviewed Windows actions, with no
Gemini API request.

**Talk Live**: Existing separate LiveKit realtime voice with its own keys,
credits and diagnostics. Gemini text integration does **not** repair the
LiveKit realtime_model_error.

## Official references

- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/docs/generate-content/text-generation
- https://ai.google.dev/gemini-api/docs/api-key
