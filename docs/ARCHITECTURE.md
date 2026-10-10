# Development architecture

- **UI:** React/TypeScript/Vite over loopback development proxy `/api`. Minimal Tauri 2 dev shell. The Python backend is launched manually; no production sidecar or MSI installer exists.
- **Authentication:** local bearer-like access token in `x-agent-token` header. API keys live only in backend environment variables (no OS credential vault yet).
- **Agent:** bounded provider-specific adapters for OpenAI chat completions, Anthropic messages and Google Gen AI function calls; all share the typed tool registry and cannot call arbitrary code or shell.
- **MT5:** official `MetaTrader5` Python gateway used only with a real signed-in Windows terminal. Pinned terminal/account, actual status, symbols/specifications, ticks, bars, positions, orders. No simulated data in production paths.
- **Charts:** restricted, optional `ChartIPC` + MQL5 companion with fixed request/response files under MT5 Common/Files; supported commands OPEN/SMA/EMA. Safe unknown outcomes do not retry automatically. EA remains uncompiled and real-terminal untested.
- **Speech:** WebView/browser microphone capture, OpenAI STT backend, system speechSynthesis output. Review transcription before send; voice cannot approve financial execution.
- **Safety:** drafts are immutable proposals with expiry, exact-input/context binding, single-use decisions, and redacted append-only event audit. Both acknowledgement and rejection are explicitly **non-executing**. No broker order submission/reconciliation.

See `docs/SETUP.md`, `docs/TESTING.md` and `docs/STATUS.md`. This implementation is extensible but **not production-ready**.
