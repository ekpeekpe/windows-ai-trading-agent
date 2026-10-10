# Architecture and implementation boundaries

- Desktop development shell: React, TypeScript, Vite, with a local /api proxy. Tauri 2 production shell pending.
- Backend: FastAPI served on 127.0.0.1 with Python business logic.
- MT5 adapter: imports the official MetaTrader5 package only when a requested operation is executed; connects using an already signed-in terminal and calls shutdown after each operation.
- Agent: OpenAI official SDK with a maximum of four response iterations and registered read-only tools. Provider APIs receive the user's instruction, tool descriptions, and tool results; they never receive broker passwords.
- Tools: static allowlist for status, quotes, positions; Pydantic argument validation.
- Safety: a separate approval state machine. Approved proposals are NOT executable and do not call MT5 order_send.
- Unimplemented: multi-provider routing, chart-control EA and IPC, secure packaged Tauri transport, cancellation, voice/audio, full trading controls.

This is a foundation rather than a definition-of-done first pilot. See STATUS.md.
