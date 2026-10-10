import pytest
from decimal import Decimal
from app.safety import ProposalStore, TradeProposal

def trade(**changes):
    data = {"account": 123, "symbol": "EURUSD", "side": "buy", "volume": Decimal("0.1")}
    data.update(changes)
    return TradeProposal(**data)

def test_rejection_never_executes():
    store = ProposalStore()
    token = store.prepare(trade())
    assert store.resolve(token, False, trade()) == "rejected"
    with pytest.raises(ValueError):
        store.resolve(token, True, trade())

def test_approval_is_not_execution():
    store = ProposalStore()
    token = store.prepare(trade())
    assert store.resolve(token, True, trade()) == "approved_not_executed"

def test_modification_invalidates_approval():
    store = ProposalStore()
    token = store.prepare(trade())
    with pytest.raises(ValueError):
        store.resolve(token, True, trade(volume=Decimal("0.2")))
    with pytest.raises(ValueError):
        store.resolve(token, True, trade())

@pytest.mark.parametrize("change", [
    {"volume": Decimal("-1")}, {"volume": Decimal("NaN")},
    {"volume": Decimal("1.1")}, {"side": "hold"}, {"symbol": "../danger"},
    {"account": 0}
])
def test_invalid_trade_rejected(change):
    with pytest.raises(ValueError):
        trade(**change)
