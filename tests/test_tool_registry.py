from __future__ import annotations

from flin_meta_ads_mcp.tool_registry import tool_specs


def test_tool_registry_exposes_expected_read_only_tools() -> None:
    names = [spec.name for spec in tool_specs()]

    assert names == [
        "list_ad_accounts",
        "get_ad_account",
        "list_campaigns",
        "get_campaign",
        "list_adsets",
        "get_adset",
        "list_ads",
        "get_ad",
        "list_ad_creatives",
        "get_ad_creative",
        "get_ad_preview",
        "get_insights",
    ]


def test_get_insights_requires_level_field() -> None:
    spec = next(spec for spec in tool_specs() if spec.name == "get_insights")

    assert "level" in spec.input_schema["required"]
