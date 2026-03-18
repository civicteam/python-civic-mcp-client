from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .auth import build_context_headers, build_user_agent, parse_auth, resolve_token
from .backends import HttpMCPBackend, MCPBackend
from .token_exchange import TokenExchangeManager
from .types import (
    AuthInput,
    CivicMCPClientConfig,
    ReconnectionOptions,
    TokenAuth,
    TokenExchangeAuth,
)


@dataclass(slots=True)
class _ResolvedConfig:
    url: str
    auth: TokenAuth | TokenExchangeAuth
    civic_account: str | None
    civic_profile: str | None
    headers: dict[str, str]
    client_name: str
    client_version: str
    reconnection: ReconnectionOptions
    ping_timeout: int
    capabilities: dict[str, Any]


class CivicMCPClient:
    def __init__(
        self,
        *,
        auth: AuthInput,
        url: str = "https://nexus.civic.com/hub/mcp",
        civic_account: str | None = None,
        civic_profile: str | None = None,
        headers: Mapping[str, str] | None = None,
        client_name: str = "civic-mcp-client-python",
        client_version: str = "0.1.0",
        reconnection: ReconnectionOptions | None = None,
        ping_timeout: int = 5000,
        capabilities: dict[str, Any] | None = None,
        backend: MCPBackend | None = None,
    ) -> None:
        config = CivicMCPClientConfig(
            auth=auth,
            url=url,
            civic_account=civic_account,
            civic_profile=civic_profile,
            headers=dict(headers) if headers else None,
            client_name=client_name,
            client_version=client_version,
            reconnection=reconnection,
            ping_timeout=ping_timeout,
            capabilities=capabilities or {},
        )
        self._config = self._resolve_config(config)
        self._token_exchange_manager: TokenExchangeManager | None = None
        if isinstance(self._config.auth, TokenExchangeAuth):
            self._token_exchange_manager = TokenExchangeManager(self._config.auth.token_exchange)
        self._backend = backend or HttpMCPBackend(
            self._config.url,
            client_name=self._config.client_name,
            client_version=self._config.client_version,
            capabilities=self._config.capabilities,
        )

    @classmethod
    def from_config(cls, config: CivicMCPClientConfig, backend: MCPBackend | None = None) -> "CivicMCPClient":
        as_dict = asdict(config)
        return cls(**as_dict, backend=backend)

    async def get_tools(self, adapter: Any | None = None) -> Any:
        raw = await self._backend.list_tools(headers=await self._build_auth_headers())
        if adapter is None:
            return raw
        if callable(adapter):
            return await adapter(self, raw)
        raise TypeError("adapter must be callable or None")

    async def get_server_instructions(self) -> str:
        return await self._backend.get_server_instructions(headers=await self._build_auth_headers())

    async def call_tool(self, *, name: str, args: Mapping[str, Any]) -> dict[str, Any]:
        return await self._backend.call_tool(name=name, args=dict(args), headers=await self._build_auth_headers())

    async def close(self) -> None:
        await self._backend.close()

    def get_config(self) -> CivicMCPClientConfig:
        return CivicMCPClientConfig(
            auth=self._config.auth,
            url=self._config.url,
            civic_account=self._config.civic_account,
            civic_profile=self._config.civic_profile,
            headers=dict(self._config.headers),
            client_name=self._config.client_name,
            client_version=self._config.client_version,
            reconnection=self._config.reconnection,
            ping_timeout=self._config.ping_timeout,
            capabilities=dict(self._config.capabilities),
        )

    async def _build_auth_headers(self) -> dict[str, str]:
        token = await self._resolve_access_token()
        headers = build_context_headers(
            base_headers=self._config.headers,
            civic_account=self._config.civic_account,
            civic_profile=self._config.civic_profile,
        )
        headers["Authorization"] = f"Bearer {token}"
        headers["User-Agent"] = build_user_agent(self._config.client_name, self._config.client_version)
        return headers

    async def _resolve_access_token(self) -> str:
        auth = self._config.auth
        if isinstance(auth, TokenAuth):
            return await resolve_token(auth.token)
        if isinstance(auth, TokenExchangeAuth):
            assert self._token_exchange_manager is not None
            return await self._token_exchange_manager.get_access_token(
                civic_account=self._config.civic_account,
                civic_profile=self._config.civic_profile,
            )
        raise RuntimeError("unsupported auth configuration")

    def _resolve_config(self, config: CivicMCPClientConfig) -> _ResolvedConfig:
        return _ResolvedConfig(
            url=config.url,
            auth=parse_auth(config.auth),
            civic_account=config.civic_account,
            civic_profile=config.civic_profile,
            headers=dict(config.headers or {}),
            client_name=config.client_name,
            client_version=config.client_version,
            reconnection=config.reconnection or ReconnectionOptions(),
            ping_timeout=config.ping_timeout,
            capabilities=dict(config.capabilities),
        )
