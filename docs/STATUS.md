# Pilot status — initial foundation

## Verified environment
- Repository was empty at first inspection; source initialized from scratch.
- Builder runtime: Linux Python 3.13.5 and Node 22.16.0.
- Rust is absent; MetaTrader5 Python package and Windows MT5 terminal are unavailable.
- No actual quote, real broker identity, chart operation or order submission has been observed.

## Implementation evidence and verification
- Source now contains authenticated local API routes, voice-recording frontend code, a transcription route and chart IPC. These implementations are **not** real-terminal or microphone acceptance results.
- Added mock-backed agent tool-call tests in backend/tests/test_agent.py; their passing status has not been independently confirmed.
- Broker order submission remains disabled, including after an approval.

## Delivered
- Python read-only MT5 adapter, bounded tool registry, OpenAI SDK orchestration.
- Trade proposal lifecycle and explicit decision endpoint; **approval cannot execute any trade**.
- FastAPI development API; React/Vite typed-chat skeleton.
- Offline tests for tool schema and proposal safety.

## Pending
- Execute tests on Windows, install MT5 and verify account selection and live quotes.
- Bind frontend to a production-authenticated Tauri command/IPC layer.
- Verify the implemented voice capture/transcription and browser speech playback on real audio hardware, then complete accessibility review.
- Compile and verify companion chart control and IPC on a real Windows MT5 terminal.
- Add Anthropic and Gemini provider adapters, cancel support, protected OS credential store.
- Add complete broker checks, exposure limits, timeout reconciliation, and independently gated order execution.
- Real-terminal acceptance tests must be run with an authenticated demo account.

## Security notice
The dev backend is loopback-only and source requires AGENT_LOCAL_TOKEN on protected routes; production-grade credential storage and IPC hardening remain pending. Do not forward ports or expose the API to a network. Do not enable actual trading against this foundation. The MT5 adapter's symbol_select may change terminal Market Watch visibility; quote queries do not alter account positions.
