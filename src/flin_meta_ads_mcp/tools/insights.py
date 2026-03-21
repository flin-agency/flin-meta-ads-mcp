from __future__ import annotations

from typing import Any

from ..config import MetaAdsSettings
from ..meta_client import MetaClient
from .common import (
    build_collection_response,
    filter_clause,
    normalize_limit,
    resolve_ad_account_id,
    resolve_fields,
    validate_meta_id,
)

DEFAULT_INSIGHT_FIELDS = [
    "account_id",
    "campaign_id",
    "adset_id",
    "ad_id",
    "impressions",
    "clicks",
    "spend",
    "reach",
    "frequency",
    "cpc",
    "ctr",
]

ALLOWED_LEVELS = {"account", "campaign", "adset", "ad"}
ALLOWED_INSIGHT_FIELDS = {
    "account_id",
    "account_name",
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "impressions",
    "clicks",
    "spend",
    "reach",
    "frequency",
    "cpc",
    "ctr",
    "cpm",
    "cpp",
    "unique_clicks",
    "unique_ctr",
    "inline_link_clicks",
    "inline_post_engagement",
    "actions",
    "action_values",
    "cost_per_action_type",
    "date_start",
    "date_stop",
    "objective",
    "buying_type",
    "social_spend",
    "outbound_clicks",
    "outbound_clicks_ctr",
    "conversion_rate_ranking",
    "quality_ranking",
    "engagement_rate_ranking",
}


def validate_insights_args(arguments: dict[str, Any]) -> dict[str, Any]:
    level = arguments.get("level")
    if level not in ALLOWED_LEVELS:
        raise ValueError("level must be one of: account, campaign, adset, ad")
    entity_ids = arguments.get("entity_ids")
    if entity_ids is not None and not isinstance(entity_ids, list):
        raise ValueError("entity_ids must be an array of string ids")
    return arguments


def get_insights(*, client: MetaClient, settings: MetaAdsSettings, arguments: dict[str, Any]) -> dict[str, Any]:
    args = validate_insights_args(arguments)
    account_id = resolve_ad_account_id(client=client, ad_account_id=args.get("ad_account_id"))
    params: dict[str, Any] = {
        "level": args["level"],
        "fields": resolve_fields(
            args.get("fields"),
            default_fields=DEFAULT_INSIGHT_FIELDS,
            allowed_fields=ALLOWED_INSIGHT_FIELDS,
        ),
    }
    if args.get("date_preset"):
        params["date_preset"] = args["date_preset"]
    if args.get("time_range"):
        params["time_range"] = args["time_range"]
    if args.get("breakdowns"):
        params["breakdowns"] = ",".join(args["breakdowns"])
    if args.get("action_breakdowns"):
        params["action_breakdowns"] = ",".join(args["action_breakdowns"])
    if args.get("time_increment") is not None:
        params["time_increment"] = args["time_increment"]
    if args.get("entity_ids"):
        entity_ids = [validate_meta_id(entity_id, parameter_name="entity_ids[]") for entity_id in args["entity_ids"]]
        params["filtering"] = filter_clause(args["level"], entity_ids)
    if args.get("limit") is not None:
        params["limit"] = normalize_limit(args["limit"])

    payload = client.get_json(f"{account_id}/insights", params=params)
    return build_collection_response(
        payload=payload,
        api_version=settings.api_version,
        request_id=getattr(client, "last_request_id", None),
    )
