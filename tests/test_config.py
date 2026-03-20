from __future__ import annotations

import pytest

from flin_meta_ads_mcp.config import load_config


def test_load_config_requires_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)

    with pytest.raises(ValueError, match="META_ACCESS_TOKEN is required"):
        load_config()


def test_load_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "token")
    monkeypatch.delenv("META_GRAPH_API_VERSION", raising=False)
    monkeypatch.delenv("META_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("META_MAX_RETRIES", raising=False)

    settings = load_config()

    assert settings.access_token == "token"
    assert settings.api_version == "v21.0"
    assert settings.timeout_seconds == 30.0
    assert settings.max_retries == 3
