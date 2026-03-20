# Civic MCP Client
[![CI](https://github.com/civicteam/python-civic-mcp-client/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/civicteam/python-civic-mcp-client/actions/workflows/python-app.yml)

Python client library for connecting to the Civic MCP Hub with direct bearer token auth
or RFC 8693 token exchange.

## Install

```bash
uv sync
```

Install optional integration extras:

```bash
uv sync --extra pydanticai --extra langchain --extra fastmcp
```

## Quick Start

```python
from civic_mcp_client import CivicMCPClient

access_token = "your-civic-access-token"  # e.g., from your session or the demo app

client = CivicMCPClient(
    auth={"token": access_token},
)

tools = await client.get_tools()
instructions = await client.get_server_instructions()
result = await client.call_tool(name="tool-name", args={"foo": "bar"})

await client.close()
```

> Recommended: use the demo app for a production-like frontend + Python backend setup.

## Demo-first setup (recommended)

Start with the reference implementation here:

- https://github.com/civicteam/demos/tree/main/apps/civic-auth-demo-python-backend

That demo uses `@civic/auth` in the frontend and forwards the authenticated Civic access token to the Python backend (which then passes it into `CivicMCPClient(auth={"token": ...})`).

## Optional: Manually self-serve `CIVIC_ACCESS_TOKEN` (local testing only)

Use the existing Civic install flow:

1. Open https://app.civic.com/web/install/mcp-url
2. Click **Generate token**
3. Copy the returned `access_token`
4. Set it in your app as `CIVIC_ACCESS_TOKEN`

Treat this as a secret and keep it out of source control. Token expiry and rotation follow Civic's token lifecycle.

### Separated frontend and backend apps

If your frontend is separate from your Python backend (for example, a Next.js frontend with `@civic/auth/nextjs`):

- Frontend obtains the user session token at runtime
- Backend receives that token and passes it to `CivicMCPClient(auth={"token": ...})`
- Keep `CIVIC_CLIENT_ID` and `CIVIC_PROFILE_ID` as app configuration values

The manual self-serve flow above is useful for local testing when you want to bypass a full frontend session.

## Token Exchange (RFC 8693)

```python
import os
from civic_mcp_client import CivicMCPClient

client = CivicMCPClient(
    auth={
        "token_exchange": {
            "client_id": os.environ["CIVIC_CLIENT_ID"],
            "client_secret": os.environ["CIVIC_CLIENT_SECRET"],
            "subject_token": lambda: "external-token",
            "expires_in": 3600,  # optional requested lifetime in seconds
        }
    },
)
```

The token exchange manager provides:

- cache + expiry handling
- token change detection
- in-flight deduplication for concurrent calls
- expiry buffer of `min(30s, expires_in / 2)`

Current access token can be retrieved via:

```python
token = await client.get_access_token()
```

## Testing

```bash
uv run --extra test python -m pytest
uv run --extra test python -m pytest -m integration
```

## Manual Test Examples

Runnable scripts are available in `examples/`.

```bash
uv run python examples/direct_token.py
uv run python examples/token_exchange.py
uv run python examples/langchain_adapter.py
uv run python examples/pydanticai_adapter.py
uv run python examples/fastmcp_backend.py
```

To load environment variables from a `.env` file:

```bash
uv sync --extra examples
cp .env.example .env
uv run python -m dotenv run -- python examples/direct_token.py
```

Or, if you prefer running from inside the `examples/` directory:

```bash
cd examples
cp ../.env.example .env
uv run python -m dotenv run -- python direct_token.py
```

## Library Integrations

Use `await client.adapt_for(...)` with the adapter for your framework. It returns either a new `CivicMCPClient` (for backend adapters like FastMCP) or adapter-native tool output (e.g. list of schemas or tool definitions).

### PydanticAI

```python
from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.pydanticai import pydanticai

client = CivicMCPClient(auth={"token": "your-civic-access-token"})
tools = await client.adapt_for(pydanticai())
```

### LangChain

```python
from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.langchain import execute_langchain_tool_call, langchain

client = CivicMCPClient(auth={"token": "your-civic-access-token"})
tool_schemas = await client.adapt_for(langchain())

# model = model.bind_tools(tool_schemas)
# response = model.invoke("...")
# tool_result = await execute_langchain_tool_call(client, response.tool_calls[0])
```

### FastMCP

```python
from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.fastmcp import fastmcp

client = CivicMCPClient(
    auth={"token": "your-civic-access-token"},
)

fastmcp_client = await client.adapt_for(fastmcp())
# fastmcp_client is a CivicMCPClient with FastMCP backend; auth/headers come from config
tools = await fastmcp_client.get_tools()
```

## Optional Profile Scoping (advanced)

If you want to lock requests to a specific profile, pass `civic_profile`:

```python
client = CivicMCPClient(
    auth={"token": "your-civic-access-token"},
    civic_profile="optional-profile-id",
)
```

## Interface Notes

- `civic_account` was removed from Python client config to match the updated TypeScript direction.
- `civic_profile` remains supported and maps to `x-civic-profile-id`.
- `TokenExchangeConfig` supports `expires_in` and `lock_to_profile` (account lock removed).
