"""Genuine read-only MT5 gateway. Never substitutes offline/sample data."""
from __future__ import annotations

from contextlib import contextmanager
from math import isfinite
from time import time
from threading import RLock
from typing import Any, Iterator

_LOCK = RLock()  # Official MT5 module operates against a process-wide terminal session.


class MT5Unavailable(RuntimeError):
    """Terminal, account, or requested market data are unavailable."""


class MT5ReadOnly:
    def __init__(self, terminal_path: str | None = None, expected_login: int | None = None):
        self.terminal_path = terminal_path
        self.expected_login = expected_login

    @contextmanager
    def _session(self) -> Iterator[Any]:
        with _LOCK:
            try:
                import MetaTrader5 as mt5
            except ImportError as exc:
                raise MT5Unavailable("MetaTrader5 is unavailable; use supported Windows Python") from exc
            kwargs = {"path": self.terminal_path} if self.terminal_path else {}
            if not mt5.initialize(timeout=5000, **kwargs):
                raise MT5Unavailable(f"MT5 initialization failed: {mt5.last_error()}")
            try:
                terminal = mt5.terminal_info()
                account = mt5.account_info()
                if terminal is None or not bool(terminal.connected):
                    raise MT5Unavailable("MT5 terminal is disconnected")
                if account is None:
                    raise MT5Unavailable("No authenticated account in terminal")
                if self.expected_login is not None and int(account.login) != self.expected_login:
                    raise MT5Unavailable("Selected MT5 account changed; reconnect explicitly")
                yield mt5
            finally:
                mt5.shutdown()

    def status(self) -> dict[str, Any]:
        with self._session() as mt5:
            t, a = mt5.terminal_info(), mt5.account_info()
            mode = int(a.trade_mode)
            return {"connected": True, "terminal": t.name, "path": t.path,
                    "account": {"login": int(a.login), "server": a.server,
                                "trade_mode": mode, "mode_label": {0: "demo", 1: "contest", 2: "real"}.get(mode, "unknown")},
                    "source": "MetaTrader5"}

    def symbols(self, limit: int = 100) -> dict[str, Any]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._session() as mt5:
            items = mt5.symbols_get()
            if items is None:
                raise MT5Unavailable(f"Symbol list query failed: {mt5.last_error()}")
            return {"symbols": [s.name for s in items[:limit]], "total": len(items), "source": "MetaTrader5"}

    def specifications(self, symbol: str) -> dict[str, Any]:
        with self._session() as mt5:
            s = mt5.symbol_info(symbol)
            if s is None:
                raise MT5Unavailable(f"Symbol not available: {symbol}")
            return {"symbol": s.name, "point": float(s.point), "digits": int(s.digits),
                    "volume_min": float(s.volume_min), "volume_max": float(s.volume_max),
                    "volume_step": float(s.volume_step), "trade_mode": int(s.trade_mode),
                    "visible": bool(s.visible), "source": "MetaTrader5"}

    def quote(self, symbol: str) -> dict[str, Any]:
        """Read an actual, fresh tick; never present an old quote as current.

        SymbolSelect changes Market Watch visibility, not account positions. It is
        used only if the requested broker symbol exists but is not visible.
        """
        with self._session() as mt5:
            info = mt5.symbol_info(symbol)
            if info is None:
                raise MT5Unavailable(f"Symbol not available: {symbol}")
            if not bool(info.visible) and not mt5.symbol_select(symbol, True):
                raise MT5Unavailable(f"Cannot select {symbol} in Market Watch: {mt5.last_error()}")
            tick = mt5.symbol_info_tick(symbol)
            if tick is None or int(tick.time_msc) <= 0:
                raise MT5Unavailable(f"No valid tick for {symbol}; check Market Watch and session")
            bid, ask, stamp = float(tick.bid), float(tick.ask), int(tick.time_msc)
            if not all(map(isfinite, (bid, ask))) or bid <= 0 or ask <= 0 or ask < bid:
                raise MT5Unavailable(f"Invalid bid/ask for {symbol}; no usable live quote")
            age_seconds = time() - stamp / 1000.0
            if age_seconds > 300 or age_seconds < -60:
                raise MT5Unavailable(f"Stale or future-dated {symbol} quote; last tick age {age_seconds:.0f} seconds")
            return {"symbol": symbol, "bid": bid, "ask": ask,
                    "time_msc": stamp, "age_seconds": round(age_seconds, 2),
                    "source": "MetaTrader5"}

    def rates(self, symbol: str, timeframe: str = "H1", count: int = 50) -> dict[str, Any]:
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        if timeframe not in ("M1", "M5", "M15", "M30", "H1", "H4", "D1"):
            raise ValueError("Unsupported timeframe")
        with self._session() as mt5:
            if mt5.symbol_info(symbol) is None:
                raise MT5Unavailable(f"Symbol not available: {symbol}")
            bars = mt5.copy_rates_from_pos(symbol, getattr(mt5, "TIMEFRAME_" + timeframe), 0, count)
            if bars is None:
                raise MT5Unavailable(f"Historical data query failed: {mt5.last_error()}")
            return {"symbol": symbol, "timeframe": timeframe, "source": "MetaTrader5",
                    "bars": [{k: (int(b[k]) if k in ("time", "tick_volume", "spread", "real_volume") else float(b[k]))
                              for k in ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")}
                             for b in bars]}

    def positions(self) -> dict[str, Any]:
        with self._session() as mt5:
            rows = mt5.positions_get()
            if rows is None:
                raise MT5Unavailable(f"Position query failed: {mt5.last_error()}")
            return {"positions": [{"ticket": int(p.ticket), "symbol": p.symbol,
                       "type": int(p.type), "volume": float(p.volume), "profit": float(p.profit)} for p in rows],
                    "source": "MetaTrader5"}

    def pending_orders(self) -> dict[str, Any]:
        with self._session() as mt5:
            rows = mt5.orders_get()
            if rows is None:
                raise MT5Unavailable(f"Pending-order query failed: {mt5.last_error()}")
            return {"orders": [{"ticket": int(o.ticket), "symbol": o.symbol, "type": int(o.type),
                     "volume_current": float(o.volume_current), "price_open": float(o.price_open)} for o in rows],
                    "source": "MetaTrader5"}
