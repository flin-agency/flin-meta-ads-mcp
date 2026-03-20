from __future__ import annotations

from dataclasses import dataclass

from flin_meta_ads_mcp.config import MetaAdsSettings
from flin_meta_ads_mcp.tools.ads import list_ads
from flin_meta_ads_mcp.tools.campaigns import list_campaigns
from flin_meta_ads_mcp.tools.insights import get_insights


@dataclass
class DummyClient:
    calls: list[tuple[str, dict]]

    def get_json(self, path: str, params: dict) -> dict:
        self.calls.append((path, dict(params)))
        return {"data": []}


def test_list_campaigns_prefers_per_call_ad_account_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        default_ad_account_id="act_111",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = list_campaigns(client=client, settings=settings, arguments={"ad_account_id": "act_222", "limit": 10})

    assert result["ok"] is True
    assert client.calls == [("act_222/campaigns", {"fields": "id,name,status,effective_status,objective", "limit": 10})]


def test_list_ads_uses_default_account_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        default_ad_account_id="act_111",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = list_ads(client=client, settings=settings, arguments={})

    assert result["ok"] is True
    assert client.calls[0][0] == "act_111/ads"


def test_get_insights_passes_entity_filters() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        default_ad_account_id="act_111",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = get_insights(
        client=client,
        settings=settings,
        arguments={"level": "campaign", "entity_ids": ["123", "456"], "date_preset": "last_7d"},
    )

    assert result["ok"] is True
    path, params = client.calls[0]
    assert path == "act_111/insights"
    assert params["level"] == "campaign"
    assert params["date_preset"] == "last_7d"
    assert "filtering" in params
