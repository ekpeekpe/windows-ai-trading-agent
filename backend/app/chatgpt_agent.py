"""ChatGPT-plan inference with official streaming Responses API and MT5 read tools.

This uses an OAuth bearer token, NOT a billed OpenAI API key. Tool execution
is bound to the existing typed registry and never includes chart/trade writes.
"""
import json
from .chatgpt_auth import ChatGPTAuthError
class ChatGPTInferenceError(ChatGPTAuthError): pass

class ChatGPTAgent:
    def __init__(self, token: str, tools, client=None):
        self.tools=tools
        if client is None:
            from openai import OpenAI
            client=OpenAI(api_key=token,base_url="https://api.openai.com/v1",timeout=45,max_retries=0)
        self.client=client

    def _definitions(self):
        allow={"terminal_status","symbols","symbol_specifications","quote",
               "historical_rates","open_positions","pending_orders"}
        names=[]
        for entry in self.tools.definitions():
            f=entry["function"]
            if f["name"] in allow:
                names.append({"type":"function","name":f["name"],"description":f["description"],
                              "parameters":f["parameters"]})
        return [{"type":"namespace","name":"mt5",
                 "description":"Read-only MetaTrader 5 account information and market prices",
                 "tools":names}] if names else []

    def ask(self,message: str,model: str) -> str:
        if not message or len(message)>3000 or not model or len(model)>100:
            raise ChatGPTInferenceError("Invalid ChatGPT message or model")
        input_items=[{"role":"user","content":message}]
        tools=self._definitions()
        for _ in range(4):
            final=None;text=[]
            try:
                with self.client.responses.create(model=model,input=input_items,
                    instructions="You are a read-only MetaTrader 5 assistant. Never invent account or price data. Broker trading is disabled.",
                    tools=tools,store=False,stream=True) as stream:
                    for event in stream:
                        if event.type=="response.output_text.delta": text.append(event.delta)
                        elif event.type in ("response.failed","response.incomplete","error"):
                            raise ChatGPTInferenceError("ChatGPT request failed or reached a usage limit")
                        elif event.type=="response.completed": final=event.response
            except ChatGPTInferenceError: raise
            except Exception as exc:
                raise ChatGPTInferenceError("ChatGPT plan inference failed; check selected model and plan limits") from exc
            if final is None: raise ChatGPTInferenceError("ChatGPT stream ended before response.completed")
            output=getattr(final,"output",[]) or []
            calls=[c for c in output if getattr(c,"type",None)=="function_call"]
            if not calls:
                answer="".join(text).strip()
                if not answer: raise ChatGPTInferenceError("ChatGPT returned no reply")
                return answer
            if len(calls)>6: raise ChatGPTInferenceError("Too many function calls")
            for entry in output:
                input_items.append(entry.model_dump(mode="json",exclude_none=True)
                    if hasattr(entry,"model_dump") else dict(entry))
            seen=set()
            for call in calls:
                ident=getattr(call,"call_id","")
                if not ident or ident in seen: raise ChatGPTInferenceError("Invalid duplicate tool identifier")
                seen.add(ident)
                name=getattr(call,"name","")
                if name.startswith("mt5."): name=name[4:]
                try:
                    args=json.loads(getattr(call,"arguments",""))
                    if name not in {"terminal_status","symbols","symbol_specifications","quote",
                                    "historical_rates","open_positions","pending_orders"}:
                        raise ValueError("Tool is not registered")
                    result={"ok":True,"data":self.tools.execute(name,args)}
                except Exception as exc:
                    result={"ok":False,"error":type(exc).__name__}
                input_items.append({"type":"function_call_output","call_id":ident,
                                    "output":json.dumps(result,default=str)})
        raise ChatGPTInferenceError("Tool iteration limit reached; no additional operations executed")
