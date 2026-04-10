from __future__ import annotations

from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import (
    build_collection_response,
    build_entity_response,
    compact_params,
    normalize_limit,
    resolve_ad_account_id,
    resolve_fields,
    validate_meta_id,
)

DEFAULT_AD_IMAGE_FIELDS = [
    "id",
    "hash",
    "name",
    "width",
    "height",
    "url",
    "url_128",
    "permalink_url",
    "status",
    "created_time",
    "updated_time",
]
ALLOWED_AD_IMAGE_FIELDS = {
    "id",
    "account_id",
    "created_time",
    "creatives",
    "hash",
    "height",
    "is_associated_creatives_in_adgroups",
    "name",
    "original_height",
    "original_width",
    "permalink_url",
    "status",
    "updated_time",
    "url",
    "url_128",
    "width",
}
ENTITY_PATH = "adimages"


def list_ad_images(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    account_id = resolve_ad_account_id(client=client, ad_account_id=arguments.get("ad_account_id"))
    payload = client.get_json(
        f"{account_id}/{ENTITY_PATH}",
        params=compact_params({
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_AD_IMAGE_FIELDS,
                allowed_fields=ALLOWED_AD_IMAGE_FIELDS,
            ),
            "limit": normalize_limit(arguments.get("limit")),
            "after": arguments.get("after"),
        }),
    )
    return build_collection_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )


def get_ad_image(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    image_id = validate_meta_id(arguments["id"], parameter_name="id")
    payload = client.get_json(
        image_id,
        params={
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_AD_IMAGE_FIELDS,
                allowed_fields=ALLOWED_AD_IMAGE_FIELDS,
            )
        },
    )
    return build_entity_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
