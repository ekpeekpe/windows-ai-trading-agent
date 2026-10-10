# Pilot status — evidence recorded 2026-10-10

This is a development pilot, **not** a verified Windows MT5 release. Real trade submission remains disabled.

## Executed in Linux development runtime (Python 3.13.5)

- **PASS:** `python -m pytest -q`: **45 passed, 2 skipped** in approximately 1.4 seconds, against the available local source snapshot with the MT5 quote and HTTP regression changes. The two opt-in tests require a real MT5 terminal and live AI credentials. The local snapshot is not a full authenticated checkout, so GitHub CI must independently verify the complete remote tree.
- **PASS:** `python -m compileall -q app`.
- **PASS:** Uvicorn started a real HTTP service on `127.0.0.1:18765`. Actual HTTP requests returned `GET /health = 200`, unauthenticated `GET /terminal = 401`, authenticated `GET /terminal = 503` with the clear missing-MT5 diagnostic, and authenticated `POST /chat = 503` with the clear missing-API-key diagnostic.
- **PASS (MOCKED ONLY):** HTTP chat route -> mocked OpenAI tool call -> restricted MT5 quote tool -> fake terminal quote -> mocked provider response. The test quote source is explicitly `MOCKED_NOT_REAL`; this is **not** a live price, provider API, UI-browser test, or broker connection.
- **PASS (MOCKED ONLY):** rejected and replayed trade proposals, exact binding/expiry, disabled execution, tool permissions, agent loop, mocked MT5 disconnect and quote rejection.
- **BLOCKED:** offline `npm ci` cannot retrieve `@tauri-apps/cli`; no dependency installation or React production build was completed locally.
- **BLOCKED:** offline `pip install -e '.[dev]' --no-index` cannot obtain build dependencies; tests used already installed portable Python packages (OpenAI/Anthropic/Gemini SDKs and MetaTrader5 are absent).
- **NOT TESTED:** GitHub Actions completion/results; workflow source includes Linux backend, Windows portable tests and one frontend build job.

## Code presently implemented (not evidence of live acceptance)

- FastAPI development backend with local token on protected routes.
- OpenAI, Anthropic, Gemini adapter source with official SDK invocation and read-only registered tools.
- MT5 Python wrapper for terminal/account status, symbol specs, fresh quotes, rates, positions and orders. A hidden symbol may be selected in Market Watch; no account trading is performed.
- React typed chat, recorded microphone transcription, browser speech playback and proposal preview.
- Restricted, opt-in chart-only MQL5 companion and file IPC, **not compiled or tested here**.
- Proposal acknowledgements return `approved_not_executed`; broker order sending is not implemented.

## Mandatory real Windows acceptance — BLOCKED

Requires Windows 10/11, 64-bit Python 3.12, Node.js 22, installed and logged-in MetaTrader 5 terminal, selected account ID, valid provider credentials and microphone/speaker hardware.

1. Follow [SETUP.md](SETUP.md) and install dependencies from a networked Windows machine.
2. Run `cd backend; python -m pytest -q` and `cd desktop; npm run build`. Check GitHub Actions independently.
3. Launch backend + frontend; check terminal status. Retrieve a real fresh bid/ask. Run `RUN_LIVE_MT5=1 python -m pytest -q -m live` in the backend on Windows. Market may be closed; stale quotes must fail rather than appear live.
4. Only with an API key and MT5, run the opt-in tool workflow `RUN_LIVE_AI=1 python -m pytest -q -m provider_live`.
5. Compile the MQL5 EA with MetaEditor and visually verify EURUSD H1 and SMA20 after confirmed IPC response. Do not treat a queued command as success.
6. Test microphone, transcription, screen-reader focus, repeat speech and speaker output on actual hardware.
7. Do not place any live or demo orders during this milestone.

## Security

The HTTP backend is loopback-only; development credentials are process environment variables, not yet an OS credential store. Never expose its port, commit tokens, or interpret fabricated test data as actual MT5 results. Approval is only a proposal acknowledgement; trade execution is disabled. Frontend cancellation cannot guarantee a synchronous provider request is terminated on the server. Tauri bundling/sidecar integration is not finished.
