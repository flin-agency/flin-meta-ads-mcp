from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from flin_meta_ads_mcp.config import MetaAdsSettings
from flin_meta_ads_mcp.errors import AccountSelectionRequired
from flin_meta_ads_mcp.tools.ads import list_ads
from flin_meta_ads_mcp.tools.campaigns import get_campaign, list_campaigns
from flin_meta_ads_mcp.tools.images import get_ad_image, list_ad_images
from flin_meta_ads_mcp.tools.insights import get_insights
from flin_meta_ads_mcp.tools.previews import get_ad_preview, get_ad_preview_screenshot
import flin_meta_ads_mcp.tools.previews as preview_tools


@dataclass
class DummyClient:
    calls: list[tuple[str, dict]]
    ad_accounts: list[str] = field(default_factory=lambda: ["act_111"])
    last_request_id: str | None = None

    def get_json(self, path: str, params: dict) -> dict:
        self.calls.append((path, dict(params)))
        if path == "me/adaccounts":
            return {"data": [{"id": account_id} for account_id in self.ad_accounts]}
        return {"data": []}


def test_list_campaigns_prefers_per_call_ad_account_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = list_campaigns(client=client, settings=settings, arguments={"ad_account_id": "act_222", "limit": 10})

    assert result["ok"] is True
    assert client.calls == [("act_222/campaigns", {"fields": "id,name,status,effective_status,objective", "limit": 10})]


def test_list_ads_auto_resolves_single_account_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = list_ads(client=client, settings=settings, arguments={})

    assert result["ok"] is True
    assert client.calls[0][0] == "me/adaccounts"
    assert client.calls[1][0] == "act_111/ads"


def test_list_ads_uses_client_default_account_id_without_discovery_call() -> None:
    client = DummyClient(calls=[], ad_accounts=["act_111", "act_222"])
    setattr(client, "_default_ad_account_id", "act_2054139041534164")
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = list_ads(client=client, settings=settings, arguments={})

    assert result["ok"] is True
    assert client.calls == [
        ("act_2054139041534164/ads", {"fields": "id,name,status,effective_status,adset_id,campaign_id", "limit": 50})
    ]


def test_get_insights_passes_entity_filters() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
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
    path, params = client.calls[1]
    assert path == "act_111/insights"
    assert params["level"] == "campaign"
    assert params["date_preset"] == "last_7d"
    assert "filtering" in params


def test_list_ads_requires_ad_account_id_when_multiple_accounts_exist() -> None:
    client = DummyClient(calls=[], ad_accounts=["act_111", "act_222"])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(AccountSelectionRequired) as exc_info:
        list_ads(client=client, settings=settings, arguments={})
    assert [choice["ad_account_id"] for choice in exc_info.value.choices] == ["act_111", "act_222"]


def test_get_campaign_rejects_non_numeric_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="numeric"):
        get_campaign(client=client, settings=settings, arguments={"id": "act_111/campaigns"})


def test_list_campaigns_rejects_invalid_ad_account_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="ad_account_id"):
        list_campaigns(client=client, settings=settings, arguments={"ad_account_id": "act_foo"})


def test_list_campaigns_rejects_unknown_fields() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="Unsupported fields"):
        list_campaigns(
            client=client,
            settings=settings,
            arguments={"ad_account_id": "act_222", "fields": ["id", "not_a_real_field"]},
        )


def test_get_insights_rejects_unknown_fields() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="Unsupported fields"):
        get_insights(
            client=client,
            settings=settings,
            arguments={"level": "campaign", "fields": ["impressions", "not_a_real_metric"]},
        )


def test_get_ad_preview_rejects_non_numeric_ad_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="ad_id"):
        get_ad_preview(client=client, settings=settings, arguments={"ad_id": "../bad"})


def test_get_ad_preview_returns_extracted_preview_url() -> None:
    class PreviewClient(DummyClient):
        def get_json(self, path: str, params: dict) -> dict:
            self.calls.append((path, dict(params)))
            return {
                "data": [
                    {
                        "body": '<iframe src="https://business.facebook.com/ads/api/preview_iframe.php?d=AQX&amp;t=AQY" '
                        'width="335" height="450"></iframe>'
                    }
                ]
            }

    client = PreviewClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = get_ad_preview(client=client, settings=settings, arguments={"ad_id": "120242247667500564"})

    assert result["ok"] is True
    assert client.calls == [("120242247667500564/previews", {"ad_format": "DESKTOP_FEED_STANDARD"})]
    assert result["data"][0]["preview_url"] == "https://business.facebook.com/ads/api/preview_iframe.php?d=AQX&t=AQY"


def test_get_ad_preview_supports_ad_creative_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = get_ad_preview(
        client=client,
        settings=settings,
        arguments={"ad_creative_id": "120242247667500564", "ad_format": "MOBILE_FEED_STANDARD"},
    )

    assert result["ok"] is True
    assert client.calls == [("120242247667500564/previews", {"ad_format": "MOBILE_FEED_STANDARD"})]


def test_get_ad_preview_supports_generatepreviews_with_creative_spec() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = get_ad_preview(
        client=client,
        settings=settings,
        arguments={
            "ad_account_id": "act_222",
            "ad_format": "MOBILE_FEED_STANDARD",
            "creative": {"object_story_spec": {"page_id": "123"}},
        },
    )

    assert result["ok"] is True
    assert client.calls == [
        (
            "act_222/generatepreviews",
            {"ad_format": "MOBILE_FEED_STANDARD", "creative": '{"object_story_spec":{"page_id":"123"}}'},
        )
    ]


def test_get_ad_preview_rejects_multiple_preview_sources() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="Exactly one"):
        get_ad_preview(
            client=client,
            settings=settings,
            arguments={"ad_id": "120242247667500564", "ad_creative_id": "120242247667500565"},
        )


def test_get_ad_preview_screenshot_returns_base64_and_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_capture(*, preview_url: str, viewport_width: int, viewport_height: int, timeout_ms: int) -> str:
        assert preview_url == "https://business.facebook.com/ads/api/preview_iframe.php?d=AQX&t=AQY"
        assert viewport_width == 390
        assert viewport_height == 844
        assert timeout_ms == 30000
        return "ZmFrZV9wbmc="

    monkeypatch.setattr(preview_tools, "_capture_preview_screenshot", fake_capture)

    class PreviewClient(DummyClient):
        def get_json(self, path: str, params: dict) -> dict:
            self.calls.append((path, dict(params)))
            return {
                "data": [
                    {
                        "body": '<iframe src="https://business.facebook.com/ads/api/preview_iframe.php?d=AQX&amp;t=AQY"></iframe>'
                    }
                ]
            }

    client = PreviewClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = get_ad_preview_screenshot(
        client=client,
        settings=settings,
        arguments={"ad_id": "120242247667500564", "ad_format": "MOBILE_FEED_STANDARD"},
    )

    assert result["ok"] is True
    assert client.calls == [("120242247667500564/previews", {"ad_format": "MOBILE_FEED_STANDARD"})]
    assert result["data"]["preview_url"] == "https://business.facebook.com/ads/api/preview_iframe.php?d=AQX&t=AQY"
    assert result["data"]["mime_type"] == "image/png"
    assert result["data"]["image_base64"] == "ZmFrZV9wbmc="
    assert result["data"]["viewport"] == {"width": 390, "height": 844}


def test_get_ad_preview_screenshot_rejects_when_preview_url_is_missing() -> None:
    class PreviewClient(DummyClient):
        def get_json(self, path: str, params: dict) -> dict:
            self.calls.append((path, dict(params)))
            return {"data": [{"body": "<div>no iframe here</div>"}]}

    client = PreviewClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="preview_url"):
        get_ad_preview_screenshot(
            client=client,
            settings=settings,
            arguments={"ad_id": "120242247667500564"},
        )


def test_list_ad_images_prefers_per_call_ad_account_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    result = list_ad_images(client=client, settings=settings, arguments={"ad_account_id": "act_222", "limit": 10})

    assert result["ok"] is True
    assert client.calls == [
        (
            "act_222/adimages",
            {
                "fields": "id,hash,name,width,height,url,url_128,permalink_url,status,created_time,updated_time",
                "limit": 10,
            },
        )
    ]


def test_get_ad_image_rejects_non_numeric_id() -> None:
    client = DummyClient(calls=[])
    settings = MetaAdsSettings(
        access_token="token",
        api_version="v21.0",
        timeout_seconds=10,
        max_retries=1,
    )

    with pytest.raises(ValueError, match="numeric"):
        get_ad_image(client=client, settings=settings, arguments={"id": "act_111/adimages"})
