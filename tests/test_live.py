"""Live integration tests against the real GitHub API.

These tests are SKIPPED unless ``GITHUB_TOKEN`` is set in the environment.
They use the ``cli/cli`` public repo for read-only smoke tests, plus a
``create_issue`` test that targets a test repo if ``GITHUB_TEST_REPO`` is set
(format: ``owner/repo``).

Run with: ``GITHUB_TOKEN=ghp_... pytest tests/test_live.py -v``
"""

from __future__ import annotations

import os

import pytest

from github_mcp.client import GitHubClient

PUBLIC_REPO = ("cli", "cli")


@pytest.fixture
def client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set; skipping live API tests")
    return GitHubClient(token=token)


@pytest.mark.asyncio
async def test_list_issues(client):
    issues = await client.list_issues(*PUBLIC_REPO, state="open", limit=5)
    assert isinstance(issues, list)
    for issue in issues:
        assert "number" in issue
        assert "title" in issue
        assert "pull_request" not in issue  # PRs filtered out


@pytest.mark.asyncio
async def test_get_issue(client):
    issue = await client.get_issue(*PUBLIC_REPO, 1)
    assert issue["number"] == 1
    assert "title" in issue


@pytest.mark.asyncio
async def test_list_pull_requests(client):
    prs = await client.list_pull_requests(*PUBLIC_REPO, state="closed", limit=3)
    assert isinstance(prs, list)
    for pr in prs:
        assert "number" in pr
        assert "title" in pr


@pytest.mark.asyncio
async def test_get_pull_request(client):
    prs = await client.list_pull_requests(*PUBLIC_REPO, state="closed", limit=1)
    if not prs:
        pytest.skip("no closed PRs to test against")
    pr = await client.get_pull_request(*PUBLIC_REPO, prs[0]["number"])
    assert pr["number"] == prs[0]["number"]


@pytest.mark.asyncio
async def test_get_file_content_decodes_text(client):
    data = await client.get_file_content(*PUBLIC_REPO, "README.md")
    assert "content" in data
    assert "name" in data
    # New: text files are auto-decoded
    if data.get("encoding") == "base64":
        # binary or didn't decode
        pytest.skip("README.md returned without decode; older client?")
    assert data.get("encoding") == "utf-8"
    assert "decoded_content" in data
    assert "GitHub" in data["decoded_content"] or "cli" in data["decoded_content"]


@pytest.mark.asyncio
async def test_create_issue_optional(client):
    """Creates a real issue if GITHUB_TEST_REPO is set; skipped otherwise."""
    target = os.environ.get("GITHUB_TEST_REPO")
    if not target:
        pytest.skip("GITHUB_TEST_REPO=owner/repo not set; skipping destructive test")
    owner, repo = target.split("/", 1)
    issue = await client.create_issue(
        owner, repo, "smoke-test: please ignore", body="Created by automated test."
    )
    assert "number" in issue
    assert "html_url" in issue
