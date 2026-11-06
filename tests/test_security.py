from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import respx
from test_server import _DummyMcpTypes, _DummyServer

from flin_meta_ads_mcp.config import load_config
from flin_meta_ads_mcp.errors import MetaAdsError, MetaAPIError
from flin_meta_ads_mcp.meta_client import MetaClient
from flin_meta_ads_mcp.server import _preview_mcp_app_html, create_server
from flin_meta_ads_mcp.tools.previews import _extract_preview_url_from_body


def client(**kwargs):
    return MetaClient(access_token="private-token", api_version="v21.0",
                      timeout_seconds=10, max_retries=0, **kwargs)


@pytest.mark.parametrize("method", ["POST", "DELETE", "PATCH", "PUT"])
@respx.mock
def test_write_methods_are_blocked_at_transport(method):
    with client() as meta, pytest.raises(PermissionError):
        meta.request_json(method, "123")
    assert not respx.calls


@pytest.mark.parametrize("path", [
    "../oauth/access_token", "123?method=delete", "https://evil.test", "me/feed",
    "123/ads", "act_123/../456", "act_123%2fads", "/me", "123#fragment",
])
@respx.mock
def test_unapproved_paths_are_blocked(path):
    with client() as meta, pytest.raises(ValueError):
        meta.get_json(path)
    assert not respx.calls


@pytest.mark.parametrize("key", ["method", "METHOD", "http_method", "X-HTTP-Method-Override"])
@respx.mock
def test_method_override_blocked(key):
    with client() as meta, pytest.raises(PermissionError):
        meta.get_json("123", {key: "DELETE"})
    assert not respx.calls


@respx.mock
def test_redirect_not_followed_even_with_injected_redirecting_client():
    respx.get("https://graph.facebook.com/v21.0/me").respond(
        302, headers={"location": "https://evil.test/steal"})
    with (httpx.Client(follow_redirects=True) as transport,
          client(client=transport) as meta, pytest.raises(MetaAPIError)):
        meta.get_json("me")
    assert len(respx.calls) == 1


@pytest.mark.parametrize("body", [
    {"error": {"message": "private-token", "error_data": {"token": "private-token"}, "code": 100}},
    {"error": "private-token"},
])
@respx.mock
def test_upstream_errors_do_not_leak_secrets(body):
    respx.get("https://graph.facebook.com/v21.0/me").respond(400, json=body)
    with client() as meta, pytest.raises(MetaAdsError) as error:
        meta.get_json("me")
    assert "private-token" not in str(error.value)
    assert "private-token" not in json.dumps(error.value.details)


@respx.mock
def test_transport_errors_do_not_leak_urls():
    respx.get("https://graph.facebook.com/v21.0/me").mock(
        side_effect=httpx.ReadTimeout("private-token"))
    with client() as meta, pytest.raises(MetaAPIError) as error:
        meta.get_json("me")
    assert "private-token" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "data:text/html,hello", "https://evil.test/ads/api/preview_iframe.php",
    "https://business.facebook.com.evil.test/ads/api/preview_iframe.php",
    "https://user:pass@business.facebook.com/ads/api/preview_iframe.php",
    "http://business.facebook.com/ads/api/preview_iframe.php",
    "https://business.facebook.com/other", "https://business.facebook.com:bad/",
])
def test_untrusted_previews_are_not_embedded(url):
    assert _extract_preview_url_from_body(f'<iframe src="{url}"></iframe>') is None
    assert _preview_mcp_app_html(name="get_ad_preview", result={
        "ok": True, "data": [{"preview_url": url}],
    }) is None


def test_trusted_preview_is_sandboxed():
    html = _preview_mcp_app_html(name="get_ad_preview", result={
        "ok": True, "data": [{"preview_url": "https://business.facebook.com/ads/api/preview_iframe.php?d=1"}],
    })
    assert "sandbox='allow-scripts allow-same-origin'" in html
    assert "Content-Security-Policy" in html
    assert "referrerpolicy='no-referrer'" in html


@pytest.mark.parametrize("key,value", [
    ("META_GRAPH_API_VERSION", "v21.0/../oauth"), ("META_TIMEOUT_SECONDS", "nan"),
    ("META_TIMEOUT_SECONDS", "inf"), ("META_TIMEOUT_SECONDS", "-1"),
    ("META_TIMEOUT_SECONDS", "121"), ("META_MAX_RETRIES", "-1"), ("META_MAX_RETRIES", "6"),
])
def test_invalid_connection_configuration_is_rejected(key, value):
    with pytest.raises(ValueError):
        load_config({"META_ACCESS_TOKEN": "private-token", key: value})


def test_unexpected_exception_is_not_logged_with_secret(monkeypatch, caplog):
    from flin_meta_ads_mcp import server
    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypes)
    def fail(*args, **kwargs):
        raise RuntimeError("private-token")
    monkeypatch.setattr(server, "dispatch_tool", fail)
    app = create_server(settings=load_config({"META_ACCESS_TOKEN": "private-token"}), client=object())
    chunks = asyncio.run(app.call_tool_handler("list_ad_accounts", {}))
    assert "private-token" not in caplog.text
    assert "private-token" not in chunks[0].text
