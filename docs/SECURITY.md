# Security controls and limitations

Never commit API keys, terminal credentials, or account passwords. Use environment-based API key injection only for local development; OS-protected key storage is not implemented yet. Do not send backend error traces or secrets to an AI provider. Read-only commands require explicit schemas and are not allowed arbitrary code execution.

The HTTP development backend has **no authentication** and must listen on 127.0.0.1 only. Avoid browser tabs from unknown websites while running the backend; the security hardening work is not complete. Do not open the port to the LAN or Internet.

Trading is disabled independently of any AI instructions: there is no order submission handler. Proposal approval produces `approved_not_executed`, never a broker request. There is no risk-management enforcement suitable for real-money orders.

Clear ephemeral proposal state by stopping the backend. Conversation history lives only in the active frontend state. Audit logs, encrypted credential storage, production IPC authorization and an emergency trading switch are not yet built.
