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
