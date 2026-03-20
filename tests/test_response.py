from __future__ import annotations

from flin_meta_ads_mcp.response import ok_response


def test_ok_response_includes_paging_and_meta() -> None:
    payload = ok_response(
        data=[{"id": "1"}],
        next_after=None,
        has_next=False,
        api_version="v21.0",
        request_id="abc123",
    )

    assert payload == {
        "ok": True,
        "data": [{"id": "1"}],
        "paging": {"next_after": None, "has_next": False},
        "meta": {"api_version": "v21.0", "request_id": "abc123"},
    }
