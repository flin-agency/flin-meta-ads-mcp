from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Mapping

ACCOUNT_ID_PATTERN = re.compile(r"^(?:act_)?([0-9]+)$")


@dataclass(frozen=True, slots=True)
class MetaAdsSettings:
    access_token: str
    api_version: str
    timeout_seconds: float
    max_retries: int
    default_ad_account_id: str | None = None


def load_config(env: Mapping[str, str] | None = None) -> MetaAdsSettings:
    source = os.environ if env is None else env
    access_token = source.get("META_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("META_ACCESS_TOKEN is required")

    default_ad_account_id = _normalize_optional_account_id(source.get("META_DEFAULT_AD_ACCOUNT_ID"))

    return MetaAdsSettings(
        access_token=access_token,
        api_version=source.get("META_GRAPH_API_VERSION", "v21.0"),
        timeout_seconds=float(source.get("META_TIMEOUT_SECONDS", "30")),
        max_retries=int(source.get("META_MAX_RETRIES", "3")),
        default_ad_account_id=default_ad_account_id,
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
