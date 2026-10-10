"""Authenticated loopback development API. Does not support broker order submission."""
from __future__ import annotations
import hmac
import os
from decimal import Decimal, InvalidOperation
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from .mt5 import MT5ReadOnly, MT5Unavailable
from .agent import OpenAIAgent, AgentCancelled, ProviderProtocolError
from .providers import AnthropicAgent, GeminiAgent
from .safety import TradeProposal, ProposalStore
from .audit import record
from .tools import ToolRegistry
from .chatgpt_auth import chatgpt, ChatGPTAuthError
from .chatgpt_agent import ChatGPTAgent, ChatGPTInferenceError
from .credentials import get_key, set_key, delete_key, connection_status, check_connection, CredentialUnavailable, validate_provider

app = FastAPI(title="Windows AI Trading Agent", version="0.3.2")
mt5 = MT5ReadOnly(os.getenv("MT5_TERMINAL_PATH") or None,
                  int(os.environ["MT5_EXPECTED_LOGIN"]) if os.getenv("MT5_EXPECTED_LOGIN") else None)
proposals = ProposalStore(audit=record)


def authorized(request: Request):
    expected = os.getenv("AGENT_LOCAL_TOKEN", "")
    if len(expected) < 24:
        raise HTTPException(status_code=503, detail="Configure AGENT_LOCAL_TOKEN (at least 24 characters)")
    received = request.headers.get("x-agent-token", "")
    if not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Invalid local access token")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    model: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="openai", pattern="^(openai|anthropic|gemini|chatgpt)$")

class ProposalRequest(BaseModel):
    account: int
    symbol: str
    side: str
    volume: str
    stop_loss: str | None = None
    take_profit: str | None = None

class DecisionRequest(BaseModel):
    proposal: ProposalRequest
    approve: bool


def unpack(p: ProposalRequest) -> TradeProposal:
    try:
        return TradeProposal(p.account, p.symbol, p.side, Decimal(p.volume),
                             Decimal(p.stop_loss) if p.stop_loss is not None else None,
                             Decimal(p.take_profit) if p.take_profit is not None else None)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid trade parameters") from exc

@app.get("/health")
def health():
    return {"ok": True, "mode": "trade_disabled", "trading_enabled": False,
            "chart_control_enabled": os.getenv("ENABLE_CHART_CONTROL") == "1",
            "authentication_required": True}

@app.get("/terminal", dependencies=[Depends(authorized)])
def terminal():
    try:
        return mt5.status()
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/quote/{symbol}", dependencies=[Depends(authorized)])
def quote(symbol: str):
    from .tools import SymbolArgs
    try:
        validated = SymbolArgs(symbol=symbol)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid symbol") from exc
    try:
        return mt5.quote(validated.symbol)
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/chat", dependencies=[Depends(authorized)])
def chat(request: ChatRequest):
    if request.provider == "chatgpt":
        try:
            token = chatgpt.access_token()
            return {"answer": ChatGPTAgent(token, tools=ToolRegistry(mt5=mt5)).ask(request.message, request.model)}
        except ChatGPTAuthError as exc:
            raise HTTPException(status_code=409 if not isinstance(exc, ChatGPTInferenceError) else 502, detail=str(exc)) from exc
    secret = get_key(request.provider)
    if not secret:
        raise HTTPException(status_code=503, detail=f"No {request.provider} API key configured")
    try:
        registry = ToolRegistry(mt5=mt5, chart_ipc=(ChartIPC(default_common_files()) if os.getenv("ENABLE_CHART_CONTROL") == "1" else None))
        provider_type = {"openai": OpenAIAgent, "anthropic": AnthropicAgent, "gemini": GeminiAgent}[request.provider]
        return {"answer": provider_type(tools=registry, api_key=secret).ask(request.message, request.model)}
    except AgentCancelled as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProviderProtocolError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {type(exc).__name__}") from exc

@app.post("/proposals", dependencies=[Depends(authorized)])
def prepare(request: ProposalRequest):
    proposal = unpack(request)
    return {"id": proposals.prepare(proposal), "proposal": request.model_dump(),
            "status": "pending", "execution_enabled": False}

@app.post("/proposals/{proposal_id}/decision", dependencies=[Depends(authorized)])
def decide(proposal_id: str, request: DecisionRequest):
    try:
        state = proposals.resolve(proposal_id, request.approve, unpack(request.proposal))
        return {"status": state, "order_submitted": False}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

from fastapi import File, UploadFile
from .speech import SpeechError, transcribe

@app.post("/transcribe", dependencies=[Depends(authorized)])
def transcription(audio: UploadFile = File(...)):
    speech_key = get_key("openai")
    if not speech_key:
        raise HTTPException(status_code=503, detail="OpenAI API key required for speech transcription")
    data = audio.file.read(10 * 1024 * 1024 + 1)
    mime_type = (audio.content_type or "").split(";")[0]
    try:
        text = transcribe(data, mime_type, api_key=speech_key)
        return {"text": text, "speech_provider": "openai"}
    except SpeechError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Speech provider failed: {type(exc).__name__}") from exc

from .chart_ipc import ChartIPC, ChartControlError, default_common_files

class ChartRequest(BaseModel):
    operation: str = Field(pattern="^(OPEN|SMA|EMA)$")
    symbol: str = Field(pattern=r"^[A-Za-z0-9._-]{1,32}$")
    timeframe: str = Field(pattern="^(M1|M5|M15|M30|H1|H4|D1)$")
    period: int = Field(default=20, ge=2, le=500)

@app.post("/chart", dependencies=[Depends(authorized)])
def chart(request: ChartRequest):
    if os.getenv("ENABLE_CHART_CONTROL") != "1":
        raise HTTPException(status_code=403, detail="Chart control disabled until companion is installed and verified")
    try:
        return ChartIPC(default_common_files()).execute(request.operation, request.symbol,
                                                        request.timeframe, request.period)
    except (ChartControlError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

# Provider connection centre. Never send stored secrets back to the UI.
class KeyRequest(BaseModel):
    api_key: str = Field(min_length=12, max_length=512)

@app.get("/providers", dependencies=[Depends(authorized)])
def providers_status():
    return {"providers": connection_status(), "account_auth": {
            "chatgpt": "open_source_dynamic_registration",
            "claude": "independent_app_flow_not_available"}}

@app.put("/providers/{provider}/key", dependencies=[Depends(authorized)])
def put_key(provider: str, data: KeyRequest):
    try:
        set_key(provider, data.api_key)
        return {"provider": provider, "configured": True, "verified": False}
    except (CredentialUnavailable, ValueError) as exc:
        raise HTTPException(status_code=503 if isinstance(exc, CredentialUnavailable) else 422,
                            detail=str(exc)) from exc

@app.delete("/providers/{provider}/key", dependencies=[Depends(authorized)])
def remove_key(provider: str):
    try:
        delete_key(provider)
        return {"provider": provider, "configured": False}
    except (CredentialUnavailable, ValueError) as exc:
        raise HTTPException(status_code=503 if isinstance(exc, CredentialUnavailable) else 422,
                            detail=str(exc)) from exc

@app.post("/providers/{provider}/test", dependencies=[Depends(authorized)])
def test_provider_connection(provider: str):
    try:
        validate_provider(provider)
        key = get_key(provider)
        if not key:
            raise HTTPException(status_code=409, detail="Configure an API key first")
        check_connection(provider, key)
        return {"provider": provider, "verified": True, "check": "provider_models_list"}
    except HTTPException:
        raise
    except (CredentialUnavailable, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Provider connection failed: {type(exc).__name__}") from exc

from .model_catalog import provider_models

@app.get("/providers/{provider}/models", dependencies=[Depends(authorized)])
def provider_models_endpoint(provider: str):
    try:
        validate_provider(provider)
        secret=get_key(provider)
        if not secret: raise HTTPException(status_code=409, detail="Connect this provider first")
        return {"provider":provider,"models":provider_models(provider,secret),
                "order":"oldest_to_newest_when_release_dates_exist",
                "note":"Model visibility is not guaranteed inference entitlement."}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502,detail=
                            f"Could not load models from {provider}: {type(exc).__name__}") from exc

from .discovery import discover_terminals

class TerminalSelection(BaseModel):
    path: str = Field(min_length=1, max_length=2048)

@app.get("/terminals", dependencies=[Depends(authorized)])
def terminals_list():
    return {"terminals": discover_terminals(), "selected": mt5.terminal_path}

@app.post("/terminals/select", dependencies=[Depends(authorized)])
def terminals_select(request: TerminalSelection):
    discovered = discover_terminals()
    if request.path not in discovered:
        raise HTTPException(status_code=422, detail="Select a discovered MetaTrader 5 installation")
    mt5.terminal_path = request.path
    return {"selected": request.path, "connected": False,
            "message": "Terminal selected; connection and account not yet verified"}

# Official open-source public-client OAuth: browser callback is bound to a
# separate random loopback port, never the authenticated application HTTP port.
class ChatGPTStartRequest(BaseModel):
    account_key: str | None = Field(default=None, max_length=100)
    # Native Tauri shell opens the browser itself. The OAuth URL must never be
    # forwarded into the renderer in packaged Windows builds.
    launch_browser: bool = True

class ChatGPTTestRequest(BaseModel):
    model: str = Field(min_length=1, max_length=100)

@app.get("/chatgpt/status", dependencies=[Depends(authorized)])
def chatgpt_status():
    return chatgpt.status()

@app.post("/chatgpt/start", dependencies=[Depends(authorized)])
def chatgpt_start(request: ChatGPTStartRequest):
    try:
        return chatgpt.start(request.account_key, launch_browser=request.launch_browser)
    except (CredentialUnavailable, ChatGPTAuthError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

class ChatGPTSelectRequest(BaseModel):
    account_key: str = Field(min_length=1, max_length=100)

@app.post("/chatgpt/select", dependencies=[Depends(authorized)])
def chatgpt_select(request: ChatGPTSelectRequest):
    try:
        return chatgpt.select(request.account_key)
    except ChatGPTAuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@app.post("/chatgpt/cancel", dependencies=[Depends(authorized)])
def chatgpt_cancel():
    return chatgpt.cancel()

@app.get("/chatgpt/models", dependencies=[Depends(authorized)])
def chatgpt_models():
    try:
        return {"models": chatgpt.models(), "catalog_is_not_entitlement": True}
    except ChatGPTAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/chatgpt/test", dependencies=[Depends(authorized)])
def chatgpt_test(request: ChatGPTTestRequest):
    try:
        result = ChatGPTAgent(chatgpt.access_token(), tools=ToolRegistry(mt5=mt5)).ask(
            "Reply with exactly: ChatGPT plan connection verified.", request.model)
        return {"verified": True, "response": result,
                "note": "Verified by a completed inference turn, not model-list availability"}
    except ChatGPTAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/chatgpt/signout", dependencies=[Depends(authorized)])
def chatgpt_signout():
    try:
        return chatgpt.signout()
    except CredentialUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
