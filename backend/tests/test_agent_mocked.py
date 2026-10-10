"""Only mocked provider and mocked terminal tests; no live API calls."""
import json
from threading import Event
from types import SimpleNamespace
import pytest
from app.agent import OpenAIAgent, AgentCancelled, ProviderProtocolError
from app.tools import ToolRegistry

class MockTerminal:
    def __init__(self):self.calls=[]
    def quote(self,symbol):
        self.calls.append(symbol)
        return {'symbol': symbol, 'bid':1.1234, 'ask':1.1236, 'source':'MOCKED'}

class Response:
    def __init__(self,content=None, calls=None):
        self.message=SimpleNamespace(content=content,tool_calls=calls or [],model_dump=lambda **kw:{'role':'assistant','content':content, 'tool_calls':[{'id':c.id,'type':'function','function':{'name':c.function.name,'arguments':c.function.arguments}} for c in (calls or [])]})
        self.choices=[SimpleNamespace(message=self.message)]

def call(id='c1',name='quote',params='{"symbol":"EURUSD"}'):
    return SimpleNamespace(id=id,function=SimpleNamespace(name=name,arguments=params))

class MockClient:
    def __init__(self,responses):
        self.responses=iter(responses);self.history=[]
        self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
    def create(self,**kwargs):
        self.history.append(kwargs['messages'])
        return next(self.responses)

def test_mocked_provider_tool_result_round_trip():
    terminal=MockTerminal();client=MockClient([Response(calls=[call()]),Response(content='Bid from tool')])
    result=OpenAIAgent(client=client,tools=ToolRegistry(terminal)).ask('What is bid?', 'test-model')
    assert result=='Bid from tool'
    tool=json.loads(client.history[1][-1]['content'])
    assert tool['data']['bid']==1.1234
    assert tool['data']['source']=='MOCKED'
    assert terminal.calls==['EURUSD']

def test_mocked_provider_rejects_illegal_tool_call():
    client=MockClient([Response(calls=[call(name='order_send')]),Response(content='I cannot place orders')])
    result=OpenAIAgent(client=client,tools=ToolRegistry(MockTerminal())).ask('place a trade','test-model')
    assert result=='I cannot place orders'
    assert json.loads(client.history[1][-1]['content'])['ok'] is False

def test_mocked_provider_bad_args_rejected():
    client=MockClient([Response(calls=[call(params='bad-json')]),Response(content='Error')])
    OpenAIAgent(client=client,tools=ToolRegistry(MockTerminal())).ask('quote','test-model')
    assert json.loads(client.history[1][-1]['content'])['ok'] is False

def test_mocked_provider_duplicate_call_blocked():
    client=MockClient([Response(calls=[call(),call()])])
    with pytest.raises(ProviderProtocolError,match='Duplicate'):
        OpenAIAgent(client=client,tools=ToolRegistry(MockTerminal())).ask('quote','test-model')

def test_cancel_prevents_provider_call():
    cancel=Event();cancel.set();client=MockClient([])
    with pytest.raises(AgentCancelled):
        OpenAIAgent(client=client,tools=ToolRegistry(MockTerminal())).ask('quote','test-model',cancel=cancel)
    assert client.history==[]

def test_mocked_provider_empty_response_rejected():
    with pytest.raises(ProviderProtocolError,match='empty'):
        OpenAIAgent(client=MockClient([Response()]),tools=ToolRegistry(MockTerminal())).ask('quote','test-model')
