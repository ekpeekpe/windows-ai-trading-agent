import pytest
from pydantic import ValidationError
from app.tools import ToolRegistry

class FakeTerminal:
    def status(self):
        return {"connected": True}
    def quote(self, symbol):
        return {"symbol": symbol, "bid": 1.0, "ask": 1.1}
    def positions(self):
        return {"positions": []}

def test_registered_tools():
    registry = ToolRegistry(FakeTerminal())
    assert registry.execute("quote", {"symbol": "EURUSD"})["bid"] == 1.0
    assert registry.execute("terminal_status", {})["connected"]
    assert registry.execute("open_positions", {}) == {"positions": []}

def test_rejects_arbitrary_commands():
    registry = ToolRegistry(FakeTerminal())
    with pytest.raises(ValueError):
        registry.execute("run_shell", {"command": "whoami"})
    with pytest.raises(ValidationError):
        registry.execute("quote", {"symbol": "../outside"})
