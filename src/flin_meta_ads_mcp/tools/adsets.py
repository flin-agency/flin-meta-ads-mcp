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

DEFAULT_ADSET_FIELDS = ["id", "name", "status", "effective_status", "campaign_id", "daily_budget"]
ALLOWED_ADSET_FIELDS = {
    "id",
    "name",
    "status",
    "effective_status",
    "campaign_id",
    "daily_budget",
    "lifetime_budget",
    "billing_event",
    "optimization_goal",
    "bid_strategy",
    "start_time",
    "end_time",
    "updated_time",
    "created_time",
}
ENTITY_PATH = "adsets"


def list_adsets(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    account_id = resolve_ad_account_id(client=client, ad_account_id=arguments.get("ad_account_id"))
    payload = client.get_json(
        f"{account_id}/{ENTITY_PATH}",
        params=compact_params({
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_ADSET_FIELDS,
                allowed_fields=ALLOWED_ADSET_FIELDS,
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


def get_adset(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    adset_id = validate_meta_id(arguments["id"], parameter_name="id")
    payload = client.get_json(
        adset_id,
        params={
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_ADSET_FIELDS,
                allowed_fields=ALLOWED_ADSET_FIELDS,
            )
        },
    )
    return build_entity_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
