from __future__ import annotations

import httpx
import pytest
import respx

from flin_meta_ads_mcp.errors import MetaPermissionError, MetaRateLimitError
from flin_meta_ads_mcp.meta_client import MetaClient


@respx.mock
def test_get_json_retries_after_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    route = respx.get("https://graph.facebook.com/v21.0/act_123/campaigns")
    route.side_effect = [
        httpx.Response(429, json={"error": {"message": "rate limit"}}),
        httpx.Response(200, json={"data": [{"id": "1"}]}, headers={"x-fb-request-id": "req-1"}),
    ]

    sleeps: list[float] = []
    monkeypatch.setattr("flin_meta_ads_mcp.meta_client.time.sleep", lambda seconds: sleeps.append(seconds))

    client = MetaClient(access_token="token", api_version="v21.0", timeout_seconds=10, max_retries=2)
    payload = client.get_json("act_123/campaigns", params={})

    assert payload["data"] == [{"id": "1"}]
    assert sleeps == [0.5]


@respx.mock
def test_get_json_maps_permission_error() -> None:
    respx.get("https://graph.facebook.com/v21.0/act_123/campaigns").mock(
        return_value=httpx.Response(
            403,
            json={"error": {"message": "Permissions error", "code": 200}},
        )
    )

    client = MetaClient(access_token="token", api_version="v21.0", timeout_seconds=10, max_retries=1)

    with pytest.raises(MetaPermissionError):
        client.get_json("act_123/campaigns", params={})


@respx.mock
def test_get_json_raises_rate_limit_error_after_retries() -> None:
    respx.get("https://graph.facebook.com/v21.0/act_123/campaigns").mock(
        return_value=httpx.Response(429, json={"error": {"message": "rate limit"}})
    )

    client = MetaClient(access_token="token", api_version="v21.0", timeout_seconds=10, max_retries=1)

    with pytest.raises(MetaRateLimitError):
        client.get_json("act_123/campaigns", params={})
