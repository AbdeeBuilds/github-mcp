# Contributing

Thanks for your interest in improving `github-mcp`!

## Setup

```bash
git clone https://github.com/hermes-agent/github-mcp
cd github-mcp
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
# .venv\Scripts\Activate.ps1    # PowerShell
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

## Run the tests

```bash
pytest                      # full suite, live tests skip without GITHUB_TOKEN
GITHUB_TOKEN=... pytest     # include live integration tests
```

## Code style

- Lint: `ruff check src tests`
- Format: `ruff format src tests`
- Types: `mypy src`

CI runs all three on every PR and fails on any error.

## Adding a tool

1. Add a method to `GitHubClient` in `src/github_mcp/client.py`.
   - Validate inputs (raise `ValueError` with a clear message).
   - Return parsed JSON. Raise `GitHubError` for non-2xx (the helper does this for you).
2. Register a `Tool(...)` in `TOOLS` in `src/github_mcp/server.py`.
   - Provide a `description` and a JSON Schema with `description` on every property.
3. Add a dispatch branch in `_dispatch`.
4. Add mock-based tests in `tests/test_client.py` and dispatch tests in `tests/test_server.py`.
5. Update `README.md` and `USAGE.md`.
6. Bump the version in `pyproject.toml` and add an entry to `CHANGELOG.md`.

## Pull request checklist

- [ ] `pytest` passes locally
- [ ] `ruff check src tests` clean
- [ ] `ruff format --check src tests` clean
- [ ] `mypy src` clean (or new errors are explained)
- [ ] New behavior has tests (mock-based; live tests are optional)
- [ ] Public APIs documented in `USAGE.md`
- [ ] `CHANGELOG.md` updated

## Reporting bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- `github-mcp --version` output
- `python --version`
- Relevant logs (token already redacted by the server)

## Security issues

See `SECURITY.md` — do not file public issues for security bugs.
