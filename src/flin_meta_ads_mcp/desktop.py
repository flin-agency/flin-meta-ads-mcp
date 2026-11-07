"""Apple Silicon desktop launcher with isolated, background PyPI updates."""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import httpx
from packaging.version import InvalidVersion, Version

from . import __version__
from .tool_registry import auth_tool_specs, tool_specs

PACKAGE = "flin-meta-ads-mcp"
PYPI = f"https://pypi.org/pypi/{PACKAGE}/json"
INDEX = "https://pypi.org/simple"
RELEASE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
ENV_NAME = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+-[a-f0-9]{32}")
# This launcher understands the 0.1 CLI, META_* configuration, credentials JSON,
# and MCP tool contracts. A new minor/major needs an explicitly reviewed launcher.
MINIMUM_SERVER = Version("0.1.15")
MAXIMUM_SERVER = Version("0.2.0")


def compatible_release(version: str) -> bool:
    return bool(RELEASE.fullmatch(version)) and MINIMUM_SERVER <= Version(version) < MAXIMUM_SERVER


def state_directory() -> Path:
    return Path.home() / "Library/Application Support" / PACKAGE / "desktop"


def clean_environment(*, credentials: bool = False) -> dict[str, str]:
    # Do not let uv/pip configuration, Python injection or a proxy redirect the
    # updater. Never expose Meta credentials to package installation/probe code.
    allowed = {"HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"}
    return {
        key: value for key, value in os.environ.items()
        if key in allowed or (credentials and key.startswith("META_"))
    }


def read_active(root: Path, *, minimum: str | None = None) -> tuple[str, Path] | None:
    try:
        record = json.loads((root / "active.json").read_text())
        version, name = record["version"], record["environment"]
        if not compatible_release(version) or not ENV_NAME.fullmatch(name):
            return None
        if not name.startswith(version + "-") or Version(version) < Version(minimum or __version__):
            return None
        directory = root / "versions" / name
        if directory.is_symlink():
            return None
        python = directory / "bin/python"
        if not python.is_file():
            return None
        return version, python
    except (OSError, ValueError, KeyError, TypeError, InvalidVersion):
        return None


def latest_release() -> tuple[str, str]:
    with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
        response = client.get(PYPI)
        response.raise_for_status()
        releases = response.json()["releases"]
    candidates = {
        version: files for version, files in releases.items()
        if compatible_release(version) and any(
            file.get("packagetype") == "bdist_wheel" and not file.get("yanked") for file in files
        )
    }
    if not candidates:
        raise ValueError("No compatible stable release is available")
    version = max(candidates, key=Version)
    info = next(file for file in candidates[version]
                if file.get("packagetype") == "bdist_wheel" and not file.get("yanked"))
    # Ask uv for a runtime compatible with the published package, not the host's
    # Python. Restrict the metadata to version-specifier syntax; never a path/URL.
    requires_python = info.get("requires_python") or ">=3.11"
    if not re.fullmatch(r"[0-9<>=!~.*, ]+", requires_python):
        raise ValueError("Invalid Python version requirement")
    return version, requires_python


def run_checked(args: list[str], *, env: dict[str, str], timeout: int = 180) -> None:
    subprocess.run(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=timeout, check=True)


def probe(python: Path, version: str, root: Path, env: dict[str, str]) -> None:
    # A real, credential-free MCP handshake must pass before activation.
    script = '''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def check():
    env = dict(os.environ, META_AUTH_FILE=sys.argv[2])
    params = StdioServerParameters(command=sys.executable,
        args=["-I", "-m", "flin_meta_ads_mcp.cli"], env=env)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        result = await session.initialize()
        assert result.serverInfo.version == sys.argv[1]
        tools = await session.list_tools()
        actual = {tool.name: tool.inputSchema for tool in tools.tools}
        for name, schema in json.loads(sys.argv[3]).items():
            assert name in actual
            assert set(actual[name].get("required", [])) <= set(schema.get("required", []))
            for key, value in schema.get("properties", {}).items():
                assert actual[name]["properties"][key] == value
        status = await session.call_tool("get_meta_auth_status", {})
        assert json.loads(status.content[0].text)["status"] == "authentication_required"
        status = await session.call_tool("connection_status", {})
        data = json.loads(status.content[0].text)
        assert data["server_version"] == sys.argv[1]
        assert data["auth_status"] == "unauthenticated"
        assert data["live_access"] == "not_checked"
asyncio.run(asyncio.wait_for(check(), 15))
'''
    contracts = {spec.name: spec.input_schema for spec in [*tool_specs(), *auth_tool_specs()]}
    run_checked([str(python), "-I", "-c", script, version,
                 str(root / "probe-no-credentials.json"), json.dumps(contracts)], env=env, timeout=25)


def prepare_update(root: Path, uv: Path) -> None:
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if root.is_symlink():
        raise ValueError("Update directory must not be a symlink")
    root.chmod(0o700)
    with (root / "update.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # Another Claude process is already preparing the update.
        version, requires_python = latest_release()
        if not compatible_release(version):
            raise ValueError("Incompatible server release")
        active = read_active(root)
        current = active[0] if active else __version__
        if Version(version) <= Version(current):
            return
        name = f"{version}-{uuid4().hex}"
        directory = root / "versions" / name
        env = clean_environment()
        env.update({"UV_CACHE_DIR": str(root / "uv-cache"),
                    "UV_PYTHON_INSTALL_DIR": str(root / "python")})
        run_checked([str(uv), "venv", "--no-config", "--no-project", "--managed-python",
                     "--python", requires_python, str(directory)], env=env)
        python = directory / "bin/python"
        run_checked([str(uv), "pip", "install", "--no-config", "--python", str(python),
                     "--default-index", INDEX, "--only-binary", ":all:",
                     f"{PACKAGE}=={version}"], env=env)
        probe(python, version, root, env)
        # Never modify an environment used by another running Claude process.
        fd, temporary = tempfile.mkstemp(prefix=".active-", dir=root)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump({"version": version, "environment": name}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, root / "active.json")
        finally:
            Path(temporary).unlink(missing_ok=True)


def main() -> None:
    root = state_directory()
    uv = Path(sys.executable).parent / "uv"
    if sys.argv[1:] == ["--desktop-update"]:
        try:
            prepare_update(root, uv)
        except Exception:  # noqa: BLE001 - never print installer output or secrets
            print("Meta Ads update unavailable; keeping the current version.", file=sys.stderr)
        return
    if uv.is_file():
        # Separate lifetime: closing Claude does not interrupt package installation.
        # Reset PyInstaller so the worker owns its extracted runtime independently.
        env = clean_environment()
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            subprocess.Popen([sys.executable, "--desktop-update"], env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass  # Offline / restricted clients still get the bundled server.
    active = read_active(root)
    if active:
        try:
            env = clean_environment(credentials=True)
            env.update(FLIN_META_DESKTOP_VERSION=__version__, FLIN_META_DESKTOP_RUNTIME="cached")
            os.execve(str(active[1]), [str(active[1]), "-I", "-m", "flin_meta_ads_mcp.cli"],
                      env)
        except OSError:
            pass
    from .cli import main as serve
    os.environ.update(FLIN_META_DESKTOP_VERSION=__version__, FLIN_META_DESKTOP_RUNTIME="bundled")
    serve()


if __name__ == "__main__":
    main()
