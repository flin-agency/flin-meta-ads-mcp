from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_mcp_connection_initializes_without_access_token(tmp_path) -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("META_")}
    env.update({
        "META_APP_SECRET": "dummy-secret",
        "META_AUTH_FILE": str(tmp_path / "missing.json"),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    })

    async def check():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "flin_meta_ads_mcp.cli"], env=env,
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "flin-meta-ads-mcp"
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {"start_meta_login", "get_meta_auth_status", "list_ad_accounts"} <= names
            for name in ("get_meta_auth_status", "start_meta_login", "list_ad_accounts"):
                response = await session.call_tool(name, {})
                assert not response.isError
                payload = json.loads(response.content[0].text)
                assert payload["status"] == "authentication_required"
                assert payload["missing_configuration"] == ["META_APP_ID"]
                assert "dummy-secret" not in str(response)

    asyncio.run(asyncio.wait_for(check(), timeout=15))
