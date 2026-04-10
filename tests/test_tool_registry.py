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
        "list_ad_images",
        "get_ad_image",
        "list_ad_creatives",
        "get_ad_creative",
        "get_ad_preview",
        "get_ad_preview_screenshot",
        "get_insights",
    ]


def test_get_insights_requires_level_field() -> None:
    spec = next(spec for spec in tool_specs() if spec.name == "get_insights")

    assert "level" in spec.input_schema["required"]


def test_get_ad_preview_supports_ad_creative_and_generatepreviews_inputs() -> None:
    spec = next(spec for spec in tool_specs() if spec.name == "get_ad_preview")

    one_of_required = spec.input_schema["oneOf"]
    assert {"required": ["ad_id"]} in one_of_required
    assert {"required": ["ad_creative_id"]} in one_of_required
    assert {"required": ["creative"]} in one_of_required


def test_get_ad_preview_screenshot_supports_ad_creative_and_generatepreviews_inputs() -> None:
    spec = next(spec for spec in tool_specs() if spec.name == "get_ad_preview_screenshot")

    one_of_required = spec.input_schema["oneOf"]
    assert {"required": ["ad_id"]} in one_of_required
    assert {"required": ["ad_creative_id"]} in one_of_required
    assert {"required": ["creative"]} in one_of_required
