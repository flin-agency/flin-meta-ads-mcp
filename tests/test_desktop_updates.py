from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
import respx

from flin_meta_ads_mcp import desktop
from flin_meta_ads_mcp.tool_registry import ToolSpec


def active_record(root: Path, version="0.1.90"):
    name = version + "-" + "a" * 32
    python = root / "versions" / name / "bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    record = {"version": version, "environment": name}
    (root / "active.json").write_text(json.dumps(record))
    return record, python


def test_updater_never_receives_meta_secrets_or_index_overrides(monkeypatch):
    for key in ["META_ACCESS_TOKEN", "META_APP_SECRET", "PIP_INDEX_URL", "UV_INDEX", "PYTHONPATH", "HTTPS_PROXY"]:
        monkeypatch.setenv(key, "private")
    env = desktop.clean_environment()
    assert "private" not in env.values()
    assert desktop.clean_environment(credentials=True)["META_ACCESS_TOKEN"] == "private"
    assert "UV_INDEX" not in desktop.clean_environment(credentials=True)


@pytest.mark.parametrize("record", [
    {"version": "0.1.90", "environment": "../../evil"},
    {"version": "0.1.90rc1", "environment": "0.1.90rc1-" + "a" * 32},
    {"version": "0.0.1", "environment": "0.0.1-" + "a" * 32},
    {}, [], None,
])
def test_invalid_update_pointer_cannot_escape_state_directory(tmp_path, record):
    (tmp_path / "active.json").write_text(json.dumps(record))
    assert desktop.read_active(tmp_path) is None


def test_existing_verified_update_is_selected(tmp_path):
    _, python = active_record(tmp_path)
    assert desktop.read_active(tmp_path) == ("0.1.90", python)


@pytest.mark.parametrize("version", ["0.1.99rc1", "0.1.99.dev1", "0.1.99.post1", "0.2.0", "1.0.0", "../evil"])
@respx.mock
def test_incompatible_and_prerelease_metadata_is_rejected(version):
    respx.get(desktop.PYPI).respond(200, json={"releases": {
        version: [{"packagetype": "bdist_wheel", "requires_python": ">=3.11"}],
    }})
    with pytest.raises(ValueError):
        desktop.latest_release()


@respx.mock
def test_select_latest_compatible_non_yanked_wheel_and_validate_python():
    wheel = {"packagetype": "bdist_wheel", "requires_python": ">=3.11"}
    releases = {"0.1.90": [wheel], "0.1.91": [dict(wheel, yanked=True)],
                "0.2.0": [wheel], "0.1.92rc1": [wheel], "0.1.93": []}
    route = respx.get(desktop.PYPI).respond(200, json={"releases": releases})
    assert desktop.latest_release() == ("0.1.90", ">=3.11")
    releases["0.1.90"] = [dict(wheel, requires_python="https://evil.test/python")]
    route.respond(200, json={"releases": releases})
    with pytest.raises(ValueError):
        desktop.latest_release()


@pytest.mark.parametrize("version", ["0.1.14", "0.2.0", "1.0.0"])
def test_incompatible_cached_environment_is_not_activated(tmp_path, version):
    active_record(tmp_path, version)
    assert desktop.read_active(tmp_path) is None


@respx.mock
def test_metadata_redirects_are_not_followed():
    respx.get(desktop.PYPI).respond(302, headers={"location": "https://evil.test"})
    with pytest.raises(httpx.HTTPStatusError):
        desktop.latest_release()
    assert len(respx.calls) == 1


def test_failed_probe_preserves_previous_version(tmp_path, monkeypatch):
    record, _ = active_record(tmp_path)
    monkeypatch.setattr(desktop, "latest_release", lambda: ("0.1.91", ">=3.11"))
    monkeypatch.setattr(desktop, "run_checked", Mock())
    monkeypatch.setattr(desktop, "probe", Mock(side_effect=RuntimeError("bad release")))
    with pytest.raises(RuntimeError):
        desktop.prepare_update(tmp_path, Path("/trusted/uv"))
    assert json.loads((tmp_path / "active.json").read_text()) == record


def test_successful_update_is_published_only_after_probe(tmp_path, monkeypatch):
    record, old_python = active_record(tmp_path)
    monkeypatch.setattr(desktop, "latest_release", lambda: ("0.1.91", ">=3.11"))
    commands = []
    def run(args, **kwargs):
        commands.append(args)
        assert "META_ACCESS_TOKEN" not in kwargs["env"]
        assert json.loads((tmp_path / "active.json").read_text()) == record
        if args[1] == "venv":
            python = Path(args[-1]) / "bin/python"
            python.parent.mkdir(parents=True)
            python.touch()
    def probe(*args):
        assert json.loads((tmp_path / "active.json").read_text()) == record
    monkeypatch.setattr(desktop, "run_checked", run)
    monkeypatch.setattr(desktop, "probe", probe)
    desktop.prepare_update(tmp_path, Path("/trusted/uv"))
    assert desktop.read_active(tmp_path)[0] == "0.1.91"
    assert old_python.exists()
    assert "--no-config" in commands[0]
    assert commands[1][-1] == "flin-meta-ads-mcp==0.1.91"
    assert "--only-binary" in commands[1]
    assert desktop.INDEX in commands[1]


def test_no_downgrade_or_reinstall(tmp_path, monkeypatch):
    active_record(tmp_path)
    monkeypatch.setattr(desktop, "latest_release", lambda: ("0.1.89", ">=3.11"))
    install = Mock()
    monkeypatch.setattr(desktop, "run_checked", install)
    desktop.prepare_update(tmp_path, Path("/trusted/uv"))
    install.assert_not_called()


def test_concurrent_updaters_do_not_install_twice(tmp_path, monkeypatch):
    import fcntl
    install = Mock()
    monkeypatch.setattr(desktop, "latest_release", install)
    with (tmp_path / "update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        desktop.prepare_update(tmp_path, Path("/trusted/uv"))
    install.assert_not_called()


def test_cached_server_receives_credentials_but_updater_does_not(tmp_path, monkeypatch):
    _, python = active_record(tmp_path)
    uv = tmp_path / "uv"
    uv.touch()
    monkeypatch.setattr(desktop, "state_directory", lambda: tmp_path)
    monkeypatch.setattr(desktop.sys, "executable", str(tmp_path / "launcher"))
    monkeypatch.setattr(desktop.sys, "argv", [str(tmp_path / "launcher")])
    monkeypatch.setenv("META_ACCESS_TOKEN", "private")
    worker = Mock()
    monkeypatch.setattr(desktop.subprocess, "Popen", worker)
    def execute(path, args, env):
        assert path == str(python)
        assert "-I" in args
        assert env["META_ACCESS_TOKEN"] == "private"
        raise SystemExit(0)
    monkeypatch.setattr(desktop.os, "execve", execute)
    with pytest.raises(SystemExit):
        desktop.main()
    assert "META_ACCESS_TOKEN" not in worker.call_args.kwargs["env"]
    assert worker.call_args.kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"


def test_offline_update_does_not_break_bundled_fallback(tmp_path, monkeypatch):
    from flin_meta_ads_mcp import cli
    monkeypatch.setattr(desktop, "state_directory", lambda: tmp_path)
    monkeypatch.setattr(desktop.sys, "executable", str(tmp_path / "launcher"))
    monkeypatch.setattr(desktop.sys, "argv", ["launcher"])
    fallback = Mock()
    monkeypatch.setattr(cli, "main", fallback)
    desktop.main()
    fallback.assert_called_once()


def test_real_probe_rejects_missing_tool_contract(tmp_path, monkeypatch):
    desktop.probe(Path(sys.executable), desktop.__version__, tmp_path, desktop.clean_environment())
    specs = desktop.tool_specs()
    monkeypatch.setattr(desktop, "tool_specs", lambda: [
        *specs, ToolSpec("missing_required_tool", "test", {"type": "object", "properties": {}}),
    ])
    with pytest.raises(subprocess.CalledProcessError):
        desktop.probe(Path(sys.executable), desktop.__version__, tmp_path, desktop.clean_environment())


def test_incompatible_update_cannot_replace_active_pointer(tmp_path, monkeypatch):
    record, _ = active_record(tmp_path)
    monkeypatch.setattr(desktop, "latest_release", lambda: ("0.2.0", ">=3.11"))
    install = Mock()
    monkeypatch.setattr(desktop, "run_checked", install)
    with pytest.raises(ValueError):
        desktop.prepare_update(tmp_path, Path("/trusted/uv"))
    assert json.loads((tmp_path / "active.json").read_text()) == record
    install.assert_not_called()
