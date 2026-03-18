from __future__ import annotations

import json
from typing import Any, Protocol

import httpx


class MCPBackend(Protocol):
    async def list_tools(self, headers: dict[str, str]) -> dict[str, Any]:
        ...

    async def get_server_instructions(self, headers: dict[str, str]) -> str:
        ...

    async def call_tool(self, name: str, args: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        ...

    async def close(self) -> None:
        ...


class HttpMCPBackend:
    def __init__(
        self,
        url: str,
        *,
        client_name: str,
        client_version: str,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        self._url = url
        self._client_name = client_name
        self._client_version = client_version
        self._capabilities = capabilities or {}
        self._session_id: str | None = None
        self._request_id = 0
        self._initialized = False
        self._server_instructions = ""
        self._http = httpx.AsyncClient(timeout=30.0)

    async def list_tools(self, headers: dict[str, str]) -> dict[str, Any]:
        await self._ensure_initialized(headers=headers)
        result = await self._rpc("tools/list", params={}, headers=headers)
        return result if isinstance(result, dict) else {"tools": []}

    async def get_server_instructions(self, headers: dict[str, str]) -> str:
        await self._ensure_initialized(headers=headers)
        return self._server_instructions

    async def call_tool(self, name: str, args: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        await self._ensure_initialized(headers=headers)
        result = await self._rpc(
            "tools/call",
            params={"name": name, "arguments": args},
            headers=headers,
        )
        return result if isinstance(result, dict) else {"content": result}

    async def _ensure_initialized(self, headers: dict[str, str]) -> None:
        if self._initialized:
            return
        result = await self._rpc(
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": self._capabilities,
                "clientInfo": {"name": self._client_name, "version": self._client_version},
            },
            headers=headers,
        )
        if isinstance(result, dict):
            instructions = result.get("instructions")
            if isinstance(instructions, str):
                self._server_instructions = instructions
        await self._notify("notifications/initialized", params={}, headers=headers)
        self._initialized = True

    async def _rpc(self, method: str, params: dict[str, Any], headers: dict[str, str]) -> Any:
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        data = await self._post(payload=payload, headers=headers)
        if "error" in data:
            message = data["error"].get("message", "MCP error")
            raise RuntimeError(f"MCP request failed for {method}: {message}")
        return data.get("result")

    async def _notify(self, method: str, params: dict[str, Any], headers: dict[str, str]) -> None:
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        await self._post(payload=payload, headers=headers)

    async def _post(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request_headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            **headers,
        }
        if self._session_id:
            request_headers["mcp-session-id"] = self._session_id

        response = await self._http.post(self._url, headers=request_headers, json=payload)
        response.raise_for_status()
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self._session_id = session_id
        if not response.content:
            return {}
        content_type = (response.headers.get("content-type") or "").lower()
        if content_type.startswith("text/event-stream"):
            # Hub responds with SSE, typically with `event: message` and `data: {json}`.
            data_lines = []
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())
                    break
            if not data_lines:
                return {}
            body = json.loads(data_lines[0])
        else:
            try:
                body = response.json()
            except Exception:
                return {}
        if isinstance(body, list):
            if not body:
                return {}
            first = body[0]
            return first if isinstance(first, dict) else {}
        return body if isinstance(body, dict) else {}

    async def close(self) -> None:
        await self._http.aclose()
