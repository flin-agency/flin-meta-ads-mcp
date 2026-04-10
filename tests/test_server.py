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
