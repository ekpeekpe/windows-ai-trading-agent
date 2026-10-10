# ChatGPT / Codex sign-in for the open-source Windows agent (October 2026)

## What changed

The GitHub repository is now **public**, and the Windows agent implements OpenAI's documented **open-source dynamic registration**. This is different from the commercial partner website / plugin OAuth programme. First sign-in uses the published bootstrap identifier `dynamic_agent_client`. OpenAI, **not the application developer**, issues a per-account `oaiapp_…` client ID during the actual browser authorization. Neither a paid OpenAI API key nor a pre-registered commercial partner client ID is needed for this OSS flow.

This is for genuinely open-source, locally hosted applications. **Public visibility alone does not establish an open-source license.** This repository had no `LICENSE` file when inspected. The project owner must select and publish an OSI-compliant software license, taking future paid commercial distribution into account. If the product later becomes a paid or remotely hosted service, apply for the separate OpenAI partner programme: https://developers.openai.com/siwc/request-client-id .

Official references:
- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
- https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server

## App flow

1. Launch **AI Trading Agent → AI Provider → Connections and API keys**.
2. Choose **ChatGPT plan (Codex)**; select **Continue with ChatGPT**. The backend opens the Windows system browser, not a webview or unofficial ChatGPT login.
3. OpenAI's browser authorization shows the permissions requested: `openid profile email offline_access resource.invoke chatgpt.tokens.use.direct`. Consent may require an eligible ChatGPT account/workspace.
4. The browser returns to a random `http://127.0.0.1:PORT/auth/callback` listening only for this attempt. The local Python backend validates state, nonce, callback host and PKCE, exchanges the code at the **official OpenAI OAuth token endpoint** and checks the signed ID token against official JWKS before storing it.
5. A dynamically issued account/client ID and rotating tokens are stored in **Windows Credential Manager**; never in the frontend or an API-key field. Choose **Refresh status**, then **Load account models** and **Test real ChatGPT inference**. Model list visibility is not proof of entitlement; completion of an actual Responses stream is.
6. The **ChatGPT plan** provider can then answer chat messages. The Responses adapter permits only the existing typed read-only MT5 tools, and never brokers orders. Tool calls will report unavailable/disconnected markets rather than fabricate prices.
7. **Disconnect** attempts OpenAI's published refresh-token revocation endpoint and removes local credentials, even if remote revocation cannot be confirmed.

Do not obtain client IDs from other apps, copied Codex CLI tokens, browser cookies, or the ChatGPT desktop app. No client secret is embedded. Every installation receives its own stable opaque `ext_agent_host_id` identifier in protected local storage.

## Limits, tradeoffs and acceptance

- No successful live OpenAI OAuth callback or inference has been witnessed in CI, which deliberately has no user's ChatGPT credentials. Mock-backed OAuth callback, replay, expiry, refresh and tool-loop tests are distinct from a real sign-in.
- OpenAI's documented OSS plan-usage Responses contract requires `store=false`, `stream=true`, history sent as inputs, and function tools in namespaces. The backend uses these properties. It sends no unsupported background jobs, browser scraping, or system shells.
- This **direct Responses integration** provides Codex-capable ChatGPT plan inference. It does not claim to bundle the separate `codex app-server` binary or grant unrestricted Codex shell privileges. Codex app-server is an optional later implementation; it also requires the same authorized OAuth token and attribution.
- The account model catalog does **not** establish usage quota or credits; direct the user to ChatGPT Settings → Usage for actual account-scoped limits. Subscription plan use does not use the OpenAI API-key billing credential.
- The OpenAI plan-inference preview may not support audio transcription; the separate microphone transcription feature currently requires an OpenAI API key. Windows TTS does not require the API key.
- Each login is independent of MetaTrader; MT5 must be installed and signed in separately for actual market data.
- Real trading remains completely disabled.
- When signed out locally but remote revocation could not be verified, revoke the integration in ChatGPT Settings.
