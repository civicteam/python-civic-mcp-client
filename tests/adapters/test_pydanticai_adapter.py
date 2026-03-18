from __future__ import annotations

import pytest

from civic_mcp_client.adapters.pydanticai import to_pydanticai_toolset
from civic_mcp_client.client import CivicMCPClient


class StubBackend:
    def __init__(self) -> None:
        self.last_headers: dict[str, str] | None = None

    async def list_tools(self, headers: dict[str, str]):
        self.last_headers = headers
        return {
            "tools": [
                {
                    "name": "search_docs",
                    "description": "Search docs",
                    "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
                }
            ]
        }

    async def get_server_instructions(self, headers: dict[str, str]) -> str:
        self.last_headers = headers
        return "instructions"

    async def call_tool(self, name: str, args: dict[str, object], headers: dict[str, str]):
        self.last_headers = headers
        return {"name": name, "args": args}

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_pydanticai_bridge_lists_tools():
    backend = StubBackend()
    client = CivicMCPClient(auth={"token": "token"}, backend=backend)
    bridge = to_pydanticai_toolset(client)
    tools = await bridge.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "search_docs"
    assert tools[0].parameters_json_schema["type"] == "object"
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_pydanticai_bridge_call_tool_uses_client_auth_headers():
    backend = StubBackend()
    client = CivicMCPClient(auth={"token": "token-2"}, backend=backend)
    bridge = to_pydanticai_toolset(client)
    result = await bridge.call_tool("search_docs", {"query": "hello"})
    assert result["name"] == "search_docs"
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer token-2"
