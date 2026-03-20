from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Mapping

from ..errors import AccountSelectionRequired
from ..response import ok_response

if TYPE_CHECKING:
    from ..meta_client import MetaClient

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def resolve_ad_account_id(*, client: MetaClient, ad_account_id: str | None) -> str:
    if ad_account_id:
        return normalize_account_id(ad_account_id)
    return _discover_single_ad_account_id(client)


def normalize_account_id(value: str) -> str:
    return value if value.startswith("act_") else f"act_{value}"


def _discover_single_ad_account_id(client: MetaClient) -> str:
    cached = getattr(client, "_resolved_ad_account_id", None)
    if isinstance(cached, str) and cached:
        return cached

    payload = client.get_json("me/adaccounts", params={"fields": "id,name", "limit": 100})
    accounts = payload.get("data", [])
    choices_by_id: dict[str, dict[str, str]] = {}
    for account in accounts:
        if not isinstance(account, Mapping) or not account.get("id"):
            continue
        account_id = normalize_account_id(str(account.get("id")))
        name = str(account.get("name") or "")
        label = f"{name} ({account_id})" if name else account_id
        choices_by_id[account_id] = {"ad_account_id": account_id, "label": label}
    choices = [choices_by_id[key] for key in sorted(choices_by_id)]

    if not choices:
        raise ValueError("No ad accounts accessible for this token")
    if len(choices) > 1:
        raise AccountSelectionRequired(
            choices=choices,
            message="Multiple ad accounts available. Which ad_account_id should I use?",
        )

    resolved = choices[0]["ad_account_id"]
    setattr(client, "_resolved_ad_account_id", resolved)
    return resolved


def normalize_limit(value: Any, default: int = DEFAULT_LIMIT) -> int:
    if value is None:
        return default
    return max(1, min(MAX_LIMIT, int(value)))


def fields_to_csv(fields: Iterable[str] | None, default_fields: Iterable[str]) -> str:
    values = list(fields or default_fields)
    return ",".join(values)


def build_ok_response(
    *,
    data: Any,
    api_version: str,
    request_id: str | None,
    next_after: str | None = None,
    has_next: bool = False,
) -> dict[str, Any]:
    return ok_response(
        data=data,
        next_after=next_after,
        has_next=has_next,
        api_version=api_version,
        request_id=request_id,
    )


def compact_params(params: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def build_collection_response(
    *,
    payload: Mapping[str, Any],
    api_version: str,
    request_id: str | None,
) -> dict[str, Any]:
    data = list(payload.get("data", []))
    paging = payload.get("paging", {})
    cursors = paging.get("cursors", {}) if isinstance(paging, Mapping) else {}
    next_after = cursors.get("after") if isinstance(cursors, Mapping) else None
    has_next = bool(paging.get("next")) if isinstance(paging, Mapping) else False
    if not has_next:
        has_next = next_after is not None
    return build_ok_response(
        data=data,
        api_version=api_version,
        request_id=request_id,
        next_after=next_after,
        has_next=has_next,
    )


def build_entity_response(
    *,
    payload: Mapping[str, Any],
    api_version: str,
    request_id: str | None,
) -> dict[str, Any]:
    return build_ok_response(
        data=dict(payload),
        api_version=api_version,
        request_id=request_id,
    )


def filter_clause(level: str, entity_ids: list[str]) -> list[dict[str, Any]]:
    field_map = {
        "campaign": "campaign.id",
        "adset": "adset.id",
        "ad": "ad.id",
        "account": "account.id",
    }
    return [
        {
            "field": field_map[level],
            "operator": "IN",
            "value": entity_ids,
        }
    ]
