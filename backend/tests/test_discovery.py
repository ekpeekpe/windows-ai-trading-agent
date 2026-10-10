"""Filesystem fake installation, no actual MetaTrader executable is run."""
from app.discovery import discover_terminals

def test_terminals_discovered_without_launching(tmp_path):
    installed = tmp_path / "Broker A" / "terminal64.exe"
    installed.parent.mkdir()
    installed.write_bytes(b"dummy-test-only")
    appdata = tmp_path / "MetaQuotes" / "Terminal"
    origin = appdata / "installed" / "origin.txt"
    origin.parent.mkdir(parents=True)
    origin.write_text(str(installed.parent), encoding="utf-16")
    paths = discover_terminals(appdata, [])
    assert paths == [str(installed.resolve())]
    assert installed.read_bytes() == b"dummy-test-only"

def test_nonexisting_terminals_not_returned(tmp_path):
    assert discover_terminals(tmp_path / "empty", []) == []
