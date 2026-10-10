"""MOCKED ChatGPT-plan Responses tool loop; no live OpenAI or MT5 call."""
import json
from types import SimpleNamespace
import pytest
from app.chatgpt_agent import ChatGPTAgent, ChatGPTInferenceError

class FakeEvent:
    def __init__(self,type,delta=None,response=None):
        self.type=type;self.delta=delta;self.response=response
class FakeCall:
    type="function_call"
    name="quote"
    call_id="call_one"
    arguments='{"symbol":"EURUSD"}'
    def model_dump(self,**_):
        return {"type":"function_call","name":self.name,"call_id":self.call_id,"arguments":self.arguments}
class Stream:
    def __init__(self,events):self.events=events
    def __enter__(self):return iter(self.events)
    def __exit__(self,*args):pass
class Completion:
    def __init__(self,iterations):self.responses=list(iterations);self.requests=[]
    def create(self,**kwargs):
        self.requests.append(kwargs)
        return Stream(self.responses.pop(0))
class FakeTools:
    def __init__(self):self.calls=[]
    def definitions(self):
        return [{"type":"function","function":{"name":"quote","description":"Real broker price",
                "parameters":{"type":"object","properties":{"symbol":{"type":"string"}}}}}]
    def execute(self,name,args):
        self.calls.append((name,args))
        if name!="quote" or args!={"symbol":"EURUSD"}:raise ValueError("Not allowlisted")
        return {"symbol":"EURUSD","bid":1.12,"ask":1.13,"source":"MOCK-ONLY"}

def test_inference_requires_streamed_completion():
    calls=Completion([[FakeEvent("response.output_text.delta",delta="Mock hello"),
                        FakeEvent("response.completed",response=SimpleNamespace(output=[]))]])
    output=ChatGPTAgent("fake-token",FakeTools(),client=SimpleNamespace(responses=calls)).ask("Hi","mock-model")
    assert output=="Mock hello"
    req=calls.requests[0]
    assert req["store"] is False and req["stream"] is True
    assert req["tools"][0]["type"]=="namespace"
    assert req["tools"][0]["name"]=="mt5"

def test_real_tools_behind_allowlist_and_bounded_loop():
    tool=FakeCall()
    calls=Completion([
        [FakeEvent("response.completed",response=SimpleNamespace(output=[tool]))],
        [FakeEvent("response.output_text.delta",delta="Mock quote was returned"),
         FakeEvent("response.completed",response=SimpleNamespace(output=[]))]
    ])
    tools=FakeTools()
    result=ChatGPTAgent("fake-token",tools,client=SimpleNamespace(responses=calls)).ask("What is EURUSD?", "mock-model")
    assert result=="Mock quote was returned"
    assert tools.calls==[("quote",{"symbol":"EURUSD"})]
    assert "MOCK-ONLY" in calls.requests[1]["input"][-1]["output"]

def test_no_shell_or_trade_execution():
    bad=FakeCall();bad.name="order_send"
    calls=Completion([[FakeEvent("response.completed",response=SimpleNamespace(output=[bad]))],
                      [FakeEvent("response.output_text.delta",delta="Not allowed"),
                       FakeEvent("response.completed",response=SimpleNamespace(output=[]))]])
    tools=FakeTools()
    ChatGPTAgent("fake",tools,client=SimpleNamespace(responses=calls)).ask("Buy now","mock-model")
    assert tools.calls==[]
    assert json.loads(calls.requests[1]["input"][-1]["output"])["ok"] is False

def test_failed_or_interrupted_stream_not_success():
    for events in ([FakeEvent("response.failed")], [FakeEvent("response.output_text.delta",delta="Partial")]):
        client=SimpleNamespace(responses=Completion([events]))
        with pytest.raises(ChatGPTInferenceError):
            ChatGPTAgent("fake",FakeTools(),client=client).ask("Hello","fake-model")
