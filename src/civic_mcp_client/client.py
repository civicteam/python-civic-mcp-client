from __future__ import annotations

import inspect
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
        url: str = "https://app.civic.com/hub/mcp",
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

    async def get_tools(self) -> Any:
        """Return raw MCP tools from the hub."""
        return await self._get_raw_tools()

    async def adapt_for(self, adapter: Any) -> Any:
        """
        Run the given adapter and return either a new CivicMCPClient (backend adapters)
        or adapter-native tool output (e.g. list of schemas or tool definitions).

        Usage:
            client.adapt_for(fastmcp())   -> CivicMCPClient with FastMCP backend
            client.adapt_for(langchain()) -> list of LangChain tool schemas
            client.adapt_for(pydanticai()) -> list of PydanticAI tool definitions
        """
        if not callable(adapter):
            raise TypeError("adapter must be callable")

        if self._adapter_accepts_raw_tools(adapter):
            raw_tools = await self._get_raw_tools()
            adapted = adapter(self, raw_tools)
        else:
            adapted = adapter(self)

        if inspect.isawaitable(adapted):
            adapted = await adapted

        if isinstance(adapted, CivicMCPClient):
            return adapted
        if self._looks_like_backend(adapted):
            return CivicMCPClient.from_config(self.get_config(), backend=adapted)

        get_tools = getattr(adapted, "get_tools", None)
        if callable(get_tools):
            value = get_tools()
            return await value if inspect.isawaitable(value) else value
        return adapted

    async def get_server_instructions(self) -> str:
        return await self._backend.get_server_instructions(headers=await self._build_auth_headers())

    async def call_tool(self, *, name: str, args: Mapping[str, Any]) -> dict[str, Any]:
        return await self._backend.call_tool(name=name, args=dict(args), headers=await self._build_auth_headers())

    async def get_access_token(self) -> str:
        """
        Return the access token currently used for hub authentication.
        For token exchange auth, this returns the cached/exchanged token.
        """
        return await self._resolve_access_token()

    async def close(self) -> None:
        await self._backend.close()

    async def _get_raw_tools(self) -> Any:
        return await self._backend.list_tools(headers=await self._build_auth_headers())

    def _adapter_accepts_raw_tools(self, adapter: Any) -> bool:
        try:
            sig = inspect.signature(adapter)
        except (TypeError, ValueError):
            return False

        required_positionals = [
            param
            for param in sig.parameters.values()
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            and param.default is inspect.Parameter.empty
        ]
        has_varargs = any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in sig.parameters.values())
        return len(required_positionals) >= 2 or has_varargs

    def _looks_like_backend(self, value: Any) -> bool:
        required_methods = ("list_tools", "get_server_instructions", "call_tool", "close")
        return all(callable(getattr(value, method, None)) for method in required_methods)

    def get_config(self) -> CivicMCPClientConfig:
        return CivicMCPClientConfig(
            auth=self._config.auth,
            url=self._config.url,
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
                civic_profile=self._config.civic_profile,
            )
        raise RuntimeError("unsupported auth configuration")

    def _resolve_config(self, config: CivicMCPClientConfig) -> _ResolvedConfig:
        return _ResolvedConfig(
            url=config.url,
            auth=parse_auth(config.auth),
            civic_profile=config.civic_profile,
            headers=dict(config.headers or {}),
            client_name=config.client_name,
            client_version=config.client_version,
            reconnection=config.reconnection or ReconnectionOptions(),
            ping_timeout=config.ping_timeout,
            capabilities=dict(config.capabilities),
        )
