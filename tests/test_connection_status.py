from __future__ import annotations

import json

import httpx
import pytest
import respx

from flin_meta_ads_mcp import __version__
from flin_meta_ads_mcp.credentials import Credentials, save_credentials
from flin_meta_ads_mcp.status import connection_status


@respx.mock
def test_local_status_never_contacts_meta_or_starts_login(tmp_path, monkeypatch):
    monkeypatch.setattr("webbrowser.open", lambda *a: pytest.fail("Browser must not start"))
    env = {"META_AUTH_FILE": str(tmp_path / "missing.json")}
    result = connection_status(env)
    assert result["server_version"] == __version__
    assert result["configuration_status"] == "incomplete"
    assert result["auth_status"] == "unauthenticated"
    env.update(META_APP_ID="123", META_APP_SECRET="private-secret")
    assert connection_status(env)["configuration_status"] == "configured"
    env["META_ACCESS_TOKEN"] = "private-token"
    result = connection_status(env)
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "not_checked"
    assert "private" not in json.dumps(result)
    assert len(respx.calls) == 0
    assert not list(tmp_path.iterdir())


def test_saved_token_is_not_claimed_as_live_authenticated(tmp_path):
    path = tmp_path / "auth.json"
    save_credentials(path, Credentials("123", "private-secret", "private-token", "v21.0"))
    before = path.read_bytes()
    result = connection_status({"META_AUTH_FILE": str(path)})
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "not_checked"
    assert path.read_bytes() == before


def test_expired_saved_token_requires_login(tmp_path):
    path = tmp_path / "auth.json"
    save_credentials(path, Credentials("123", "private-secret", "private-token", "v21.0", 1))
    assert connection_status({"META_AUTH_FILE": str(path)})["auth_status"] == "unauthenticated"


@pytest.mark.parametrize("status,payload,auth,live", [
    (200, {"data": [{"id": "customer-account"}]}, "authenticated", "ok"),
    (200, {"data": []}, "authenticated", "ok"),
    (200, {"bad": "private-token"}, "unknown", "error"),
    (400, {"error": {"code": 190, "message": "private-token"}}, "unauthenticated", "error"),
    (403, {"error": {"code": 200, "message": "private-token"}}, "unknown", "error"),
    (500, {"error": {"message": "private-token"}}, "unknown", "error"),
])
@respx.mock
def test_opt_in_live_check_returns_no_customer_data(status, payload, auth, live):
    route = respx.get("https://graph.facebook.com/v21.0/me/adaccounts").respond(status, json=payload)
    result = connection_status({"META_ACCESS_TOKEN": "private-token"}, check_live=True)
    assert result["auth_status"] == auth
    assert result["live_access"] == live
    assert route.call_count == 1
    assert dict(route.calls[0].request.url.params) == {"fields": "id", "limit": "1"}
    assert "private-token" not in json.dumps(result)
    assert "customer-account" not in json.dumps(result)
    # A later local check must not reuse stale evidence.
    assert connection_status({"META_ACCESS_TOKEN": "private-token"})["live_access"] == "not_checked"


@respx.mock
def test_network_failure_is_unknown_not_unauthenticated():
    respx.get("https://graph.facebook.com/v21.0/me/adaccounts").mock(side_effect=httpx.ConnectError("secret"))
    result = connection_status({"META_ACCESS_TOKEN": "private-token"}, check_live=True)
    assert result["auth_status"] == "unknown"
    assert result["live_access"] == "error"
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("runtime", ["cached", "bundled"])
def test_desktop_version_is_distinct_from_running_version(runtime, tmp_path):
    result = connection_status({"FLIN_META_DESKTOP_VERSION": "0.1.15", "FLIN_META_DESKTOP_RUNTIME": runtime,
                                "META_AUTH_FILE": str(tmp_path / "missing")})
    assert result["extension_version"] == "0.1.15"
    assert result["server_version"] == __version__
    assert result["runtime_source"] == runtime
