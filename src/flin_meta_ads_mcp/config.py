from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True, slots=True)
class MetaAdsSettings:
    access_token: str
    default_ad_account_id: str | None
    api_version: str
    timeout_seconds: float
    max_retries: int


def load_config(env: Mapping[str, str] | None = None) -> MetaAdsSettings:
    source = os.environ if env is None else env
    access_token = source.get("META_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("META_ACCESS_TOKEN is required")

    return MetaAdsSettings(
        access_token=access_token,
        default_ad_account_id=_normalize_account_id(source.get("META_AD_ACCOUNT_ID")),
        api_version=source.get("META_GRAPH_API_VERSION", "v21.0"),
        timeout_seconds=float(source.get("META_TIMEOUT_SECONDS", "30")),
        max_retries=int(source.get("META_MAX_RETRIES", "3")),
    )


def _normalize_account_id(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value if value.startswith("act_") else f"act_{value}"
