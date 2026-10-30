from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from typing import Any

from .config import load_config
from .credentials import credentials_path, save_credentials
from .login import DEFAULT_REDIRECT_URI, LoginError, LoginSettings, browser_login


class AuthSession:
    """Keep MCP responsive while the user completes a local browser login."""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self.env = dict(os.environ if env is None else env)
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._result: dict[str, Any] = {}

    def status(self) -> dict[str, Any]:
        with self._lock:
            result = dict(self._result)
        if result.get("status") == "pending":
            return result
        try:
            load_config(self.env)
        except ValueError:
            return result if result.get("status") == "login_failed" else self.required()
        return {
            "ok": True, "status": "ready",
            "message": "Credentials are configured. You can now call the Meta Ads tools.",
        }

    def required(self) -> dict[str, Any]:
        missing = [key for key in ("META_APP_ID", "META_APP_SECRET") if not self.env.get(key)]
        return {
            "ok": False, "status": "authentication_required",
            "message": (
                "Sign in with start_meta_login, open the returned login_url, then call "
                "get_meta_auth_status. No access token needs to be copied into the configuration. "
                "The public App ID can be passed as app_id; put the App Secret in META_APP_SECRET, "
                "never in chat."
            ),
            "missing_configuration": missing,
            "next_tool": "start_meta_login",
        }

    def start(self, app_id: str | None = None) -> dict[str, Any]:
        if app_id is not None and (not isinstance(app_id, str) or not app_id.isascii() or not app_id.isdigit()):
            raise LoginError("app_id must be a numeric Meta App ID.")
        with self._lock:
            if self._thread and self._thread.is_alive():
                return dict(self._result)
            if self._cancel.is_set():
                raise LoginError("Server is shutting down. Restart the MCP client to sign in.")
            if app_id:
                self.env["META_APP_ID"] = app_id
            if not self.env.get("META_APP_ID") or not self.env.get("META_APP_SECRET"):
                return self.required()
            if self.env.get("META_ACCESS_TOKEN"):
                return {
                    "ok": False, "status": "configuration_required",
                    "message": "Remove META_ACCESS_TOKEN from the MCP configuration and restart before browser login.",
                }
            settings = LoginSettings(
                app_id=self.env["META_APP_ID"].strip(),
                app_secret=self.env["META_APP_SECRET"].strip(),
                api_version=self.env.get("META_GRAPH_API_VERSION", "v21.0"),
                redirect_uri=self.env.get("META_REDIRECT_URI", DEFAULT_REDIRECT_URI),
                config_id=self.env.get("META_LOGIN_CONFIG_ID") or None,
            )
            settings.validate(manual=False)
            self._ready.clear()
            self._result = {"ok": True, "status": "pending", "message": "Preparing Meta login."}
            self._thread = threading.Thread(target=self._login, args=(settings,), daemon=True)
            self._thread.start()
        self._ready.wait(timeout=5)
        with self._lock:
            return dict(self._result)

    def _login(self, settings: LoginSettings) -> None:
        def announce(url: str) -> None:
            with self._lock:
                self._result = {
                    "ok": True, "status": "pending", "login_url": url,
                    "message": (
                        "Open login_url in your browser and approve Meta access within 3 minutes. "
                        "Then call get_meta_auth_status. The server stays connected during login."
                    ),
                }
            self._ready.set()

        result: dict[str, Any] = {
            "ok": False, "status": "login_failed",
            "message": "Login could not be completed. Retry start_meta_login.",
        }
        try:
            credentials = browser_login(
                settings, no_browser=True, on_authorization_url=announce, cancel=self._cancel,
            )
            if self._cancel.is_set():
                return
            save_credentials(credentials_path(self.env), credentials)
            result = {"ok": True, "status": "ready", "message": "Login completed. Meta Ads tools are ready."}
        except LoginError as exc:
            result = {"ok": False, "status": "login_failed", "message": str(exc)}
        except OSError:
            result = {
                "ok": False, "status": "login_failed",
                "message": "Could not save login. Check META_AUTH_FILE permissions and retry.",
            }
        finally:
            with self._lock:
                self._result = result
            self._ready.set()

    def close(self) -> None:
        self._cancel.set()
        if self._thread:
            self._thread.join(timeout=2)
