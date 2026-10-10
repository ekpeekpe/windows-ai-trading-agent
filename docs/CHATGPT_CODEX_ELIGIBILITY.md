# Official ChatGPT / Codex account integration assessment — October 2026

The app is presently **private-source, Windows desktop, intended for commercial distribution**, with no verified Sign in with ChatGPT client ID or approved redirect registrations. This is not the same scenario as an approved open-source Codex client.

## Documented paths

1. **Sign in with ChatGPT identity**: OpenAI's official programme uses registered application clients and controlled sign-in flows. Registration and the user's consent are prerequisites. A ChatGPT identity token is not a generic OpenAI API key.
2. **ChatGPT plan usage / Codex app-server**: OpenAI documents configuring Codex app-server with a ChatGPT-plan-authorized OAuth access token for an eligible participating app. This uses Responses requests, not the existing official API-key Chat Completions adapter. Even `model/list` can be merely a catalog and is **not** a proof of model entitlement. A successful inference turn verifies access to that model for that request.
3. **Codex CLI personal login**: Codex CLI's own Sign in with ChatGPT does **not** authorize copying its token, browser cookies, browser profiles, or account session into this separate private commercial application.
4. **OpenAI API keys**: Implemented independently through official SDKs and Windows Credential Manager. They are usage-billed separately from ChatGPT subscription entitlement.

## Implementation decision

- API-key mode is available and unchanged.
- The UI truthfully explains that ChatGPT/Codex sign-in is **not enabled**, and links to official registration guidance. No dead or misleading sign-in button is shown.
- No OAuth authorization endpoint, client secret, redirect URL, PKCE callback, token sharing or Codex app-server child process is invented or embedded.
- To enable an official flow, the publisher must first obtain the approved client ID and registered callback and confirm that **private commercial redistribution** is permitted for the selected ChatGPT-plan product. After registration, implement browser authorization with PKCE/CSRF/redirect checks, protected OS token storage, disconnect/revocation, and a real permitted inference test. Do not silently reuse the API-key tool loop as subscription inference.
- Codex usage/quota/credit figures are **not implemented**: no approved account-scoped endpoint and authorized token are configured. No numbers, credit balance, or reset times should be displayed without a documented authorized data source.

References:
- https://developers.openai.com/siwc/quickstart
- https://developers.openai.com/siwc/request-client-id
- https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server
- https://help.openai.com/en/articles/11381614-api-codex-cli-and-sign-in-with-chatgpt

## External action needed

Request a client ID and commercial-use eligibility decision using the official OpenAI registration process. Once approved, register the exact desktop redirect and permitted inference interface; do not guess values. Account eligibility is **BLOCKED** until then. The existing OpenAI, Anthropic, and Gemini API-key routes remain independent.
