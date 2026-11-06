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
def test_get_json_uses_authorization_header_not_query_token() -> None:
    route = respx.get("https://graph.facebook.com/v21.0/act_123/campaigns").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    client = MetaClient(access_token="token", api_version="v21.0", timeout_seconds=10, max_retries=1)
    client.get_json("act_123/campaigns", params={"limit": 10})

    assert len(route.calls) == 1
    request = route.calls[0].request
    assert request.headers.get("Authorization") == "Bearer token"
    assert request.url.params.get("access_token") is None
    assert request.url.params.get("appsecret_proof") is None


@respx.mock
def test_requests_sign_with_app_secret_and_preserve_parameters() -> None:
    # RFC 4231 test case 2: fixed expected HMAC, independent of implementation.
    expected_proof = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    route = respx.route(method="GET", url="https://graph.facebook.com/v21.0/me").mock(
        return_value=httpx.Response(200, json={"id": "123"})
    )
    params = {"fields": "id", "access_token": "wrong-token", "appsecret_proof": "stale"}

    with MetaClient(
        access_token="what do ya want for nothing?",
        app_secret="Jefe",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=0,
    ) as client:
        assert client.get_json("me", params=params) == {"id": "123"}

    request = route.calls[0].request
    assert request.url.params["appsecret_proof"] == expected_proof
    assert request.url.params["fields"] == "id"
    assert request.headers["Authorization"] == "Bearer what do ya want for nothing?"
    assert "access_token" not in request.url.params
    assert "app_secret" not in request.url.params
    assert "Jefe" not in str(request.url)
    assert "Jefe" not in str(request.headers)
    assert b"Jefe" not in request.content
    assert params == {"fields": "id", "access_token": "wrong-token", "appsecret_proof": "stale"}


@respx.mock
def test_retries_keep_app_secret_proof(monkeypatch: pytest.MonkeyPatch) -> None:
    route = respx.get("https://graph.facebook.com/v21.0/me")
    route.side_effect = [
        httpx.Response(500, json={"error": {"message": "temporary error"}}),
        httpx.Response(200, json={"id": "123"}),
    ]
    monkeypatch.setattr("flin_meta_ads_mcp.meta_client.time.sleep", lambda _: None)

    with MetaClient(
        access_token="what do ya want for nothing?",
        app_secret="Jefe",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    ) as client:
        assert client.get_json("me") == {"id": "123"}

    assert len(route.calls) == 2
    for call in route.calls:
        assert call.request.url.params["appsecret_proof"] == (
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
        )


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
