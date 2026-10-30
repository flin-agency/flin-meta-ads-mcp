from __future__ import annotations

import threading
from pathlib import Path

import pytest

from flin_meta_ads_mcp.auth_session import AuthSession
from flin_meta_ads_mcp.credentials import Credentials, load_credentials, save_credentials
from flin_meta_ads_mcp.login import LoginError


def test_secret_only_config_requests_public_app_id_without_disclosing_secret(tmp_path) -> None:
    auth = AuthSession({"META_APP_SECRET": "private-secret", "META_AUTH_FILE": str(tmp_path / "auth.json")})
    result = auth.start()
    assert result["status"] == "authentication_required"
    assert result["missing_configuration"] == ["META_APP_ID"]
    assert "private-secret" not in str(result)
    assert auth.status()["status"] == "authentication_required"
    auth.close()


def test_login_runs_in_background_reuses_link_and_saves_without_stdout(tmp_path, monkeypatch, capsys) -> None:
    complete = threading.Event()
    calls = []
    path = tmp_path / "auth.json"

    def fake_login(settings, *, no_browser, on_authorization_url, cancel):
        assert no_browser is True
        calls.append(settings.app_id)
        on_authorization_url("https://www.facebook.com/dialog/oauth?state=expected")
        assert complete.wait(timeout=5)
        return Credentials(settings.app_id, settings.app_secret, "private-token", settings.api_version)

    monkeypatch.setattr("flin_meta_ads_mcp.auth_session.browser_login", fake_login)
    auth = AuthSession({"META_APP_SECRET": "private-secret", "META_AUTH_FILE": str(path)})
    try:
        pending = auth.start("123")
        assert pending["status"] == "pending"
        assert "login_url" in pending
        assert auth.start("123") == pending
        assert auth.status() == pending
        assert calls == ["123"]
        assert not path.exists()
        complete.set()
        auth._thread.join(timeout=5)
        assert auth.status()["status"] == "ready"
        assert "login_url" not in auth.status()
        assert load_credentials(path).access_token == "private-token"
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err == ""
        assert "private-secret" not in str(pending) + str(auth.status())
        assert "private-token" not in str(auth.status())
    finally:
        complete.set()
        auth.close()


@pytest.mark.parametrize("failure", [LoginError("Login cancelled."), OSError("private-secret")])
def test_failed_login_is_reported_without_overwriting_credentials(tmp_path, monkeypatch, failure) -> None:
    path = tmp_path / "auth.json"

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("flin_meta_ads_mcp.auth_session.browser_login", fail)
    auth = AuthSession({"META_APP_ID": "123", "META_APP_SECRET": "private-secret", "META_AUTH_FILE": str(path)})
    try:
        result = auth.start()
        assert result["status"] == "login_failed"
        assert auth.status()["status"] == "login_failed"
        assert "private-secret" not in str(result)
        assert not path.exists()
    finally:
        auth.close()


def test_closing_session_cancels_login_and_does_not_save(tmp_path, monkeypatch) -> None:
    path = tmp_path / "auth.json"

    def cancelled(settings, *, no_browser, on_authorization_url, cancel):
        on_authorization_url("https://www.facebook.com/dialog/oauth")
        assert cancel.wait(timeout=5)
        return Credentials("123", "secret", "token", "v21.0")

    monkeypatch.setattr("flin_meta_ads_mcp.auth_session.browser_login", cancelled)
    auth = AuthSession({"META_APP_ID": "123", "META_APP_SECRET": "secret", "META_AUTH_FILE": str(path)})
    assert auth.start()["status"] == "pending"
    auth.close()
    assert not auth._thread.is_alive()
    assert not path.exists()


def test_explicit_token_is_not_silently_overridden() -> None:
    auth = AuthSession({"META_APP_ID": "123", "META_APP_SECRET": "secret", "META_ACCESS_TOKEN": "token"})
    assert auth.start()["status"] == "configuration_required"
    assert auth.status()["status"] == "ready"
    auth.close()


def test_status_rechecks_saved_login_expiration(tmp_path) -> None:
    path = tmp_path / "auth.json"
    auth = AuthSession({"META_APP_ID": "123", "META_APP_SECRET": "secret", "META_AUTH_FILE": str(path)})
    auth._result = {"ok": True, "status": "ready"}
    save_credentials(path, Credentials("123", "secret", "expired", "v21.0", expires_at=1))
    assert auth.status()["status"] == "authentication_required"
    save_credentials(path, Credentials("123", "secret", "new-token", "v21.0"))
    assert auth.status()["status"] == "ready"
    auth.close()


@pytest.mark.parametrize("app_id", [123, "not-an-id", "１２３"])
def test_login_rejects_invalid_app_id(app_id) -> None:
    auth = AuthSession({"META_APP_SECRET": "secret"})
    with pytest.raises(LoginError, match="numeric"):
        auth.start(app_id)
    auth.close()


def test_auth_callback_does_not_print_login_url(tmp_path: Path, monkeypatch, capsys) -> None:
    from flin_meta_ads_mcp import login

    announced = []

    def receive(settings, *, state, timeout, launch, cancel):
        launch()
        return "code"

    monkeypatch.setattr(login, "receive_code", receive)
    monkeypatch.setattr(login, "exchange_code", lambda *args: Credentials("123", "secret", "token", "v21.0"))
    monkeypatch.setattr(login, "verify_access", lambda *args: None)
    login.browser_login(
        login.LoginSettings("123", "secret"), no_browser=True,
        on_authorization_url=announced.append,
    )
    assert announced[0].startswith("https://www.facebook.com/")
    assert capsys.readouterr().out == ""
