from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.fastmcp import create_fastmcp_backend


async def main() -> None:
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("CIVIC_ACCESS_TOKEN is required")

    backend = await create_fastmcp_backend(
        os.getenv("CIVIC_MCP_HUB_URL", "https://nexus.civic.com/hub/mcp")
    )
    client = CivicMCPClient(
        auth={"token": token},
        civic_account=os.getenv("CIVIC_ACCOUNT_ID"),
        civic_profile=os.getenv("CIVIC_PROFILE_ID"),
        backend=backend,
    )

    try:
        tools = await client.get_tools()
        tool_count = len(tools.get("tools", [])) if isinstance(tools, dict) else 0
        print(f"FastMCP backend tool count: {tool_count}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
