from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..client import CivicMCPClient


@dataclass(slots=True)
class PydanticAIToolDefinition:
    name: str
    description: str | None
    parameters_json_schema: dict[str, Any]


@dataclass(slots=True)
class PydanticAIToolsetBridge:
    client: CivicMCPClient

    async def list_tools(self) -> list[PydanticAIToolDefinition]:
        tools = await self.client.get_tools()
        raw_tools = tools.get("tools", []) if isinstance(tools, Mapping) else []
        result: list[PydanticAIToolDefinition] = []
        for tool in raw_tools:
            if not isinstance(tool, Mapping):
                continue
            result.append(
                PydanticAIToolDefinition(
                    name=str(tool.get("name", "")),
                    description=tool.get("description") if isinstance(tool.get("description"), str) else None,
                    parameters_json_schema=(
                        dict(tool.get("inputSchema"))
                        if isinstance(tool.get("inputSchema"), Mapping)
                        else {"type": "object"}
                    ),
                )
            )
        return result

    async def call_tool(self, name: str, args: Mapping[str, Any]) -> dict[str, Any]:
        return await self.client.call_tool(name=name, args=args)


def to_pydanticai_toolset(client: CivicMCPClient) -> PydanticAIToolsetBridge:
    return PydanticAIToolsetBridge(client=client)
