"""Bounded, typed registry: only explicitly allowlisted read tools reach MT5."""
from __future__ import annotations
from collections.abc import Callable
from pydantic import BaseModel, ConfigDict, Field
from .mt5 import MT5ReadOnly

class StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

class NoArgs(StrictArgs):
    pass

class SymbolArgs(StrictArgs):
    symbol: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")

class SymbolsArgs(StrictArgs):
    limit: int = Field(default=100, ge=1, le=500)

class RatesArgs(SymbolArgs):
    timeframe: str = Field(default="H1", pattern=r"^(M1|M5|M15|M30|H1|H4|D1)$")
    count: int = Field(default=50, ge=1, le=500)

class ChartArgs(SymbolArgs):
    timeframe: str = Field(default="H1", pattern=r"^(M1|M5|M15|M30|H1|H4|D1)$")
    period: int = Field(default=20, ge=2, le=500)

class ToolRegistry:
    def __init__(self, mt5: MT5ReadOnly | None = None, chart_ipc=None):
        self.mt5 = mt5 if mt5 is not None else MT5ReadOnly()
        self._tools: dict[str, tuple[type[BaseModel], str, Callable]] = {
            "terminal_status": (NoArgs, "Read actual MT5 terminal and account status", lambda x: self.mt5.status()),
            "symbols": (SymbolsArgs, "List broker symbols", lambda x: self.mt5.symbols(x.limit)),
            "symbol_specifications": (SymbolArgs, "Read broker symbol specifications", lambda x: self.mt5.specifications(x.symbol)),
            "quote": (SymbolArgs, "Get actual timestamped bid and ask", lambda x: self.mt5.quote(x.symbol)),
            "historical_rates": (RatesArgs, "Read historical OHLC rates", lambda x: self.mt5.rates(x.symbol, x.timeframe, x.count)),
            "open_positions": (NoArgs, "Read currently open positions", lambda x: self.mt5.positions()),
            "pending_orders": (NoArgs, "Read pending broker orders", lambda x: self.mt5.pending_orders()),
        }
        # Only register chart-mutating operations when explicitly enabled and supplied.
        if chart_ipc is not None:
            self._tools["open_chart"] = (ChartArgs, "Open a broker symbol chart at a timeframe",
                                          lambda x: chart_ipc.execute("OPEN", x.symbol, x.timeframe, x.period))
            self._tools["add_sma"] = (ChartArgs, "Open chart and add a simple moving average",
                                       lambda x: chart_ipc.execute("SMA", x.symbol, x.timeframe, x.period))
            self._tools["add_ema"] = (ChartArgs, "Open chart and add an exponential moving average",
                                       lambda x: chart_ipc.execute("EMA", x.symbol, x.timeframe, x.period))

    def definitions(self) -> list[dict]:
        return [{"type": "function", "function": {"name": name, "description": description,
                 "parameters": schema.model_json_schema()}}
                for name, (schema, description, _) in self._tools.items()]

    def execute(self, name: str, args: dict):
        if name not in self._tools:
            raise ValueError(f"Unregistered tool: {name}")
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object")
        schema, _, handler = self._tools[name]
        return handler(schema.model_validate(args))
