# Jarvis account chatbot — no API key or local language model

## Connect

1. Update Jarvis, close it and reopen it.
2. Click **Connect AI** and accept opening the connection page.
3. On the page, tick the chat-data disclosure, then **Sign in & connect**.
4. Sign in to your own Puter account. Return to the Jarvis desktop dashboard.
5. Keep the connection tab open while chatting. Main chat and Sandbox share it.
6. To disconnect, click **Disconnect** in that tab or close Jarvis.

Puter account authentication is handled by its official browser SDK. No API key,
manual token copying or password is entered into Jarvis. This replaces the old
local chat backend. Jarvis no longer starts, installs, checks or calls it. The app
does not uninstall software or delete model files already present on your PC.

## Free scope

Puter provides a free monthly account allowance, subject to model/account limits.
This is not unlimited free inference. Exact message counts depend on model,
context and output length. Use a free account and check the account's usage view.
The provider controls allowance/billing; an existing paid account can use its
paid entitlement. Jarvis does not buy credits or upgrade plans. Quota errors are
shown instead of silently switching to another provider. Corrections for echoed
or wrong-script replies can use one additional completion from the allowance.

Supported desktop commands still work without an AI account. AI chat and AI
plans need internet and an open, signed-in connection tab. Free Edge neural
speech is a separate online service; mic recognition and Windows speech remain
local. No model download is needed for account chat.

## Data and architecture

Native Jarvis keeps its dashboard, orb, voice controls and reviewed actions. It
starts a temporary HTTP relay only after you click Connect AI. The relay binds
to 127.0.0.1 on a random port, requires a random per-run capability for its JSON
endpoints, validates Host/Origin, and exposes no desktop-control or file APIs.
Only bounded chat messages/recent context and saved reply preferences are sent
to the Puter/model provider, after the connection disclosure. The provider's
processing policies apply. Microphone audio and screenshots are not attached.

The capability is delivered in a URL fragment (not an HTTP query), removed from
the browser address, and never logged. Puter credentials remain managed by the
browser SDK; the Python process does not receive or save the account token.
Chat state is volatile in the app. The browser/provider can retain account data
according to their own settings/policies.

STOP cancels native waiting and discards late answers; the connection tab aborts
its pending SDK call when it notices cancellation. A provider can still process
an already-sent request and count its usage. AI plans remain untrusted JSON;
existing validation, screen permission and per-action review still apply.

## Verification

Tests use an authenticated fake browser/SDK, loopback HTTP, temporary folders and
synthetic text. They verify sign-in gating, quotas, disconnects, cancellation,
late results, hostile origins, native chat history and no desktop command bridge.
A passing build does not prove a real Puter account sign-in or model response.
That requires the user's signed-in connection page on the target PC.

Official open-source platform: https://github.com/HeyPuter/puter
SDK docs: https://docs.puter.com/getting-started/
Account model: https://docs.puter.com/user-pays-model/
