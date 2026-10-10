# Pilot status — 2026-10-10

**Development implementation only; not a completed Windows acceptance-tested trading agent.**

## Results actually observed

- **PASS** — Python portable backend tests on Linux/Python 3.13: **45 passed, 2 skipped** at last local run. Tests use explicit mocked MT5/provider/chart/speech dependencies; passing results do not prove any live integration.
- **PASS** — Python source `compileall` completed and FastAPI `GET /health` returned HTTP 200 with `trading_enabled:false`, `chart_control_enabled:false` and `authentication_required:true`.
- **PASS** — Implemented changes committed to the private GitHub repository; latest SHA should be verified from the branch before deployment.
- **BLOCKED** — Real Windows MetaTrader 5 account, read-only quotes and OHLC retrieval: no authenticated Windows terminal available here.
- **BLOCKED** — Actual OpenAI, Anthropic or Gemini API calls: no live API credentials were used. The tool-call tests for all three use explicit fakes.
- **BLOCKED** — Microphone/transcription and speech output with Windows hardware: no real speech provider or audio hardware used. Audio mock tests pass only.
- **BLOCKED** — MQL5 companion compilation and live chart/indicator change: no MetaEditor or MT5 available. File IPC simulated tests passed; never classify those as real chart operations.
- **BLOCKED** — Frontend build in local container: `npm run build` produced TypeScript missing React/JSX-module errors because Node dependencies are not available offline. Re-test on a connected Windows machine and inspect GitHub CI.
- **BLOCKED** — Tauri 2 desktop/installer validation: Rust and Windows toolchain are absent. Tauri dev scaffold exists, but the backend is started separately; no production sidecar or installer.
- **NOT TESTED** — Demo-order execution and result reconciliation. There is no broker order submission endpoint; trade execution is deliberately disabled.
- **NOT TESTED** — GitHub Actions job results: workflow source is present, but no successful workflow run has been verified through the available repository connection.

## Features present in source

- Official MetaTrader5 Python gateway for an already authenticated terminal (status, selected account, symbol list/specifications, timestamped quotes, historical rates, positions and pending orders), with no fallback to fabricated data.
- OpenAI, Anthropic and Gemini official-SDK tool adapters with bounded loops and the same schema-validated tool registry.
- Authenticated loopback FastAPI, typed React chat, provider selector, terminal diagnostics, browser microphone recording with OpenAI transcription, OS speech synthesis, repeat and client stop.
- Chart-only MQL5 companion plus atomic file request/response IPC for OPEN, SMA and EMA. Chart tools are disabled by default until explicitly enabled.
- Single-use, expiring and context-bound non-executable proposal approvals with local redacted audit events. Both rejection and acknowledgement cause **zero broker order submissions**.

## Known limitations requiring engineering work

- Exact broker volume/margin/risk validation, durable approval contexts, execution idempotency, post-order reconciliation and emergency trading disable must be engineered and verified **before** any real order submission is allowed.
- Frontend Stop aborts a client request, but cannot forcibly cancel a synchronous provider request already running server-side.
- Local token uses a developer-configured environment variable. Provider credentials are in backend environment variables; Windows Credential Manager integration is not implemented. Development HTTP API must remain bound to loopback.
- The MQL5 fixed-file protocol is not cryptographically authenticated against malicious same-user local processes and cannot be extended to trade operations without a security redesign.
- RSI/MACD/Bollinger chart configuration, removal confirmations and robust chart-state inspection beyond current EA checks are incomplete.
- Native Tauri package/sidecar launch, installer, and voice accessibility acceptance on Windows are incomplete.

## Next gate

Follow `docs/SETUP.md` and `docs/TESTING.md`: install dependencies on target Windows machine, verify the Actions build, run opt-in **real** MT5 quote and OpenAI tool tests, compile the EA, check an actual H1 chart and SMA 20, and test push-to-talk/voice output. Keep account execution disabled until risk and reconciliation work is completed.
