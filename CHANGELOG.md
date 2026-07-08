# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-08

### Added
- Connection pooling: single `httpx.AsyncClient` reused across all calls (`async with` and `aclose()` supported).
- Retry with exponential backoff for transient failures: 429, 500, 502, 503, 504. Honors `Retry-After`.
- `list_issues(..., labels=..., since=...)` — filter by label and last-update time.
- `create_issue(..., labels=[...])` — apply labels at creation.
- `get_file_content(..., decode=True)` — base64 → UTF-8 text decoding for text files (binary files unchanged).
- `GitHubError.endpoint` and structured `message` extraction from GitHub's JSON error responses.
- Server: lazy single `GitHubClient` for the server's lifetime, no per-call token re-read.
- Server: input validation (missing required args) with clean error messages.
- Server: per-call timing logged at INFO; errors logged at WARNING/ERROR.
- Tests: full mock-based coverage via `respx` (no `GITHUB_TOKEN` required for the suite).
- Tests: 6 live integration tests moved to `tests/test_live.py` (still require `GITHUB_TOKEN`).
- Dev tooling: `ruff` (lint), `mypy` (types) in `[project.optional-dependencies].dev`.
- CI: GitHub Actions matrix (Ubuntu / Windows / macOS × Python 3.10 / 3.11 / 3.12 / 3.13).
- CI: ruff + mypy + pytest on every PR.
- Docs: `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.

### Changed
- `pyproject.toml`: bumped to `0.2.0`, `Development Status` advanced to Beta.
- `pyproject.toml`: dependency `mcp>=1.0` (was `mcp>=0.9.0`).
- `pyproject.toml`: `pytest-asyncio` mode is now `auto` (was already; confirmed).
- Tool schemas: every property now has a `description` for better LLM tool-use.
- Tool schemas: new `minimum`/`maximum` on integer params.
- Logging format: now includes logger name.

### Removed
- None.

### Fixed
- `create_issue` no longer sends an empty `labels` field when labels are absent.
- `get_file_content` no longer sends an empty `ref` parameter when `ref` is `None`.

### Security
- Token never logged (HTTP headers are not logged).
- Error messages truncate response bodies to 500 chars to avoid log flooding.

## [0.1.0] - 2026-07-04

### Added
- Initial MVP release: 7 tools (`list_issues`, `get_issue`, `create_issue`,
  `list_pull_requests`, `get_pull_request`, `search_code`, `get_file_content`).
- `GitHubClient` with single-shot requests (no pooling, no retry).
- MCP stdio server with tool dispatch.
- Smoke test guide (`SMOKE_TEST.md`).
- README, LICENSE (MIT), AUTH, USAGE docs.

[0.2.0]: https://github.com/hermes-agent/github-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hermes-agent/github-mcp/releases/tag/v0.1.0
