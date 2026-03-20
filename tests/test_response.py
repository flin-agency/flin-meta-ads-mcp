from __future__ import annotations

from flin_meta_ads_mcp.response import ok_response, selection_required_response


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


def test_selection_required_response_shape() -> None:
    payload = selection_required_response(
        question="Which account?",
        parameter="ad_account_id",
        choices=[
            {"ad_account_id": "act_1", "label": "Account One (act_1)"},
            {"ad_account_id": "act_2", "label": "Account Two (act_2)"},
        ],
        api_version="v21.0",
        request_id="req-1",
    )

    assert payload["ok"] is True
    assert payload["data"]["type"] == "selection_required"
    assert payload["data"]["parameter"] == "ad_account_id"
    assert len(payload["data"]["choices"]) == 2
