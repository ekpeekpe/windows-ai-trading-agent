# Windows setup and real-terminal acceptance

This is a **development pilot**, not a production release or autonomous trading system.

## Prerequisites

Windows 10/11, 64-bit Python 3.12, Node.js 22, authenticated MetaTrader 5 desktop terminal. For the Tauri 2 developer shell install Rust with MSVC target, Microsoft C++ Build Tools and WebView2.

## Backend (PowerShell)

```powershell
git clone https://github.com/ekpeekpe/windows-ai-trading-agent.git
cd windows-ai-trading-agent\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[windows,dev]"
python -c "import secrets;print(secrets.token_urlsafe(32))"
```

Copy the generated random token into the local environment variable; do not use the example placeholder as a token. Use only the provider keys you intend to use.

```powershell
$env:AGENT_LOCAL_TOKEN = "<your-random-token>"
$env:OPENAI_API_KEY = "<your-key>"
# Optional, if you want another provider:
# $env:ANTHROPIC_API_KEY = "<key>"
# $env:GEMINI_API_KEY = "<key>"
# Optional, to pin terminal and prevent account switching:
# $env:MT5_TERMINAL_PATH = "C:\Program Files\MetaTrader 5\terminal64.exe"
# $env:MT5_EXPECTED_LOGIN = "<numeric-account-login>"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

No broker password is needed or stored. Keep provider credentials out of Git; environment-based storage is a development compromise, **not Windows Credential Manager integration**. Rotate any compromised key in the corresponding provider dashboard and restart the backend.

## Frontend and Tauri

In another PowerShell terminal, from the repository root:

```powershell
cd desktop
npm install
npm run dev
```

Open the local URL shown (usually `http://127.0.0.1:5173`), paste the same local access token in the UI, and check terminal status. Select the provider and model and send an instruction.

With Rust and Windows Tauri prerequisites installed, use `npm run tauri dev`. The Python backend still runs **manually** in the other terminal. Tauri's installer/production sidecar is not implemented; bundling is disabled.

## MQL5 chart companion (uncompiled)

1. In MT5, choose **File → Open Data Folder** and copy `mt5/ChartControlEA.mq5` into `MQL5\Experts`.
2. Open it in MetaEditor and compile with F7, recording the actual compiler result.
3. Attach the EA to one chart. Verify the Experts journal prints its online message.
4. Locate the shared folder, usually `%APPDATA%\MetaQuotes\Terminal\Common\Files`. Set `MT5_COMMON_FILES` to that actual folder.
5. Only after confirming installation, set `$env:ENABLE_CHART_CONTROL = "1"` in the backend terminal and restart it.
6. With the same local token, send a chart command:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/chart" -Method Post -Headers @{"x-agent-token"=$env:AGENT_LOCAL_TOKEN} -ContentType "application/json" -Body '{"operation":"OPEN","symbol":"EURUSD","timeframe":"H1","period":20}'
```

Verify EURUSD H1 appeared in **real MT5**. Next try `"operation":"SMA"` and `"period":20` and verify the chart's indicator list. Supported commands are OPEN, SMA and EMA only. A response labelled `EA_REPORTED_OK` reflects a response from the companion, not proof from this development environment that MetaEditor or MT5 ran. IPC has bounded expiration and does not silently retry unknown outcomes. If a command times out, inspect the chart and the fixed request/response files before attempting recovery.

## Voice

Push-to-talk records only after granting microphone permission. Stopping sends the recording to OpenAI transcription, regardless of which provider is chosen for reasoning. The transcript is displayed for review before Send. Spoken responses use browser/OS speech synthesis; WebView2 permissions/available voices must be tested on Windows. **Voice text never counts as trade approval.**

## Stop

Press Ctrl+C in the backend and frontend consoles. The UI's Stop button aborts client requests but cannot guarantee an already running synchronous provider call has terminated. The proposal store is in-memory and account trading is disabled. Local event audit JSONL defaults to `~/.windows_ai_trading_agent/audit.jsonl`.
