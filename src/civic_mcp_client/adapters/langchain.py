from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from ..client import CivicMCPClient


@dataclass(slots=True)
class LangChainToolCall:
    name: str
    arguments: dict[str, Any]


def parse_langchain_tool_call(tool_call: Mapping[str, Any]) -> LangChainToolCall:
    name = str(tool_call.get("name", ""))
    if not name:
        raise ValueError("tool_call missing name")

    arguments = tool_call.get("args", {})
    if isinstance(arguments, str):
        parsed = json.loads(arguments)
        if not isinstance(parsed, dict):
            raise ValueError("tool args JSON must decode to an object")
        arguments = parsed

    if not isinstance(arguments, Mapping):
        raise ValueError("tool_call args must be a mapping")

    return LangChainToolCall(name=name, arguments=dict(arguments))


async def execute_langchain_tool_call(
    client: CivicMCPClient,
    tool_call: Mapping[str, Any],
) -> dict[str, Any]:
    parsed = parse_langchain_tool_call(tool_call)
    return await client.call_tool(name=parsed.name, args=parsed.arguments)


def langchain():
    """Return an adapter for use with client.adapt_for(langchain())."""

    async def adapter(_client: CivicMCPClient, raw_tools_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        raw_tools = raw_tools_payload.get("tools", []) if isinstance(raw_tools_payload, Mapping) else []
        schemas: list[dict[str, Any]] = []
        for tool in raw_tools:
            if not isinstance(tool, Mapping):
                continue
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("inputSchema", {"type": "object"}),
                    },
                }
            )
        return schemas

    return adapter
