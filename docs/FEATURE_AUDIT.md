# Feature audit — premium Windows UI, 2026-10-10

Status definitions: `CODED` means source exists, `MOCK` automated fake provider/terminal, `WINDOWS CI` means previously tested on hosted Windows build, and `PENDING` means no execution evidence yet.

| Capability | Implemented | Automated evidence | Verified packaged Windows v0.3 | Limitations |
|---|---|---|---|---|
| Fixed-size chat, anchored composer, internal scrolling | CODED | Playwright added; results pending | PENDING | Must inspect rendered Windows WebView |
| File/AI Provider/MetaTrader/Tools/View/Help menus | CODED | Playwright added | PENDING | In-window menus, no OS-native File/Exit action |
| Provider API-key save/remove/test | CODED | Mocked backend tests previously passed | PENDING | Real credentials not available |
| ChatGPT account/Codex plan login | NO | None | PENDING | Approved client ID and commercial eligibility required |
| OpenAI/Anthropic/Gemini tool calling | CODED | Mocked provider tests | PENDING | Valid credentials and real inference needed |
| New conversation/export | CODED | Playwright added | PENDING | In-memory only; export is local text |
| Voice transcription/speech synthesis | CODED | Mocked voice tests | PENDING | Real microphone, WebView2 and provider key required |
| MT5 discovery and explicit terminal selection | CODED | Mock filesystem tests | PENDING | Broker terminal discovery must be tested on Windows |
| Actual quotes/account inspection | CODED | Mock terminal tests | PENDING | Real authenticated MT5 and fresh market data required |
| Chart IPC and MQL5 EA | CODED | Mock IPC tests | PENDING | EA compilation + real chart verification required |
| Trade proposal acknowledgement | CODED | Independent safety tests | PENDING | Order execution deliberately disabled |
| Protected provider credential storage | CODED | Mock Windows Vault tests | PENDING | Real Windows Credential Manager test required |
| Diagnostics and read-only health | CODED | HTTP route/sidecar tests | PENDING | Packaged v0.3 smoke test |
| Installer build/launch/shutdown | CODED | Previous v0.2 Windows CI passed | PENDING | New v0.3 build and clean GUI test required |
| Signing and Defender malware scan | PARTIAL | Signature/scan CI stage added; not executed | PENDING | Publisher certificate & actual detection details needed |
| Keyboard accessibility | CODED | Playwright Escape/menu/appearance tests added | PENDING | Screen reader/real audio user test required |

Read-only trading and restricted tool execution must not be relaxed for a UI or installer feature.
