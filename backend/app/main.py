"""Loopback-only development API. Trading submission intentionally absent."""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .mt5 import MT5ReadOnly, MT5Unavailable
from .agent import OpenAIAgent
from .safety import TradeProposal, ProposalStore

app = FastAPI(title="Windows AI Trading Agent", version="0.1.0")
mt5 = MT5ReadOnly(os.getenv("MT5_TERMINAL_PATH") or None)
proposals = ProposalStore()

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
    from decimal import Decimal, InvalidOperation
    try:
        return TradeProposal(p.account, p.symbol, p.side, Decimal(p.volume),
                             Decimal(p.stop_loss) if p.stop_loss else None,
                             Decimal(p.take_profit) if p.take_profit else None)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/health")
def health():
    return {"ok": True, "mode": "read_only", "trading_enabled": False}

@app.get("/terminal")
def terminal():
    try:
        return mt5.status()
    except MT5Unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/quote/{symbol}")
def quote(symbol: str):
    from .tools import SymbolArgs
    try:
        validated = SymbolArgs(symbol=symbol)
        return mt5.quote(validated.symbol)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/chat")
def chat(request: ChatRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    try:
        return {"answer": OpenAIAgent().ask(request.message, request.model)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider request failed: {type(exc).__name__}") from exc

@app.post("/proposals")
def prepare(request: ProposalRequest):
    proposal = unpack(request)
    return {"id": proposals.prepare(proposal), "proposal": request.model_dump(),
            "status": "pending", "execution_enabled": False}

@app.post("/proposals/{proposal_id}/decision")
def decide(proposal_id: str, request: DecisionRequest):
    try:
        status = proposals.resolve(proposal_id, request.approve, unpack(request.proposal))
        return {"status": status, "order_submitted": False}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
