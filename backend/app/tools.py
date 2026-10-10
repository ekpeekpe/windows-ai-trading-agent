"""Explicit allowlist; model cannot invoke Python or shell directly."""
from pydantic import BaseModel, Field
from .mt5 import MT5ReadOnly

class SymbolArgs(BaseModel):
    symbol: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")

class NoArgs(BaseModel):
    pass

class ToolRegistry:
    def __init__(self, mt5: MT5ReadOnly | None = None):
        self.mt5 = mt5 or MT5ReadOnly()
        self._tools = {
            "terminal_status": (NoArgs, lambda _: self.mt5.status()),
            "quote": (SymbolArgs, lambda a: self.mt5.quote(a.symbol)),
            "open_positions": (NoArgs, lambda _: self.mt5.positions()),
        }

    def definitions(self):
        return [
            {"type": "function", "function": {"name": name,
             "description": {"terminal_status": "Get the actual MT5 terminal status and account identity",
                             "quote": "Get a real, timestamped MT5 bid and ask",
                             "open_positions": "Read actual open MT5 positions"}[name],
             "parameters": schema.model_json_schema()}}
            for name, (schema, _) in self._tools.items()
        ]

    def execute(self, name: str, args: dict):
        if name not in self._tools:
            raise ValueError(f"Unregistered tool: {name}")
        schema, handler = self._tools[name]
        return handler(schema.model_validate(args))
