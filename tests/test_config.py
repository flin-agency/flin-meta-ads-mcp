from __future__ import annotations

import pytest

from flin_meta_ads_mcp.config import load_config


@pytest.fixture(autouse=True)
def isolate_saved_login(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("flin_meta_ads_mcp.credentials.Path.home", lambda: tmp_path)
    monkeypatch.setenv("META_AUTH_FILE", str(tmp_path / "credentials.json"))


def test_load_config_requires_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)

    with pytest.raises(ValueError, match="META_ACCESS_TOKEN is required"):
        load_config()


def test_load_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "token")
    monkeypatch.delenv("META_GRAPH_API_VERSION", raising=False)
    monkeypatch.delenv("META_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("META_MAX_RETRIES", raising=False)
    monkeypatch.delenv("META_DEFAULT_AD_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("META_APP_SECRET", raising=False)

    settings = load_config()

    assert settings.access_token == "token"
    assert settings.api_version == "v21.0"
    assert settings.timeout_seconds == 30.0
    assert settings.max_retries == 3
    assert settings.default_ad_account_id is None
    assert settings.app_secret is None


@pytest.mark.parametrize("value", ["", "   ", "\n"])
def test_load_config_treats_blank_app_secret_as_unset(value: str) -> None:
    settings = load_config({"META_ACCESS_TOKEN": "token", "META_APP_SECRET": value})

    assert settings.app_secret is None


def test_load_config_reads_app_secret_without_exposing_credentials_in_repr() -> None:
    settings = load_config({
        "META_ACCESS_TOKEN": "private-token",
        "META_APP_SECRET": "  private-secret\n",
    })

    assert settings.app_secret == "private-secret"
    assert "private-token" not in repr(settings)
    assert "private-secret" not in repr(settings)


def test_app_secret_does_not_replace_access_token() -> None:
    with pytest.raises(ValueError, match="META_ACCESS_TOKEN is required"):
        load_config({"META_APP_SECRET": "secret"})


def test_load_config_normalizes_default_ad_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "token")
    monkeypatch.setenv("META_DEFAULT_AD_ACCOUNT_ID", "2054139041534164")

    settings = load_config()

    assert settings.default_ad_account_id == "act_2054139041534164"


def test_load_config_rejects_invalid_default_ad_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "token")
    monkeypatch.setenv("META_DEFAULT_AD_ACCOUNT_ID", "act_not_valid")

    with pytest.raises(ValueError, match="META_DEFAULT_AD_ACCOUNT_ID"):
        load_config()
