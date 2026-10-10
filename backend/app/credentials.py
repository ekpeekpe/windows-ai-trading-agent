"""OS protected AI credentials. Environment keys remain developer-only.

Refuse non-Windows or non-Windows-Vault backends; never write plaintext files.
"""
from __future__ import annotations
import os
from typing import Callable

SERVICE = "com.ekpeekpe.windows-ai-trading-agent.providers"
ENV_NAMES = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}

class CredentialUnavailable(RuntimeError):
    pass

def validate_provider(provider: str) -> str:
    if provider not in ENV_NAMES:
        raise ValueError("Unsupported AI provider")
    return provider

def vault():
    if os.name != "nt":
        raise CredentialUnavailable("Protected credential storage is supported on Windows only")
    try:
        from keyring.backends.Windows import WinVaultKeyring
        # Always use OS-protected WinVault, regardless of global keyring setup.
        # Never fall back to third-party or file-based credential backends.
        backend = WinVaultKeyring()
        if backend.priority <= 0:
            raise CredentialUnavailable("Windows Credential Manager is unavailable")
        return backend
    except ImportError as exc:
        raise CredentialUnavailable("Windows credential storage dependency not installed") from exc

def stored(provider: str) -> bool:
    return bool(vault().get_password(SERVICE, validate_provider(provider)))

def get_key(provider: str) -> str | None:
    provider = validate_provider(provider)
    env = os.environ.get(ENV_NAMES[provider])
    if env:
        return env
    try:
        return vault().get_password(SERVICE, provider)
    except CredentialUnavailable:
        return None

def set_key(provider: str, secret: str):
    validate_provider(provider)
    if not isinstance(secret, str) or not 12 <= len(secret) <= 512 or any(x in secret for x in ("\r", "\n", "\0")):
        raise ValueError("Invalid API key format")
    vault().set_password(SERVICE, provider, secret)

def delete_key(provider: str):
    provider = validate_provider(provider)
    v = vault()
    if v.get_password(SERVICE, provider):
        v.delete_password(SERVICE, provider)

def connection_status() -> list[dict]:
    result = []
    for provider in ENV_NAMES:
        try:
            configured = bool(get_key(provider))
        except Exception:
            configured = False
        result.append({"provider": provider, "configured": configured,
                       "authentication": "api_key", "verified": False})
    return result

def check_connection(provider: str, key: str, clients: dict[str, Callable] | None = None) -> None:
    """Real harmless official-SDK models-list call; exceptions never mean success."""
    validate_provider(provider)
    if clients is not None:
        return clients[provider](key)
    if provider == "openai":
        from openai import OpenAI
        OpenAI(api_key=key, timeout=12, max_retries=0).models.list()
    elif provider == "anthropic":
        from anthropic import Anthropic
        Anthropic(api_key=key, timeout=12, max_retries=0).models.list(limit=1)
    else:
        from google import genai
        client = genai.Client(api_key=key, http_options={"timeout": 12000})
        next(iter(client.models.list(config={"page_size": 1})), None)

# Win32 generic credentials have a 2,560-byte blob limit (wincred.h).
# OAuth token records can exceed it. Store every segment in *Windows
# Credential Manager*, not ordinary files or an unprotected key store.
# The root credential is a signed-by-hash manifest; a rotating revision
# prevents refresh-token updates from corrupting an older complete record.
import hashlib
import secrets

_CHUNK_PREFIX="@agent-wincred-v1:"
_MAX_SEGMENTS=96
_SEGMENT_CHARS=700  # <= 1,400 UTF-16LE bytes per protected WinVault entry

class SegmentedWindowsVault:
    def __init__(self, backing):
        self.backing=backing

    @staticmethod
    def _manifest(value):
        if not value or not value.startswith(_CHUNK_PREFIX):return None
        try:
            revision,count,digest=value[len(_CHUNK_PREFIX):].split(":")
            size=int(count)
            if len(revision)!=20 or not 1<=size<=_MAX_SEGMENTS or len(digest)!=64:
                raise ValueError("Bad vault manifest")
            if not all(x in "0123456789abcdef" for x in revision+digest):
                raise ValueError("Bad vault manifest")
            return revision,size,digest
        except (ValueError,TypeError) as exc:
            raise CredentialUnavailable("Protected ChatGPT credentials are incomplete; sign in again") from exc

    @staticmethod
    def _part_key(key,revision,index):
        return f"{key}:part:{revision}:{index}"

    def _clear_parts(self,service,key,manifest):
        if not manifest:return
        revision,count,_=manifest
        for i in range(count):
            entry=self._part_key(key,revision,i)
            if self.backing.get_password(service,entry) is not None:
                self.backing.delete_password(service,entry)

    def get_password(self,service,key):
        stored=self.backing.get_password(service,key)
        manifest=self._manifest(stored)
        if not manifest:return stored
        revision,count,digest=manifest
        parts=[self.backing.get_password(service,self._part_key(key,revision,i))
               for i in range(count)]
        if any(part is None for part in parts):
            raise CredentialUnavailable("Protected ChatGPT token record is incomplete; sign in again")
        value="".join(parts)
        if hashlib.sha256(value.encode("utf-8")).hexdigest()!=digest:
            raise CredentialUnavailable("Protected ChatGPT token record failed integrity validation")
        return value

    def set_password(self,service,key,value):
        if not isinstance(value,str):raise ValueError("Protected credential must be text")
        previous=self.backing.get_password(service,key)
        old=self._manifest(previous)
        if len(value.encode("utf-16-le"))<=1600:
            self.backing.set_password(service,key,value)
            self._clear_parts(service,key,old)
            return
        parts=[value[i:i+_SEGMENT_CHARS] for i in range(0,len(value),_SEGMENT_CHARS)]
        if not 1<=len(parts)<=_MAX_SEGMENTS:
            raise CredentialUnavailable("OAuth token record exceeds protected storage limit")
        revision=secrets.token_hex(10)
        written=[]
        try:
            for i,part in enumerate(parts):
                name=self._part_key(key,revision,i)
                self.backing.set_password(service,name,part)
                written.append(name)
            digest=hashlib.sha256(value.encode("utf-8")).hexdigest()
            self.backing.set_password(service,key,f"{_CHUNK_PREFIX}{revision}:{len(parts)}:{digest}")
        except Exception:
            # No manifest was published, so the previous token stays readable.
            for entry in written:
                try:self.backing.delete_password(service,entry)
                except Exception:pass
            raise
        self._clear_parts(service,key,old)

    def delete_password(self,service,key):
        stored=self.backing.get_password(service,key)
        if stored is None:return
        manifest=self._manifest(stored)
        self.backing.delete_password(service,key)
        self._clear_parts(service,key,manifest)

def protected_chatgpt_vault():
    return SegmentedWindowsVault(vault())
