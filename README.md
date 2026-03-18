# Civic MCP Client

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

client = CivicMCPClient(
    auth={"token": "your-civic-access-token"},
    civic_profile="7c9e6679-7425-40de-944b-e07fc1f90ae7",
)

tools = await client.get_tools()
instructions = await client.get_server_instructions()
result = await client.call_tool(name="tool-name", args={"foo": "bar"})

await client.close()
```

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
    civic_profile="7c9e6679-7425-40de-944b-e07fc1f90ae7",
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
    civic_profile="optional-profile-id",
    url="https://app.civic.com/hub/mcp",
)

fastmcp_client = await client.adapt_for(fastmcp())
# fastmcp_client is a CivicMCPClient with FastMCP backend; auth/headers come from config
tools = await fastmcp_client.get_tools()
```

## Interface Notes

- `civic_account` was removed from Python client config to match the updated TypeScript direction.
- `civic_profile` remains supported and maps to `x-civic-profile-id`.
- `TokenExchangeConfig` supports `expires_in` and `lock_to_profile` (account lock removed).
