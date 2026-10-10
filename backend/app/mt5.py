"""Read-only MetaTrader 5 interface. Never returns invented market data."""
from __future__ import annotations
from typing import Any

class MT5Unavailable(RuntimeError):
    pass

class MT5ReadOnly:
    def __init__(self, terminal_path: str | None = None):
        self.terminal_path = terminal_path

    def _connect(self):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise MT5Unavailable("MetaTrader5 package requires the supported Windows Python runtime") from exc
        opts = {"path": self.terminal_path} if self.terminal_path else {}
        if not mt5.initialize(**opts):
            raise MT5Unavailable(f"MT5 initialization failed: {mt5.last_error()}")
        return mt5

    def status(self) -> dict[str, Any]:
        mt5 = self._connect()
        try:
            t = mt5.terminal_info()
            a = mt5.account_info()
            if t is None:
                raise MT5Unavailable(f"Terminal information unavailable: {mt5.last_error()}")
            return {"connected": bool(t.connected), "terminal": t.name, "path": t.path,
                    "account": None if a is None else {"login": a.login, "server": a.server,
                    "trade_mode": int(a.trade_mode)}}
        finally:
            mt5.shutdown()

    def quote(self, symbol: str) -> dict[str, Any]:
        mt5 = self._connect()
        try:
            if not mt5.symbol_select(symbol, True):
                raise MT5Unavailable(f"Symbol unavailable: {symbol}")
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                raise MT5Unavailable(f"No tick for {symbol}: {mt5.last_error()}")
            return {"symbol": symbol, "bid": float(tick.bid), "ask": float(tick.ask),
                    "time_msc": int(tick.time_msc), "source": "MetaTrader5"}
        finally:
            mt5.shutdown()

    def positions(self) -> dict[str, Any]:
        mt5 = self._connect()
        try:
            rows = mt5.positions_get()
            if rows is None:
                raise MT5Unavailable(f"Position query failed: {mt5.last_error()}")
            return {"positions": [{"ticket": p.ticket, "symbol": p.symbol,
                "type": int(p.type), "volume": float(p.volume),
                "profit": float(p.profit)} for p in rows], "source": "MetaTrader5"}
        finally:
            mt5.shutdown()
