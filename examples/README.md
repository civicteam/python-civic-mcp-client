# Examples

These scripts are intended for manual testing of `civic-mcp-client`.
They demonstrate the adapter pattern: `await client.adapt_for(...)`.

## Prerequisites

- Install dependencies:

```bash
uv sync --extra examples --extra pydanticai --extra langchain --extra fastmcp
```

- Set your environment variables as needed (either via shell exports or a `.env` file):
  - `CIVIC_ACCESS_TOKEN`
  - `CIVIC_MCP_HUB_URL` (optional, defaults to `https://app.civic.com/hub/mcp`)
  - `CIVIC_PROFILE_ID` (optional)
  - `CIVIC_CLIENT_ID` (token exchange example)
  - `CIVIC_CLIENT_SECRET` (token exchange example)

## Run Examples

From the package root:

```bash
uv run python examples/direct_token.py
uv run python examples/token_exchange.py
uv run python examples/langchain_adapter.py
uv run python examples/pydanticai_adapter.py
uv run python examples/fastmcp_backend.py
```

## Using a `.env` file

Copy the template and fill in your values (this creates a `.env` file in the package root):

```bash
cp .env.example .env
```

Then run via `python-dotenv`:

```bash
uv run python -m dotenv run -- python examples/direct_token.py
```

If you prefer working from inside the `examples/` directory (so the `.env` lives next to the scripts):

```bash
cd examples
cp ../.env.example .env
uv run python -m dotenv run -- python direct_token.py
uv run python -m dotenv run -- python fastmcp_backend.py
```
