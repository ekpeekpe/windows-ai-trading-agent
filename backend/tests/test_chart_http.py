from fastapi.testclient import TestClient
from app.main import app

def test_chart_endpoint_disabled_by_default(monkeypatch):
    monkeypatch.setenv('AGENT_LOCAL_TOKEN','a-very-long-development-local-token')
    monkeypatch.delenv('ENABLE_CHART_CONTROL', raising=False)
    client=TestClient(app)
    payload={'operation':'OPEN','symbol':'EURUSD','timeframe':'H1'}
    assert client.post('/chart',json=payload).status_code==401
    assert client.post('/chart',json=payload,headers={'x-agent-token':'a-very-long-development-local-token'}).status_code==403
