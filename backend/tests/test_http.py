from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_health_read_only():
    result = client.get("/health")
    assert result.status_code == 200
    assert result.json()["trading_enabled"] is False

def test_propose_and_reject():
    p = {"account": 123, "symbol": "EURUSD", "side": "buy", "volume": "0.1"}
    result = client.post("/proposals", json=p)
    assert result.status_code == 200
    token = result.json()["id"]
    decision = client.post(f"/proposals/{token}/decision", json={"proposal": p, "approve": False})
    assert decision.json() == {"status": "rejected", "order_submitted": False}
