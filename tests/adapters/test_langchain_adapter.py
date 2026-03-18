from __future__ import annotations

import pytest

from civic_mcp_client.adapters.langchain import (
    execute_langchain_tool_call,
    get_langchain_tool_schemas,
    parse_langchain_tool_call,
)
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
async def test_langchain_tool_schema_shape():
    backend = StubBackend()
    client = CivicMCPClient(auth={"token": "token"}, backend=backend)
    schemas = await get_langchain_tool_schemas(client)
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "search_docs"
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_execute_langchain_tool_call_bridge():
    backend = StubBackend()
    client = CivicMCPClient(auth={"token": "token"}, backend=backend)
    result = await execute_langchain_tool_call(
        client,
        {"name": "search_docs", "args": {"query": "auth docs"}},
    )
    assert result["name"] == "search_docs"
    assert result["args"]["query"] == "auth docs"
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer token"


def test_parse_langchain_tool_call_json_args():
    parsed = parse_langchain_tool_call({"name": "search_docs", "args": '{"query":"hello"}'})
    assert parsed.name == "search_docs"
    assert parsed.arguments["query"] == "hello"
