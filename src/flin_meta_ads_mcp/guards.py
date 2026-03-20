from __future__ import annotations


READ_ONLY_TOOL_NAMES = {
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
}


def assert_read_only_tool(name: str) -> None:
    if name not in READ_ONLY_TOOL_NAMES:
        raise PermissionError("Tool is not allowed in strict read-only mode")

