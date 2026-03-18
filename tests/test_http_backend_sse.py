from __future__ import annotations

import json

import httpx
import pytest

from civic_mcp_client.backends import HttpMCPBackend


class _FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, dict[str, str], dict]] = []

    async def post(self, url: str, headers: dict[str, str], json: dict):  # noqa: A002
        self.requests.append((url, headers, json))
        return self._responses.pop(0)

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_http_backend_parses_sse_initialize_and_tools_list() -> None:
    req = httpx.Request("POST", "https://example.com/mcp")
    sse_payload = {"jsonrpc": "2.0", "id": 1, "result": {"instructions": "hello"}}
    sse_body = f"event: message\ndata: {json.dumps(sse_payload)}\n\n"

    # initialize returns SSE, notifications/initialized returns empty body, tools/list returns JSON.
    responses = [
        httpx.Response(
            200,
            request=req,
            headers={"content-type": "text/event-stream", "mcp-session-id": "sess-1"},
            content=sse_body.encode("utf-8"),
        ),
        httpx.Response(
            200,
            request=req,
            headers={"content-type": "application/json", "mcp-session-id": "sess-1"},
            content=b"",
        ),
        httpx.Response(
            200,
            request=req,
            headers={"content-type": "application/json", "mcp-session-id": "sess-1"},
            json={"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "t1"}]}},
        ),
    ]

    backend = HttpMCPBackend("https://example.com/mcp", client_name="x", client_version="0")
    backend._http = _FakeAsyncClient(responses)  # type: ignore[attr-defined]

    tools = await backend.list_tools(headers={"Authorization": "Bearer token"})
    assert tools["tools"][0]["name"] == "t1"
    assert await backend.get_server_instructions(headers={"Authorization": "Bearer token"}) == "hello"

    # Ensure session id got persisted to subsequent calls.
    assert backend._session_id == "sess-1"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_http_backend_empty_or_non_json_response_does_not_crash() -> None:
    responses = [
        httpx.Response(
            200,
            request=httpx.Request("POST", "https://example.com/mcp"),
            headers={"content-type": "application/json", "mcp-session-id": "sess-1"},
            content=b"",
        )
    ]
    backend = HttpMCPBackend("https://example.com/mcp", client_name="x", client_version="0")
    backend._http = _FakeAsyncClient(responses)  # type: ignore[attr-defined]

    out = await backend._post(payload={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, headers={})  # type: ignore[attr-defined]
    assert out == {}
