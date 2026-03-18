from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx

from .auth import AuthConfigError, resolve_token
from .types import TokenExchangeConfig


class TokenExchangeError(RuntimeError):
    pass


TokenRequester = Callable[[TokenExchangeConfig, str, str | None], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class CachedExchangeToken:
    access_token: str
    expires_at: float
    subject_token: str


class TokenExchangeManager:
    def __init__(
        self,
        config: TokenExchangeConfig,
        requester: TokenRequester | None = None,
    ) -> None:
        self._config = config
        self._cache: CachedExchangeToken | None = None
        self._lock = asyncio.Lock()
        self._inflight_by_subject: dict[str, asyncio.Task[str]] = {}
        self._requester = requester or self._default_requester

    async def get_access_token(
        self,
        civic_profile: str | None = None,
    ) -> str:
        try:
            subject = await resolve_token(self._config.subject_token)
        except AuthConfigError as exc:
            await self._clear_cache()
            raise TokenExchangeError(str(exc)) from exc

        async with self._lock:
            now = time.time()
            if self._cache and self._cache.subject_token != subject:
                self._cache = None
            if self._cache and now < self._cache.expires_at:
                return self._cache.access_token

            task = self._inflight_by_subject.get(subject)
            if task is None:
                task = asyncio.create_task(
                    self._exchange_and_store(subject, civic_profile=civic_profile)
                )
                self._inflight_by_subject[subject] = task

        try:
            return await task
        finally:
            async with self._lock:
                existing = self._inflight_by_subject.get(subject)
                if existing is task and task.done():
                    self._inflight_by_subject.pop(subject, None)

    async def _exchange_and_store(
        self,
        subject: str,
        civic_profile: str | None,
    ) -> str:
        payload = await self._requester(self._config, subject, civic_profile)
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            await self._clear_cache()
            raise TokenExchangeError("token exchange response did not include a valid access_token")

        expires_in_raw = payload.get("expires_in", 0)
        expires_in = int(expires_in_raw) if isinstance(expires_in_raw, (int, float, str)) else 0
        if expires_in <= 0:
            expires_at = time.time()
        else:
            buffer_seconds = min(30.0, float(expires_in) / 2.0)
            expires_at = time.time() + max(0.0, float(expires_in) - buffer_seconds)

        async with self._lock:
            self._cache = CachedExchangeToken(
                access_token=access_token,
                expires_at=expires_at,
                subject_token=subject,
            )
        return access_token

    async def _default_requester(
        self,
        config: TokenExchangeConfig,
        subject_token: str,
        civic_profile: str | None,
    ) -> dict[str, Any]:
        basic = base64.b64encode(f"{config.client_id}:{config.client_secret}".encode("utf-8")).decode("ascii")
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        form: dict[str, str] = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }
        if config.expires_in is not None:
            form["expires_in"] = str(config.expires_in)
        if config.lock_to_profile and civic_profile:
            form["civic_profile"] = civic_profile

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(config.auth_url, headers=headers, data=form)
            if not response.is_success:
                err_body = (response.text or "")[:500]
                raise TokenExchangeError(
                    f"token exchange failed ({response.status_code}): {err_body}"
                )
            data = response.json()
            if not isinstance(data, dict):
                raise TokenExchangeError("token exchange response must be a JSON object")
            return data

    async def _clear_cache(self) -> None:
        async with self._lock:
            self._cache = None
