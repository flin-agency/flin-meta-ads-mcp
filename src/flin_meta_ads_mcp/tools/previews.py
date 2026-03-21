from __future__ import annotations

from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import build_ok_response, validate_meta_id

DEFAULT_AD_FORMAT = "DESKTOP_FEED_STANDARD"


def normalize_preview_format(value: str | None) -> str:
    return value or DEFAULT_AD_FORMAT


def get_ad_preview(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    ad_id = validate_meta_id(arguments["ad_id"], parameter_name="ad_id")
    payload = client.get_json(
        f"{ad_id}/previews",
        params={
            "ad_format": normalize_preview_format(arguments.get("ad_format")),
        },
    )
    return build_ok_response(
        data=payload.get("data", payload),
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
