"""Mocked tests for GitHubClient. No network, no GITHUB_TOKEN required.

Uses ``respx`` to intercept httpx requests and return canned responses.
Covers:
- HTTP method, URL, and query parameter correctness
- Success and error responses (status codes, JSON shapes)
- Retry on 429 / 5xx with exponential backoff
- Retry-After header honored
- Connection pool reuse (single httpx.AsyncClient)
- Input validation (ValueError before any request)
- Base64 decoding of text files
- Async context manager lifecycle
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from github_mcp.client import (
    GitHubClient,
    GitHubError,
    _extract_error_detail,
)

API = "https://api.github.com"


# ----------------------------- helpers ---------------------------------------


def _client() -> GitHubClient:
    return GitHubClient(token="test-token")


def _params(call) -> dict[str, str]:
    """httpx encodes query params as strings; collapse to a plain dict."""
    return {k: v for k, v in call.request.url.params.items()}


# ----------------------------- error detail parsing --------------------------


class TestExtractErrorDetail:
    def test_parses_github_error_json(self):
        body = json.dumps({"message": "Not Found", "documentation_url": "https://docs.example/x"})
        out = _extract_error_detail(body)
        assert "Not Found" in out
        assert "https://docs.example/x" in out

    def test_falls_back_to_raw_text(self):
        assert "plain text error" in _extract_error_detail("plain text error")

    def test_empty_body(self):
        assert _extract_error_detail("") == "(empty response body)"

    def test_handles_non_dict_json(self):
        out = _extract_error_detail(json.dumps(["weird", "array"]))
        assert "weird" in out

    def test_truncates_long_bodies(self):
        long_body = "x" * 2000
        out = _extract_error_detail(long_body)
        assert len(out) <= 500


# ----------------------------- init ------------------------------------------


class TestInit:
    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            GitHubClient()

    def test_explicit_token(self):
        c = GitHubClient(token="abc")
        assert c.token == "abc"

    def test_env_token(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "from-env")
        c = GitHubClient()
        assert c.token == "from-env"

    def test_lazy_client_creation(self):
        c = GitHubClient(token="x")
        assert c._client is None  # not created until first request
        _ = c._get_client()
        assert c._client is not None
        assert isinstance(c._client, httpx.AsyncClient)

    def test_client_headers(self):
        c = GitHubClient(token="abc")
        hdrs = c._get_client().headers
        assert hdrs["Authorization"] == "Bearer abc"
        assert hdrs["Accept"] == "application/vnd.github+json"
        assert hdrs["X-GitHub-Api-Version"] == "2022-11-28"
        assert "github-mcp" in hdrs["User-Agent"]


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aclose_releases_client(self):
        c = GitHubClient(token="x")
        _ = c._get_client()
        assert c._client is not None
        await c.aclose()
        assert c._client is None
        # Idempotent
        await c.aclose()
        assert c._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with GitHubClient(token="x") as c:
            _ = c._get_client()
            assert c._client is not None
        assert c._client is None


# ----------------------------- input validation ------------------------------


class TestInputValidation:
    @pytest.mark.asyncio
    async def test_list_issues_invalid_state(self):
        c = _client()
        with pytest.raises(ValueError, match="state"):
            await c.list_issues("o", "r", state="bogus")

    @pytest.mark.asyncio
    async def test_list_issues_invalid_limit(self):
        c = _client()
        with pytest.raises(ValueError, match="limit"):
            await c.list_issues("o", "r", limit=0)
        with pytest.raises(ValueError, match="limit"):
            await c.list_issues("o", "r", limit=101)

    @pytest.mark.asyncio
    async def test_list_issues_invalid_owner(self):
        c = _client()
        with pytest.raises(ValueError, match="owner"):
            await c.list_issues("", "r")
        with pytest.raises(ValueError, match="owner"):
            await c.list_issues("o/w", "r")

    @pytest.mark.asyncio
    async def test_get_issue_invalid_number(self):
        c = _client()
        with pytest.raises(ValueError, match="number"):
            await c.get_issue("o", "r", 0)
        with pytest.raises(ValueError, match="number"):
            await c.get_issue("o", "r", -1)

    @pytest.mark.asyncio
    async def test_create_issue_empty_title(self):
        c = _client()
        with pytest.raises(ValueError, match="title"):
            await c.create_issue("o", "r", title="")
        with pytest.raises(ValueError, match="title"):
            await c.create_issue("o", "r", title="   ")

    @pytest.mark.asyncio
    async def test_search_code_empty_query(self):
        c = _client()
        with pytest.raises(ValueError, match="query"):
            await c.search_code("")
        with pytest.raises(ValueError, match="query"):
            await c.search_code("   ")

    @pytest.mark.asyncio
    async def test_get_file_content_empty_path(self):
        c = _client()
        with pytest.raises(ValueError, match="path"):
            await c.get_file_content("o", "r", "")


# ----------------------------- list_issues -----------------------------------


class TestListIssues:
    @pytest.mark.asyncio
    async def test_basic_request(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        {"number": 1, "title": "bug"},
                        {"number": 2, "title": "feature"},
                    ],
                )
            )
            c = _client()
            issues = await c.list_issues("o", "r")
            assert len(r.calls) == 1
            assert _params(r.calls[0]) == {"state": "open", "per_page": "10"}
        assert [i["number"] for i in issues] == [1, 2]

    @pytest.mark.asyncio
    async def test_filters_out_pull_requests(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        {"number": 1, "title": "real issue"},
                        {
                            "number": 2,
                            "title": "PR disguised as issue",
                            "pull_request": {"url": "x"},
                        },
                        {"number": 3, "title": "another real issue"},
                    ],
                )
            )
            c = _client()
            issues = await c.list_issues("o", "r")
        assert [i["number"] for i in issues] == [1, 3]

    @pytest.mark.asyncio
    async def test_passes_state_and_limit(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(return_value=httpx.Response(200, json=[]))
            c = _client()
            await c.list_issues("o", "r", state="closed", limit=50)
            assert _params(r.calls[0]) == {
                "state": "closed",
                "per_page": "50",
            }

    @pytest.mark.asyncio
    async def test_passes_labels_string(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(return_value=httpx.Response(200, json=[]))
            c = _client()
            await c.list_issues("o", "r", labels="bug,priority:high")
            assert r.calls[0].request.url.params["labels"] == "bug,priority:high"

    @pytest.mark.asyncio
    async def test_passes_labels_list(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(return_value=httpx.Response(200, json=[]))
            c = _client()
            await c.list_issues("o", "r", labels=["bug", "p1"])
            assert r.calls[0].request.url.params["labels"] == "bug,p1"

    @pytest.mark.asyncio
    async def test_passes_since(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(return_value=httpx.Response(200, json=[]))
            c = _client()
            await c.list_issues("o", "r", since="2026-01-01T00:00:00Z")
            assert r.calls[0].request.url.params["since"] == "2026-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_404_raises(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues").mock(
                return_value=httpx.Response(404, json={"message": "Not Found"})
            )
            c = _client()
            with pytest.raises(GitHubError) as ei:
                await c.list_issues("o", "r")
        assert ei.value.status == 404
        assert "Not Found" in str(ei.value)
        assert ei.value.endpoint == "/repos/o/r/issues"


# ----------------------------- get_issue -------------------------------------


class TestGetIssue:
    @pytest.mark.asyncio
    async def test_success(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/42").mock(
                return_value=httpx.Response(200, json={"number": 42, "title": "x"})
            )
            c = _client()
            issue = await c.get_issue("o", "r", 42)
        assert issue["number"] == 42
        assert issue["title"] == "x"

    @pytest.mark.asyncio
    async def test_not_found(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/9999").mock(
                return_value=httpx.Response(404, json={"message": "Not Found"})
            )
            c = _client()
            with pytest.raises(GitHubError) as ei:
                await c.get_issue("o", "r", 9999)
        assert ei.value.status == 404


# ----------------------------- create_issue ----------------------------------


class TestCreateIssue:
    @pytest.mark.asyncio
    async def test_minimal(self):
        with respx.mock(base_url=API) as r:
            r.post("/repos/o/r/issues").mock(
                return_value=httpx.Response(
                    201, json={"number": 1, "title": "t", "html_url": "https://..."}
                )
            )
            c = _client()
            issue = await c.create_issue("o", "r", "t")
            body = json.loads(r.calls[0].request.content)
        assert issue["number"] == 1
        assert body == {"title": "t", "body": ""}

    @pytest.mark.asyncio
    async def test_with_body_and_labels(self):
        with respx.mock(base_url=API) as r:
            r.post("/repos/o/r/issues").mock(return_value=httpx.Response(201, json={"number": 2}))
            c = _client()
            await c.create_issue("o", "r", "t", body="hello", labels=["bug", "p1"])
            body = json.loads(r.calls[0].request.content)
        assert body["title"] == "t"
        assert body["body"] == "hello"
        assert body["labels"] == ["bug", "p1"]

    @pytest.mark.asyncio
    async def test_strips_title_whitespace(self):
        with respx.mock(base_url=API) as r:
            r.post("/repos/o/r/issues").mock(return_value=httpx.Response(201, json={"number": 3}))
            c = _client()
            await c.create_issue("o", "r", "  hi  ")
            body = json.loads(r.calls[0].request.content)
        assert body["title"] == "hi"


# ----------------------------- pull requests ---------------------------------


class TestPullRequests:
    @pytest.mark.asyncio
    async def test_list(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/pulls").mock(
                return_value=httpx.Response(200, json=[{"number": 1, "title": "x"}])
            )
            c = _client()
            prs = await c.list_pull_requests("o", "r", state="closed", limit=25)
            assert _params(r.calls[0]) == {
                "state": "closed",
                "per_page": "25",
            }
        assert prs[0]["number"] == 1

    @pytest.mark.asyncio
    async def test_get(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/pulls/7").mock(
                return_value=httpx.Response(200, json={"number": 7, "title": "x"})
            )
            c = _client()
            pr = await c.get_pull_request("o", "r", 7)
        assert pr["number"] == 7


# ----------------------------- search_code -----------------------------------


class TestSearchCode:
    @pytest.mark.asyncio
    async def test_basic(self):
        with respx.mock(base_url=API) as r:
            r.get("/search/code").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "total_count": 2,
                        "incomplete_results": False,
                        "items": [
                            {"name": "a.py", "path": "a.py"},
                            {"name": "b.py", "path": "b.py"},
                        ],
                    },
                )
            )
            c = _client()
            res = await c.search_code("function foo", limit=20)
            assert _params(r.calls[0]) == {
                "q": "function foo",
                "per_page": "20",
            }
        assert res["total_count"] == 2

    @pytest.mark.asyncio
    async def test_403_for_insufficient_scope(self):
        with respx.mock(base_url=API) as r:
            r.get("/search/code").mock(
                return_value=httpx.Response(
                    403, json={"message": "You must be authenticated to search"}
                )
            )
            c = _client()
            with pytest.raises(GitHubError) as ei:
                await c.search_code("x")
        assert ei.value.status == 403


# ----------------------------- get_file_content ------------------------------


class TestGetFileContent:
    @pytest.mark.asyncio
    async def test_text_file_decoded(self):
        original = "# hello\nworld\n"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/contents/README.md").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "name": "README.md",
                        "path": "README.md",
                        "encoding": "base64",
                        "content": encoded,
                    },
                )
            )
            c = _client()
            data = await c.get_file_content("o", "r", "README.md")
        assert data["decoded_content"] == original
        assert data["encoding"] == "utf-8"

    @pytest.mark.asyncio
    async def test_binary_file_not_decoded(self):
        # Non-UTF8 bytes — should NOT be decoded
        raw = b"\x00\x01\x02\xff"
        encoded = base64.b64encode(raw).decode("ascii")
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/contents/blob.bin").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "name": "blob.bin",
                        "encoding": "base64",
                        "content": encoded,
                    },
                )
            )
            c = _client()
            data = await c.get_file_content("o", "r", "blob.bin")
        assert "decoded_content" not in data
        assert data["encoding"] == "base64"
        assert data["content"] == encoded

    @pytest.mark.asyncio
    async def test_decode_false_skips(self):
        encoded = base64.b64encode(b"hi").decode("ascii")
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/contents/x.txt").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "encoding": "base64",
                        "content": encoded,
                    },
                )
            )
            c = _client()
            data = await c.get_file_content("o", "r", "x.txt", decode=False)
        assert "decoded_content" not in data

    @pytest.mark.asyncio
    async def test_passes_ref(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/contents/src/main.py").mock(
                return_value=httpx.Response(200, json={"encoding": "base64", "content": ""})
            )
            c = _client()
            await c.get_file_content("o", "r", "src/main.py", ref="v1.2.3")
            assert r.calls[0].request.url.params["ref"] == "v1.2.3"

    @pytest.mark.asyncio
    async def test_no_ref_omits_param(self):
        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/contents/x.py").mock(
                return_value=httpx.Response(200, json={"encoding": "base64", "content": ""})
            )
            c = _client()
            await c.get_file_content("o", "r", "x.py")
            assert "ref" not in r.calls[0].request.url.params


# ----------------------------- retry & resilience ----------------------------


class TestRetry:
    @pytest.mark.asyncio
    async def test_retries_500_then_succeeds(self, monkeypatch):
        # Speed up the test by shrinking the backoff base
        import github_mcp.client as client_mod

        monkeypatch.setattr(client_mod, "_RETRY_BASE_DELAY", 0)

        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/1").mock(
                side_effect=[
                    httpx.Response(500, text="oops"),
                    httpx.Response(200, json={"number": 1, "title": "ok"}),
                ]
            )
            c = _client()
            data = await c.get_issue("o", "r", 1)
            assert len(r.calls) == 2
        assert data["number"] == 1

    @pytest.mark.asyncio
    async def test_retries_429_and_honors_retry_after(self, monkeypatch):
        import github_mcp.client as client_mod

        monkeypatch.setattr(client_mod, "_RETRY_BASE_DELAY", 0)

        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/1").mock(
                side_effect=[
                    httpx.Response(429, headers={"Retry-After": "0"}, text="slow down"),
                    httpx.Response(200, json={"number": 1, "title": "ok"}),
                ]
            )
            c = _client()
            data = await c.get_issue("o", "r", 1)
            assert len(r.calls) == 2
        assert data["number"] == 1

    @pytest.mark.asyncio
    async def test_gives_up_after_max_retries(self, monkeypatch):
        import github_mcp.client as client_mod

        monkeypatch.setattr(client_mod, "_RETRY_BASE_DELAY", 0)

        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/1").mock(return_value=httpx.Response(503, text="down"))
            c = _client()
            with pytest.raises(GitHubError) as ei:
                await c.get_issue("o", "r", 1)
            # Initial attempt + 3 retries = 4 total
            assert len(r.calls) == 4
        assert ei.value.status == 503

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_other_than_429(self, monkeypatch):
        import github_mcp.client as client_mod

        monkeypatch.setattr(client_mod, "_RETRY_BASE_DELAY", 0)

        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/1").mock(
                return_value=httpx.Response(404, json={"message": "Not Found"})
            )
            c = _client()
            with pytest.raises(GitHubError) as ei:
                await c.get_issue("o", "r", 1)
            assert len(r.calls) == 1
        assert ei.value.status == 404

    @pytest.mark.asyncio
    async def test_network_error_raises_after_retries(self, monkeypatch):
        import github_mcp.client as client_mod

        monkeypatch.setattr(client_mod, "_RETRY_BASE_DELAY", 0)

        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/1").mock(side_effect=httpx.ConnectError("connection refused"))
            c = _client()
            with pytest.raises(GitHubError) as ei:
                await c.get_issue("o", "r", 1)
        assert ei.value.status == 0
        assert "connection refused" in ei.value.message


# ----------------------------- connection pool reuse -------------------------


class TestConnectionPool:
    @pytest.mark.asyncio
    async def test_single_client_reused_across_requests(self):
        c = _client()
        # Trigger lazy creation
        _ = c._get_client()
        first_client = c._client

        with respx.mock(base_url=API) as r:
            r.get("/repos/o/r/issues/1").mock(return_value=httpx.Response(200, json={"number": 1}))
            r.get("/repos/o/r/pulls/1").mock(return_value=httpx.Response(200, json={"number": 1}))
            await c.get_issue("o", "r", 1)
            await c.get_pull_request("o", "r", 1)
        # Same httpx.AsyncClient instance for both calls
        assert c._client is first_client
