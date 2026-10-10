"""Mocked HTTP -> provider -> approved tool -> MT5 gateway regression.

No actual provider API or MetaTrader 5 terminal is contacted.
"""
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app import main
from app.agent import OpenAIAgent

TOKEN = 'fake-development-local-token-with-more-than-24-chars'

class MockTerminal:
    def __init__(self):
        self.queried = []
    def quote(self, symbol):
        self.queried.append(symbol)
        return {'symbol': symbol, 'bid': 1.1, 'ask': 1.2, 'source': 'MOCKED_NOT_REAL'}

class MockMessage:
    def __init__(self, content=None, calls=None):
        self.content = content
        self.tool_calls = calls or []
    def model_dump(self, exclude_none=True):
        if self.tool_calls:
            return {'role': 'assistant', 'tool_calls': [
                {'type': 'function', 'id': c.id, 'function': {
                    'name': c.function.name, 'arguments': c.function.arguments}}
                for c in self.tool_calls]}
        return {'role': 'assistant', 'content': self.content}

class MockCompletions:
    def __init__(self):
        self.requests = []
    def create(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            c = SimpleNamespace(id='one', function=SimpleNamespace(name='quote', arguments='{"symbol":"EURUSD"}'))
            return SimpleNamespace(choices=[SimpleNamespace(message=MockMessage(calls=[c]))])
        return SimpleNamespace(choices=[SimpleNamespace(message=MockMessage(content='Mocked provider got mocked EURUSD quote.'))])

def test_http_to_agent_tool_result_roundtrip(monkeypatch):
    terminal = MockTerminal()
    completions = MockCompletions()
    sdk_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(main, 'mt5', terminal)
    monkeypatch.setattr(main, 'OpenAIAgent', lambda tools: OpenAIAgent(client=sdk_client, tools=tools))
    monkeypatch.setenv('AGENT_LOCAL_TOKEN', TOKEN)
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-key-only-in-test')
    monkeypatch.delenv('ENABLE_CHART_CONTROL', raising=False)
    client = TestClient(main.app)
    body = {'provider': 'openai', 'model': 'test-model', 'message': 'Read EURUSD quote'}
    assert client.post('/chat', json=body).status_code == 401
    result = client.post('/chat', json=body, headers={'x-agent-token': TOKEN})
    assert result.status_code == 200
    assert 'Mocked provider' in result.json()['answer']
    assert terminal.queried == ['EURUSD']
    assert len(completions.requests) == 2
    assert 'MOCKED_NOT_REAL' in completions.requests[1]['messages'][-1]['content']

def test_health_and_trading_disabled(monkeypatch):
    monkeypatch.setenv('AGENT_LOCAL_TOKEN', TOKEN)
    client = TestClient(main.app)
    r = client.get('/health')
    assert r.status_code == 200 and r.json()['trading_enabled'] is False
    assert client.post('/chart', json={'operation':'OPEN','symbol':'EURUSD','timeframe':'H1'},
                       headers={'x-agent-token':TOKEN}).status_code == 403
