"""Official open-source ChatGPT plan authorization: dynamic client, loopback PKCE.
Never exposes access/refresh tokens, callback codes, or browser URLs to the UI.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, secrets, threading, time, uuid, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
import httpx
from .credentials import vault, SERVICE, CredentialUnavailable

AUTH="https://auth.openai.com/api/accounts/authorize"
TOKEN="https://auth.openai.com/api/accounts/oauth/token"
DISCOVERY="https://auth.openai.com/.well-known/openid-configuration"
ISSUER="https://auth.openai.com"
RESOURCE="https://api.openai.com/v1"
SCOPES="openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
STORAGE=SERVICE+".chatgpt-oss"

class ChatGPTAuthError(RuntimeError): pass

def verify_id_token(token, client_id, nonce):
    import jwt
    key=jwt.PyJWKClient("https://auth.openai.com/.well-known/jwks.json",timeout=12).get_signing_key_from_jwt(token)
    claims=jwt.decode(token,key.key,algorithms=["RS256"],audience=client_id,issuer=ISSUER,leeway=5,
                      options={"require":["iss","sub","aud","exp","iat","nonce"]})
    if not hmac.compare_digest(str(claims.get("nonce","")),nonce) or not claims.get("sub"):
        raise ChatGPTAuthError("Invalid OpenAI identity or nonce")
    return claims

class ChatGPTOSS:
    def __init__(self, *, store=None, client=None, browser=None, verifier=None):
        self.store=store or vault
        self.client=client or httpx.Client
        self.browser=browser or webbrowser.open
        self.verifier=verifier or verify_id_token
        self.lock=threading.RLock()
        self.pending=None
        self.listener=None
        self.error=None

    def _get(self,key):
        data=self.store().get_password(STORAGE,key)
        return json.loads(data) if data else None
    def _put(self,key,data):
        self.store().set_password(STORAGE,key,json.dumps(data))
    def _delete(self,key):
        v=self.store()
        if v.get_password(STORAGE,key) is not None: v.delete_password(STORAGE,key)
    def _registrations(self):
        return self._get("registrations") or []
    def _active(self):
        key=self._get("active")
        if not key: return None
        for registration in self._registrations():
            if registration["key"]==key:
                tokens=self._get("tokens:"+key)
                return {**registration,**tokens} if tokens else None
        return None
    def _close(self):
        server,self.listener=self.listener,None
        if server: threading.Thread(target=server.shutdown,daemon=True).start()

    def status(self):
        with self.lock:
            try:
                active=self._active()
                accounts=[{"key":r["key"],"email":r.get("email"),"client_id":r["client_id"],
                           "connected":bool(self._get("tokens:"+r["key"]))} for r in self._registrations()]
            except CredentialUnavailable:
                return {"available":False,"connected":False,"usage_enabled":False,
                        "state":"windows_vault_unavailable","accounts":[]}
            if self.pending and time.monotonic()>self.pending["until"]:
                self.pending=None
                self._close()
                self.error="Sign-in timed out"
            return {"available":True,"connected":bool(active),
                    "usage_enabled":bool(active and "chatgpt.tokens.use.direct" in active.get("scopes",[])),
                    "state":"waiting_for_browser" if self.pending else "connected" if active else "disconnected",
                    "email":active.get("email") if active else None,
                    "accounts":accounts,"error":self.error}

    def start(self, account_key=None):
        with self.lock:
            if self.pending: raise ChatGPTAuthError("Sign-in already underway")
            self.store() # fail closed when Windows vault is unavailable
            host=self._get("host_id")
            if not host:
                host="urn:uuid:"+str(uuid.uuid4())
                self._put("host_id",host)
            selected=next((r for r in self._registrations() if r["key"]==account_key),None) if account_key else None
            if account_key and selected is None: raise ChatGPTAuthError("Saved account not found")
            state,nonce,verifier=secrets.token_urlsafe(32),secrets.token_urlsafe(32),secrets.token_urlsafe(48)
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            owner=self
            class Callback(BaseHTTPRequestHandler):
                def log_message(self,*_): pass # never log query params
                def do_GET(self):
                    parsed=urlparse(self.path)
                    if parsed.path!="/auth/callback" or self.headers.get("Host")!=f"127.0.0.1:{self.server.server_port}":
                        self.send_error(404); return
                    qs=parse_qs(parsed.query,keep_blank_values=True)
                    try:
                        owner.complete({k:v[0] for k,v in qs.items() if len(v)==1})
                        status,message=200,"ChatGPT sign-in completed. Return to AI Trading Agent."
                    except ChatGPTAuthError:
                        status,message=400,"ChatGPT sign-in failed. Return to the app and try again."
                    body=("<h1>"+message+"</h1><p>You may close this browser tab.</p>").encode()
                    self.send_response(status)
                    self.send_header("Content-Type","text/html; charset=utf-8")
                    self.send_header("Cache-Control","no-store")
                    self.send_header("Content-Security-Policy","default-src 'none'")
                    self.send_header("Content-Length",str(len(body)))
                    self.end_headers(); self.wfile.write(body)
            try: server=ThreadingHTTPServer(("127.0.0.1",0),Callback)
            except OSError as exc: raise ChatGPTAuthError("Local callback listener unavailable") from exc
            redirect=f"http://127.0.0.1:{server.server_port}/auth/callback"
            self.listener=server
            self.pending={"state":state,"nonce":nonce,"verifier":verifier,"redirect":redirect,
                          "selected":selected,"until":time.monotonic()+300}
            self.error=None
            params={"client_id":selected["client_id"] if selected else "dynamic_agent_client",
                    "ext_agent_host_id":host,"response_type":"code","redirect_uri":redirect,
                    "scope":SCOPES,"resource":RESOURCE,"state":state,"nonce":nonce,
                    "code_challenge_method":"S256","code_challenge":challenge}
            if selected:
                old=self._get("tokens:"+selected["key"])
                if old and old.get("id_token"): params["id_token_hint"]=old["id_token"]
                if selected.get("email"): params["login_hint"]=selected["email"]
            else: params["agent_name_hint"]="Windows AI Trading Agent"
            threading.Thread(target=server.serve_forever,daemon=True).start()
            try: opened=bool(self.browser(AUTH+"?"+urlencode(params)))
            except Exception: opened=False
            if not opened:
                self.pending=None;self._close()
                raise ChatGPTAuthError("Could not open the system browser")
            return {"state":"waiting_for_browser","expires_in":300}

    def complete(self,query):
        with self.lock:
            tx=self.pending
            if not tx or time.monotonic()>tx["until"]:
                self.pending=None;self._close()
                raise ChatGPTAuthError("No unexpired sign-in request")
            self.pending=None;self._close() # consume once, even on errors
            if not isinstance(query.get("state"),str) or not hmac.compare_digest(query["state"],tx["state"]):
                self.error="Invalid sign-in callback state";raise ChatGPTAuthError(self.error)
            if query.get("error"):
                self.error="Sign-in declined or cancelled";raise ChatGPTAuthError(self.error)
            selected=tx["selected"]
            issued=query.get("client_id")
            if selected:
                if issued and issued!=selected["client_id"]:
                    self.error="Mismatched registered client";raise ChatGPTAuthError(self.error)
                client_id=selected["client_id"]
            else:
                if not issued or not issued.startswith("oaiapp_") or len(issued)>200:
                    self.error="No valid issued client ID";raise ChatGPTAuthError(self.error)
                client_id=issued
            code=query.get("code")
            if not isinstance(code,str) or len(code)<4:
                self.error="Authorization code missing";raise ChatGPTAuthError(self.error)
            try:
                with self.client(timeout=15,follow_redirects=False) as http:
                    response=http.post(TOKEN,data={"grant_type":"authorization_code","client_id":client_id,
                        "code":code,"code_verifier":tx["verifier"],"redirect_uri":tx["redirect"],"resource":RESOURCE})
                    response.raise_for_status()
                    tokens=response.json()
                if not all(isinstance(tokens.get(x),str) and tokens[x] for x in ("access_token","refresh_token","id_token","scope")):
                    raise ChatGPTAuthError("Incomplete token response")
                identity=self.verifier(tokens["id_token"],client_id,tx["nonce"])
                key=hashlib.sha256((client_id+":"+identity["sub"]).encode()).hexdigest()[:36]
                if selected and key!=selected["key"]: raise ChatGPTAuthError("Unexpected ChatGPT account")
                entry={"key":key,"client_id":client_id,"subject":identity["sub"],
                       "email":identity.get("email") if isinstance(identity.get("email"),str) else None}
                record={"access_token":tokens["access_token"],"refresh_token":tokens["refresh_token"],
                        "id_token":tokens["id_token"],"scopes":tokens["scope"].split(),
                        "expires_at":time.time()+int(tokens.get("expires_in",3600))}
                self._put("tokens:"+key,record)
                self._put("registrations",[r for r in self._registrations() if r["key"]!=key]+[entry])
                self._put("active",key)
                self.error=None
            except Exception as exc:
                self.error="ChatGPT sign-in failed; please retry"
                raise ChatGPTAuthError(self.error) from exc

    def access_token(self):
        with self.lock:
            a=self._active()
            if not a: raise ChatGPTAuthError("Sign in with ChatGPT first")
            if "chatgpt.tokens.use.direct" not in a.get("scopes",[]):
                raise ChatGPTAuthError("ChatGPT plan permission not granted")
            if time.time()<a.get("expires_at",0)-90: return a["access_token"]
            try:
                with self.client(timeout=15,follow_redirects=False) as http:
                    response=http.post(TOKEN,data={"grant_type":"refresh_token","client_id":a["client_id"],
                        "refresh_token":a["refresh_token"],"resource":RESOURCE})
                    response.raise_for_status();tokens=response.json()
                if not tokens.get("access_token") or not tokens.get("refresh_token"): raise ValueError()
            except Exception as exc:
                raise ChatGPTAuthError("Session expired; sign in again") from exc
            self._put("tokens:"+a["key"],{"access_token":tokens["access_token"],
                "refresh_token":tokens["refresh_token"],"id_token":a.get("id_token"),
                "scopes":tokens.get("scope"," ".join(a["scopes"])).split(),
                "expires_at":time.time()+int(tokens.get("expires_in",3600))})
            return tokens["access_token"]

    def models(self):
        token=self.access_token()
        try:
            with self.client(timeout=20,follow_redirects=False) as http:
                r=http.get(RESOURCE+"/models",headers={"Authorization":"Bearer "+token})
                r.raise_for_status();data=r.json()
            return [{"slug":m["slug"],"display_name":m.get("display_name",m["slug"])}
                    for m in data.get("models",[]) if m.get("visibility")=="list"
                    and isinstance(m.get("slug"),str)][:100]
        except Exception as exc:
            raise ChatGPTAuthError("Unable to retrieve ChatGPT model catalog") from exc

    def signout(self):
        with self.lock:
            a=self._active()
            if not a: return {"signed_out":True,"remote_revocation_confirmed":False}
            revoked=False
            try:
                with self.client(timeout=10,follow_redirects=False) as http:
                    r=http.get(DISCOVERY);r.raise_for_status()
                    endpoint=r.json().get("revocation_endpoint","")
                    parsed=urlparse(endpoint)
                    if parsed.scheme!="https" or parsed.hostname!="auth.openai.com":
                        raise ChatGPTAuthError("Unsafe revocation endpoint")
                    response=http.post(endpoint,data={"token":a["refresh_token"],
                        "token_type_hint":"refresh_token","client_id":a["client_id"]})
                    revoked=response.status_code==200
            except Exception: revoked=False
            self._delete("tokens:"+a["key"]);self._delete("active")
            return {"signed_out":True,"remote_revocation_confirmed":revoked}

chatgpt=ChatGPTOSS()
