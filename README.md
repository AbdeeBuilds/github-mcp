# github-mcp

[![Tests](https://github.com/AbdeeBuilds/github-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/AbdeeBuilds/github-mcp/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/github-mcp.svg)](https://pypi.org/project/github-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/github-mcp.svg)](https://pypi.org/project/github-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GitHub MCP server for Claude Code, Cursor, Cline, Windsurf, and any MCP-compatible client.

Exposes GitHub tools (issues, pull requests, code search, file content) to your LLM via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Features

- 🔁 **Connection pooling & retry** — single HTTP client per process, exponential backoff on 429/5xx, honors `Retry-After`.
- 🛡️ **Typed errors** — `GitHubError` carries HTTP status, parsed message, and endpoint.
- ✅ **Input validation** — catches bad inputs before the network round-trip.
- 📄 **Text files decoded** — `get_file_content` returns UTF-8 text under `decoded_content` for text files.
- 🧪 **Fully tested** — 75 mock-based tests, plus opt-in live integration tests.
- 🪶 **Tiny** — three runtime deps (`mcp`, `httpx`, `pydantic`); no PyGithub.

## Tools exposed

| Tool | Description |
|---|---|
| `list_issues` | List issues (filter by state, labels, since) — PRs filtered out |
| `get_issue` | Get a single issue by number |
| `create_issue` | Create an issue (with optional labels) |
| `list_pull_requests` | List PRs (filter by state) |
| `get_pull_request` | Get a single PR by number |
| `search_code` | Search code across GitHub (requires code-search scope) |
| `get_file_content` | Read a file at a ref; text files returned UTF-8-decoded |

Full parameter docs: [docs/USAGE.md](docs/USAGE.md).

## Install

```bash
pip install github-mcp
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install github-mcp
```

Requires Python 3.10+.

## Authenticate

1. Create a GitHub personal access token:
   - **Fine-grained (recommended):** https://github.com/settings/personal-access-tokens/new
   - **Classic (legacy):** https://github.com/settings/tokens/new

2. Set the token:

   ```bash
   export GITHUB_TOKEN="ghp_..."   # macOS / Linux / Git Bash
   # or PowerShell: $env:GITHUB_TOKEN = "ghp_..."
   ```

   See [docs/AUTH.md](docs/AUTH.md) for Windows and per-client config.

## Configure your client

### Claude Code

```bash
claude mcp add --transport stdio github -- github-mcp
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "github-mcp",
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

### Cline / Windsurf

See your client's docs for adding a stdio MCP server. Command: `github-mcp`. Env: `GITHUB_TOKEN`.

## Example prompts

> "List the 5 most recent open issues in `cli/cli` labeled `bug`."

> "Get issue #1234 in `cli/cli` and summarize the discussion."

> "Create a new issue in `my-org/my-repo` titled `Bug: login fails on Safari` with body `Steps to reproduce: ...`."

> "Show me the contents of `src/main.py` in `cli/cli` on the `main` branch."

> "Search GitHub for `function authenticate` in `cli/cli`."

## Development

```bash
git clone https://github.com/AbdeeBuilds/github-mcp
cd github-mcp
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
pip install -e ".[dev]"
pytest                          # mock-based suite
GITHUB_TOKEN=*** pytest tests/test_live.py -v   # live integration
```

Quality gates (run on every PR):

```bash
ruff check src tests
ruff format --check src tests
mypy src
```

## License

MIT — see [LICENSE](LICENSE).
