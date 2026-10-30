from __future__ import annotations

from http.client import HTTPConnection
import json
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import respx

from flin_meta_ads_mcp import cli, login
from flin_meta_ads_mcp.config import load_config
from flin_meta_ads_mcp.credentials import Credentials, load_credentials, save_credentials


@pytest.fixture
def auth_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "auth" / "credentials.json"
    monkeypatch.setenv("META_AUTH_FILE", str(path))
    for key in ("META_ACCESS_TOKEN", "META_APP_ID", "META_APP_SECRET", "META_LOGIN_CONFIG_ID",
                "META_REDIRECT_URI", "META_GRAPH_API_VERSION"):
        monkeypatch.delenv(key, raising=False)
    return path


def test_authorization_url_contains_only_public_parameters() -> None:
    settings = login.LoginSettings(app_id="123", app_secret="private-secret")
    query = parse_qs(urlsplit(login.authorization_url(settings, "csrf-state")).query)
    assert query == {
        "client_id": ["123"], "redirect_uri": [login.DEFAULT_REDIRECT_URI],
        "response_type": ["code"], "state": ["csrf-state"], "scope": ["ads_read"],
    }
    business = login.LoginSettings(app_id="123", app_secret="private-secret", config_id="456")
    query = parse_qs(urlsplit(login.authorization_url(business, "csrf-state")).query)
    assert query["config_id"] == ["456"]
    assert "scope" not in query


@pytest.mark.parametrize("suffix", [
    "?code=secret-code", "?state=wrong&code=secret-code",
    "?state=expected&state=expected&code=secret-code",
    "?state=expected&code=first&code=second", "?state=expected&code=",
    "?state=expected&error=access_denied", "?state=expected&code=secret-code#fragment",
])
def test_callback_rejects_invalid_or_cancelled_login_without_echoing_code(suffix: str) -> None:
    with pytest.raises(login.LoginError) as error:
        login.callback_code(
            login.DEFAULT_REDIRECT_URI + suffix,
            redirect_uri=login.DEFAULT_REDIRECT_URI, state="expected",
        )
    assert "secret-code" not in str(error.value)


def test_callback_checks_destination_and_accepts_valid_code() -> None:
    with pytest.raises(login.LoginError, match="does not match"):
        login.callback_code(
            "https://other.example/callback?state=expected&code=code",
            redirect_uri=login.DEFAULT_REDIRECT_URI, state="expected",
        )
    assert login.callback_code(
        login.DEFAULT_REDIRECT_URI + "?state=expected&code=valid-code",
        redirect_uri=login.DEFAULT_REDIRECT_URI, state="expected",
    ) == "valid-code"


@pytest.mark.parametrize("uri,manual", [
    ("http://remote.example/callback", False),
    ("http://remote.example/callback", True),
    ("https://remote.example/callback", False),
    ("http://localhost/callback", False),
    ("http://localhost:8765", False),
    ("http://localhost:8765/callback?extra=1", False),
    ("https://user:pass@remote.example/callback", True),
])
def test_rejects_unsafe_or_unsupported_redirects(uri: str, manual: bool) -> None:
    with pytest.raises(login.LoginError):
        login.LoginSettings(app_id="123", app_secret="secret", redirect_uri=uri).validate(manual=manual)


def test_local_callback_ignores_wrong_state_and_accepts_valid_code(monkeypatch, capsys) -> None:
    original_server = login._CallbackServer
    servers = []
    responses = []
    workers = []

    def ephemeral_server(address, handler):
        assert address[0] == "127.0.0.1"
        server = original_server(("127.0.0.1", 0), handler)
        servers.append(server)
        return server

    def send_callbacks():
        for path in (
            "/favicon.ico", "/callback?state=wrong&code=unsolicited",
            "/callback?state=expected&code=secret-code",
        ):
            connection = HTTPConnection("127.0.0.1", servers[0].server_port, timeout=3)
            try:
                connection.request("GET", path)
                response = connection.getresponse()
                responses.append((response.status, response.read()))
                assert response.getheader("Cache-Control") == "no-store"
            finally:
                connection.close()

    def launch():
        worker = threading.Thread(target=send_callbacks)
        workers.append(worker)
        worker.start()

    monkeypatch.setattr(login, "_CallbackServer", ephemeral_server)
    result = login.receive_code(
        login.LoginSettings(app_id="123", app_secret="secret"),
        state="expected", timeout=5, launch=launch,
    )
    for worker in workers:
        worker.join(timeout=5)
        assert not worker.is_alive()
    assert result == "secret-code"
    assert [status for status, _ in responses] == [400, 400, 200]
    assert all(b"secret-code" not in body for _, body in responses)
    assert "secret-code" not in capsys.readouterr().err


def test_callback_timeout_closes_listener(monkeypatch) -> None:
    original_server = login._CallbackServer
    servers = []

    def ephemeral_server(address, handler):
        server = original_server(("127.0.0.1", 0), handler)
        servers.append(server)
        return server

    monkeypatch.setattr(login, "_CallbackServer", ephemeral_server)
    with pytest.raises(login.LoginError, match="timed out"):
        login.receive_code(
            login.LoginSettings(app_id="123", app_secret="secret"),
            state="expected", timeout=0.01, launch=lambda: None,
        )
    assert servers[0].socket.fileno() == -1


def mock_meta_success():
    tokens = respx.post("https://graph.facebook.com/v21.0/oauth/access_token")
    tokens.side_effect = [
        httpx.Response(200, json={"access_token": "short-secret", "expires_in": 3600}),
        httpx.Response(200, json={"access_token": "long-secret", "expires_in": 5184000}),
    ]
    permissions = respx.get("https://graph.facebook.com/v21.0/me/permissions").respond(
        200, json={"data": [{"permission": "ads_read", "status": "granted"}]},
    )
    accounts = respx.get("https://graph.facebook.com/v21.0/me/adaccounts").respond(
        200, json={"data": [{"id": "act_123"}]},
    )
    return tokens, permissions, accounts


@respx.mock
def test_cli_login_exchanges_verifies_saves_and_server_loads(auth_path, monkeypatch, capsys) -> None:
    tokens, permissions, accounts = mock_meta_success()
    monkeypatch.setattr(cli, "getpass", lambda _: "private-secret")
    monkeypatch.setattr(login.secrets, "token_urlsafe", lambda _: "expected")
    monkeypatch.setattr("getpass.getpass", lambda _: (
        "https://example.com/callback?code=secret-code&state=expected"
    ))
    monkeypatch.setattr(login.webbrowser, "open", lambda _: pytest.fail("--no-browser ignored"))
    cli.main([
        "login", "--app-id", "123", "--manual", "--no-browser",
        "--redirect-uri", "https://example.com/callback",
    ])

    first = parse_qs(tokens.calls[0].request.content.decode())
    assert first == {
        "client_id": ["123"], "client_secret": ["private-secret"],
        "code": ["secret-code"], "redirect_uri": ["https://example.com/callback"],
    }
    second = parse_qs(tokens.calls[1].request.content.decode())
    assert second["grant_type"] == ["fb_exchange_token"]
    assert second["fb_exchange_token"] == ["short-secret"]
    for route in (tokens, permissions, accounts):
        for call in route.calls:
            assert "private-secret" not in str(call.request.url)
            assert "long-secret" not in str(call.request.url)
    assert accounts.calls[0].request.headers["Authorization"] == "Bearer long-secret"
    assert "appsecret_proof" in accounts.calls[0].request.url.params

    assert auth_path.stat().st_mode & 0o777 == 0o600
    assert auth_path.parent.stat().st_mode & 0o777 == 0o700
    saved = load_credentials(auth_path)
    assert saved is not None and saved.expires_at > time.time() + 5000000
    settings = load_config()
    assert settings.access_token == "long-secret"
    assert settings.app_secret == "private-secret"
    output = capsys.readouterr()
    assert "Login successful" in output.out
    for secret in ("private-secret", "long-secret", "short-secret", "secret-code"):
        assert secret not in output.out + output.err + repr(settings) + repr(saved)


@respx.mock
@pytest.mark.parametrize("failure", ["exchange", "permission", "accounts"])
def test_failed_login_preserves_previous_credentials(auth_path, monkeypatch, capsys, failure) -> None:
    previous = Credentials("123", "old-secret", "old-token", "v21.0")
    save_credentials(auth_path, previous)
    original = auth_path.read_bytes()
    tokens, permissions, accounts = mock_meta_success()
    if failure == "exchange":
        tokens.side_effect = None
        tokens.respond(400, json={"error": {"message": "private-secret secret-code"}})
    elif failure == "permission":
        permissions.respond(200, json={"data": [{"permission": "ads_read", "status": "declined"}]})
    else:
        accounts.respond(200, json={"data": []})
    monkeypatch.setenv("META_APP_SECRET", "private-secret")
    monkeypatch.setattr(login, "receive_code", lambda *args, **kwargs: "secret-code")
    with pytest.raises(SystemExit) as error:
        cli.main(["login", "--app-id", "123"])
    assert error.value.code == 1
    assert auth_path.read_bytes() == original
    output = capsys.readouterr()
    assert "Login successful" not in output.out
    assert "private-secret" not in output.err
    assert "secret-code" not in output.err


def test_saved_credentials_expiry_and_manual_token_precedence(auth_path, monkeypatch) -> None:
    save_credentials(auth_path, Credentials("123", "secret", "expired-token", "v21.0", 1))
    with pytest.raises(ValueError, match="expired"):
        load_config()
    monkeypatch.setenv("META_ACCESS_TOKEN", "manual-token")
    settings = load_config()
    assert settings.access_token == "manual-token"
    assert settings.app_secret is None  # Do not combine credentials from unrelated apps.


@pytest.mark.parametrize("override", [{"META_APP_ID": "456"}, {"META_APP_SECRET": "different"}])
def test_saved_login_rejects_mismatched_app(auth_path, monkeypatch, override) -> None:
    save_credentials(auth_path, Credentials("123", "secret", "token", "v21.0"))
    for key, value in override.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="login again"):
        load_config()


@pytest.mark.parametrize("payload", ["invalid-json", "[]", '{"access_token": "secret"}'])
def test_invalid_saved_credentials_have_actionable_errors(auth_path, payload) -> None:
    auth_path.parent.mkdir()
    auth_path.write_text(payload)
    with pytest.raises(ValueError, match="login again"):
        load_config()


def test_atomic_write_failure_preserves_previous_login(auth_path, monkeypatch) -> None:
    previous = Credentials("123", "old-secret", "old-token", "v21.0")
    save_credentials(auth_path, previous)

    def fail_replace(*args):
        raise OSError("write failure")

    monkeypatch.setattr("flin_meta_ads_mcp.credentials.os.replace", fail_replace)
    with pytest.raises(OSError):
        save_credentials(auth_path, Credentials("123", "new-secret", "new-token", "v21.0"))
    assert json.loads(auth_path.read_text())["access_token"] == "old-token"
    assert list(auth_path.parent.iterdir()) == [auth_path]


def test_cli_without_subcommand_still_starts_mcp(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("flin_meta_ads_mcp.server.main", lambda: calls.append(True))
    cli.main([])
    assert calls == [True]


def test_cli_version_does_not_require_login(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "__version__", "0.1.11")
    with pytest.raises(SystemExit) as error:
        cli.main(["--version"])
    assert error.value.code == 0
    assert "0.1.11" in capsys.readouterr().out
