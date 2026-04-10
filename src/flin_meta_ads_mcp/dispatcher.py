from __future__ import annotations

from typing import Any, Callable

from .config import MetaAdsSettings
from .guards import assert_read_only_tool
from .meta_client import MetaClient
from .tools.accounts import get_ad_account, list_ad_accounts
from .tools.ads import get_ad, list_ads
from .tools.adsets import get_adset, list_adsets
from .tools.campaigns import get_campaign, list_campaigns
from .tools.creatives import get_ad_creative, list_ad_creatives
from .tools.images import get_ad_image, list_ad_images
from .tools.insights import get_insights
from .tools.previews import get_ad_preview, get_ad_preview_screenshot

ToolHandler = Callable[[MetaClient, MetaAdsSettings, dict[str, Any]], dict[str, Any]]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "list_ad_accounts": lambda client, settings, arguments: list_ad_accounts(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_ad_account": lambda client, settings, arguments: get_ad_account(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "list_campaigns": lambda client, settings, arguments: list_campaigns(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_campaign": lambda client, settings, arguments: get_campaign(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "list_adsets": lambda client, settings, arguments: list_adsets(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_adset": lambda client, settings, arguments: get_adset(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "list_ads": lambda client, settings, arguments: list_ads(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_ad": lambda client, settings, arguments: get_ad(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "list_ad_images": lambda client, settings, arguments: list_ad_images(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_ad_image": lambda client, settings, arguments: get_ad_image(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "list_ad_creatives": lambda client, settings, arguments: list_ad_creatives(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_ad_creative": lambda client, settings, arguments: get_ad_creative(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_ad_preview": lambda client, settings, arguments: get_ad_preview(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_ad_preview_screenshot": lambda client, settings, arguments: get_ad_preview_screenshot(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
    "get_insights": lambda client, settings, arguments: get_insights(
        client=client,
        settings=settings,
        arguments=arguments,
    ),
}


def dispatch_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    settings: MetaAdsSettings,
    client: MetaClient,
) -> dict[str, Any]:
    assert_read_only_tool(name)
    try:
        handler = TOOL_HANDLERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown tool: {name}") from exc
    return handler(client, settings, arguments)
