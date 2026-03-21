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

DEFAULT_CAMPAIGN_FIELDS = ["id", "name", "status", "effective_status", "objective"]
ALLOWED_CAMPAIGN_FIELDS = {
    "id",
    "name",
    "status",
    "effective_status",
    "objective",
    "created_time",
    "updated_time",
    "start_time",
    "stop_time",
    "daily_budget",
    "lifetime_budget",
    "bid_strategy",
    "buying_type",
}
ENTITY_PATH = "campaigns"


def list_campaigns(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    account_id = resolve_ad_account_id(client=client, ad_account_id=arguments.get("ad_account_id"))
    payload = client.get_json(
        f"{account_id}/{ENTITY_PATH}",
        params=compact_params({
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_CAMPAIGN_FIELDS,
                allowed_fields=ALLOWED_CAMPAIGN_FIELDS,
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


def get_campaign(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    campaign_id = validate_meta_id(arguments["id"], parameter_name="id")
    payload = client.get_json(
        campaign_id,
        params={
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_CAMPAIGN_FIELDS,
                allowed_fields=ALLOWED_CAMPAIGN_FIELDS,
            )
        },
    )
    return build_entity_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
