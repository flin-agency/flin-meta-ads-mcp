from __future__ import annotations

from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import build_collection_response, build_entity_response, compact_params, fields_to_csv, normalize_limit, resolve_ad_account_id

DEFAULT_CREATIVE_FIELDS = ["id", "name", "object_story_spec", "thumbnail_url", "image_url", "degrees_of_freedom_spec"]
ENTITY_PATH = "adcreatives"


def list_ad_creatives(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    account_id = resolve_ad_account_id(client=client, ad_account_id=arguments.get("ad_account_id"))
    payload = client.get_json(
        f"{account_id}/{ENTITY_PATH}",
        params=compact_params({
            "fields": fields_to_csv(arguments.get("fields"), DEFAULT_CREATIVE_FIELDS),
            "limit": normalize_limit(arguments.get("limit")),
            "after": arguments.get("after"),
        }),
    )
    return build_collection_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )


def get_ad_creative(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = client.get_json(arguments["id"], params={"fields": fields_to_csv(arguments.get("fields"), DEFAULT_CREATIVE_FIELDS)})
    return build_entity_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
