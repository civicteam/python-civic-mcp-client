from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..client import CivicMCPClient


@dataclass(slots=True)
class PydanticAIToolDefinition:
    name: str
    description: str | None
    parameters_json_schema: dict[str, Any]


def pydanticai():
    """Return an adapter for use with client.adapt_for(pydanticai())."""

    async def adapter(_client: CivicMCPClient, raw_tools_payload: Mapping[str, Any]) -> list[PydanticAIToolDefinition]:
        raw_tools = raw_tools_payload.get("tools", []) if isinstance(raw_tools_payload, Mapping) else []
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

    return adapter
