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
    civic_account="550e8400-e29b-41d4-a716-446655440000",
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
        }
    },
    civic_account="550e8400-e29b-41d4-a716-446655440000",
    civic_profile="7c9e6679-7425-40de-944b-e07fc1f90ae7",
)
```

The token exchange manager provides:

- cache + expiry handling
- token change detection
- in-flight deduplication for concurrent calls
- expiry buffer of `min(30s, expires_in / 2)`

## Testing

```bash
uv run pytest
uv run pytest -m integration
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

- `civic_mcp_client.adapters.pydanticai` for PydanticAI toolset-style integration
- `civic_mcp_client.adapters.langchain` for LangChain `bind_tools`-ready schemas
- `civic_mcp_client.adapters.fastmcp` for FastMCP-backed runtime bridge

### PydanticAI

```python
from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.pydanticai import to_pydanticai_toolset

client = CivicMCPClient(auth={"token": "your-civic-access-token"})
toolset = to_pydanticai_toolset(client)

tools = await toolset.list_tools()
result = await toolset.call_tool("tool-name", {"arg": "value"})
```

### LangChain

```python
from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.langchain import (
    execute_langchain_tool_call,
    get_langchain_tool_schemas,
)

client = CivicMCPClient(auth={"token": "your-civic-access-token"})
tool_schemas = await get_langchain_tool_schemas(client)

# model = model.bind_tools(tool_schemas)
# response = model.invoke("...")
# Assume response tool call payload in response.tool_calls[0]
# tool_result = await execute_langchain_tool_call(client, response.tool_calls[0])
```

### FastMCP

```python
from civic_mcp_client import CivicMCPClient
from civic_mcp_client.adapters.fastmcp import create_fastmcp_backend

backend = await create_fastmcp_backend("https://nexus.civic.com/hub/mcp")
client = CivicMCPClient(
    auth={"token": "your-civic-access-token"},
    civic_account="optional-account-id",
    civic_profile="optional-profile-id",
    backend=backend,
)
```

In this mode, auth and context headers still come from `CivicMCPClient` config.
