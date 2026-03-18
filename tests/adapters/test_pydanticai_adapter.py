from __future__ import annotations

import pytest

from civic_mcp_client.adapters.pydanticai import pydanticai
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
async def test_pydanticai_adapt_for_returns_tool_definitions():
    backend = StubBackend()
    client = CivicMCPClient(auth={"token": "token"}, backend=backend)
    tools = await client.adapt_for(pydanticai())
    assert len(tools) == 1
    assert tools[0].name == "search_docs"
    assert tools[0].parameters_json_schema["type"] == "object"
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_pydanticai_adapt_for_client_call_tool_uses_auth_headers():
    backend = StubBackend()
    client = CivicMCPClient(auth={"token": "token-2"}, backend=backend)
    await client.adapt_for(pydanticai())
    result = await client.call_tool(name="search_docs", args={"query": "hello"})
    assert result["name"] == "search_docs"
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer token-2"
