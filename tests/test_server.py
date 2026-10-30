from __future__ import annotations

import asyncio
import json

import httpx
import pytest
import respx

from flin_meta_ads_mcp import server
from flin_meta_ads_mcp.auth_session import AuthSession
from flin_meta_ads_mcp.config import MetaAdsSettings, load_config
from flin_meta_ads_mcp.credentials import Credentials, save_credentials


@respx.mock
def test_server_client_uses_app_secret_from_environment() -> None:
    settings = load_config({
        "META_ACCESS_TOKEN": "what do ya want for nothing?",
        "META_APP_SECRET": "Jefe",
    })
    route = respx.get("https://graph.facebook.com/v21.0/me/adaccounts").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with server._client(settings) as client:
        assert client.get_json("me/adaccounts") == {"data": []}

    assert route.calls[0].request.url.params["appsecret_proof"] == (
        "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    )


class _DummyTextContent:
    def __init__(self, *, type: str, text: str) -> None:
        self.type = type
        self.text = text


class _DummyMcpTypes:
    TextContent = _DummyTextContent

    class Tool:
        def __init__(self, *, name: str, description: str, inputSchema: dict) -> None:
            self.name = name
            self.description = description
            self.inputSchema = inputSchema


class _DummyTextResourceContents:
    def __init__(self, *, uri: str, mimeType: str, text: str) -> None:
        self.uri = uri
        self.mimeType = mimeType
        self.text = text


class _DummyEmbeddedResource:
    def __init__(self, *, type: str, resource: _DummyTextResourceContents) -> None:
        self.type = type
        self.resource = resource


class _DummyMcpTypesWithUi(_DummyMcpTypes):
    TextResourceContents = _DummyTextResourceContents
    EmbeddedResource = _DummyEmbeddedResource


class _DummyServer:
    def __init__(self, _: str, version: str | None = None) -> None:
        self.call_tool_handler = None
        self.list_tools_handler = None
        self.version = version

    def list_tools(self):
        def decorator(func):
            self.list_tools_handler = func
            return func

        return decorator

    def call_tool(self):
        def decorator(func):
            self.call_tool_handler = func
            return func

        return decorator


def test_server_starts_without_token_and_returns_login_instructions(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypes)
    monkeypatch.setattr(server, "_client", lambda _: pytest.fail("Must not contact Meta without login"))
    auth = AuthSession({"META_APP_SECRET": "private-secret", "META_AUTH_FILE": str(tmp_path / "auth.json")})
    test_server = server.create_server(auth_session=auth)
    names = [tool.name for tool in asyncio.run(test_server.list_tools_handler())]
    assert "start_meta_login" in names
    assert "get_meta_auth_status" in names
    chunks = asyncio.run(test_server.call_tool_handler("list_ad_accounts", {}))
    result = json.loads(chunks[0].text)
    assert result["status"] == "authentication_required"
    assert result["missing_configuration"] == ["META_APP_ID"]
    assert "private-secret" not in chunks[0].text
    auth.close()


@respx.mock
def test_running_server_uses_newly_saved_login_without_restart(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypes)
    path = tmp_path / "auth.json"
    auth = AuthSession({"META_APP_ID": "123", "META_APP_SECRET": "secret", "META_AUTH_FILE": str(path)})
    test_server = server.create_server(auth_session=auth)
    before = asyncio.run(test_server.call_tool_handler("list_ad_accounts", {}))
    assert json.loads(before[0].text)["status"] == "authentication_required"
    save_credentials(path, Credentials("123", "secret", "new-token", "v21.0"))
    route = respx.get("https://graph.facebook.com/v21.0/me/adaccounts").respond(
        200, json={"data": [{"id": "act_123"}]},
    )
    after = asyncio.run(test_server.call_tool_handler("list_ad_accounts", {}))
    assert json.loads(after[0].text)["data"] == [{"id": "act_123"}]
    assert route.calls[0].request.headers["Authorization"] == "Bearer new-token"
    assert "appsecret_proof" in route.calls[0].request.url.params
    auth.close()


def test_auth_tools_do_not_bypass_ads_write_guard(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypes)
    auth = AuthSession({"META_AUTH_FILE": str(tmp_path / "auth.json")})
    test_server = server.create_server(auth_session=auth)
    chunks = asyncio.run(test_server.call_tool_handler("update_campaign", {}))
    assert json.loads(chunks[0].text)["error"]["code"] == "permission_error"
    auth.close()


def test_call_tool_unexpected_exception_does_not_leak_internal_error_details(monkeypatch) -> None:
    def _boom(*_, **__):
        raise RuntimeError("sensitive backend failure")

    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypes)
    monkeypatch.setattr(server, "dispatch_tool", _boom)

    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )
    client = type("ClientStub", (), {"last_request_id": "req-123"})()

    test_server = server.create_server(settings=settings, client=client)
    response_chunks = asyncio.run(test_server.call_tool_handler("list_campaigns", {}))
    payload = json.loads(response_chunks[0].text)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "meta_api_error"
    assert payload["error"]["message"] == "Unexpected server error"
    assert payload["error"]["details"] == {}
    assert "sensitive backend failure" not in response_chunks[0].text


def test_create_server_sets_server_version(monkeypatch) -> None:
    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypes)
    monkeypatch.setattr(server, "_client", lambda _: type("ClientStub", (), {})())

    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )
    test_server = server.create_server(settings=settings)

    assert test_server.version == server.__version__


def test_preview_mcp_app_html_is_generated_for_get_ad_preview_result() -> None:
    html = server._preview_mcp_app_html(
        name="get_ad_preview",
        result={"ok": True, "data": [{"preview_url": "https://business.facebook.com/ads/api/preview_iframe.php?d=AQ&t=AQ"}]},
    )

    assert html is not None
    assert "iframe" in html
    assert "Open in new tab" in html


def test_tool_result_contents_adds_embedded_preview_when_ui_types_available(monkeypatch) -> None:
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypesWithUi)

    contents = server._tool_result_contents(
        name="get_ad_preview",
        result={"ok": True, "data": [{"preview_url": "https://business.facebook.com/ads/api/preview_iframe.php?d=AQ&t=AQ"}]},
    )

    assert len(contents) == 2
    assert contents[0].type == "text"
    assert contents[1].type == "resource"
    assert contents[1].resource.mimeType == "text/html;profile=mcp-app"
