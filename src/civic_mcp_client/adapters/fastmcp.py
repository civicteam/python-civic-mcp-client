from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..backends import MCPBackend


class FastMCPDependencyError(ImportError):
    pass


@dataclass(slots=True)
class FastMCPBackend:
    url: str
    client_cls: Any
    transport_cls: Any
    _client_ctx: Any = None
    _client: Any = None
    _header_signature: tuple[tuple[str, str], ...] | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def _ensure_client(self, headers: dict[str, str]) -> Any:
        signature = tuple(sorted(headers.items()))
        async with self._lock:
            if self._client is not None and self._header_signature == signature:
                return self._client

            await self._close_client_unlocked()
            transport = self.transport_cls(self.url, headers=dict(headers))
            self._client_ctx = self.client_cls(transport)
            self._client = await self._client_ctx.__aenter__()
            self._header_signature = signature
            return self._client

    async def list_tools(self, headers: dict[str, str]) -> dict[str, Any]:
        client = await self._ensure_client(headers)
        tools = await client.list_tools()
        normalized = []
        for tool in tools:
            if isinstance(tool, Mapping):
                normalized.append(dict(tool))
            else:
                normalized.append(
                    {
                        "name": getattr(tool, "name", ""),
                        "description": getattr(tool, "description", None),
                        "inputSchema": getattr(tool, "inputSchema", {"type": "object"}),
                    }
                )
        return {"tools": normalized}

    async def get_server_instructions(self, headers: dict[str, str]) -> str:
        client = await self._ensure_client(headers)
        info = await client.get_server_info()
        if isinstance(info, Mapping):
            instructions = info.get("instructions", "")
            return instructions if isinstance(instructions, str) else ""
        return ""

    async def call_tool(self, name: str, args: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        client = await self._ensure_client(headers)
        result = await client.call_tool(name, args)
        if isinstance(result, Mapping):
            return dict(result)
        return {"content": result}

    async def close(self) -> None:
        async with self._lock:
            await self._close_client_unlocked()

    async def _close_client_unlocked(self) -> None:
        if self._client_ctx is None:
            return

        if hasattr(self._client_ctx, "__aexit__"):
            await self._client_ctx.__aexit__(None, None, None)
        elif hasattr(self._client_ctx, "aclose"):
            await self._client_ctx.aclose()

        self._client_ctx = None
        self._client = None
        self._header_signature = None


async def create_fastmcp_backend(url: str) -> MCPBackend:
    try:
        from fastmcp import Client
        from fastmcp.client import StreamableHttpTransport
    except ImportError as exc:
        raise FastMCPDependencyError(
            "fastmcp extra is not installed. Install with: pip install civic-mcp-client[fastmcp]"
        ) from exc

    return FastMCPBackend(url=url, client_cls=Client, transport_cls=StreamableHttpTransport)
