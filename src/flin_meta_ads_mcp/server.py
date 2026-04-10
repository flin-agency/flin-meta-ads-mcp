from __future__ import annotations

import asyncio
import json
import logging
from html import escape
from typing import Any
from uuid import uuid4

from . import __version__
from .config import MetaAdsSettings, load_config
from .dispatcher import dispatch_tool
from .errors import AccountSelectionRequired, MetaAdsError
from .response import error_response, selection_required_response
from .tool_registry import tool_specs

logger = logging.getLogger(__name__)

mcp_types: Any = None
Server: Any = None
stdio_server: Any = None

try:  # Optional at import time for local testing without the dependency installed.
    from mcp import types as mcp_types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except Exception:  # pragma: no cover - exercised only when dependency is unavailable.
    pass


def create_server(settings: MetaAdsSettings | None = None, client: Any | None = None) -> Any:
    if Server is None or mcp_types is None:
        raise RuntimeError("mcp is required to create the MCP server")

    try:
        server = Server("flin-meta-ads-mcp", version=__version__)
    except TypeError:  # pragma: no cover - compatibility fallback for older mcp versions.
        server = Server("flin-meta-ads-mcp")
    resolved_settings = settings or load_config()
    runtime_client = client or _client(resolved_settings)

    @server.list_tools()
    async def list_tools() -> list[Any]:
        return [
            mcp_types.Tool(
                name=spec.name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for spec in tool_specs()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        request_id = getattr(runtime_client, "last_request_id", None)
        try:
            result = dispatch_tool(name, arguments or {}, settings=resolved_settings, client=runtime_client)
        except AccountSelectionRequired as exc:
            result = selection_required_response(
                question=str(exc),
                parameter="ad_account_id",
                choices=exc.choices,
                api_version=resolved_settings.api_version,
                request_id=request_id,
            )
        except MetaAdsError as exc:
            result = error_response(
                code=exc.error_code,
                message=exc.message,
                api_version=resolved_settings.api_version,
                request_id=exc.request_id or request_id,
                details=exc.details,
            )
        except PermissionError as exc:
            result = error_response(
                code="permission_error",
                message=str(exc),
                api_version=resolved_settings.api_version,
                request_id=request_id,
            )
        except (ValueError, TypeError, KeyError) as exc:
            result = error_response(
                code="validation_error",
                message=str(exc),
                api_version=resolved_settings.api_version,
                request_id=request_id,
            )
        except Exception:  # pragma: no cover - defensive fallback
            logger.exception("Unexpected server error while handling MCP tool call")
            result = error_response(
                code="meta_api_error",
                message="Unexpected server error",
                api_version=resolved_settings.api_version,
                request_id=request_id,
            )
        return _tool_result_contents(name=name, result=result)

    return server


def main() -> None:
    if stdio_server is None or Server is None:
        raise RuntimeError("mcp is required to run flin-meta-ads-mcp")
    asyncio.run(_main())


async def _main() -> None:
    resolved_settings = load_config()
    with _client(resolved_settings) as runtime_client:
        server = create_server(resolved_settings, client=runtime_client)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


def _client(settings: MetaAdsSettings):
    from .meta_client import MetaClient

    client = MetaClient(
        access_token=settings.access_token,
        api_version=settings.api_version,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    if settings.default_ad_account_id:
        setattr(client, "_default_ad_account_id", settings.default_ad_account_id)
    return client


def _tool_result_contents(*, name: str, result: dict[str, Any]) -> list[Any]:
    contents: list[Any] = [mcp_types.TextContent(type="text", text=json.dumps(result, separators=(",", ":"), sort_keys=True))]
    preview_html = _preview_mcp_app_html(name=name, result=result)
    if preview_html is None:
        return contents

    text_resource_contents = getattr(mcp_types, "TextResourceContents", None)
    embedded_resource = getattr(mcp_types, "EmbeddedResource", None)
    if text_resource_contents is None or embedded_resource is None:
        return contents

    contents.append(
        embedded_resource(
            type="resource",
            resource=text_resource_contents(
                uri=f"ui://flin-meta-ads-mcp/ad-preview/{uuid4().hex}",
                mimeType="text/html;profile=mcp-app",
                text=preview_html,
            ),
        )
    )
    return contents


def _preview_mcp_app_html(*, name: str, result: dict[str, Any]) -> str | None:
    if name != "get_ad_preview" or not result.get("ok"):
        return None

    rows = result.get("data")
    if not isinstance(rows, list):
        return None

    preview_url: str | None = None
    for row in rows:
        if isinstance(row, dict):
            url = row.get("preview_url")
            if isinstance(url, str) and url:
                preview_url = url
                break

    if preview_url is None:
        return None

    safe_preview_url = escape(preview_url, quote=True)
    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'/>"
        "<style>"
        "html,body{margin:0;padding:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}"
        ".wrap{padding:12px;}"
        ".hint{font-size:12px;color:#344054;margin-bottom:8px;}"
        ".cta{display:inline-block;font-size:12px;margin-bottom:10px;color:#0c66e4;text-decoration:none;}"
        ".frame{width:335px;height:450px;border:0;background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(16,24,40,.15);}"
        "</style></head><body>"
        "<div class='wrap'>"
        "<div class='hint'>Ad Preview</div>"
        f"<a class='cta' href='{safe_preview_url}' target='_blank' rel='noopener noreferrer'>Open in new tab</a>"
        f"<iframe class='frame' src='{safe_preview_url}' loading='lazy'></iframe>"
        "</div></body></html>"
    )
