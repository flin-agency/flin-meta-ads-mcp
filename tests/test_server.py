from __future__ import annotations

import asyncio
import json

from flin_meta_ads_mcp import server
from flin_meta_ads_mcp.config import MetaAdsSettings


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


class _DummyImageContent:
    def __init__(self, *, type: str, data: str, mimeType: str) -> None:
        self.type = type
        self.data = data
        self.mimeType = mimeType


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


class _DummyMcpTypesWithUiAndImage(_DummyMcpTypesWithUi):
    ImageContent = _DummyImageContent


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


def test_tool_result_contents_adds_image_content_for_preview_screenshot(monkeypatch) -> None:
    monkeypatch.setattr(server, "mcp_types", _DummyMcpTypesWithUiAndImage)

    contents = server._tool_result_contents(
        name="get_ad_preview_screenshot",
        result={
            "ok": True,
            "data": {
                "preview_url": "https://business.facebook.com/ads/api/preview_iframe.php?d=AQ&t=AQ",
                "mime_type": "image/png",
                "image_base64": "ZmFrZV9wbmc=",
            },
        },
    )

    assert len(contents) == 2
    assert contents[0].type == "text"
    assert contents[1].type == "image"
    assert contents[1].mimeType == "image/png"

    payload = json.loads(contents[0].text)
    assert payload["data"]["image_base64"].startswith("<omitted:")
