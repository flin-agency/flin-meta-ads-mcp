"""After PyPI publication, prove the bundled launcher runs a PyPI-installed server."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
import zipfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from smoke_mcpb import check_session

from flin_meta_ads_mcp import desktop
from flin_meta_ads_mcp.credentials import Credentials, save_credentials


async def check_saved_settings(params, expected, marker):
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        assert (await session.initialize()).serverInfo.version == expected
        result = await session.call_tool("connection_status", {})
        data = json.loads(result.content[0].text)
        assert data["server_version"] == expected
        assert data["configuration_status"] == "configured"
        assert data["auth_status"] == "unknown"
        assert data["live_access"] == "not_checked"
        assert data["runtime_source"] == "cached"
        assert data["extension_version"] == expected
        assert "synthetic" not in json.dumps(data)
    assert marker.exists()


def main(bundle: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="meta-update-test-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(root)
        manifest = json.loads((root / "manifest.json").read_text())
        expected = manifest["version"]
        launcher, uv = root / "server/flin-meta-ads-mcp", root / "server/uv"
        launcher.chmod(0o700)
        uv.chmod(0o700)
        # Use only an isolated home with synthetic settings, never user credentials.
        os.environ["HOME"] = str(root)
        state = desktop.state_directory()
        for attempt in range(12):
            version, _ = desktop.latest_release()
            if version == expected:
                break
            time.sleep(5)
        else:
            raise AssertionError(f"Release {expected} is not the latest on PyPI")
        old_version = "0.1.16"
        desktop.__version__ = old_version  # Simulate a previously installed extension.
        state.mkdir(parents=True)
        old_name = old_version + "-" + "a" * 32
        old_directory = state / "versions" / old_name
        update_env = desktop.clean_environment()
        update_env.update(UV_CACHE_DIR=str(state / "uv-cache"),
                          UV_PYTHON_INSTALL_DIR=str(state / "python"))
        desktop.run_checked([str(uv), "venv", "--no-config", "--no-project", "--managed-python",
                             "--python", ">=3.11", str(old_directory)], env=update_env)
        desktop.run_checked([str(uv), "pip", "install", "--no-config", "--python",
                             str(old_directory / "bin/python"), "--default-index", desktop.INDEX,
                             "--only-binary", ":all:", f"{desktop.PACKAGE}=={old_version}"], env=update_env)
        (state / "active.json").write_text(json.dumps({"version": old_version, "environment": old_name}))
        credentials = root / "saved-login.json"
        save_credentials(credentials, Credentials("123", "synthetic-secret", "synthetic-token", "v21.0"))
        before = credentials.read_bytes()
        settings = {"HOME": str(root), "PATH": "/usr/bin:/bin", "META_AUTH_FILE": str(credentials),
                    "META_APP_ID": "123", "META_APP_SECRET": "synthetic-secret",
                    "META_DEFAULT_AD_ACCOUNT_ID": "act_123"}
        assert desktop.read_active(state)[0] == old_version
        desktop.prepare_update(state, uv)
        active = desktop.read_active(state, minimum=expected)
        assert active and active[0] == expected
        assert credentials.read_bytes() == before
        assert (old_directory / "bin/python").exists()
        # Instrument only the disposable venv to prove the launcher really uses
        # its interpreter instead of silently falling back to the same version.
        marker = root / "cached-interpreter-used"
        site = next(active[1].parent.parent.glob("lib/python*/site-packages"))
        (site / "smoke-marker.pth").write_text(
            f"import pathlib; pathlib.Path({str(marker)!r}).touch()\n"
        )
        # Inspect resolved settings without calling Meta. -I prevents source-tree imports.
        verify = "from flin_meta_ads_mcp.config import load_config; s=load_config(); " \
                 "assert s.access_token == 'synthetic-token'; assert s.app_secret == 'synthetic-secret'; " \
                 "assert s.default_ad_account_id == 'act_123'"
        desktop.run_checked([str(active[1]), "-I", "-c", verify], env=settings)
        marker.unlink()
        # Force a failing offline update: the already prepared server must still start.
        uv.rename(uv.with_name("uv-offline"))
        params = StdioServerParameters(command=str(launcher), args=[], cwd=str(root), env={
            "HOME": str(root), "PATH": "/usr/bin:/bin",
            "META_AUTH_FILE": str(root / "missing.json"),
        })
        with (root / "stderr.log").open("w+") as errors:
            asyncio.run(asyncio.wait_for(check_session(params, manifest, errors), 30))
            errors.seek(0)
            assert "Traceback" not in errors.read()
        assert marker.exists(), "Launcher did not use the prepared PyPI environment"
        marker.unlink()
        params = StdioServerParameters(command=str(launcher), args=[], env=settings, cwd=str(root))
        asyncio.run(asyncio.wait_for(check_saved_settings(params, expected, marker), 30))
        assert credentials.read_bytes() == before
        print(f"PASS: PyPI {old_version} -> {expected}, MCP contracts, saved settings/credentials, "
              "atomic activation and next offline packaged start")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
