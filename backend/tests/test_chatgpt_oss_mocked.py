"""MOCKED public-client OAuth tests. No real account, token, or OpenAI calls."""
import hashlib, base64, time
from urllib.parse import urlparse, parse_qs
import httpx, pytest
from fastapi.testclient import TestClient
from app.chatgpt_auth import ChatGPTOSS, ChatGPTAuthError, RESOURCE, TOKEN
from app import main

class Vault:
    def __init__(self): self.values={}
    def get_password(self,service,key): return self.values.get((service,key))
    def set_password(self,service,key,value): self.values[(service,key)]=value
    def delete_password(self,service,key): self.values.pop((service,key),None)

class FakeResponse:
    def __init__(self,data,status_code=200):self.data=data;self.status_code=status_code
    def json(self): return self.data
    def raise_for_status(self):
        if self.status_code>=400: raise httpx.HTTPStatusError("Mocked failure",request=httpx.Request("POST",TOKEN),
                                                              response=httpx.Response(self.status_code))

class HTTPMock:
    history=[]
    def __init__(self,**kwargs):pass
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def post(self,url,data):
        self.history.append((url,data))
        if data["grant_type"]=="refresh_token":
            return FakeResponse({"access_token":"refreshed-access","refresh_token":"rotated-refresh",
                                 "expires_in":3600})
        if "token_type_hint" in data:return FakeResponse({})
        return FakeResponse({"id_token":"test-id-token","access_token":"test-access-token",
                             "refresh_token":"test-refresh-token","scope":
                             "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct",
                             "expires_in":3600})
    def get(self,url,headers=None):
        if url.endswith("/models"):
            assert headers["Authorization"].startswith("Bearer ")
            return FakeResponse({"models":[{"slug":"fake-codex-test-model","display_name":"Mock Codex",
                                            "visibility":"list"},
                                           {"slug":"hidden","visibility":"hidden"}]})
        return FakeResponse({"revocation_endpoint":"https://auth.openai.com/oauth/revoke"})

def make():
    v=Vault();urls=[]
    auth=ChatGPTOSS(store=lambda:v,client=HTTPMock,browser=lambda url:urls.append(url) or True,
                    verifier=lambda token,client,nonce:{"sub":"mock-user","email":"mock@example.test"})
    return auth,urls,v

def test_pkce_dynamic_client_and_no_preminted_key():
    auth,urls,v=make()
    result=auth.start()
    assert result["state"]=="waiting_for_browser"
    params=parse_qs(urlparse(urls[0]).query)
    assert params["client_id"]==["dynamic_agent_client"]
    assert params["agent_name_hint"]==["Windows AI Trading Agent"]
    assert params["code_challenge_method"]==["S256"]
    assert params["redirect_uri"][0].startswith("http://127.0.0.1:")
    assert params["redirect_uri"][0].endswith("/auth/callback")
    assert params["ext_agent_host_id"][0].startswith("urn:uuid:")
    # Separate callback listener has no local app auth token.
    auth.complete({"state":params["state"][0],"code":"fake-code","client_id":"oaiapp_mockissued"})
    assert auth.status()["connected"]
    assert auth.status()["usage_enabled"]
    assert "test-access-token" not in str(auth.status())
    assert auth.models()==[{"slug":"fake-codex-test-model","display_name":"Mock Codex"}]

def test_state_replay_mismatch_fails_closed():
    auth,urls,_=make()
    auth.start()
    with pytest.raises(ChatGPTAuthError,match="callback state"):
        auth.complete({"state":"wrong","code":"fake-code","client_id":"oaiapp_mockissued"})
    with pytest.raises(ChatGPTAuthError,match="No unexpired"):
        auth.complete({"state":"wrong","code":"fake-code","client_id":"oaiapp_mockissued"})
    assert not auth.status()["connected"]

def test_registration_client_must_be_issued_not_dynamic():
    auth,urls,_=make()
    auth.start()
    state=parse_qs(urlparse(urls[0]).query)["state"][0]
    with pytest.raises(ChatGPTAuthError,match="issued client"):
        auth.complete({"state":state,"code":"fake-code","client_id":"dynamic_agent_client"})

def test_nonce_validation_is_required():
    from app.chatgpt_auth import verify_id_token
    # Production verifier is RSA/JWKS based; a forged JWT must not pass.
    with pytest.raises(Exception):
        verify_id_token("not-a-valid-id-token","oaiapp_fake","expected-nonce")

def test_expired_or_reused_signin_rejected():
    auth,urls,_=make();auth.start()
    auth.pending["until"]=time.monotonic()-1
    params=parse_qs(urlparse(urls[0]).query)
    with pytest.raises(ChatGPTAuthError,match="No unexpired"):
        auth.complete({"state":params["state"][0],"code":"fake","client_id":"oaiapp_mockissued"})

def test_refresh_rotation_and_signout():
    auth,urls,_=make();auth.start()
    params=parse_qs(urlparse(urls[0]).query)
    auth.complete({"state":params["state"][0],"code":"fake-code","client_id":"oaiapp_mockissued"})
    row=auth._active()
    raw=auth._get("tokens:"+row["key"]);raw["expires_at"]=time.time()-1
    auth._put("tokens:"+row["key"],raw)
    assert auth.access_token()=="refreshed-access"
    assert auth._get("tokens:"+row["key"])["refresh_token"]=="rotated-refresh"
    result=auth.signout()
    assert result["signed_out"] and result["remote_revocation_confirmed"]
    assert not auth.status()["connected"]
    # Preserve per-account issued ID for reauthorization and avoid dynamic_agent_client on return
    auth.start(account_key=row["key"])
    assert parse_qs(urlparse(urls[-1]).query)["client_id"]==["oaiapp_mockissued"]
    auth._close()

def test_no_permission_means_no_inference_token():
    auth,urls,_=make();auth.start()
    params=parse_qs(urlparse(urls[0]).query)
    auth.complete({"state":params["state"][0],"code":"fake-code","client_id":"oaiapp_mockissued"})
    active=auth._active()
    record=auth._get("tokens:"+active["key"])
    record["scopes"]=["openid","profile"]
    auth._put("tokens:"+active["key"],record)
    with pytest.raises(ChatGPTAuthError,match="permission"):
        auth.access_token()

def test_protected_http_routes_mocked(monkeypatch):
    auth,_,_=make()
    monkeypatch.setattr(main,"chatgpt",auth)
    monkeypatch.setenv("AGENT_LOCAL_TOKEN","test-only-local-secret-long-enough")
    client=TestClient(main.app)
    assert client.get("/chatgpt/status").status_code==401
    headers={"x-agent-token":"test-only-local-secret-long-enough"}
    assert client.get("/chatgpt/status",headers=headers).json()["connected"] is False
    assert client.get("/chatgpt/models",headers=headers).status_code==503
    assert client.post("/chatgpt/start",headers=headers,json={}).status_code==200
    assert client.get("/chatgpt/status",headers=headers).json()["state"]=="waiting_for_browser"
    auth._close()
