from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Mapping


TokenCallable = Callable[[], str | Awaitable[str]]
TokenInput = str | TokenCallable


@dataclass(slots=True)
class TokenExchangeConfig:
    client_id: str
    client_secret: str
    subject_token: TokenInput
    auth_url: str = "https://auth.civic.com/oauth/token"
    expires_in: int | None = None
    lock_to_profile: bool = True


@dataclass(slots=True)
class TokenAuth:
    token: TokenInput


@dataclass(slots=True)
class TokenExchangeAuth:
    token_exchange: TokenExchangeConfig


AuthInput = TokenAuth | TokenExchangeAuth | Mapping[str, Any]


@dataclass(slots=True)
class ReconnectionOptions:
    max_retries: int = 5
    initial_reconnection_delay: int = 300
    max_reconnection_delay: int = 30000
    reconnection_delay_grow_factor: float = 1.5


@dataclass(slots=True)
class CivicMCPClientConfig:
    auth: AuthInput
    url: str = "https://app.civic.com/hub/mcp"
    civic_profile: str | None = None
    headers: dict[str, str] | None = None
    client_name: str = "civic-mcp-client-python"
    client_version: str = "0.1.0"
    reconnection: ReconnectionOptions | None = None
    ping_timeout: int = 5000
    capabilities: dict[str, Any] = field(default_factory=dict)
