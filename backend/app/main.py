"""Authenticated loopback development API. Does not support broker order submission."""
from __future__ import annotations
import hmac
import os
from decimal import Decimal, InvalidOperation
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from .mt5 import MT5ReadOnly, MT5Unavailable
from .agent import OpenAIAgent, AgentCancelled, ProviderProtocolError
from .safety import TradeProposal, ProposalStore
from .audit import record
from .tools import ToolRegistry

app = FastAPI(title="Windows AI Trading Agent", version="0.2.0")
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
    return {"ok": True, "mode": "read_only", "trading_enabled": False,
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
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        return {"answer": OpenAIAgent(tools=ToolRegistry(mt5=mt5, chart_ipc=(ChartIPC(default_common_files()) if os.getenv("ENABLE_CHART_CONTROL") == "1" else None))).ask(request.message, request.model) }
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
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY required for speech transcription")
    data = audio.file.read(10 * 1024 * 1024 + 1)
    mime_type = (audio.content_type or "").split(";")[0]
    try:
        text = transcribe(data, mime_type)
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
