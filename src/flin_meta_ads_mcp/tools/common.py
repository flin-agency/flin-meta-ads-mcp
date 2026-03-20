from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..config import MetaAdsSettings
from ..response import ok_response


DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def resolve_ad_account_id(ad_account_id: str | None, default_ad_account_id: str | None) -> str:
    resolved = ad_account_id or default_ad_account_id
    if not resolved:
        raise ValueError("ad_account_id is required (argument or META_AD_ACCOUNT_ID)")
    return normalize_account_id(resolved)


def normalize_account_id(value: str) -> str:
    return value if value.startswith("act_") else f"act_{value}"


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


def get_settings_api_version(settings: MetaAdsSettings) -> str:
    return settings.api_version
