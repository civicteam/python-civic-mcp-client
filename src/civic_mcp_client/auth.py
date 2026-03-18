from __future__ import annotations

import inspect
from typing import Any, Mapping

from .types import (
    AuthInput,
    TokenAuth,
    TokenExchangeAuth,
    TokenExchangeConfig,
    TokenInput,
)


class AuthConfigError(ValueError):
    pass


def parse_auth(auth: AuthInput) -> TokenAuth | TokenExchangeAuth:
    if isinstance(auth, (TokenAuth, TokenExchangeAuth)):
        return auth

    if not isinstance(auth, Mapping):
        raise AuthConfigError("auth must be TokenAuth, TokenExchangeAuth, or a mapping")

    if "token" in auth and "token_exchange" in auth:
        raise AuthConfigError("auth cannot define both token and token_exchange")

    if "token" in auth:
        token = auth["token"]
        if not isinstance(token, str) and not callable(token):
            raise AuthConfigError("token must be a string or callable returning string")
        return TokenAuth(token=token)

    if "token_exchange" in auth:
        raw = auth["token_exchange"]
        if isinstance(raw, TokenExchangeConfig):
            return TokenExchangeAuth(token_exchange=raw)
        if not isinstance(raw, Mapping):
            raise AuthConfigError("token_exchange must be a TokenExchangeConfig or mapping")

        required = ("client_id", "client_secret", "subject_token")
        missing = [key for key in required if key not in raw]
        if missing:
            raise AuthConfigError(f"token_exchange missing required fields: {', '.join(missing)}")

        subject_token = raw["subject_token"]
        if not isinstance(subject_token, str) and not callable(subject_token):
            raise AuthConfigError("subject_token must be a string or callable returning string")

        return TokenExchangeAuth(
            token_exchange=TokenExchangeConfig(
                client_id=str(raw["client_id"]),
                client_secret=str(raw["client_secret"]),
                subject_token=subject_token,
                auth_url=str(raw.get("auth_url", "https://auth.civic.com/oauth/token")),
                expires_in=int(raw["expires_in"]) if raw.get("expires_in") is not None else None,
                lock_to_profile=bool(raw.get("lock_to_profile", True)),
            )
        )

    raise AuthConfigError("auth must define either 'token' or 'token_exchange'")


async def resolve_token(token: TokenInput) -> str:
    if isinstance(token, str):
        resolved = token
    else:
        candidate = token()
        resolved = await candidate if inspect.isawaitable(candidate) else candidate

    if not isinstance(resolved, str):
        raise AuthConfigError("resolved token must be a string")
    if not resolved.strip():
        raise AuthConfigError("resolved token is empty")
    return resolved


def build_context_headers(
    base_headers: Mapping[str, str] | None,
    civic_profile: str | None,
) -> dict[str, str]:
    headers = dict(base_headers or {})
    if civic_profile:
        headers["x-civic-profile-id"] = civic_profile
    return headers


def build_user_agent(client_name: str, client_version: str) -> str:
    return f"{client_name}/{client_version}"
