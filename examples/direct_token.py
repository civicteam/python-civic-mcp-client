from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient


async def main() -> None:
    # Recommended production-like path:
    # - https://github.com/civicteam/demos/tree/main/apps/civic-auth-demo-python-backend
    #
    # This script is for optional local testing using direct token auth:
    # 1) open https://app.civic.com/web/install/mcp-url
    # 2) click "Generate token"
    # 3) set the returned access_token as CIVIC_ACCESS_TOKEN
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "CIVIC_ACCESS_TOKEN is required for direct token auth.\n\n"
            "For the recommended demo flow see:\n"
            "https://github.com/civicteam/demos/tree/main/apps/civic-auth-demo-python-backend\n\n"
            "For local testing, generate a token at:\n"
            "https://app.civic.com/web/install/mcp-url"
        )

    client = CivicMCPClient(
        auth={"token": token},
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
