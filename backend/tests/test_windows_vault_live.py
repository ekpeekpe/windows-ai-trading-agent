"""REAL WinVault smoke test for Windows CI, not a mocked credential backend.
Stores a synthetic value temporarily; never involves a user's provider key.
"""
import os
import uuid
import pytest

@pytest.mark.skipif(os.name!="nt",reason="Requires real Windows Credential Manager")
def test_real_windows_credential_manager_round_trip():
    from app.credentials import vault,SERVICE
    key="oauth-ci-probe-"+uuid.uuid4().hex
    secret="test-only-"+uuid.uuid4().hex
    store=vault()
    try:
        store.set_password(SERVICE,key,secret)
        assert store.get_password(SERVICE,key)==secret
    finally:
        if store.get_password(SERVICE,key):
            store.delete_password(SERVICE,key)
        assert store.get_password(SERVICE,key) is None

@pytest.mark.skipif(os.name!="nt",reason="Requires real Windows Credential Manager")
def test_real_windows_chatgpt_status_without_credentials():
    from app.chatgpt_auth import ChatGPTOSS
    status=ChatGPTOSS().status()
    assert status["available"],status.get("error","Windows protected storage unavailable")
    assert status["state"] in ("disconnected","connected")
    assert isinstance(status["accounts"],list)
