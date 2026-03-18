from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.fastmcp import fastmcp


async def main() -> None:
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("CIVIC_ACCESS_TOKEN is required")

    client = CivicMCPClient(
        auth={"token": token},
        civic_profile=os.getenv("CIVIC_PROFILE_ID"),
    )

    fastmcp_client = await client.adapt_for(fastmcp())

    try:
        tools = await fastmcp_client.get_tools()
        tool_count = len(tools.get("tools", [])) if isinstance(tools, dict) else 0
        print(f"FastMCP backend tool count: {tool_count}")
    finally:
        await fastmcp_client.close()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
