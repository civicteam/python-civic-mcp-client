from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.pydanticai import pydanticai


async def main() -> None:
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("CIVIC_ACCESS_TOKEN is required")

    client = CivicMCPClient(
        auth={"token": token},
        url=os.getenv("CIVIC_MCP_HUB_URL", "https://app.civic.com/hub/mcp"),
        civic_profile=os.getenv("CIVIC_PROFILE_ID"),
    )

    try:
        tools = await client.adapt_for(pydanticai())
        print(f"PydanticAI tool count: {len(tools)}")
        if tools:
            print(f"First tool name: {tools[0].name}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
