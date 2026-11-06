"""After PyPI publication, prove the bundled launcher runs a PyPI-installed server."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
import zipfile
from pathlib import Path

from mcp import StdioServerParameters
from smoke_mcpb import check_session

from flin_meta_ads_mcp import desktop


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
        # This test uses no user credentials, existing Python runtime or update cache.
        os.environ["HOME"] = str(root)
        state = desktop.state_directory()
        for attempt in range(12):
            version, _ = desktop.latest_release()
            if version == expected:
                break
            time.sleep(5)
        else:
            raise AssertionError(f"Release {expected} is not the latest on PyPI")
        desktop.__version__ = "0.0.0"  # Simulate a previously installed extension.
        desktop.prepare_update(state, uv)
        active = desktop.read_active(state, minimum=expected)
        assert active and active[0] == expected
        # Instrument only the disposable venv to prove the launcher really uses
        # its interpreter instead of silently falling back to the same version.
        marker = root / "cached-interpreter-used"
        site = next(active[1].parent.parent.glob("lib/python*/site-packages"))
        (site / "smoke-marker.pth").write_text(
            f"import pathlib; pathlib.Path({str(marker)!r}).touch()\n"
        )
        # Force a failing offline update: the already prepared server must still start.
        uv.rename(uv.with_name("uv-offline"))
        params = StdioServerParameters(command=str(launcher), args=[], env={
            "HOME": str(root), "PATH": "/usr/bin:/bin",
            "META_AUTH_FILE": str(root / "missing.json"),
        })
        with (root / "stderr.log").open("w+") as errors:
            asyncio.run(asyncio.wait_for(check_session(params, manifest, errors), 30))
            errors.seek(0)
            assert "Traceback" not in errors.read()
        assert marker.exists(), "Launcher did not use the prepared PyPI environment"
        print(f"PASS: PyPI {expected} installed, probed, atomically activated and launched offline")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]))
