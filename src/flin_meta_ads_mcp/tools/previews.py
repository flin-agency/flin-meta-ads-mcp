from __future__ import annotations

import json
import re
from collections.abc import Mapping
from html import unescape
from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import build_ok_response, resolve_ad_account_id, validate_meta_id

DEFAULT_AD_FORMAT = "DESKTOP_FEED_STANDARD"
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
