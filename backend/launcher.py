"""Frozen Python sidecar entry point. Windows Tauri supplies port and local token."""
import os
import sys

def main():
    token = os.getenv("AGENT_LOCAL_TOKEN", "")
    try:
        port = int(os.getenv("AGENT_PORT", "0"))
    except ValueError:
        port = 0
    if len(token) < 24 or not 1024 <= port <= 65535:
        print("Missing secure local launch configuration", file=sys.stderr)
        return 2
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning",
                access_log=False, workers=1)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
