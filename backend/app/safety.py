"""Fail-closed proposal lifecycle. No broker order submission is implemented."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from time import monotonic
from typing import Callable
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
        if self.account <= 0 or not self.symbol.isascii() or not 1 <= len(self.symbol) <= 32:
            raise ValueError('Invalid account or symbol')
        if not all(c.isalnum() or c in '._-' for c in self.symbol) or not any(c.isalnum() for c in self.symbol):
            raise ValueError('Unsafe symbol')
        if self.side not in ('buy', 'sell') or not self.volume.is_finite() or self.volume <= 0:
            raise ValueError('Invalid side or volume')
        if self.volume > Decimal('1'):
            raise ValueError('Pilot volume must not exceed 1 lot')
        for value in (self.stop_loss, self.take_profit):
            if value is not None and (not value.is_finite() or value <= 0):
                raise ValueError('Invalid stop/take-profit')

class ProposalStore:
    def __init__(self, lifetime_seconds: int = 120, clock: Callable[[], float] = monotonic,
                 audit: Callable[[str, str], None] | None = None):
        if not 1 <= lifetime_seconds <= 600:
            raise ValueError('Invalid proposal lifetime')
        self._items: dict[str, tuple[TradeProposal, str, float, str]] = {}
        self._lock = Lock()
        self._clock = clock
        self._lifetime = lifetime_seconds
        self._audit = audit

    def prepare(self, proposal: TradeProposal, context: str = '') -> str:
        key = uuid4().hex
        with self._lock:
            self._items[key] = (proposal, 'pending', self._clock() + self._lifetime, context)
            if self._audit:
                self._audit('proposal_prepared', key)
        return key

    def resolve(self, key: str, approve: bool, actual: TradeProposal, context: str = '') -> str:
        with self._lock:
            if key not in self._items:
                raise ValueError('Unknown or expired proposal')
            saved, status, deadline, original_context = self._items[key]
            if status != 'pending':
                raise ValueError('Proposal already resolved')
            if self._clock() >= deadline:
                self._items[key] = (saved, 'expired', deadline, original_context)
                raise ValueError('Proposal expired; prepare again')
            if actual != saved or context != original_context:
                self._items[key] = (saved, 'invalidated', deadline, original_context)
                if self._audit: self._audit('proposal_invalidated', key)
                raise ValueError('Proposed action or execution context changed; new approval required')
            result = 'approved_not_executed' if approve else 'rejected'
            self._items[key] = (saved, result, deadline, original_context)
            if self._audit: self._audit('proposal_acknowledged' if approve else 'proposal_rejected', key)
            return result

    def get(self, key: str) -> tuple[TradeProposal, str]:
        with self._lock:
            saved, status, _, _ = self._items[key]
            return saved, status
