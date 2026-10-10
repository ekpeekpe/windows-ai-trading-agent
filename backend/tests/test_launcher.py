"""Launcher fails closed unless started with a secure local token and port."""
import launcher

def test_launcher_refuses_no_token(monkeypatch):
    monkeypatch.delenv("AGENT_LOCAL_TOKEN", raising=False)
    monkeypatch.setenv("AGENT_PORT", "18765")
    assert launcher.main() == 2

def test_launcher_refuses_invalid_port(monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_TOKEN", "X"*32)
    monkeypatch.setenv("AGENT_PORT", "0")
    assert launcher.main() == 2
