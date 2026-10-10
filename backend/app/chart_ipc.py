"""Restricted, non-trading local IPC for the MQL5 ChartControlEA helper.

A successful response is supplied by the EA, NEVER fabricated by Python.
"""
from __future__ import annotations
import os
import re
import threading
import time
import uuid
from pathlib import Path

LOCK = threading.Lock()
SYMBOL = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
TIMEFRAMES = frozenset({"M1", "M5", "M15", "M30", "H1", "H4", "D1"})
OPERATIONS = frozenset({"OPEN", "SMA", "EMA"})

class ChartControlError(RuntimeError):
    pass

class ChartIPC:
    def __init__(self, common_files: Path):
        self.folder = Path(common_files)

    def execute(self, operation: str, symbol: str, timeframe: str, period: int = 20,
                timeout: float = 8.0) -> dict:
        if operation not in OPERATIONS or timeframe not in TIMEFRAMES or not SYMBOL.fullmatch(symbol):
            raise ValueError("Unsupported chart command")
        if not 2 <= period <= 500:
            raise ValueError("Invalid indicator period")
        if not 1 <= timeout <= 15:
            raise ValueError("Invalid chart timeout")
        if not self.folder.is_dir():
            raise ChartControlError("MT5 Common/Files directory not found; install the companion EA")
        with LOCK:
            req, resp = self.folder / "agent_request.txt", self.folder / "agent_response.txt"
            if req.exists():
                raise ChartControlError("Previous chart command is pending; inspect terminal before retry")
            if resp.exists():
                raise ChartControlError("Unconsumed chart response exists; inspect/clear it before retry")
            ident = uuid.uuid4().hex
            expiry = int(time.time() + timeout)
            line = f"{ident}|{expiry}|{operation}|{symbol}|{timeframe}|{period}\n"
            temp = self.folder / ("agent_request_" + ident + ".tmp")
            try:
                with temp.open("x", encoding="ascii", newline="\n") as stream:
                    stream.write(line)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, req)  # atomic handoff on the same volume
            finally:
                temp.unlink(missing_ok=True)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if resp.is_file():
                    raw = resp.read_text(encoding="ascii").strip().split("|", 3)
                    if len(raw) != 4 or raw[0] != ident:
                        raise ChartControlError("Unexpected chart response ID or format")
                    resp.unlink(missing_ok=True)
                    if raw[1] != "OK":
                        raise ChartControlError("Chart companion failed: " + raw[3][:180])
                    try:
                        chart_id = int(raw[2])
                    except ValueError as exc:
                        raise ChartControlError("Invalid chart identifier") from exc
                    if chart_id <= 0:
                        raise ChartControlError("Companion returned invalid chart identifier")
                    return {"request_id": ident, "chart_id": chart_id, "status": "EA_REPORTED_OK",
                            "detail": raw[3], "source": "MQL5 ChartControlEA"}
                time.sleep(.05)
            raise ChartControlError("Chart command timed out; outcome unknown. Inspect MT5 before retry")


def default_common_files() -> Path:
    override = os.getenv("MT5_COMMON_FILES")
    if override:
        return Path(override)
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise ChartControlError("Set MT5_COMMON_FILES to the actual terminal Common/Files directory")
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"
