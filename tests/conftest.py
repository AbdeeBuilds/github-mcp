"""Shared pytest fixtures and configuration."""

from __future__ import annotations

import pytest

import github_mcp.server as server_mod


@pytest.fixture(autouse=True)
def _reset_server_singleton():
    """Ensure the server's lazy client singleton is reset between tests.

    Otherwise one test's stubbed client would leak into the next.
    """
    saved = server_mod._client
    server_mod._client = None
    try:
        yield
    finally:
        server_mod._client = saved


@pytest.fixture
def respx_calls():
    """Respx 0.23+ exposes ``router.calls`` as a list.

    Returns a helper that yields the call_count from inside a ``with respx.mock`` block.
    Usage::

        with respx.mock(base_url=API) as router:
            router.get(...).mock(...)
            ...
            count = respx_calls(router)
    """

    def _count(router) -> int:
        return len(router.calls)

    return _count
