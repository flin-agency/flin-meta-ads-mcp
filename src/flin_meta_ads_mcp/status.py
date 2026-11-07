"""Secret-free connection diagnostics; network access is explicitly opt-in."""
from __future__ import annotations

import re
from collections.abc import Mapping

from . import __version__
from .config import MetaAdsSettings, load_config
from .errors import MetaAuthError, MetaPermissionError
from .login import DEFAULT_REDIRECT_URI, LoginSettings
from .meta_client import MetaClient


def connection_status(
    env: Mapping[str, str], *, check_live: bool = False,
    settings: MetaAdsSettings | None = None,
) -> dict[str, str]:
    if not isinstance(check_live, bool):
        raise TypeError("check_live must be a boolean")
    result = {
        "server_version": __version__,
        "configuration_status": "incomplete",
        "auth_status": "unauthenticated",
        "live_access": "not_checked",
        "next_step": "Enter Meta App ID and App Secret from your administrator/password manager "
                     "in extension settings, or configure an access token with ads_read.",
    }
    # These values are supplied by the desktop launcher, never inferred from PyPI.
    bundle = env.get("FLIN_META_DESKTOP_VERSION", "")
    runtime = env.get("FLIN_META_DESKTOP_RUNTIME", "")
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", bundle) and runtime in {"bundled", "cached"}:
        result.update(extension_version=bundle, runtime_source=runtime)
    try:
        resolved = settings or load_config(env)
    except ValueError:
        try:
            # Validate connection options independently of the missing/expired token.
            load_config(dict(env, META_ACCESS_TOKEN="diagnostic-placeholder"))
            LoginSettings(
                app_id=env.get("META_APP_ID", ""), app_secret=env.get("META_APP_SECRET", ""),
                api_version=env.get("META_GRAPH_API_VERSION", "v21.0"),
                redirect_uri=env.get("META_REDIRECT_URI", DEFAULT_REDIRECT_URI),
                config_id=env.get("META_LOGIN_CONFIG_ID") or None,
            ).validate(manual=False)
        except ValueError:
            pass
        else:
            result.update(configuration_status="configured", next_step=
                          "Call start_meta_login, open its login link, then check connection_status.")
        if env.get("META_ACCESS_TOKEN"):
            result.update(configuration_status="incomplete", auth_status="unknown", next_step=
                          "Check the token and connection settings in the extension configuration.")
        return result
    result.update(configuration_status="configured", auth_status="unknown", next_step=
                  "Call connection_status with check_live=true to verify Meta access.")
    if not check_live:
        return result
    try:
        # One bounded read; do not fetch insights, follow paging, or return account data.
        with MetaClient(access_token=resolved.access_token, app_secret=resolved.app_secret,
                        api_version=resolved.api_version, timeout_seconds=10, max_retries=0) as client:
            payload = client.get_json("me/adaccounts", {"fields": "id", "limit": 1})
        if not isinstance(payload.get("data"), list):
            raise TypeError("Invalid account response")
    except MetaAuthError:
        result.update(auth_status="unauthenticated", live_access="error", next_step=
                      "Sign in again with start_meta_login, or replace the configured access token.")
    except MetaPermissionError:
        result.update(live_access="error", next_step=
                      "Ask your administrator to check ads_read and ad account permissions.")
    except Exception:  # noqa: BLE001 - upstream errors may contain secrets/customer data
        result.update(live_access="error", next_step=
                      "Meta access could not be verified. Check your network and retry the live check.")
    else:
        result.update(auth_status="authenticated", live_access="ok", next_step=
                      "Call list_ad_accounts and select the intended account." if payload["data"] else
                      "Meta responded, but no ad account is accessible. Ask your administrator for access.")
    return result
