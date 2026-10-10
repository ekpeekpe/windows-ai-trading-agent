# Windows AI Trading Agent — developer pilot (not live-trading ready)

Local-first, Windows-oriented MT5 assistant with typed chat, OpenAI/Anthropic/Gemini tool-call adapters, opt-in chart helper, microphone transcription, and deliberately disabled broker execution.

**This is a development build.** The Python source and mocked integrations have portable tests. No Windows terminal, AI provider, MQL5 compilation, voice hardware, or Tauri package has yet been verified end-to-end.

## Architecture

- `backend/`: FastAPI + official provider SDK adapters + `MetaTrader5` Python read API.
- `desktop/`: accessible React/Vite development interface; minimal Tauri 2 dev shell under `src-tauri/`.
- `mt5/ChartControlEA.mq5`: restricted chart-only companion with request/response files.
- `docs/SETUP.md`: exact Windows installation and launch instructions.
- `docs/STATUS.md`: evidence and remaining acceptance criteria.

## Local commands (Windows PowerShell)

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[windows,dev]"
$env:AGENT_LOCAL_TOKEN = "replace-with-a-random-32-byte-token"
$env:OPENAI_API_KEY = "your-own-api-key"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

In a separate terminal:

```powershell
cd desktop
npm install
npm run dev
# or: npm run tauri dev (needs Rust, Tauri Windows prerequisites)
```

Enter the same local token in the frontend. The frontend does not store provider API keys. Only `/health` is accessible without the local token. For voice recognition, the selected reasoning provider can differ from the speech provider (OpenAI transcription).

The backend **has no `order_send` entry point**. A proposal acknowledgement returns `approved_not_executed`; it never places a trade. Do not deploy or expose the development service on a network.

## Tests

```powershell
cd backend
python -m pytest -q
```

Real terminal/provider tests are opt-in; see `docs/TESTING.md`. All production packaging, broker order validation and demo execution remain incomplete.
