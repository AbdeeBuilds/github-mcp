"""Async GitHub REST API client with connection pooling, retry, and typed errors.

Public surface:
- ``GitHubClient`` — async context manager; reuse a single instance per process.
- ``GitHubError`` — raised on non-2xx responses, carries ``status`` and ``endpoint``.

Backward compatible: ``GitHubClient(token)`` still works; ``httpx.AsyncClient``
is lazily created on first request and reused. Call ``await client.aclose()``
or use ``async with GitHubClient() as c:`` to release the connection pool.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import os
from typing import Any, ClassVar

import httpx

# Retry policy for transient GitHub failures (5xx, 429 rate limiting)
_MAX_RETRIES = 3
_RETRY_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_RETRY_BASE_DELAY = 0.5  # seconds, doubled each attempt (0.5, 1, 2)
_MAX_ERROR_BODY_CHARS = 500


def _extract_error_detail(body: str) -> str:
    """Pull a human-readable message out of a GitHub error response.

    GitHub returns JSON like ``{"message": "Not Found", "documentation_url": "..."}``
    on errors. If the body isn't JSON, return the raw text (truncated).
    """
    if not body:
        return "(empty response body)"
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return body[:_MAX_ERROR_BODY_CHARS]
    if isinstance(data, dict):
        msg = data.get("message")
        doc = data.get("documentation_url")
        if msg and doc:
            return f"{msg} (see {doc})"
        if msg:
            return str(msg)
        if doc:
            return str(doc)
        return json.dumps(data)[:_MAX_ERROR_BODY_CHARS]
    return str(data)[:_MAX_ERROR_BODY_CHARS]


class GitHubError(Exception):
    """Raised on non-2xx GitHub API responses or unrecoverable transport errors.

    Attributes:
        status: HTTP status code (0 if the request never reached the server).
        message: Raw response body (or transport error message).
        endpoint: API path that was called (e.g. ``/repos/owner/repo/issues``).
    """

    def __init__(self, status: int, message: str, endpoint: str | None = None):
        self.status = status
        self.message = message
        self.endpoint = endpoint
        detail = _extract_error_detail(message)
        text = f"GitHub API error {status}: {detail}"
        if endpoint:
            text += f" [endpoint: {endpoint}]"
        super().__init__(text)


def _validate_owner_repo(owner: str, repo: str) -> None:
    """Lightweight validation; GitHub itself returns 404 for invalid names."""
    if not owner or not isinstance(owner, str):
        raise ValueError("owner is required and must be a non-empty string")
    if not repo or not isinstance(repo, str):
        raise ValueError("repo is required and must be a non-empty string")
    if "/" in owner or "/" in repo:
        raise ValueError("owner and repo must not contain '/'")


def _validate_positive_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be >= 1")
    return value


class GitHubClient:
    """Lightweight async client for the GitHub REST API.

    Reuses a single ``httpx.AsyncClient`` for connection pooling. Retries
    transient failures (5xx, 429) with exponential backoff and honors the
    ``Retry-After`` header.

    Example::

        async with GitHubClient() as c:
            issues = await c.list_issues("cli", "cli", limit=5)
    """

    BASE_URL: ClassVar[str] = "https://api.github.com"
    DEFAULT_TIMEOUT: ClassVar[float] = 30.0
    USER_AGENT: ClassVar[str] = "github-mcp/0.2.0"

    def __init__(self, token: str | None = None, *, timeout: float = DEFAULT_TIMEOUT):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError(
                "GITHUB_TOKEN not set. Create a token at "
                "https://github.com/settings/personal-access-tokens/new "
                "and export it as GITHUB_TOKEN."
            )
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self.token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": self.USER_AGENT,
                },
            )
        return self._client

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool. Safe to call multiple times."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.BASE_URL}{path}"
        client = self._get_client()
        last_status: int = 0
        last_body: str = ""

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.request(method, url, **kwargs)
            except httpx.TransportError as e:
                # Network/connectivity failure — retry if attempts remain
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_BASE_DELAY * (2**attempt))
                    continue
                raise GitHubError(0, f"Network error: {e}", endpoint=path) from e

            status = response.status_code

            if status in _RETRY_STATUS and attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    with contextlib.suppress(ValueError):
                        # Non-numeric Retry-After (e.g. HTTP date) — keep computed delay.
                        delay = max(delay, float(retry_after))
                await asyncio.sleep(delay)
                continue

            if status >= 400:
                # Don't re-raise in the retry loop — the error is final.
                last_status = status
                last_body = response.text
                break

            if not response.content:
                return None
            return response.json()

        raise GitHubError(last_status, last_body, endpoint=path)

    # ---- Issues ----

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
        labels: str | list[str] | None = None,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """List issues for a repo. PRs are filtered out (they have a ``pull_request`` key).

        Args:
            owner: Repository owner (user or org).
            repo: Repository name.
            state: ``"open"``, ``"closed"``, or ``"all"``.
            limit: Max issues to return (1-100).
            labels: Comma-separated string or list of label names to filter by.
            since: ISO 8601 timestamp; only return issues updated at or after this time.
        """
        _validate_owner_repo(owner, repo)
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be 'open', 'closed', or 'all'")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params: dict[str, Any] = {"state": state, "per_page": min(limit, 100)}
        if labels:
            params["labels"] = labels if isinstance(labels, str) else ",".join(labels)
        if since:
            params["since"] = since
        data = await self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)
        return [i for i in (data or []) if "pull_request" not in i]

    async def get_issue(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        _validate_owner_repo(owner, repo)
        _validate_positive_int("number", number)
        return await self._request("GET", f"/repos/{owner}/{repo}/issues/{number}")

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue. Requires write access on the target repo.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title (required, non-empty).
            body: Issue body in markdown.
            labels: Optional list of label names to apply.
        """
        _validate_owner_repo(owner, repo)
        if not title or not isinstance(title, str) or not title.strip():
            raise ValueError("title is required and must be a non-empty string")
        payload: dict[str, Any] = {"title": title.strip(), "body": body}
        if labels:
            payload["labels"] = labels
        return await self._request("POST", f"/repos/{owner}/{repo}/issues", json=payload)

    # ---- Pull requests ----

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        _validate_owner_repo(owner, repo)
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be 'open', 'closed', or 'all'")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = {"state": state, "per_page": min(limit, 100)}
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)

    async def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        _validate_owner_repo(owner, repo)
        _validate_positive_int("number", number)
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")

    # ---- Code ----

    async def search_code(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Search code across GitHub. Requires code-search scope.

        Returns the raw GitHub search response (``total_count``, ``incomplete_results``,
        ``items``).
        """
        if not query or not isinstance(query, str) or not query.strip():
            raise ValueError("query is required and must be a non-empty string")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = {"q": query.strip(), "per_page": min(limit, 100)}
        return await self._request("GET", "/search/code", params=params)

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
        *,
        decode: bool = True,
    ) -> dict[str, Any]:
        """Read a file's contents (and metadata) at the given ref.

        If ``decode=True`` (default) and the file is a UTF-8 text file, the response
        includes a ``decoded_content`` field with the base64-decoded text and
        ``encoding`` is set to ``"utf-8"``. Binary files are returned with the raw
        base64 content unchanged.
        """
        _validate_owner_repo(owner, repo)
        if not path or not isinstance(path, str):
            raise ValueError("path is required and must be a non-empty string")
        params: dict[str, Any] | None = {"ref": ref} if ref else None
        data = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params)
        if (
            decode
            and isinstance(data, dict)
            and data.get("encoding") == "base64"
            and data.get("content")
        ):
            try:
                decoded = base64.b64decode(data["content"]).decode("utf-8")
                data["decoded_content"] = decoded
                data["encoding"] = "utf-8"
            except (ValueError, UnicodeDecodeError):
                # Binary file; leave base64 content in place
                pass
        return data
