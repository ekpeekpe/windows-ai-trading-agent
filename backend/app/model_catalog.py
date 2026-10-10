"""Model choices are retrieved from each provider using that provider's own key.
No fabricated model entitlement or performance rankings.
"""
from __future__ import annotations
from datetime import datetime, timezone
from itertools import islice
from .credentials import validate_provider

def _order(items):
    # Oldest first ONLY when the upstream API provides a release timestamp;
    # unknown dates go last in stable identifier order.
    def key(item):
        return (0, item["created_at"], item["id"]) if item["created_at"] else (1, "", item["id"])
    return sorted(items,key=key)

def _date(value):
    if isinstance(value,(int,float)):
        return datetime.fromtimestamp(value,tz=timezone.utc).isoformat()
    if isinstance(value,datetime):return value.isoformat()
    return value if isinstance(value,str) else None

def provider_models(provider:str, key:str, sdk_factories=None):
    validate_provider(provider)
    if not key: raise ValueError("Provider API key not configured")
    if sdk_factories:
        client=sdk_factories[provider](key)
    elif provider=="openai":
        from openai import OpenAI
        client=OpenAI(api_key=key,timeout=15,max_retries=0)
    elif provider=="anthropic":
        from anthropic import Anthropic
        client=Anthropic(api_key=key,timeout=15,max_retries=0)
    else:
        from google import genai
        client=genai.Client(api_key=key,http_options={"timeout":15000})
    if provider=="openai":
        raw=client.models.list().data
    elif provider=="anthropic":
        raw=client.models.list(limit=100).data
    else:
        raw=islice(client.models.list(),100)
    items=[]
    for m in raw:
        identifier=getattr(m,"id",None) or getattr(m,"name",None)
        if not isinstance(identifier,str):continue
        if provider=="gemini":
            identifier=identifier.removeprefix("models/")
            if not identifier.startswith("gemini-") or any(x in identifier.lower() for x in
                    ("embedding","tts","image","live","robotics")):continue
            actions=getattr(m,"supported_actions",None) or getattr(m,"supported_generation_methods",None)
            if actions and "generateContent" not in actions:continue
        elif provider=="openai":
            if not (identifier.startswith("gpt-") or identifier.startswith("o") and
                    identifier[1:2].isdigit()):continue
            if any(x in identifier for x in ("audio","transcribe","tts","realtime","search","image")):continue
        else:
            if not identifier.startswith("claude-"):continue
            if getattr(m,"lifecycle",None)=="retired":continue
        items.append({"id":identifier,"label":getattr(m,"display_name",None) or getattr(m,"display_name",None)
                      or identifier,"created_at":_date(getattr(m,"created_at",None) or getattr(m,"created",None))})
        if len(items)>=100:break
    return _order(items)
