"""SDK protocol mocks. This file does not call provider APIs."""
from types import SimpleNamespace as NS
import json
from app.providers import AnthropicAgent, GeminiAgent
from app.tools import ToolRegistry

class Terminal:
    def quote(self, s):return {'bid':1.2345,'symbol':s,'source':'MOCK'}

class AnthropicClient:
    def __init__(self):self.inputs=[];self.messages=NS(create=self.create)
    def create(self,**kwargs):
        self.inputs.append(kwargs)
        if len(self.inputs)==1:
            return NS(content=[NS(type='tool_use',id='tool-1',name='quote',input={'symbol':'EURUSD'})])
        return NS(content=[NS(type='text',text='Mocked quote received')])

def test_anthropic_mocked_round_trip():
    client=AnthropicClient()
    assert AnthropicAgent(client=client,tools=ToolRegistry(Terminal())).ask('quote?','test-anthropic')=='Mocked quote received'
    response=client.inputs[1]['messages'][-1]['content'][0]
    assert json.loads(response['content'])['data']['source']=='MOCK'

class GeminiTypes:
    class Part:
        @staticmethod
        def from_text(**kw):return kw
        @staticmethod
        def from_function_response(**kw):return kw
    class Content:
        def __init__(self,**kw):self.__dict__.update(kw)
    class FunctionDeclaration:
        def __init__(self,**kw):self.__dict__.update(kw)
    class Tool:
        def __init__(self,**kw):self.__dict__.update(kw)
    class AutomaticFunctionCallingConfig:
        def __init__(self,**kw):self.__dict__.update(kw)
    class GenerateContentConfig:
        def __init__(self,**kw):self.__dict__.update(kw)

class GeminiClient:
    def __init__(self):self.inputs=[];self.models=NS(generate_content=self.generate)
    def generate(self,**kwargs):
        self.inputs.append(kwargs)
        if len(self.inputs)==1:
            return NS(function_calls=[NS(name='quote',args={'symbol':'EURUSD'})],
                      candidates=[NS(content=NS(role='model',parts=[]))])
        return NS(function_calls=[],text='Gemini mock observed quote')

def test_gemini_mocked_round_trip():
    c=GeminiClient()
    result=GeminiAgent(client=c,types=GeminiTypes,tools=ToolRegistry(Terminal())).ask('quote','test-gemini')
    assert result=='Gemini mock observed quote'
    assert c.inputs[1]['contents'][-1].parts[0]['response']['data']['source']=='MOCK'
