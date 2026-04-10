from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


def tool_specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="list_ad_accounts",
            description="List ad accounts accessible by the token",
            input_schema=_list_schema(),
        ),
        ToolSpec(
            name="get_ad_account",
            description="Fetch a single ad account by id",
            input_schema=_account_id_schema(),
        ),
        ToolSpec(
            name="list_campaigns",
            description="List campaigns for an ad account",
            input_schema=_list_schema(),
        ),
        ToolSpec(
            name="get_campaign",
            description="Fetch a single campaign by id",
            input_schema=_id_schema(),
        ),
        ToolSpec(
            name="list_adsets",
            description="List ad sets for an ad account",
            input_schema=_list_schema(),
        ),
        ToolSpec(
            name="get_adset",
            description="Fetch a single ad set by id",
            input_schema=_id_schema(),
        ),
        ToolSpec(
            name="list_ads",
            description="List ads for an ad account",
            input_schema=_list_schema(),
        ),
        ToolSpec(
            name="get_ad",
            description="Fetch a single ad by id",
            input_schema=_id_schema(),
        ),
        ToolSpec(
            name="list_ad_images",
            description="List ad images for an ad account",
            input_schema=_list_schema(),
        ),
        ToolSpec(
            name="get_ad_image",
            description="Fetch a single ad image by id",
            input_schema=_id_schema(),
        ),
        ToolSpec(
            name="list_ad_creatives",
            description="List ad creatives for an ad account",
            input_schema=_list_schema(),
        ),
        ToolSpec(
            name="get_ad_creative",
            description="Fetch a single ad creative by id",
            input_schema=_id_schema(),
        ),
        ToolSpec(
            name="get_ad_preview",
            description="Fetch or generate a rendered preview for an ad or ad creative",
            input_schema={
                "type": "object",
                "properties": {
                    "ad_id": {"type": "string", "pattern": "^[0-9]+$"},
                    "ad_creative_id": {"type": "string", "pattern": "^[0-9]+$"},
                    "creative": {
                        "oneOf": [
                            {"type": "object"},
                            {"type": "string"},
                        ]
                    },
                    "ad_format": {"type": "string", "default": "DESKTOP_FEED_STANDARD"},
                    "ad_account_id": {"type": "string", "pattern": "^(act_)?[0-9]+$"},
                },
                "oneOf": [
                    {"required": ["ad_id"]},
                    {"required": ["ad_creative_id"]},
                    {"required": ["creative"]},
                ],
                "additionalProperties": False,
            },
        ),
        ToolSpec(
            name="get_insights",
            description="Fetch insights for an account, campaign, ad set, or ad",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["account", "campaign", "adset", "ad"]},
                    "ad_account_id": {"type": "string", "pattern": "^(act_)?[0-9]+$"},
                    "date_preset": {"type": "string"},
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "since": {"type": "string"},
                            "until": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]*$"},
                    },
                    "breakdowns": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]*$"},
                    },
                    "action_breakdowns": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]*$"},
                    },
                    "time_increment": {
                        "oneOf": [
                            {"type": "integer"},
                            {"type": "string"},
                        ]
                    },
                    "entity_ids": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^[0-9]+$"},
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                },
                "required": ["level"],
                "additionalProperties": False,
            },
        ),
    ]


def _list_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "ad_account_id": {"type": "string", "pattern": "^(act_)?[0-9]+$"},
            "fields": {
                "type": "array",
                "items": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]*$"},
            },
            "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
            "after": {"type": "string"},
            "effective_status": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    }


def _id_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^[0-9]+$"},
            "fields": {
                "type": "array",
                "items": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]*$"},
            },
        },
        "required": ["id"],
        "additionalProperties": False,
    }


def _account_id_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^(act_)?[0-9]+$"},
            "fields": {
                "type": "array",
                "items": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.]*$"},
            },
        },
        "required": ["id"],
        "additionalProperties": False,
    }
