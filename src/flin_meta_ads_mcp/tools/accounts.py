from __future__ import annotations

from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import build_collection_response, build_entity_response, compact_params

DEFAULT_ACCOUNT_FIELDS = ["id", "name", "account_id", "currency", "amount_spent", "account_status"]


def list_ad_accounts(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = client.get_json(
        "me/adaccounts",
        params=compact_params({
            "fields": _fields(arguments.get("fields")),
            "limit": arguments.get("limit", 50),
            "after": arguments.get("after"),
        }),
    )
    return build_collection_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )


def get_ad_account(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    account_id = arguments["id"]
    payload = client.get_json(
        _account_path(account_id),
        params={"fields": _fields(arguments.get("fields"))},
    )
    return build_entity_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )


def _account_path(account_id: str) -> str:
    return account_id if account_id.startswith("act_") else f"act_{account_id}"


def _fields(value: list[str] | None) -> str:
    return ",".join(value or DEFAULT_ACCOUNT_FIELDS)
