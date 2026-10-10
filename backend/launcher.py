"""Frozen, loopback-only Python sidecar entry point.

Windows GUI applications may have null standard streams. No credentials are logged.
Optional AGENT_DIAGNOSTIC=1 writes startup *event names and exception types only*
to a fixed OS-temp filename for CI diagnosis.
"""
import os
import sys

def _ensure_streams():
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))

def _diagnostic(event: str, error: BaseException | None = None):
    if os.getenv("AGENT_DIAGNOSTIC") != "1":
        return
    import tempfile
    from pathlib import Path
    location = Path(tempfile.gettempdir()) / f"windows_ai_agent_{os.getpid()}.startup.log"
    detail = "" if error is None else f" {type(error).__module__}.{type(error).__name__}"
    with location.open("a", encoding="utf-8") as log:
        log.write(event + detail + "\n")

def main():
    _ensure_streams()
    token = os.getenv("AGENT_LOCAL_TOKEN", "")
    try:
        port = int(os.getenv("AGENT_PORT", "0"))
    except ValueError:
        port = 0
    if len(token) < 24 or not 1024 <= port <= 65535:
        _diagnostic("invalid-launch-configuration")
        print("Missing secure local launch configuration", file=sys.stderr)
        return 2
    _diagnostic("uvicorn-import")
    try:
        import uvicorn
        _diagnostic("server-starting")
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning",
                    access_log=False, workers=1)
    except Exception as exc:
        _diagnostic("server-exception", exc)
        raise
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
