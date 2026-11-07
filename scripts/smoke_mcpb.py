"""Test the packaged executable with real MCP, isolated from saved user credentials."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(bundle: Path) -> None:
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    assert bundle.with_suffix(".mcpb.sha256").read_text().split()[0] == digest
    alias = bundle.with_name("flin-meta-ads-mcp.mcpb")
    assert alias.read_bytes() == bundle.read_bytes()
    assert alias.with_suffix(".mcpb.sha256").read_text().split()[0] == digest
    with tempfile.TemporaryDirectory(prefix="meta-mcpb-test-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(bundle) as archive:
            for name in archive.namelist():
                if name.startswith("/") or ".." in Path(name).parts:
                    raise AssertionError("Unsafe archive path")
            archive.extractall(root)
        manifest = json.loads((root / "manifest.json").read_text())
        binary = root / manifest["server"]["entry_point"]
        binary.chmod(0o700)
        (root / "server/uv").chmod(0o700)
        env = {key: value for key, value in os.environ.items() if not key.startswith(("META_", "PYTHON"))}
        env["HOME"] = str(root)
        env["META_AUTH_FILE"] = str(root / "missing-credentials.json")
        # Offline fallback is deterministic and cannot spawn an orphan updater.
        (root / "server/uv").rename(root / "server/uv-disabled")
        params = StdioServerParameters(command=str(binary), args=[], env=env, cwd=str(root))
        with (root / "stderr.log").open("w+") as errlog:
            await check_session(params, manifest, errlog)
            errlog.seek(0)
            assert "Traceback" not in errlog.read(), "Packaged server emitted a traceback"
        print(f"PASS: {bundle.name}: initialize, 18 tools, authentication, clean shutdown")


async def check_session(params, manifest, errlog):
    async with stdio_client(params, errlog=errlog) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        assert initialized.serverInfo.version == manifest["version"]
        listed = await session.list_tools()
        assert len(listed.tools) == 18
        assert {"start_meta_login", "get_meta_auth_status", "download_ad_image"} <= {t.name for t in listed.tools}
        status = await session.call_tool("connection_status", {})
        assert not status.isError
        data = json.loads(status.content[0].text)
        assert data["server_version"] == initialized.serverInfo.version
        assert data["configuration_status"] == "incomplete"
        assert data["auth_status"] == "unauthenticated"
        assert data["live_access"] == "not_checked"
        for name in ("get_meta_auth_status", "list_ad_accounts", "start_meta_login"):
            result = await session.call_tool(name, {})
            assert not result.isError
            assert json.loads(result.content[0].text)["status"] == "authentication_required"


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(check(Path(sys.argv[1])), timeout=60))
