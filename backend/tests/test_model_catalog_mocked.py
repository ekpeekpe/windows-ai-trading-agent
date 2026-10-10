"""MOCKED provider model catalogs, no API request or broker connection."""
from types import SimpleNamespace as Obj
from fastapi.testclient import TestClient
from app.model_catalog import provider_models
from app import main
from app import credentials

def test_models_ordered_by_actual_release_date_and_filtered():
    fake=Obj(models=Obj(list=lambda:Obj(data=[
        Obj(id="gpt-future",created=1788893000,display_name="Future"),
        Obj(id="text-embedding-old",created=1600000000,display_name="Embedding"),
        Obj(id="gpt-earlier",created=1750000000,display_name="Earlier")
    ])))
    items=provider_models("openai","MOCK-KEY",{"openai":lambda key:fake})
    assert [m["id"] for m in items]==["gpt-earlier","gpt-future"]
    assert items[0]["created_at"] and items[0]["created_at"]<items[1]["created_at"]

def test_anthropic_latest_response_reordered_oldest_first():
    fake=Obj(models=Obj(list=lambda limit:Obj(data=[
        Obj(id="claude-new",display_name="Claude New",created_at="2026-01-01T00:00:00Z"),
        Obj(id="claude-old",display_name="Claude Old",created_at="2024-01-01T00:00:00Z")
    ])))
    items=provider_models("anthropic","MOCK-KEY",{"anthropic":lambda key:fake})
    assert [m["id"] for m in items]==["claude-old","claude-new"]

def test_gemini_filters_embedding_and_tts():
    fake=Obj(models=Obj(list=lambda:[
        Obj(name="models/gemini-3-flash",supported_actions=["generateContent"]),
        Obj(name="models/gemini-embedding-001",supported_actions=["embedContent"]),
        Obj(name="models/gemini-3-tts",supported_actions=["generateContent"])
    ]))
    items=provider_models("gemini","MOCK-KEY",{"gemini":lambda key:fake})
    assert [m["id"] for m in items]==["gemini-3-flash"]

def test_authentication_and_no_keys_in_response(monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_TOKEN","TEST-TOKEN-DO-NOT-SHIP-"+("x"*32))
    monkeypatch.setattr(main,"get_key",lambda p:"mock-provider-key")
    monkeypatch.setattr(main,"provider_models",lambda p,k:[{"id":"test-model","label":"Mock only","created_at":None}])
    client=TestClient(main.app)
    assert client.get("/providers/openai/models").status_code==401
    r=client.get("/providers/openai/models",headers={"x-agent-token":"TEST-TOKEN-DO-NOT-SHIP-"+("x"*32)})
    assert r.status_code==200 and r.json()["models"][0]["id"]=="test-model"
    assert "mock-provider-key" not in r.text
