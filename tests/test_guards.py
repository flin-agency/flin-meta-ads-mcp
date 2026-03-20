from __future__ import annotations

import pytest

from flin_meta_ads_mcp.guards import assert_read_only_tool


def test_read_only_guard_accepts_list_tools() -> None:
    assert_read_only_tool("list_campaigns")
    assert_read_only_tool("get_insights")


def test_read_only_guard_rejects_write_like_tool() -> None:
    with pytest.raises(PermissionError, match="read-only"):
        assert_read_only_tool("update_campaign")
