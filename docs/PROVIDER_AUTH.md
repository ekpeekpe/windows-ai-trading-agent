# AI connection eligibility and privacy (October 2026)

## OpenAI / ChatGPT
**Update October 2026:** This repository is public. The open-source, locally hosted flow is now implemented independently of the partner programme and uses the documented `dynamic_agent_client` first-time registration. Eligible users obtain an issued `oaiapp_…` client ID in their system browser, without sharing account passwords or buying a separate OpenAI API key. The backend verifies PKCE, state, nonce and the signed ID token, and stores refreshable credentials in Windows Credential Manager. ChatGPT-plan usage requires explicit `chatgpt.tokens.use.direct` consent and a successful Responses inference stream. A live account sign-in has **not** been verified in CI.

A paid or remotely hosted future product follows a separate commercial eligibility process. Public GitHub visibility by itself does **not** create an open-source license; the repository owner must add an appropriate license.

Implementation/eligibility: [ChatGPT / Codex authentication](CHATGPT_CODEX_ELIGIBILITY.md).

Official details:
- https://help.openai.com/en/articles/20001410-sign-in-with-chatgpt
- https://help.openai.com/en/articles/20001542-using-your-chatgpt-plan-in-other-apps-and-sites
- https://help.openai.com/en/articles/9039756-managing-billing-settings-on-the-chatgpt-web-and-api-platform

## Anthropic / Claude
Anthropic documents subscription-based Claude Agent SDK usage in certain supported contexts, but no standalone Claude account sign-in flow is registered for this application; SDK access does not by itself authorize copying Claude subscription OAuth into an unrelated commercial product. The account sign-in route is not implemented. Contact Anthropic for commercial-distribution eligibility before enabling any account-based feature.
- https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- https://platform.claude.com/docs/en/manage-claude/authentication

## API keys
OpenAI, Anthropic, and Gemini use their independent official Python SDK adapters. Keys are entered in the UI only to pass to the native bridge, stored by the backend using the Windows Credential Manager keyring; their value is **never returned** to the renderer or logged. The UI reports *configured* separately from *verified*. Verification calls the provider's model list endpoint with the supplied key when the user explicitly clicks Test connection. A successful model list check does not guarantee access to the user's selected model, available billing balance, or tool-calling support.

For local development only, provider environment variables are still supported. They override stored credentials and must never be shipped inside installers. Do not enter account passwords or browser cookies as API keys.

### Revocation and privacy
Remove a key from AI connections, or revoke it in the provider account dashboard. The application does not charge license/subscription fees in this pilot; providers may bill their own API consumption separately. Market data and chat instructions requested through the agent are sent to the selected provider; voice recordings are sent to OpenAI speech transcription when enabled, independently of the reasoning provider. The MT5 terminal and broker passwords are never shared with AI SDKs. Logs must not include credentials.
