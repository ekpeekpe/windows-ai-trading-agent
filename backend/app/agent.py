"""Bounded OpenAI official-SDK tool loop. No trade-capable tools exposed."""
import json
from .tools import ToolRegistry

SYSTEM = ("You are a Windows MetaTrader 5 read-only assistant. Never invent market data, "
          "execution results, or account status. Only report verified tool results. "
          "You cannot execute trades or modify charts.")

class OpenAIAgent:
    def __init__(self, client=None, tools=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        self.client = client
        self.tools = tools or ToolRegistry()

    def ask(self, message: str, model: str) -> str:
        if not model or len(model) > 100:
            raise ValueError("Specify a supported OpenAI model")
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": message}]
        for _ in range(4):
            response = self.client.chat.completions.create(model=model, messages=messages,
                          tools=self.tools.definitions(), tool_choice="auto", timeout=30)
            item = response.choices[0].message
            calls = item.tool_calls or []
            if not calls:
                return item.content or "(No response text)"
            messages.append(item.model_dump(exclude_none=True))
            for call in calls:
                try:
                    result = self.tools.execute(call.function.name, json.loads(call.function.arguments))
                    payload = {"ok": True, "data": result}
                except Exception as exc:
                    payload = {"ok": False, "error": str(exc)}
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(payload, default=str)})
        return "Tool-call iteration limit reached. No further actions taken."
