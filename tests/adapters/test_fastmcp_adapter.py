from __future__ import annotations

import sys
from types import ModuleType

import pytest

from civic_mcp_client.adapters.fastmcp import FastMCPDependencyError, fastmcp
from civic_mcp_client.client import CivicMCPClient


class FakeTransport:
    instances: list["FakeTransport"] = []

    def __init__(self, url: str, headers: dict[str, str] | None = None, auth=None, **kwargs) -> None:
        del auth, kwargs
        self.url = url
        self.headers = headers or {}
        FakeTransport.instances.append(self)


class FakeFastMCPClient:
    instances: list["FakeFastMCPClient"] = []

    def __init__(self, transport) -> None:
        self.transport = transport
        self.entered = False
        self.closed = False
        FakeFastMCPClient.instances.append(self)

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        self.closed = True

    async def list_tools(self):
        return [
            {
                "name": "search_docs",
                "description": "Search docs",
                "inputSchema": {"type": "object"},
            }
        ]

    async def get_server_info(self):
        return {"instructions": "server instructions"}

    async def call_tool(self, name: str, args: dict[str, object]):
        return {"name": name, "args": args}

    async def aclose(self):
        self.closed = True


class StubBackend:
    async def list_tools(self, headers: dict[str, str]):
        del headers
        return {"tools": []}

    async def get_server_instructions(self, headers: dict[str, str]) -> str:
        del headers
        return ""

    async def call_tool(self, name: str, args: dict[str, object], headers: dict[str, str]):
        del name, args, headers
        return {}

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_fastmcp_adapt_for_import_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "fastmcp", None)
    client = CivicMCPClient(
        auth={"token": "token"},
        url="https://example.com/mcp",
        backend=StubBackend(),
    )
    with pytest.raises(FastMCPDependencyError):
        await client.adapt_for(fastmcp())


@pytest.mark.asyncio
async def test_fastmcp_adapt_for_returns_client_with_headers(monkeypatch: pytest.MonkeyPatch):
    FakeFastMCPClient.instances.clear()
    FakeTransport.instances.clear()
    module = ModuleType("fastmcp")
    module.Client = FakeFastMCPClient
    client_mod = ModuleType("fastmcp.client")
    client_mod.StreamableHttpTransport = FakeTransport
    monkeypatch.setitem(sys.modules, "fastmcp", module)
    monkeypatch.setitem(sys.modules, "fastmcp.client", client_mod)

    client = CivicMCPClient(
        auth={"token": "token"},
        civic_profile="profile-456",
        url="https://example.com/mcp",
        backend=StubBackend(),
    )
    adapted = await client.adapt_for(fastmcp())
    assert isinstance(adapted, CivicMCPClient)
    tools = await adapted.get_tools()
    assert tools["tools"][0]["name"] == "search_docs"
    assert FakeTransport.instances
    last_headers = FakeTransport.instances[-1].headers
    assert last_headers["Authorization"] == "Bearer token"
    assert last_headers["x-civic-profile-id"] == "profile-456"
