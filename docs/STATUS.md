# Pilot status — initial foundation

## Verified environment
- Repository was empty at first inspection; source initialized from scratch.
- Builder runtime: Linux Python 3.13.5 and Node 22.16.0.
- Rust is absent; MetaTrader5 Python package and Windows MT5 terminal are unavailable.
- No actual quote, real broker identity, chart operation or order submission has been observed.

## Delivered
- Python read-only MT5 adapter, bounded tool registry, OpenAI SDK orchestration.
- Trade proposal lifecycle and explicit decision endpoint; **approval cannot execute any trade**.
- FastAPI development API; React/Vite typed-chat skeleton.
- Offline tests for tool schema and proposal safety.

## Pending
- Execute tests on Windows, install MT5 and verify account selection and live quotes.
- Bind frontend to a production-authenticated Tauri command/IPC layer.
- Implement voice push-to-talk and spoken response with accessibility review.
- Implement MQL5 chart companion, request/response IPC, chart verification.
- Add Anthropic and Gemini provider adapters, cancel support, protected OS credential store.
- Add complete broker checks, exposure limits, timeout reconciliation, and independently gated order execution.
- Real-terminal acceptance tests must be run with an authenticated demo account.

## Security notice
The dev backend is loopback only; there is currently no HTTP authentication. Do not forward ports or expose the API to a network. Do not enable actual trading against this foundation. The MT5 adapter's symbol_select may change terminal Market Watch visibility; quote queries do not alter account positions.
