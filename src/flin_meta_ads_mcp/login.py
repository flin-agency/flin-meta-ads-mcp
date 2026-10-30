from __future__ import annotations

import math
import re
import secrets
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from .credentials import Credentials
from .errors import MetaAdsError
from .meta_client import MetaClient

DEFAULT_REDIRECT_URI = "http://localhost:8765/callback"


class LoginError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LoginSettings:
    app_id: str
    app_secret: str = field(repr=False)
    api_version: str = "v21.0"
    redirect_uri: str = DEFAULT_REDIRECT_URI
    config_id: str | None = None

    def validate(self, *, manual: bool) -> None:
        if not re.fullmatch(r"[0-9]+", self.app_id) or not self.app_secret:
            raise LoginError("A numeric Meta App ID and App Secret are required.")
        if not re.fullmatch(r"v[0-9]+\.[0-9]+", self.api_version):
            raise LoginError("Invalid META_GRAPH_API_VERSION; expected e.g. v21.0.")
        if self.config_id and not self.config_id.isdecimal():
            raise LoginError("META_LOGIN_CONFIG_ID must be numeric.")
        uri = urlsplit(self.redirect_uri)
        if uri.query or uri.fragment or uri.username or uri.password or not uri.hostname:
            raise LoginError("Redirect URI must have a host and no query, fragment or credentials.")
        if not uri.path.startswith("/"):
            raise LoginError("Redirect URI must include a callback path, e.g. /callback.")
        if uri.scheme == "http" and uri.hostname in {"localhost", "127.0.0.1"}:
            if not uri.port:
                raise LoginError("Local redirect URI requires an explicit port.")
        elif not (manual and uri.scheme == "https"):
            raise LoginError("Use a local HTTP redirect, or --manual with a registered HTTPS URI.")


def authorization_url(settings: LoginSettings, state: str) -> str:
    params = {
        "client_id": settings.app_id,
        "redirect_uri": settings.redirect_uri,
        "response_type": "code",
        "state": state,
    }
    if settings.config_id:
        params["config_id"] = settings.config_id
    else:
        params["scope"] = "ads_read"
    return f"https://www.facebook.com/{settings.api_version}/dialog/oauth?{urlencode(params)}"


def callback_code(url: str, *, redirect_uri: str, state: str) -> str:
    actual, expected = urlsplit(url), urlsplit(redirect_uri)
    if (actual.scheme, actual.netloc, actual.path) != (
        expected.scheme, expected.netloc, expected.path
    ) or actual.fragment:
        raise LoginError("Callback URL does not match the configured redirect URI.")
    params = parse_qs(actual.query, keep_blank_values=True)
    states = params.get("state", [])
    if len(states) != 1 or not secrets.compare_digest(states[0].encode(), state.encode()):
        raise LoginError("Invalid login state. Use the link from this login attempt.")
    if "error" in params or "error_reason" in params:
        raise LoginError("Meta login was declined or cancelled. Run login again to retry.")
    codes = params.get("code", [])
    if len(codes) != 1 or not codes[0]:
        raise LoginError("Meta did not return an authorization code. Run login again.")
    return codes[0]


class _CallbackServer(HTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(1)
        return connection, address


def receive_code(
    settings: LoginSettings, *, state: str, timeout: float,
    launch: Callable[[], None],
) -> str:
    uri = urlsplit(settings.redirect_uri)
    outcome: list[str | LoginError] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass  # Callback URLs contain authorization codes; never log them.

        def do_GET(self) -> None:
            incoming = urlsplit(self.path)
            status = 400
            message = "Invalid login callback. Return to the terminal."
            if incoming.path == uri.path and not incoming.scheme and not incoming.netloc:
                try:
                    code = callback_code(
                        f"{uri.scheme}://{uri.netloc}{self.path}",
                        redirect_uri=settings.redirect_uri, state=state,
                    )
                except LoginError as exc:
                    # Ignore unsolicited requests; a valid cancellation terminates the attempt.
                    params = parse_qs(incoming.query)
                    if params.get("state") == [state]:
                        outcome.append(exc)
                else:
                    outcome.append(code)
                    status = 200
                    message = "Login response received. Return to the terminal to finish."
            body = message.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

    try:
        server = _CallbackServer(("127.0.0.1", uri.port or 8765), Handler)
    except OSError:
        raise LoginError("Cannot open local callback port. Choose another META_REDIRECT_URI port.") from None
    with server:
        server.timeout = 0.25
        deadline = time.monotonic() + timeout
        launch()
        while not outcome and time.monotonic() < deadline:
            server.handle_request()
    if not outcome:
        raise LoginError("Login timed out. Run flin-meta-ads-mcp login again.")
    if isinstance(outcome[0], LoginError):
        raise outcome[0]
    return outcome[0]


def _token_request(client: httpx.Client, settings: LoginSettings, data: dict[str, str]) -> dict:
    try:
        response = client.post(
            f"https://graph.facebook.com/{settings.api_version}/oauth/access_token",
            data={"client_id": settings.app_id, "client_secret": settings.app_secret, **data},
        )
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise LoginError("Could not contact Meta for token exchange. Retry login.") from None
    if response.status_code != 200 or not isinstance(payload, dict) or payload.get("error"):
        raise LoginError(
            "Meta rejected the token exchange. Check App ID, App Secret and the exact redirect URI."
        )
    if not isinstance(payload.get("access_token"), str) or not payload["access_token"]:
        raise LoginError("Meta returned no access token. Retry login.")
    return payload


def exchange_code(settings: LoginSettings, code: str, client: httpx.Client) -> Credentials:
    short = _token_request(client, settings, {"code": code, "redirect_uri": settings.redirect_uri})
    token = _token_request(client, settings, {
        "grant_type": "fb_exchange_token", "fb_exchange_token": short["access_token"],
    })
    expires_at = None
    if "expires_in" in token:
        try:
            lifetime = float(token["expires_in"])
        except (TypeError, ValueError):
            raise LoginError("Meta returned an invalid token lifetime.") from None
        if not math.isfinite(lifetime) or lifetime <= 0:
            raise LoginError("Meta returned an invalid token lifetime.")
        expires_at = time.time() + lifetime
    return Credentials(
        app_id=settings.app_id, app_secret=settings.app_secret,
        access_token=token["access_token"], api_version=settings.api_version,
        expires_at=expires_at,
    )


def verify_access(credentials: Credentials, client: httpx.Client) -> None:
    meta = MetaClient(
        access_token=credentials.access_token, app_secret=credentials.app_secret,
        api_version=credentials.api_version, timeout_seconds=30, max_retries=0, client=client,
    )
    try:
        permissions = meta.get_json("me/permissions")
        granted = {
            row.get("permission") for row in permissions.get("data", [])
            if isinstance(row, dict) and row.get("status") == "granted"
        }
        if "ads_read" not in granted:
            raise LoginError("Login did not grant ads_read. Enable it in the app and retry login.")
        accounts = meta.get_json("me/adaccounts", params={"fields": "id", "limit": 1})
        if not accounts.get("data"):
            raise LoginError("Login succeeded, but no ad accounts are accessible. Check account access.")
    except (MetaAdsError, httpx.HTTPError, ValueError) as exc:
        if isinstance(exc, LoginError):
            raise
        raise LoginError("Could not verify Meta Ads access. Check app permissions and retry login.") from None


def browser_login(
    settings: LoginSettings, *, manual: bool = False, no_browser: bool = False,
    timeout: float = 180,
) -> Credentials:
    settings.validate(manual=manual)
    if not math.isfinite(timeout) or timeout <= 0:
        raise LoginError("Login timeout must be a positive number of seconds.")
    state = secrets.token_urlsafe(32)
    url = authorization_url(settings, state)

    def launch() -> None:
        print(f"Open this URL to sign in to Meta:\n{url}")
        if not no_browser:
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                pass  # The URL above also works when no browser can be started.

    if manual:
        launch()
        from getpass import getpass
        redirected = getpass("Paste the full redirected URL (input hidden): ")
        code = callback_code(redirected.strip(), redirect_uri=settings.redirect_uri, state=state)
    else:
        code = receive_code(settings, state=state, timeout=timeout, launch=launch)
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        credentials = exchange_code(settings, code, client)
        verify_access(credentials, client)
    return credentials
