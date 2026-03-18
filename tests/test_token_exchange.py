from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from civic_mcp_client.token_exchange import TokenExchangeError, TokenExchangeManager
from civic_mcp_client.types import TokenExchangeConfig


@pytest.fixture
def config() -> TokenExchangeConfig:
    return TokenExchangeConfig(
        client_id="client-id",
        client_secret="client-secret",
        subject_token=lambda: "subject-token",
        auth_url="https://auth.example.com/oauth/token",
    )


async def _make_requester(tokens: AsyncIterator[dict[str, object]], calls: list[tuple[str, str | None, str | None]]):
    async def requester(
        cfg: TokenExchangeConfig, subject: str, civic_account: str | None, civic_profile: str | None
    ) -> dict[str, object]:
        del cfg
        calls.append((subject, civic_account, civic_profile))
        return await anext(tokens)

    return requester


@pytest.mark.asyncio
async def test_token_exchange_happy_path_and_cache(config: TokenExchangeConfig) -> None:
    calls: list[tuple[str, str | None, str | None]] = []

    async def payloads() -> AsyncIterator[dict[str, object]]:
        yield {"access_token": "token-1", "expires_in": 120}

    requester = await _make_requester(payloads(), calls)
    manager = TokenExchangeManager(config, requester=requester)

    token1 = await manager.get_access_token(civic_account="account", civic_profile="profile")
    token2 = await manager.get_access_token(civic_account="account", civic_profile="profile")

    assert token1 == "token-1"
    assert token2 == "token-1"
    assert calls == [("subject-token", "account", "profile")]


@pytest.mark.asyncio
async def test_token_refresh_on_expiry(config: TokenExchangeConfig) -> None:
    calls: list[tuple[str, str | None, str | None]] = []

    async def payloads() -> AsyncIterator[dict[str, object]]:
        # Force immediate expiry (expires_in <= 0 => expires_at = now)
        yield {"access_token": "token-1", "expires_in": 0}
        yield {"access_token": "token-2", "expires_in": 120}

    requester = await _make_requester(payloads(), calls)
    manager = TokenExchangeManager(config, requester=requester)

    token1 = await manager.get_access_token()
    await asyncio.sleep(0)
    token2 = await manager.get_access_token()

    assert token1 == "token-1"
    assert token2 == "token-2"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_token_change_invalidates_cache() -> None:
    calls: list[tuple[str, str | None, str | None]] = []
    current_subject = {"value": "subject-a"}

    config = TokenExchangeConfig(
        client_id="client-id",
        client_secret="client-secret",
        subject_token=lambda: current_subject["value"],
        auth_url="https://auth.example.com/oauth/token",
    )

    async def payloads() -> AsyncIterator[dict[str, object]]:
        yield {"access_token": "token-a", "expires_in": 120}
        yield {"access_token": "token-b", "expires_in": 120}

    requester = await _make_requester(payloads(), calls)
    manager = TokenExchangeManager(config, requester=requester)

    first = await manager.get_access_token()
    current_subject["value"] = "subject-b"
    second = await manager.get_access_token()

    assert first == "token-a"
    assert second == "token-b"
    assert calls[0][0] == "subject-a"
    assert calls[1][0] == "subject-b"


@pytest.mark.asyncio
async def test_empty_subject_token_clears_and_raises(config: TokenExchangeConfig) -> None:
    async def requester(
        cfg: TokenExchangeConfig, subject: str, civic_account: str | None, civic_profile: str | None
    ) -> dict[str, object]:
        del cfg, subject, civic_account, civic_profile
        return {"access_token": "token-1", "expires_in": 120}

    manager = TokenExchangeManager(config, requester=requester)
    token = await manager.get_access_token()
    assert token == "token-1"

    config.subject_token = lambda: ""
    with pytest.raises(TokenExchangeError):
        await manager.get_access_token()


@pytest.mark.asyncio
async def test_concurrent_calls_deduplicate_exchange(config: TokenExchangeConfig) -> None:
    call_count = 0
    gate = asyncio.Event()

    async def requester(
        cfg: TokenExchangeConfig, subject: str, civic_account: str | None, civic_profile: str | None
    ) -> dict[str, object]:
        nonlocal call_count
        del cfg, subject, civic_account, civic_profile
        call_count += 1
        await gate.wait()
        return {"access_token": "token-shared", "expires_in": 120}

    manager = TokenExchangeManager(config, requester=requester)
    task1 = asyncio.create_task(manager.get_access_token())
    task2 = asyncio.create_task(manager.get_access_token())
    await asyncio.sleep(0)
    gate.set()
    result1, result2 = await asyncio.gather(task1, task2)

    assert result1 == "token-shared"
    assert result2 == "token-shared"
    assert call_count == 1
