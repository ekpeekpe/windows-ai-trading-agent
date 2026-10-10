"""Minimal append-only local audit events; no API keys, prompts or order payloads."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ALLOWED = {"proposal_prepared", "proposal_rejected", "proposal_acknowledged", "proposal_invalidated"}

def record(event: str, proposal_id: str, path: Path | None = None) -> None:
    if event not in ALLOWED or not isinstance(proposal_id, str) or len(proposal_id) != 32:
        raise ValueError("Invalid audit event")
    target = path or Path(os.getenv('AGENT_AUDIT_PATH', str(Path.home() / '.windows_ai_trading_agent' / 'audit.jsonl')))
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "event": event,
            "proposal_id": proposal_id}
    fd = os.open(str(target), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, (json.dumps(data, separators=(',', ':')) + '\n').encode('utf-8'))
        os.fsync(fd)
    finally:
        os.close(fd)
