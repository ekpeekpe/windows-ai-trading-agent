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
    import os
    if os.name != "nt":
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


def test_mocked_windows_vault_chunks_large_oauth_tokens_without_plaintext_files():
    from app.credentials import SegmentedWindowsVault, SERVICE
    raw=MemoryVault()
    protected=SegmentedWindowsVault(raw)
    secret='fake-oauth-claims-'*900
    protected.set_password(SERVICE,'tokens:test',secret)
    manifest=raw.get_password(SERVICE,'tokens:test')
    assert manifest.startswith('@agent-wincred-v1:')
    assert secret not in manifest
    assert protected.get_password(SERVICE,'tokens:test')==secret
    newer='rotated-oauth-tokens-'*940
    protected.set_password(SERVICE,'tokens:test',newer)
    assert protected.get_password(SERVICE,'tokens:test')==newer
    assert not any('fake-oauth-claims' in s for s in raw.keys.values())
    protected.delete_password(SERVICE,'tokens:test')
    assert protected.get_password(SERVICE,'tokens:test') is None
    assert not raw.keys

def test_mocked_chunk_integrity_failure_is_not_reported_as_connected():
    from app.credentials import SegmentedWindowsVault,SERVICE,CredentialUnavailable
    raw=MemoryVault(); protected=SegmentedWindowsVault(raw)
    protected.set_password(SERVICE,'tokens:test','large-token'*1200)
    segments=[name for (_,name) in raw.keys if ':part:' in name]
    raw.keys[(SERVICE,segments[0])]='corrupted'
    with pytest.raises(CredentialUnavailable,match='integrity'):
        protected.get_password(SERVICE,'tokens:test')
