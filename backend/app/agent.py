"""Bounded OpenAI tool-calling loop. Only registered read-only tools are exposed."""
from __future__ import annotations
import json
from threading import Event
from typing import Any
from .tools import ToolRegistry

SYSTEM = ("You are an MT5 read-only assistant. Never invent market data, order outcomes, "
          "or terminal status. Only report checked tool data. Never claim a trade or chart "
          "operation succeeded without verified tool results. You cannot submit orders or execute code.")

class AgentCancelled(RuntimeError):
    pass

class ProviderProtocolError(RuntimeError):
    pass

class OpenAIAgent:
    def __init__(self, client=None, tools=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI(timeout=20, max_retries=0)
        self.client = client
        self.tools = tools if tools is not None else ToolRegistry()

    def ask(self, message: str, model: str, cancel: Event | None = None) -> str:
        if not message or len(message) > 3000 or not model or len(model) > 100:
            raise ValueError("Invalid message or model")
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM},
                                          {"role": "user", "content": message}]
        seen: set[str] = set()
        for _ in range(4):
            if cancel is not None and cancel.is_set():
                raise AgentCancelled("Request cancelled before next provider call")
            response = self.client.chat.completions.create(
                model=model, messages=messages, tools=self.tools.definitions(),
                tool_choice="auto", timeout=20)
            if not getattr(response, "choices", None) or len(response.choices) != 1:
                raise ProviderProtocolError("Provider returned no single usable choice")
            item = response.choices[0].message
            if item is None:
                raise ProviderProtocolError("Missing provider message")
            calls = getattr(item, "tool_calls", None) or []
            if not calls:
                content = getattr(item, "content", None)
                if not isinstance(content, str) or not content.strip():
                    raise ProviderProtocolError("Provider returned empty response")
                return content
            if len(calls) > 8:
                raise ProviderProtocolError("Too many simultaneous tool requests")
            messages.append(item.model_dump(exclude_none=True))
            for call in calls:
                if cancel is not None and cancel.is_set():
                    raise AgentCancelled("Request cancelled before tool execution")
                identifier = getattr(call, "id", None)
                fn = getattr(call, "function", None)
                if not identifier or fn is None:
                    raise ProviderProtocolError("Malformed tool-call envelope")
                if identifier in seen:
                    raise ProviderProtocolError("Duplicate tool call ID")
                seen.add(identifier)
                try:
                    arguments = json.loads(fn.arguments)
                    data = self.tools.execute(fn.name, arguments)
                    payload = {"ok": True, "data": data}
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    payload = {"ok": False, "error": "Invalid tool request", "type": type(exc).__name__}
                except Exception as exc:
                    payload = {"ok": False, "error": "Tool failed", "type": type(exc).__name__}
                messages.append({"role": "tool", "tool_call_id": identifier,
                                 "content": json.dumps(payload, default=str)})
        raise ProviderProtocolError("Tool-call iteration limit reached")
