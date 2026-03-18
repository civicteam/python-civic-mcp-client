from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient


def get_subject_token() -> str:
    token = os.getenv("EXTERNAL_SUBJECT_TOKEN")
    if not token:
        raise RuntimeError("EXTERNAL_SUBJECT_TOKEN is required for token exchange")
    return token


async def main() -> None:
    client_id = os.getenv("CIVIC_CLIENT_ID")
    client_secret = os.getenv("CIVIC_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("CIVIC_CLIENT_ID and CIVIC_CLIENT_SECRET are required")

    client = CivicMCPClient(
        auth={
            "token_exchange": {
                "client_id": client_id,
                "client_secret": client_secret,
                "subject_token": get_subject_token,
                "auth_url": os.getenv("CIVIC_AUTH_URL", "https://auth.civic.com/oauth/token"),
            }
        },
        url=os.getenv("CIVIC_MCP_HUB_URL", "https://nexus.civic.com/hub/mcp"),
        civic_account=os.getenv("CIVIC_ACCOUNT_ID"),
        civic_profile=os.getenv("CIVIC_PROFILE_ID"),
    )

    try:
        tools = await client.get_tools()
        tool_count = len(tools.get("tools", [])) if isinstance(tools, dict) else 0
        print(f"Token exchange succeeded. Found {tool_count} tools.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
