# AI connection eligibility and privacy (October 2026)

## OpenAI / ChatGPT
OpenAI has introduced Sign in with ChatGPT for participating partners, including (where eligible) separate permission to use a customer's ChatGPT plan. This independent commercial Windows desktop app has **not** been approved/registered as a partner. Neither login nor subscription usage is implemented. Do not attempt undocumented ChatGPT OAuth endpoints, cookie or token extraction. Official details:
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
