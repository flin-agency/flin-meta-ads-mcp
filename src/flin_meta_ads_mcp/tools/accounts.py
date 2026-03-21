from __future__ import annotations

from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import (
    build_collection_response,
    build_entity_response,
    compact_params,
    normalize_account_id,
    normalize_limit,
    resolve_fields,
)

DEFAULT_ACCOUNT_FIELDS = ["id", "name", "account_id", "currency", "amount_spent", "account_status"]
ALLOWED_ACCOUNT_FIELDS = {
    "id",
    "name",
    "account_id",
    "currency",
    "amount_spent",
    "account_status",
    "business_name",
    "timezone_name",
    "timezone_offset_hours_utc",
    "spend_cap",
    "balance",
    "created_time",
}


def list_ad_accounts(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = client.get_json(
        "me/adaccounts",
        params=compact_params({
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_ACCOUNT_FIELDS,
                allowed_fields=ALLOWED_ACCOUNT_FIELDS,
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


def get_ad_account(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    account_id = normalize_account_id(arguments["id"])
    payload = client.get_json(
        account_id,
        params={
            "fields": resolve_fields(
                arguments.get("fields"),
                default_fields=DEFAULT_ACCOUNT_FIELDS,
                allowed_fields=ALLOWED_ACCOUNT_FIELDS,
            )
        },
    )
    return build_entity_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
