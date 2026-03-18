from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient


async def main() -> None:
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("CIVIC_ACCESS_TOKEN is required")

    client = CivicMCPClient(
        auth={"token": token},
        url=os.getenv("CIVIC_MCP_HUB_URL", "https://nexus.civic.com/hub/mcp"),
        civic_account=os.getenv("CIVIC_ACCOUNT_ID"),
        civic_profile=os.getenv("CIVIC_PROFILE_ID"),
    )

    try:
        tools = await client.get_tools()
        tool_count = len(tools.get("tools", [])) if isinstance(tools, dict) else 0
        print(f"Connected. Found {tool_count} tools.")

        instructions = await client.get_server_instructions()
        print(f"Instructions preview: {instructions[:200]!r}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
