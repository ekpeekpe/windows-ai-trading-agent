# Windows AI Trading Agent — Pilot

Local-first Windows desktop AI assistant for MetaTrader 5. **Under development; not certified for live trading.**

## Implemented foundation
- FastAPI backend with restricted endpoints and Pydantic validation.
- Official MetaTrader5 Python-package adapter for real terminal status, quotes and account inspection (Windows runtime required).
- Registered, explicitly bounded read-only tools; no arbitrary shell/Python commands.
- Separate trade proposal and explicit-approval safety state machine. Execution is **disabled** in this pilot foundation.
- OpenAI official SDK chat tool-call adapter. API keys remain backend-only.
- React/TypeScript frontend skeleton with status and typed chat.
- Unit tests for safety rules and tool validation.

## Windows setup
1. Install Python 3.11 or 3.12, Node.js 20+, Rust, Microsoft C++ Build Tools and WebView2.
2. Install and sign in to the MetaTrader 5 Windows terminal.
3. In PowerShell: `cd backend; py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ".[windows,dev]"`
4. Set `OPENAI_API_KEY` in the shell or a protected OS secret mechanism. **Do not commit secrets.**
5. Start backend: `uvicorn app.main:app --host 127.0.0.1 --port 8765`.
6. In a second terminal: `cd desktop; npm install; npm run dev`.
7. Run backend tests: `cd backend; pytest -q`.

The development UI uses a localhost HTTP backend and therefore is **not yet an authenticated production desktop bridge**. Do not expose the backend beyond loopback. Desktop packaging and stronger IPC are pending.

## Safety status
Order proposals are data only. They never call `order_send`. No trade execution endpoint exists; even an approval cannot place an order. Demo and live trade execution remain explicitly out of scope until exact-action confirmation, broker constraints, limits, reconciliation, and real-terminal testing are complete.

## Current limitations
The backend cannot be validated against MT5 in the present Linux environment. Chart control MQL5 helper, Anthropic/Gemini, voice, desktop Tauri bundling, broker-side validations, and real-terminal acceptance tests remain pending. See docs/STATUS.md.
