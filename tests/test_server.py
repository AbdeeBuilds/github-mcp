"""Tests for the MCP server tool definitions and dispatch logic.

Covers:
- ``list_tools`` returns the expected 7 tools with valid JSON Schemas
- ``_dispatch`` correctly routes every tool to the right client method
- ``_dispatch`` returns clean error messages on:
  - missing required arguments
  - GitHub API errors
  - validation errors (ValueError)
  - unknown tool names
- ``_dispatch`` returns success content with JSON-formatted payloads
- Logging captures the call (smoke)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from github_mcp import server as server_mod
from github_mcp.server import TOOLS, _dispatch, app, list_tools

EXPECTED_TOOLS = {
    "list_issues",
    "get_issue",
    "create_issue",
    "list_pull_requests",
    "get_pull_request",
    "search_code",
    "get_file_content",
}


# ----------------------------- list_tools ------------------------------------


class TestListTools:
    @pytest.mark.asyncio
    async def test_returns_all_expected_tools(self):
        tools = await list_tools()
        names = {t.name for t in tools}
        assert EXPECTED_TOOLS.issubset(names), f"missing: {EXPECTED_TOOLS - names}"

    @pytest.mark.asyncio
    async def test_module_tools_match(self):
        tools = await list_tools()
        assert {t.name for t in tools} == {t.name for t in TOOLS}

    def test_each_tool_has_input_schema(self):
        for tool in TOOLS:
            assert tool.inputSchema is not None
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema
            assert isinstance(tool.inputSchema["required"], list)
            assert len(tool.inputSchema["required"]) >= 1

    def test_required_fields_are_declared(self):
        for tool in TOOLS:
            required = set(tool.inputSchema.get("required", []))
            props = set(tool.inputSchema.get("properties", {}).keys())
            missing = required - props
            assert not missing, f"{tool.name} requires {missing} but doesn't declare them"

    def test_list_issues_includes_new_optional_params(self):
        schema = next(t.inputSchema for t in TOOLS if t.name == "list_issues")
        assert "labels" in schema["properties"]
        assert "since" in schema["properties"]

    def test_create_issue_includes_labels(self):
        schema = next(t.inputSchema for t in TOOLS if t.name == "create_issue")
        assert "labels" in schema["properties"]

    def test_state_enum_valid_values(self):
        for name in ("list_issues", "list_pull_requests"):
            schema = next(t.inputSchema for t in TOOLS if t.name == name)
            state = schema["properties"]["state"]
            assert state["enum"] == ["open", "closed", "all"]

    def test_all_params_have_descriptions(self):
        """A new param without a description is a doc bug. Catch it at test time."""
        for tool in TOOLS:
            for pname, prop in tool.inputSchema.get("properties", {}).items():
                assert "description" in prop, f"{tool.name}.{pname} has no description"

    def test_app_name(self):
        assert app.name == "github-mcp"


# ----------------------------- dispatch: success -----------------------------


def _success_text(result: list) -> str:
    assert len(result) == 1
    assert result[0].type == "text"
    return result[0].text


class TestDispatchSuccess:
    @pytest.mark.asyncio
    async def test_list_issues(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.list_issues = AsyncMock(return_value=[{"number": 1, "title": "x"}])
            gc.return_value = client
            result = await _dispatch("list_issues", {"owner": "o", "repo": "r", "limit": 5})
        text = _success_text(result)
        assert "x" in text
        # All kwargs forwarded
        client.list_issues.assert_awaited_once_with("o", "r", "open", 5, labels=None, since=None)

    @pytest.mark.asyncio
    async def test_list_issues_with_labels_and_since(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.list_issues = AsyncMock(return_value=[])
            gc.return_value = client
            await _dispatch(
                "list_issues",
                {
                    "owner": "o",
                    "repo": "r",
                    "labels": "bug,p1",
                    "since": "2026-01-01T00:00:00Z",
                },
            )
        client.list_issues.assert_awaited_once_with(
            "o", "r", "open", 10, labels="bug,p1", since="2026-01-01T00:00:00Z"
        )

    @pytest.mark.asyncio
    async def test_get_issue(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_issue = AsyncMock(return_value={"number": 42, "title": "t"})
            gc.return_value = client
            result = await _dispatch("get_issue", {"owner": "o", "repo": "r", "number": 42})
        text = _success_text(result)
        data = json.loads(text)
        assert data["number"] == 42

    @pytest.mark.asyncio
    async def test_create_issue(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.create_issue = AsyncMock(return_value={"number": 5, "html_url": "https://..."})
            gc.return_value = client
            await _dispatch(
                "create_issue",
                {
                    "owner": "o",
                    "repo": "r",
                    "title": "t",
                    "body": "b",
                    "labels": ["bug"],
                },
            )
        client.create_issue.assert_awaited_once_with("o", "r", "t", "b", labels=["bug"])

    @pytest.mark.asyncio
    async def test_list_pull_requests(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.list_pull_requests = AsyncMock(return_value=[])
            gc.return_value = client
            await _dispatch(
                "list_pull_requests",
                {"owner": "o", "repo": "r", "state": "closed", "limit": 3},
            )
        client.list_pull_requests.assert_awaited_once_with("o", "r", "closed", 3)

    @pytest.mark.asyncio
    async def test_get_pull_request(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_pull_request = AsyncMock(return_value={"number": 7, "title": "x"})
            gc.return_value = client
            await _dispatch(
                "get_pull_request",
                {"owner": "o", "repo": "r", "number": 7},
            )
        client.get_pull_request.assert_awaited_once_with("o", "r", 7)

    @pytest.mark.asyncio
    async def test_search_code(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.search_code = AsyncMock(return_value={"total_count": 0, "items": []})
            gc.return_value = client
            await _dispatch("search_code", {"query": "q", "limit": 5})
        client.search_code.assert_awaited_once_with("q", 5)

    @pytest.mark.asyncio
    async def test_get_file_content(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_file_content = AsyncMock(
                return_value={"name": "x.py", "decoded_content": "print(1)"}
            )
            gc.return_value = client
            await _dispatch(
                "get_file_content",
                {"owner": "o", "repo": "r", "path": "x.py", "ref": "main"},
            )
        client.get_file_content.assert_awaited_once_with("o", "r", "x.py", "main")

    @pytest.mark.asyncio
    async def test_get_file_content_without_ref(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_file_content = AsyncMock(return_value={})
            gc.return_value = client
            await _dispatch(
                "get_file_content",
                {"owner": "o", "repo": "r", "path": "x.py"},
            )
        client.get_file_content.assert_awaited_once_with("o", "r", "x.py", None)


# ----------------------------- dispatch: errors ------------------------------


class TestDispatchErrors:
    @pytest.mark.asyncio
    async def test_missing_token(self, monkeypatch):

        def _raise():
            raise ValueError("GITHUB_TOKEN not set")

        monkeypatch.setattr(server_mod, "_get_client", _raise)
        result = await _dispatch("list_issues", {"owner": "o", "repo": "r"})
        text = _success_text(result)
        assert "GITHUB_TOKEN" in text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        with patch.object(server_mod, "_get_client") as gc:
            gc.return_value = AsyncMock()
            result = await _dispatch("does_not_exist", {})
        text = _success_text(result)
        assert "Unknown tool" in text

    @pytest.mark.asyncio
    async def test_missing_required_arg(self):
        with patch.object(server_mod, "_get_client") as gc:
            gc.return_value = AsyncMock()
            result = await _dispatch("list_issues", {"owner": "o"})  # no repo
        text = _success_text(result)
        assert "Missing required" in text
        assert "repo" in text

    @pytest.mark.asyncio
    async def test_github_error_surfaces(self):
        from github_mcp.client import GitHubError

        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_issue = AsyncMock(
                side_effect=GitHubError(404, '{"message": "Not Found"}', "/repos/o/r/issues/1")
            )
            gc.return_value = client
            result = await _dispatch("get_issue", {"owner": "o", "repo": "r", "number": 1})
        text = _success_text(result)
        assert "404" in text
        assert "Not Found" in text

    @pytest.mark.asyncio
    async def test_validation_error_surfaces(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.list_issues = AsyncMock(
                side_effect=ValueError("state must be 'open', 'closed', or 'all'")
            )
            gc.return_value = client
            result = await _dispatch("list_issues", {"owner": "o", "repo": "r"})
        text = _success_text(result)
        assert "state must be" in text
        # No full traceback for validation errors
        assert "Traceback" not in text

    @pytest.mark.asyncio
    async def test_type_error_surfaces_cleanly(self):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_issue = AsyncMock(side_effect=TypeError("bad"))
            gc.return_value = client
            result = await _dispatch("get_issue", {"owner": "o", "repo": "r", "number": 1})
        text = _success_text(result)
        assert "bad" in text
        assert "Traceback" not in text

    @pytest.mark.asyncio
    async def test_unexpected_exception_logged_with_traceback(self, caplog):
        with patch.object(server_mod, "_get_client") as gc:
            client = AsyncMock()
            client.get_issue = AsyncMock(side_effect=RuntimeError("kaboom"))
            gc.return_value = client
            with caplog.at_level("ERROR", logger="github-mcp"):
                result = await _dispatch("get_issue", {"owner": "o", "repo": "r", "number": 1})
        text = _success_text(result)
        assert "kaboom" in text
        # Exception should have been logged
        assert any("tool call failed" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_none_arguments_dict(self):
        """Defensive: callers may pass None for arguments.

        ``args or {}`` normalizes None to {}, then the required-arg check
        surfaces a clean error for the missing owner.
        """
        with patch.object(server_mod, "_get_client") as gc:
            gc.return_value = AsyncMock()
            result = await _dispatch("list_issues", None)
        text = _success_text(result)
        assert "Missing required" in text
        assert "owner" in text


# ----------------------------- lifecycle ------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_shutdown_closes_client(self, monkeypatch):
        from github_mcp.client import GitHubClient

        # Seed a singleton
        c = GitHubClient(token="x")
        c._get_client()  # create
        monkeypatch.setattr(server_mod, "_client", c)
        await server_mod._shutdown()
        assert c._client is None

    @pytest.mark.asyncio
    async def test_shutdown_noop_when_uninitialized(self):
        import github_mcp.server as s

        s._client = None
        # Should not raise
        await s._shutdown()
        assert s._client is None

    def test_get_client_is_singleton(self, monkeypatch):
        """_get_client raises on missing token; called twice, both raise."""
        import github_mcp.server as s

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        s._client = None
        with pytest.raises(ValueError):
            s._get_client()
        # Calling again still raises (and no client is cached)
        with pytest.raises(ValueError):
            s._get_client()
