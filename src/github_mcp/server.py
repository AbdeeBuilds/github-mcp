"""MCP server exposing GitHub tools to LLM clients.

The server is a thin stdio transport wrapper around :class:`GitHubClient`.
It keeps a single :class:`GitHubClient` instance for the server's lifetime
to amortize the cost of the underlying HTTP connection pool.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import GitHubClient, GitHubError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("github-mcp")

app = Server("github-mcp")

# Single GitHubClient reused for the server's lifetime. Lazy-initialized on the
# first tool call so that import time stays free of token requirements.
_client: GitHubClient | None = None


def _get_client() -> GitHubClient:
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client


async def _shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _format(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(e: Exception) -> list[TextContent]:
    log.exception("tool call failed: %s", e)
    return [TextContent(type="text", text=f"Error: {e}")]


# ---- Tool definitions ----

TOOLS: list[Tool] = [
    Tool(
        name="list_issues",
        description=(
            "List issues in a GitHub repository. Returns the most recent issues "
            "in the specified state. Pull requests are filtered out."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (user or org)"},
                "repo": {"type": "string", "description": "Repository name"},
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                    "description": "Filter by issue state",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of issues to return",
                },
                "labels": {
                    "type": "string",
                    "description": (
                        "Optional comma-separated label names to filter by "
                        "(e.g. 'bug,priority:high')."
                    ),
                },
                "since": {
                    "type": "string",
                    "description": (
                        "Optional ISO 8601 timestamp; only return issues updated "
                        "at or after this time (e.g. '2026-01-01T00:00:00Z')."
                    ),
                },
            },
            "required": ["owner", "repo"],
        },
    ),
    Tool(
        name="get_issue",
        description="Get a single GitHub issue by its number.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (user or org)"},
                "repo": {"type": "string", "description": "Repository name"},
                "number": {"type": "integer", "minimum": 1, "description": "Issue number"},
            },
            "required": ["owner", "repo", "number"],
        },
    ),
    Tool(
        name="create_issue",
        description="Create a new issue in a GitHub repository you have write access to.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (user or org)"},
                "repo": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "Issue title (required, non-empty)"},
                "body": {
                    "type": "string",
                    "default": "",
                    "description": "Issue body in markdown",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of label names to apply at creation time.",
                },
            },
            "required": ["owner", "repo", "title"],
        },
    ),
    Tool(
        name="list_pull_requests",
        description="List pull requests in a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (user or org)"},
                "repo": {"type": "string", "description": "Repository name"},
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                    "description": "Filter by pull request state",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of pull requests to return",
                },
            },
            "required": ["owner", "repo"],
        },
    ),
    Tool(
        name="get_pull_request",
        description="Get a single GitHub pull request by its number.",
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (user or org)"},
                "repo": {"type": "string", "description": "Repository name"},
                "number": {"type": "integer", "minimum": 1, "description": "Pull request number"},
            },
            "required": ["owner", "repo", "number"],
        },
    ),
    Tool(
        name="search_code",
        description=(
            "Search for code across GitHub repos. Requires a fine-grained token "
            "with 'Code: Read' scope, or a classic token with `repo` scope."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query in GitHub code search syntax, e.g. "
                        "'repo:owner/name function_name' or 'language:python async'"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of code-search results to return",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_file_content",
        description=(
            "Read the contents of a file from a GitHub repository at a given ref "
            "(branch, tag, or commit SHA). Defaults to the repo's default branch. "
            "Text files are returned UTF-8-decoded under 'decoded_content'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (user or org)"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {
                    "type": "string",
                    "description": "File path within the repo (e.g., 'src/main.py')",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch, tag, or commit SHA (optional)",
                },
            },
            "required": ["owner", "repo", "path"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


# ---- Tool dispatch ----


def _missing(name: str, args: dict[str, Any]) -> str | None:
    """Return a human-readable error if a required param is missing/empty."""
    if not args.get(name) and args.get(name) != 0:
        return f"Missing required argument: {name!r}"
    return None


async def _dispatch(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    args = arguments or {}
    started = time.perf_counter()
    data: Any = None
    try:
        client = _get_client()
    except ValueError as e:
        # Token not set at server startup
        return _err(e)

    try:
        if name == "list_issues":
            for req in ("owner", "repo"):
                if (msg := _missing(req, args)) is not None:
                    raise ValueError(msg)
            data = await client.list_issues(
                args["owner"],
                args["repo"],
                args.get("state", "open"),
                int(args.get("limit", 10)),
                labels=args.get("labels"),
                since=args.get("since"),
            )
        elif name == "get_issue":
            for req in ("owner", "repo", "number"):
                if (msg := _missing(req, args)) is not None:
                    raise ValueError(msg)
            data = await client.get_issue(args["owner"], args["repo"], int(args["number"]))
        elif name == "create_issue":
            for req in ("owner", "repo", "title"):
                if (msg := _missing(req, args)) is not None:
                    raise ValueError(msg)
            data = await client.create_issue(
                args["owner"],
                args["repo"],
                args["title"],
                args.get("body", ""),
                labels=args.get("labels"),
            )
        elif name == "list_pull_requests":
            for req in ("owner", "repo"):
                if (msg := _missing(req, args)) is not None:
                    raise ValueError(msg)
            data = await client.list_pull_requests(
                args["owner"],
                args["repo"],
                args.get("state", "open"),
                int(args.get("limit", 10)),
            )
        elif name == "get_pull_request":
            for req in ("owner", "repo", "number"):
                if (msg := _missing(req, args)) is not None:
                    raise ValueError(msg)
            data = await client.get_pull_request(args["owner"], args["repo"], int(args["number"]))
        elif name == "search_code":
            if (msg := _missing("query", args)) is not None:
                raise ValueError(msg)
            data = await client.search_code(args["query"], int(args.get("limit", 10)))
        elif name == "get_file_content":
            for req in ("owner", "repo", "path"):
                if (msg := _missing(req, args)) is not None:
                    raise ValueError(msg)
            data = await client.get_file_content(
                args["owner"],
                args["repo"],
                args["path"],
                args.get("ref"),
            )
        else:
            raise ValueError(f"Unknown tool: {name!r}")

        elapsed_ms = (time.perf_counter() - started) * 1000
        log.info("tool=%s ok elapsed_ms=%.1f", name, elapsed_ms)
        return [TextContent(type="text", text=_format(data))]

    except GitHubError as e:
        elapsed_ms = (time.perf_counter() - started) * 1000
        log.warning(
            "tool=%s github_error status=%s elapsed_ms=%.1f",
            name,
            e.status,
            elapsed_ms,
        )
        return _err(e)
    except (ValueError, TypeError) as e:
        # Validation / input errors — surface without a full traceback.
        log.warning("tool=%s validation_error: %s", name, e)
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        return _err(e)


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    return await _dispatch(name, arguments)


# ---- Entry point ----


async def _run() -> None:
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    finally:
        await _shutdown()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        log.info("shutting down")


if __name__ == "__main__":
    main()
