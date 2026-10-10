# Test plan and evidence

## Portable tests

```powershell
cd backend
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q app
```

Evidence in the available Linux Python 3.13 environment: **43 passed, 2 skipped** (2026-10-10). The suite uses explicitly labelled fake MT5 modules, fake AI clients, simulated chart IPC responses, and fake speech services. These tests **do not** demonstrate a working brokerage terminal or live provider connection.

The backend compiled and `GET /health` returned HTTP 200 in local tests. Clean pip installation was blocked by offline package availability. Frontend dependency install/build was blocked by absent cached packages and no external registry access. Rust and Windows tooling were unavailable. GitHub Actions now defines Linux/Windows backend and frontend build jobs; verify their actual completed results separately.

## Live Windows MetaTrader 5 test

Install MT5, sign in without giving this application a broker password, and select an actual broker symbol. Optional: set `MT5_TERMINAL_PATH`, `MT5_EXPECTED_LOGIN`, `MT5_TEST_SYMBOL`.

```powershell
cd backend
$env:RUN_LIVE_MT5 = "1"
python -m pytest -q -m live -k actual_authenticated_mt5_quote
```

The test uses official MT5 Python APIs and checks actual terminal/account status, positive bid/ask and a nonzero tick timestamp. Failure must be diagnosed; never inject sample prices.

## Real OpenAI tool-call workflow

With a valid API key and an authenticated MT5 terminal:

```powershell
$env:RUN_LIVE_AI = "1"
$env:OPENAI_TEST_MODEL = "gpt-4.1-mini"
python -m pytest -q -m provider_live
```

This test verifies that an OpenAI chat tool call reached a real MT5 adapter. Anthropic/Gemini only have mocked adapter tests at present; live keys and capabilities remain unverified. Never label a model tested live just because its adapter passes unit tests.

## Manual EA/voice

Compile the MQL5 source in MetaEditor, install it, enable chart control and verify real EURUSD H1 creation and SMA 20 through the actual indicator list. Check malformed requests, stale/duplicate files, disconnects and timeout with **no automatic retries**.

Test microphone permission, recording, transcription, typed review, spoken response, interruption and repeat. Record actual Windows/WebView2 results separately.

## Trade safety

The tests cover rejection, acknowledgement, replay prevention, payload/context invalidation, expiry, audit records, tool permissions and forbidden `order_send`. Both rejected and acknowledged proposals must report `order_submitted: false`. **No demo or live order execution has been implemented or verified.**

Use statuses: **PASS** for executed successful tests; **FAIL** for observed failing tests/builds; **BLOCKED** for missing dependencies/OS/credentials; **NOT TESTED** for code written but not executed in its intended runtime.
