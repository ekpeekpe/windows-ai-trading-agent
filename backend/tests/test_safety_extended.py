import json
from decimal import Decimal
import pytest
from app.audit import record
from app.safety import ProposalStore, TradeProposal

def trade():return TradeProposal(42,'EURUSD','buy',Decimal('0.1'))

def test_expiry_and_context_binding():
    clock=[0.0]; events=[]
    store=ProposalStore(lifetime_seconds=10,clock=lambda:clock[0],audit=lambda e,i:events.append(e))
    id=store.prepare(trade(),context='account42@serverA')
    with pytest.raises(ValueError,match='context changed'):
        store.resolve(id,True,trade(),context='account42@serverB')
    assert events==['proposal_prepared','proposal_invalidated']
    other=store.prepare(trade());clock[0]=11
    with pytest.raises(ValueError,match='expired'):
        store.resolve(other,True,trade())

def test_audit_redacts_payload_and_writes_jsonl(tmp_path):
    log=tmp_path/'audit.jsonl'
    record('proposal_rejected','f'*32,path=log)
    rows=[json.loads(s) for s in log.read_text().splitlines()]
    assert rows[0]['event']=='proposal_rejected'
    assert not any(k in rows[0] for k in ('api_key','account','volume','symbol'))
    with pytest.raises(ValueError):record('order_send','f'*32,path=log)
