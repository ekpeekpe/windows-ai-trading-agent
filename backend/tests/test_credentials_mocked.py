"""Mocked credential tests: NO real Windows Vault or external AI API."""
import pytest
from fastapi.testclient import TestClient
from app import credentials
from app import main

class MemoryVault:
    def __init__(self): self.keys = {}
    def get_password(self, service, provider): return self.keys.get((service, provider))
    def set_password(self, service, provider, key): self.keys[(service, provider)] = key
    def delete_password(self, service, provider): self.keys.pop((service, provider))

def test_credential_lifecycle(monkeypatch):
    fake = MemoryVault()
    monkeypatch.setattr(credentials, "vault", lambda: fake)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    credentials.set_key("openai", "test-secret-is-not-real")
    assert credentials.get_key("openai") == "test-secret-is-not-real"
    assert credentials.connection_status()[0]["configured"] is True
    credentials.delete_key("openai")
    assert credentials.get_key("openai") is None

def test_invalid_and_non_windows_refused(monkeypatch):
    with pytest.raises(ValueError): credentials.set_key("evil", "12345678901234567890")
    with pytest.raises(ValueError): credentials.set_key("openai", "weak")
    with pytest.raises(credentials.CredentialUnavailable): credentials.vault()

def test_mock_provider_check_not_actual_api():
    called = []
    credentials.check_connection("anthropic", "mock-not-real", {"anthropic": lambda key: called.append(key)})
    assert called == ["mock-not-real"]

def test_authenticated_routes_and_no_key_echo(monkeypatch):
    fake = MemoryVault()
    monkeypatch.setattr(credentials, "vault", lambda: fake)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_LOCAL_TOKEN", "x" * 32)
    client = TestClient(main.app)
    assert client.get("/providers").status_code == 401
    auth = {"x-agent-token": "x" * 32}
    r = client.put("/providers/openai/key", json={"api_key": "test-secret-should-not-appear"}, headers=auth)
    assert r.status_code == 200
    assert "test-secret" not in r.text
    assert client.get("/providers", headers=auth).json()["providers"][0]["configured"]
    assert client.delete("/providers/openai/key", headers=auth).status_code == 200
    assert not client.get("/providers", headers=auth).json()["providers"][0]["configured"]
