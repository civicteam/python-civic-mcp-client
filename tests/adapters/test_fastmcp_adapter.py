from __future__ import annotations

import sys
from types import ModuleType

import pytest

from civic_mcp_client.adapters.fastmcp import FastMCPDependencyError, create_fastmcp_backend


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


@pytest.mark.asyncio
async def test_create_fastmcp_backend_import_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "fastmcp", None)
    with pytest.raises(FastMCPDependencyError):
        await create_fastmcp_backend("https://example.com/mcp")


@pytest.mark.asyncio
async def test_create_fastmcp_backend_and_bridge(monkeypatch: pytest.MonkeyPatch):
    FakeFastMCPClient.instances.clear()
    FakeTransport.instances.clear()
    module = ModuleType("fastmcp")
    module.Client = FakeFastMCPClient
    client_mod = ModuleType("fastmcp.client")
    client_mod.StreamableHttpTransport = FakeTransport
    monkeypatch.setitem(sys.modules, "fastmcp", module)
    monkeypatch.setitem(sys.modules, "fastmcp.client", client_mod)

    backend = await create_fastmcp_backend("https://example.com/mcp")
    tools = await backend.list_tools(headers={"Authorization": "Bearer token-a"})
    assert tools["tools"][0]["name"] == "search_docs"

    instructions = await backend.get_server_instructions(headers={"Authorization": "Bearer token-a"})
    assert instructions == "server instructions"

    call = await backend.call_tool(
        "search_docs",
        {"query": "hello"},
        headers={"Authorization": "Bearer token-b"},
    )
    assert call["args"]["query"] == "hello"
    assert len(FakeFastMCPClient.instances) == 2
    assert len(FakeTransport.instances) == 2
    assert FakeTransport.instances[0].headers["Authorization"] == "Bearer token-a"
    assert FakeTransport.instances[1].headers["Authorization"] == "Bearer token-b"
