from __future__ import annotations

import os

import pytest

from civic_mcp_client import CivicMCPClient


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_live_hub_smoke():
    token = os.getenv("CIVIC_ACCESS_TOKEN")
    if not token:
        pytest.skip("CIVIC_ACCESS_TOKEN is not configured")

    profile = os.getenv("CIVIC_PROFILE_ID")

    client = CivicMCPClient(
        auth={"token": token},
        civic_profile=profile,
    )

    try:
        tools = await client.get_tools()
        assert isinstance(tools, dict)
        assert "tools" in tools
    finally:
        await client.close()
