from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping
from html import unescape
from typing import Any

from ..config import MetaAdsSettings
from ..errors import MetaAPIError
from ..meta_client import MetaClient
from .common import build_ok_response, resolve_ad_account_id, validate_meta_id

DEFAULT_AD_FORMAT = "DESKTOP_FEED_STANDARD"
DEFAULT_SCREENSHOT_WIDTH = 390
DEFAULT_SCREENSHOT_HEIGHT = 844
DEFAULT_SCREENSHOT_TIMEOUT_MS = 30000
IFRAME_SRC_PATTERN = re.compile(r"""<iframe[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def normalize_preview_format(value: str | None) -> str:
    return value or DEFAULT_AD_FORMAT


def _extract_preview_url_from_body(body: str | None) -> str | None:
    if not isinstance(body, str):
        return None
    match = IFRAME_SRC_PATTERN.search(body)
    if not match:
        return None
    preview_url = unescape(match.group(1)).strip()
    return preview_url or None


def _normalize_creative_spec(creative: Any) -> str:
    if isinstance(creative, str):
        cleaned = creative.strip()
        if not cleaned:
            raise ValueError("creative must not be empty")
        return cleaned
    if isinstance(creative, Mapping):
        return json.dumps(creative, separators=(",", ":"))
    raise ValueError("creative must be a JSON string or object")


def _resolve_preview_target(*, client: MetaClient, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    source_arguments = {
        "ad_id": arguments.get("ad_id"),
        "ad_creative_id": arguments.get("ad_creative_id"),
        "creative": arguments.get("creative"),
    }
    selected_sources = [name for name, value in source_arguments.items() if value is not None]

    if len(selected_sources) != 1:
        raise ValueError("Exactly one of ad_id, ad_creative_id, or creative must be provided")

    if "ad_id" in selected_sources:
        ad_id = validate_meta_id(arguments["ad_id"], parameter_name="ad_id")
        return f"{ad_id}/previews", {}

    if "ad_creative_id" in selected_sources:
        ad_creative_id = validate_meta_id(arguments["ad_creative_id"], parameter_name="ad_creative_id")
        return f"{ad_creative_id}/previews", {}

    creative_spec = _normalize_creative_spec(arguments["creative"])
    ad_account_id = arguments.get("ad_account_id")
    if ad_account_id is None:
        return "generatepreviews", {"creative": creative_spec}
    account_id = resolve_ad_account_id(client=client, ad_account_id=ad_account_id)
    return f"{account_id}/generatepreviews", {"creative": creative_spec}


def _decorate_preview_rows(rows: Any) -> Any:
    if not isinstance(rows, list):
        return rows
    decorated_rows: list[Any] = []
    for row in rows:
        if not isinstance(row, Mapping):
            decorated_rows.append(row)
            continue
        normalized = dict(row)
        preview_url = _extract_preview_url_from_body(normalized.get("body"))
        if preview_url is not None:
            normalized["preview_url"] = preview_url
        decorated_rows.append(normalized)
    return decorated_rows


def _first_preview_url(rows: Any) -> str | None:
    decorated_rows = _decorate_preview_rows(rows)
    if not isinstance(decorated_rows, list):
        return None
    for row in decorated_rows:
        if isinstance(row, Mapping):
            url = row.get("preview_url")
            if isinstance(url, str) and url:
                return url
    return None


def _normalize_positive_int(
    value: Any,
    *,
    default: int,
    parameter_name: str,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{parameter_name} must be between {minimum} and {maximum}")
    return parsed


def _capture_preview_screenshot(
    *,
    preview_url: str,
    viewport_width: int,
    viewport_height: int,
    timeout_ms: int,
) -> str:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise MetaAPIError(
            "Screenshot requires Playwright browser runtime. Run `playwright install chromium` "
            "or install Google Chrome for channel-based fallback."
        ) from exc

    try:
        with sync_playwright() as playwright:
            browser = None
            try:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except PlaywrightError:
                    browser = playwright.chromium.launch(headless=True, channel="chrome")
                page = browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
                page.goto(preview_url, wait_until="networkidle", timeout=timeout_ms)
                screenshot_bytes = page.screenshot(type="png")
            finally:
                if browser is not None:
                    browser.close()
    except PlaywrightTimeoutError as exc:
        raise MetaAPIError(f"Timed out while loading preview URL after {timeout_ms}ms") from exc
    except PlaywrightError as exc:
        raise MetaAPIError(f"Failed to capture preview screenshot: {exc}") from exc

    return base64.b64encode(screenshot_bytes).decode("ascii")


def get_ad_preview(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    path, extra_params = _resolve_preview_target(client=client, arguments=arguments)
    payload = client.get_json(
        path,
        params={"ad_format": normalize_preview_format(arguments.get("ad_format")), **extra_params},
    )
    return build_ok_response(
        data=_decorate_preview_rows(payload.get("data", payload)),
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )


def get_ad_preview_screenshot(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    path, extra_params = _resolve_preview_target(client=client, arguments=arguments)
    payload = client.get_json(
        path,
        params={"ad_format": normalize_preview_format(arguments.get("ad_format")), **extra_params},
    )

    preview_url = _first_preview_url(payload.get("data", payload))
    if preview_url is None:
        raise ValueError("Could not extract preview_url from preview response")

    viewport_width = _normalize_positive_int(
        arguments.get("viewport_width"),
        default=DEFAULT_SCREENSHOT_WIDTH,
        parameter_name="viewport_width",
        minimum=200,
        maximum=1920,
    )
    viewport_height = _normalize_positive_int(
        arguments.get("viewport_height"),
        default=DEFAULT_SCREENSHOT_HEIGHT,
        parameter_name="viewport_height",
        minimum=200,
        maximum=4000,
    )
    timeout_ms = _normalize_positive_int(
        arguments.get("timeout_ms"),
        default=DEFAULT_SCREENSHOT_TIMEOUT_MS,
        parameter_name="timeout_ms",
        minimum=1000,
        maximum=120000,
    )

    image_base64 = _capture_preview_screenshot(
        preview_url=preview_url,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        timeout_ms=timeout_ms,
    )

    return build_ok_response(
        data={
            "preview_url": preview_url,
            "mime_type": "image/png",
            "image_base64": image_base64,
            "viewport": {"width": viewport_width, "height": viewport_height},
        },
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
