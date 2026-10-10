"""Official-SDK provider adapters sharing one restricted MT5 tool registry.

All providers are opt-in and must be checked against actual credentials before claiming success.
"""
from __future__ import annotations
import json
from threading import Event
from .agent import SYSTEM, AgentCancelled, ProviderProtocolError
from .tools import ToolRegistry


def perform(tools: ToolRegistry, name: str, arguments: dict) -> dict:
    try:
        return {'ok': True, 'data': tools.execute(name, arguments)}
    except Exception as exc:
        return {'ok': False, 'error': 'Tool execution rejected or failed', 'type': type(exc).__name__}


class AnthropicAgent:
    def __init__(self, client=None, tools=None, api_key=None):
        if client is None:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key, timeout=20, max_retries=0)
        self.client = client
        self.tools = tools if tools is not None else ToolRegistry()

    def ask(self, message: str, model: str, cancel: Event | None = None) -> str:
        if not message or not model or len(message) > 3000:
            raise ValueError('Missing or oversized message/model')
        tools = [{'name': x['function']['name'], 'description': x['function']['description'],
                  'input_schema': x['function']['parameters']} for x in self.tools.definitions()]
        messages = [{'role': 'user', 'content': message}]
        seen = set()
        for _ in range(4):
            if cancel and cancel.is_set(): raise AgentCancelled('Cancelled')
            response = self.client.messages.create(model=model, max_tokens=1024, system=SYSTEM,
                                                   messages=messages, tools=tools, timeout=20)
            blocks = getattr(response, 'content', None)
            if not isinstance(blocks, list) or not blocks:
                raise ProviderProtocolError('Anthropic response has no content')
            calls = [x for x in blocks if getattr(x, 'type', None) == 'tool_use']
            if not calls:
                text = '\n'.join(x.text for x in blocks if getattr(x, 'type', None) == 'text')
                if not text.strip(): raise ProviderProtocolError('Anthropic response has no text')
                return text
            if len(calls) > 8: raise ProviderProtocolError('Too many Anthropic tool requests')
            messages.append({'role': 'assistant', 'content': blocks})
            results = []
            for x in calls:
                if cancel and cancel.is_set(): raise AgentCancelled('Cancelled')
                if not x.id or x.id in seen: raise ProviderProtocolError('Duplicate/missing Anthropic tool ID')
                seen.add(x.id)
                result = perform(self.tools, x.name, x.input)
                results.append({'type': 'tool_result', 'tool_use_id': x.id,
                                'content': json.dumps(result, default=str)})
            messages.append({'role': 'user', 'content': results})
        raise ProviderProtocolError('Anthropic tool loop limit reached')


class GeminiAgent:
    def __init__(self, client=None, tools=None, types=None, api_key=None):
        if client is None:
            from google import genai
            client = genai.Client(api_key=api_key)
        if types is None:
            from google.genai import types
        self.client = client
        self.tools = tools if tools is not None else ToolRegistry()
        self.types = types

    def ask(self, message: str, model: str, cancel: Event | None = None) -> str:
        if not message or not model or len(message) > 3000:
            raise ValueError('Missing or oversized message/model')
        T = self.types
        functions = [T.FunctionDeclaration(name=x['function']['name'],
                      description=x['function']['description'],
                      parameters_json_schema=x['function']['parameters']) for x in self.tools.definitions()]
        config = T.GenerateContentConfig(system_instruction=SYSTEM,
                    tools=[T.Tool(function_declarations=functions)],
                    automatic_function_calling=T.AutomaticFunctionCallingConfig(disable=True))
        content = [T.Content(role='user', parts=[T.Part.from_text(text=message)])]
        for _ in range(4):
            if cancel and cancel.is_set(): raise AgentCancelled('Cancelled')
            response = self.client.models.generate_content(model=model,contents=content,config=config)
            calls = getattr(response, 'function_calls', None) or []
            if not calls:
                text = getattr(response, 'text', None)
                if not isinstance(text, str) or not text.strip():
                    raise ProviderProtocolError('Gemini returned no text')
                return text
            if len(calls) > 8: raise ProviderProtocolError('Too many Gemini tool requests')
            if not getattr(response, 'candidates', None) or response.candidates[0].content is None:
                raise ProviderProtocolError('Gemini tool-call content missing')
            content.append(response.candidates[0].content)
            results = []
            for call in calls:
                if cancel and cancel.is_set(): raise AgentCancelled('Cancelled')
                results.append(T.Part.from_function_response(name=call.name,
                                response=perform(self.tools, call.name, call.args)))
            content.append(T.Content(role='tool', parts=results))
        raise ProviderProtocolError('Gemini tool loop limit reached')
