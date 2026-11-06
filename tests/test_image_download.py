from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest
import respx
from test_server import _DummyMcpTypesWithUi, _DummyServer

from flin_meta_ads_mcp import server
from flin_meta_ads_mcp.config import MetaAdsSettings
from flin_meta_ads_mcp.errors import MetaAPIError
from flin_meta_ads_mcp.image_download import download_image

URL = "https://scontent.xx.fbcdn.net/image.png?signature=private"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1XcAAAAASUVORK5CYII="
)


@respx.mock
def test_download_returns_file_through_server(monkeypatch):
    class Blob:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Types(_DummyMcpTypesWithUi):
        BlobResourceContents = Blob
        ImageContent = Blob

    monkeypatch.setattr(server, "Server", _DummyServer)
    monkeypatch.setattr(server, "mcp_types", Types)
    route = respx.get(URL).respond(200, content=PNG, content_type="image/png")
    app = server.create_server(
        settings=MetaAdsSettings(access_token="secret", api_version="v21.0", timeout_seconds=10, max_retries=0),
        client=object(),
    )
    chunks = asyncio.run(app.call_tool_handler("download_ad_image", {"url": URL}))
    metadata = json.loads(chunks[0].text)
    assert metadata["ok"] is True
    assert metadata["data"]["filename"].endswith(".png")
    assert metadata["data"]["size_bytes"] == len(PNG)
    assert "blob" not in chunks[0].text
    assert chunks[1].type == "image"
    assert base64.b64decode(chunks[1].data) == PNG
    assert chunks[2].type == "resource"
    assert chunks[2].resource.mimeType == "image/png"
    assert base64.b64decode(chunks[2].resource.blob) == PNG
    assert "authorization" not in route.calls[0].request.headers
    assert "access_token" not in route.calls[0].request.url.params


@pytest.mark.parametrize("url", [
    "http://scontent.xx.fbcdn.net/a.png", "https://127.0.0.1/a.png",
    "https://fbcdn.net.evil.test/a.png", "https://evilfbcdn.net/a.png",
    "https://user:password@scontent.xx.fbcdn.net/a.png",
    "https://scontent.xx.fbcdn.net:8443/a.png",
])
@respx.mock
def test_rejects_non_cdn_urls_without_request(url):
    with pytest.raises(ValueError, match="HTTPS Meta CDN"):
        download_image(url, timeout_seconds=1)
    assert not respx.calls


@respx.mock
def test_redirect_target_is_checked_before_fetch():
    respx.get(URL).respond(302, headers={"location": "https://127.0.0.1/private"})
    with pytest.raises(ValueError, match="HTTPS Meta CDN"):
        download_image(URL, timeout_seconds=1)
    assert len(respx.calls) == 1


@respx.mock
def test_valid_relative_redirect():
    respx.get(URL).respond(302, headers={"location": "/new.png"})
    respx.get("https://scontent.xx.fbcdn.net/new.png").respond(200, content=PNG, content_type="image/png")
    assert download_image(URL, timeout_seconds=1) == (PNG, "image/png")


@respx.mock
def test_redirect_loop_is_bounded():
    respx.get(URL).respond(302, headers={"location": URL})
    with pytest.raises(ValueError, match="redirect limit"):
        download_image(URL, timeout_seconds=1)
    assert len(respx.calls) == 4


@pytest.mark.parametrize("headers,body,match", [
    ({"content-type": "text/html"}, b"<html/>", "JPEG"),
    ({"content-type": "image/png"}, b"<html/>", "declared format"),
    ({"content-type": "image/png"}, b"", "declared format"),
    ({"content-type": "image/png", "content-length": "6000000"}, PNG, "5 MiB"),
])
@respx.mock
def test_rejects_invalid_response(headers, body, match):
    respx.get(URL).respond(200, content=body, headers=headers)
    with pytest.raises(ValueError, match=match):
        download_image(URL, timeout_seconds=1)


@respx.mock
def test_stream_limit_without_content_length(monkeypatch):
    monkeypatch.setattr("flin_meta_ads_mcp.image_download.MAX_IMAGE_BYTES", 10)
    response = httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
    del response.headers["content-length"]
    respx.get(URL).mock(return_value=response)
    with pytest.raises(ValueError, match="5 MiB"):
        download_image(URL, timeout_seconds=1)


@pytest.mark.parametrize("failure", [403, "timeout"])
@respx.mock
def test_errors_do_not_expose_signed_url(failure):
    route = respx.get(URL)
    if failure == "timeout":
        route.mock(side_effect=httpx.ReadTimeout(URL))
    else:
        route.respond(failure, text="private upstream response")
    with pytest.raises(MetaAPIError) as exc:
        download_image(URL, timeout_seconds=1)
    assert "private" not in str(exc.value)


def test_embedded_file_serializes_with_real_mcp_types(monkeypatch):
    types = pytest.importorskip("mcp.types")
    monkeypatch.setattr(server, "mcp_types", types)
    chunks = server._tool_result_contents(name="download_ad_image", result={
        "ok": True,
        "data": {"filename": "ad-image.png"},
        "_image_file": {
            "uri": "meta-ads-image:///ad-image.png", "mimeType": "image/png",
            "blob": base64.b64encode(PNG).decode("ascii"),
        },
    })
    result = types.CallToolResult(content=chunks)
    restored = types.CallToolResult.model_validate_json(result.model_dump_json())
    assert base64.b64decode(restored.content[2].resource.blob) == PNG


@respx.mock
def test_compressed_transfer_is_rejected_before_decompression():
    import gzip
    route = respx.get(URL).respond(200, content=gzip.compress(PNG), headers={
        "content-type": "image/png", "content-encoding": "gzip",
    })
    with pytest.raises(ValueError, match="Compressed"):
        download_image(URL, timeout_seconds=1)
    assert route.calls[0].request.headers["accept-encoding"] == "identity"
