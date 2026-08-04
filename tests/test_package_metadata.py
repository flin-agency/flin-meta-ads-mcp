from __future__ import annotations

from pathlib import Path
import tomllib


def test_project_constrains_mcp_to_supported_major_version() -> None:
    pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert "mcp>=1.28,<2" in pyproject["project"]["dependencies"]
