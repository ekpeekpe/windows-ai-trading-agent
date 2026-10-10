"""Mock-backed agent loop tests. No provider API or MT5 terminal is called."""
from types import SimpleNamespace
from threading import Event
import json
import pytest
from app.agent import OpenAIAgent, AgentCancelled, ProviderProtocolError

class Message:
    def __init__(self, content=None, calls=None):
        self.content = content
        self.tool_calls = calls or []
    def model_dump(self, exclude_none=True):
        if self.tool_calls:
            return {"role": "assistant", "tool_calls": [
                {"id": c.id, "type": "function", "function": {
                    "name": c.function.name, "arguments": c.function.arguments
                }} for c in self.tool_calls]}
        return {"role": "assistant", "content": self.content}

def call(name, args="{}", identifier="call-1"):
    return SimpleNamespace(id=identifier, function=SimpleNamespace(name=name, arguments=args))

class MockCompletion:
    def __init__(self, messages):
        self.responses = list(messages)
        self.requests = []
    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.responses.pop(0))])

class MockTools:
    def __init__(self):
        self.calls = []
    def definitions(self):
        return [{"type": "function", "function": {"name": "quote",
                "description": "Read a quote", "parameters": {"type": "object"}}}]
    def execute(self, name, args):
        self.calls.append((name, args))
        if name != "quote":
            raise ValueError("Tool not registered")
        if args != {"symbol": "EURUSD"}:
            raise ValueError("Invalid args")
        return {"symbol": "EURUSD", "bid": 1.1, "ask": 1.2, "source": "FAKE-TEST-ONLY"}

def agent(responses):
    completion = MockCompletion(responses)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completion))
    tools = MockTools()
    return OpenAIAgent(client=client, tools=tools), completion, tools

def test_tool_result_roundtrip_is_marked_as_mock():
    bot, provider, tools = agent([
        Message(calls=[call("quote", '{"symbol":"EURUSD"}')]),
        Message(content="The test quote is 1.1 / 1.2.")
    ])
    assert "test quote" in bot.ask("Quote EURUSD", "test-model")
    assert tools.calls == [("quote", {"symbol": "EURUSD"})]
    result = json.loads(provider.requests[1]["messages"][-1]["content"])
    assert result["ok"] is True
    assert result["data"]["source"] == "FAKE-TEST-ONLY"

def test_invalid_tool_call_fails_closed():
    bot, provider, tools = agent([
        Message(calls=[call("run_shell", '{"command":"whoami"}')]),
        Message(content="Unavailable")
    ])
    bot.ask("Execute shell", "test-model")
    assert len(tools.calls) == 1
    result = json.loads(provider.requests[1]["messages"][-1]["content"])
    assert result["ok"] is False

def test_malformed_json_does_not_execute():
    bot, provider, tools = agent([
        Message(calls=[call("quote", "{broken")]),
        Message(content="Invalid request")
    ])
    bot.ask("Quote EURUSD", "test-model")
    assert tools.calls == []
    assert json.loads(provider.requests[1]["messages"][-1]["content"])["ok"] is False

def test_duplicate_tool_id_rejected():
    bot, _, _ = agent([Message(calls=[
        call("quote", '{"symbol":"EURUSD"}'),
        call("quote", '{"symbol":"EURUSD"}')
    ])])
    with pytest.raises(ProviderProtocolError, match="Duplicate"):
        bot.ask("Quote EURUSD", "test-model")

def test_cancellation_before_provider_call():
    bot, provider, _ = agent([])
    cancel = Event()
    cancel.set()
    with pytest.raises(AgentCancelled):
        bot.ask("Quote EURUSD", "test-model", cancel=cancel)
    assert provider.requests == []

def test_empty_response_rejected():
    bot, _, _ = agent([Message(content=None)])
    with pytest.raises(ProviderProtocolError, match="empty"):
        bot.ask("Quote EURUSD", "test-model")

def test_bounded_iteration_limit():
    bot, provider, _ = agent([
        Message(calls=[call("quote", '{"symbol":"EURUSD"}', f"call-{i}")])
        for i in range(4)
    ])
    with pytest.raises(ProviderProtocolError, match="iteration limit"):
        bot.ask("Quote EURUSD", "test-model")
    assert len(provider.requests) == 4
