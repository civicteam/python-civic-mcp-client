from __future__ import annotations

from typing import Any

import pytest

from civic_mcp_client.client import CivicMCPClient
from civic_mcp_client.types import TokenExchangeConfig


class RecordingBackend:
    def __init__(self) -> None:
        self.last_headers: dict[str, str] | None = None

    async def list_tools(self, headers: dict[str, str]) -> dict[str, Any]:
        self.last_headers = headers
        return {"tools": []}

    async def get_server_instructions(self, headers: dict[str, str]) -> str:
        self.last_headers = headers
        return "server instructions"

    async def call_tool(self, name: str, args: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        self.last_headers = headers
        return {"name": name, "args": args}

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_direct_token_maps_context_headers() -> None:
    backend = RecordingBackend()
    client = CivicMCPClient(
        auth={"token": "direct-token"},
        civic_profile="profile-456",
        headers={"x-extra-header": "hello"},
        backend=backend,
    )

    await client.get_tools()
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer direct-token"
    assert backend.last_headers["x-civic-profile-id"] == "profile-456"
    assert backend.last_headers["x-extra-header"] == "hello"
    assert "User-Agent" in backend.last_headers


@pytest.mark.asyncio
async def test_token_exchange_auth_used_for_headers() -> None:
    backend = RecordingBackend()
    client = CivicMCPClient(
        auth={
            "token_exchange": TokenExchangeConfig(
                client_id="client-id",
                client_secret="client-secret",
                subject_token=lambda: "external-token",
            )
        },
        civic_profile="profile-456",
        backend=backend,
    )

    # Inject a deterministic exchange requester for test reliability.
    assert client._token_exchange_manager is not None

    async def requester(cfg: TokenExchangeConfig, subject: str, civic_profile: str | None) -> dict[str, Any]:
        del cfg, subject
        assert civic_profile == "profile-456"
        return {"access_token": "exchanged-token", "expires_in": 120}

    client._token_exchange_manager._requester = requester

    await client.get_server_instructions()
    assert backend.last_headers is not None
    assert backend.last_headers["Authorization"] == "Bearer exchanged-token"


@pytest.mark.asyncio
async def test_get_access_token_returns_current_token() -> None:
    backend = RecordingBackend()
    client = CivicMCPClient(auth={"token": "direct-token"}, backend=backend)
    assert await client.get_access_token() == "direct-token"
