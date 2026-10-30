from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from typing import Mapping

from .credentials import credentials_path, load_credentials

ACCOUNT_ID_PATTERN = re.compile(r"^(?:act_)?([0-9]+)$")


@dataclass(frozen=True, slots=True)
class MetaAdsSettings:
    access_token: str = field(repr=False)
    api_version: str
    timeout_seconds: float
    max_retries: int
    default_ad_account_id: str | None = None
    app_secret: str | None = field(default=None, repr=False)


def load_config(env: Mapping[str, str] | None = None) -> MetaAdsSettings:
    source = os.environ if env is None else env
    access_token = source.get("META_ACCESS_TOKEN")
    saved = None if access_token else load_credentials(credentials_path(source))
    if saved:
        if source.get("META_APP_ID") and source["META_APP_ID"] != saved.app_id:
            raise ValueError("Saved login belongs to another app. Run flin-meta-ads-mcp login again.")
        access_token = saved.access_token
    if not access_token:
        raise ValueError("META_ACCESS_TOKEN is required, or run flin-meta-ads-mcp login first")

    app_secret = source.get("META_APP_SECRET", "").strip() or None
    if saved:
        if app_secret and app_secret != saved.app_secret:
            raise ValueError("App Secret differs from saved login. Run flin-meta-ads-mcp login again.")
        app_secret = saved.app_secret

    default_ad_account_id = _normalize_optional_account_id(source.get("META_DEFAULT_AD_ACCOUNT_ID"))

    return MetaAdsSettings(
        access_token=access_token,
        api_version=source.get("META_GRAPH_API_VERSION", saved.api_version if saved else "v21.0"),
        timeout_seconds=float(source.get("META_TIMEOUT_SECONDS", "30")),
        max_retries=int(source.get("META_MAX_RETRIES", "3")),
        default_ad_account_id=default_ad_account_id,
        app_secret=app_secret,
    )


def _normalize_optional_account_id(value: str | None) -> str | None:
    if value is None:
        return None
    clean_value = value.strip()
    if not clean_value:
        return None
    match = ACCOUNT_ID_PATTERN.fullmatch(clean_value)
    if not match:
        raise ValueError("META_DEFAULT_AD_ACCOUNT_ID must be numeric, with optional act_ prefix")
    return f"act_{match.group(1)}"
