from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desktop_manifest_is_self_contained_and_marks_secrets_sensitive():
    manifest = json.loads((ROOT / "packaging/manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["version"] == project["project"]["version"]
    assert manifest["server"]["type"] == "binary"
    assert manifest["compatibility"]["platforms"] == ["darwin"]
    config = manifest["server"]["mcp_config"]
    assert config["command"] == "${__dirname}/server/flin-meta-ads-mcp"
    assert config["args"] == []
    for secret in ("app_secret", "access_token"):
        assert manifest["user_config"][secret]["sensitive"] is True
        assert not manifest["user_config"][secret].get("default")
        assert "${user_config." + secret + "}" in config["env"].values()
