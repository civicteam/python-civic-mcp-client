from __future__ import annotations

import asyncio
import os

from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.langchain import langchain


async def main() -> None:
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("CIVIC_ACCESS_TOKEN is required")

    client = CivicMCPClient(
        auth={"token": token},
        civic_profile=os.getenv("CIVIC_PROFILE_ID"),
    )

    try:
        schemas = await client.adapt_for(langchain())
        print(f"LangChain schema count: {len(schemas)}")
        if schemas:
            first = schemas[0]["function"]["name"]
            print(f"First tool name: {first}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
