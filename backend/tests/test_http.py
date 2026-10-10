import pytest
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
TOKEN = 'a-very-long-development-local-token'

@pytest.fixture(autouse=True)
def test_token(monkeypatch):
    monkeypatch.setenv('AGENT_LOCAL_TOKEN', TOKEN)

def test_health_read_only():
    result = client.get('/health')
    assert result.status_code == 200
    assert result.json()['trading_enabled'] is False

def test_api_denies_missing_token():
    assert client.get('/terminal').status_code == 401
    assert client.post('/proposals', json={}).status_code == 401

def test_propose_and_reject():
    p = {'account': 123, 'symbol': 'EURUSD', 'side': 'buy', 'volume': '0.1'}
    auth = {'x-agent-token': TOKEN}
    result = client.post('/proposals', json=p, headers=auth)
    assert result.status_code == 200
    token = result.json()['id']
    decision = client.post(f'/proposals/{token}/decision',
                           json={'proposal':p,'approve':False}, headers=auth)
    assert decision.json() == {'status':'rejected','order_submitted':False}
    assert client.post(f'/proposals/{token}/decision',json={'proposal':p,'approve':True},headers=auth).status_code == 409

def test_approval_not_execution():
    p = {'account': 123,'symbol': 'EURUSD','side': 'buy','volume': '0.1'}
    headers = {'x-agent-token': TOKEN}
    id = client.post('/proposals', json=p, headers=headers).json()['id']
    response = client.post(f'/proposals/{id}/decision',json={'proposal':p,'approve':True},headers=headers)
    assert response.json() == {'status':'approved_not_executed','order_submitted':False}

def test_invalid_trade_rejected():
    response = client.post('/proposals',json={'account':123,'symbol':'EURUSD',
                           'side':'buy','volume':'NaN'},headers={'x-agent-token':TOKEN})
    assert response.status_code == 422
