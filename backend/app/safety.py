"""Independent, fail-closed trade proposal controller.

Proposals and approvals NEVER submit broker orders.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from uuid import uuid4

@dataclass(frozen=True)
class TradeProposal:
    account: int
    symbol: str
    side: str
    volume: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None

    def __post_init__(self):
        if self.account <= 0 or not self.symbol.isascii() or not self.symbol or len(self.symbol) > 32:
            raise ValueError("Invalid account or symbol")
        if not all(c.isalnum() or c in "._-" for c in self.symbol):
            raise ValueError("Unsafe symbol")
        if self.side not in ("buy", "sell") or not self.volume.is_finite() or self.volume <= 0:
            raise ValueError("Invalid side or volume")
        if self.volume > Decimal("1"):
            raise ValueError("Pilot proposal volume must not exceed 1 lot")
        for value in (self.stop_loss, self.take_profit):
            if value is not None and (not value.is_finite() or value <= 0):
                raise ValueError("Invalid stop/take-profit")

class ProposalStore:
    def __init__(self):
        self._items: dict[str, tuple[TradeProposal, str]] = {}
        self._lock = Lock()

    def prepare(self, proposal: TradeProposal) -> str:
        key = uuid4().hex
        with self._lock:
            self._items[key] = (proposal, "pending")
        return key

    def resolve(self, key: str, approve: bool, actual: TradeProposal) -> str:
        with self._lock:
            if key not in self._items:
                raise ValueError("Unknown or expired proposal")
            saved, status = self._items[key]
            if status != "pending":
                raise ValueError("Proposal already resolved")
            if actual != saved:
                self._items[key] = (saved, "invalidated")
                raise ValueError("Proposed trade parameters changed; new approval required")
            result = "approved_not_executed" if approve else "rejected"
            self._items[key] = (saved, result)
            return result

    def get(self, key: str) -> tuple[TradeProposal, str]:
        with self._lock:
            return self._items[key]
