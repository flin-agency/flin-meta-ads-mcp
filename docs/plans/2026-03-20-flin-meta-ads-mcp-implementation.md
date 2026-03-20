# flin-meta-ads-mcp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and publish a public, strict read-only Meta Ads MCP server (`flin-meta-ads-mcp`) that is easy for others to run and test via `uvx`.

**Architecture:** The MCP server exposes typed tools and delegates API calls to a single Meta client adapter with unified error mapping, pagination, and retry/backoff. All tools are read-only by design and return a consistent response envelope for easy downstream usage and testing.

**Tech Stack:** Python 3.11+, `mcp`, `httpx`, `pytest`, `respx`, `ruff`, `mypy`, `hatchling`, GitHub Actions, PyPI/uvx.

---

### Task 1: Project Scaffold and Packaging

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `src/flin_meta_ads_mcp/__init__.py`
- Create: `src/flin_meta_ads_mcp/server.py`

**Step 1: Write the failing test**

```python
# tests/test_package_entrypoint.py
import importlib

def test_server_module_imports():
    module = importlib.import_module("flin_meta_ads_mcp.server")
    assert hasattr(module, "main")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_package_entrypoint.py::test_server_module_imports -v`  
Expected: FAIL with `ModuleNotFoundError` or missing `main`.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/server.py
def main() -> None:
    raise SystemExit(0)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_package_entrypoint.py::test_server_module_imports -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml README.md .env.example src/flin_meta_ads_mcp/__init__.py src/flin_meta_ads_mcp/server.py tests/test_package_entrypoint.py
git commit -m "chore: scaffold flin-meta-ads-mcp package and entrypoint"
```

### Task 2: Configuration Loading and Validation

**Files:**
- Create: `src/flin_meta_ads_mcp/config.py`
- Create: `tests/test_config.py`
- Modify: `src/flin_meta_ads_mcp/server.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
import pytest
from flin_meta_ads_mcp.config import load_config

def test_load_config_requires_access_token(monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    with pytest.raises(ValueError):
        load_config()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_load_config_requires_access_token -v`  
Expected: FAIL because `load_config` does not exist yet.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/config.py
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    access_token: str
    default_ad_account_id: str | None
    api_version: str
    timeout_seconds: float
    max_retries: int

def load_config() -> Settings:
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        raise ValueError("META_ACCESS_TOKEN is required")
    return Settings(
        access_token=token,
        default_ad_account_id=os.getenv("META_AD_ACCOUNT_ID"),
        api_version=os.getenv("META_GRAPH_API_VERSION", "v21.0"),
        timeout_seconds=float(os.getenv("META_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("META_MAX_RETRIES", "3")),
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/config.py src/flin_meta_ads_mcp/server.py tests/test_config.py
git commit -m "feat: add env-based configuration and validation"
```

### Task 3: Response Envelope and Error Taxonomy

**Files:**
- Create: `src/flin_meta_ads_mcp/errors.py`
- Create: `src/flin_meta_ads_mcp/response.py`
- Create: `tests/test_errors_and_response.py`

**Step 1: Write the failing test**

```python
# tests/test_errors_and_response.py
from flin_meta_ads_mcp.response import ok_response

def test_ok_response_shape():
    payload = ok_response(data=[{"id": "1"}], next_after=None, has_next=False, api_version="v21.0", request_id="abc")
    assert payload["ok"] is True
    assert "data" in payload and "paging" in payload and "meta" in payload
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_errors_and_response.py::test_ok_response_shape -v`  
Expected: FAIL due missing module/function.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/response.py
def ok_response(data, next_after, has_next, api_version, request_id):
    return {
        "ok": True,
        "data": data,
        "paging": {"next_after": next_after, "has_next": has_next},
        "meta": {"api_version": api_version, "request_id": request_id},
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_errors_and_response.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/errors.py src/flin_meta_ads_mcp/response.py tests/test_errors_and_response.py
git commit -m "feat: add unified response envelope and error taxonomy"
```

### Task 4: Meta HTTP Client (Read-Only, Retry, Pagination)

**Files:**
- Create: `src/flin_meta_ads_mcp/meta_client.py`
- Create: `tests/test_meta_client.py`

**Step 1: Write the failing test**

```python
# tests/test_meta_client.py
import respx
import httpx
from flin_meta_ads_mcp.meta_client import MetaClient

@respx.mock
def test_get_json_handles_paging():
    route = respx.get("https://graph.facebook.com/v21.0/act_123/campaigns").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "1"}], "paging": {"cursors": {"after": "cursor1"}}})
    )
    client = MetaClient(access_token="token", api_version="v21.0", timeout_seconds=30, max_retries=1)
    out = client.get_json("act_123/campaigns", params={})
    assert route.called
    assert out["data"][0]["id"] == "1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_meta_client.py::test_get_json_handles_paging -v`  
Expected: FAIL due missing client.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/meta_client.py
import httpx

class MetaClient:
    def __init__(self, access_token: str, api_version: str, timeout_seconds: float, max_retries: int):
        self._access_token = access_token
        self._base = f"https://graph.facebook.com/{api_version}"
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    def get_json(self, path: str, params: dict):
        request_params = dict(params)
        request_params["access_token"] = self._access_token
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base}/{path}", params=request_params)
            resp.raise_for_status()
            return resp.json()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_meta_client.py::test_get_json_handles_paging -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/meta_client.py tests/test_meta_client.py
git commit -m "feat: add meta graph read client with base GET support"
```

### Task 5: MCP Server Skeleton (Tool Registry + Dispatch)

**Files:**
- Modify: `src/flin_meta_ads_mcp/server.py`
- Create: `src/flin_meta_ads_mcp/tool_registry.py`
- Create: `tests/test_server_tools.py`

**Step 1: Write the failing test**

```python
# tests/test_server_tools.py
import pytest
from flin_meta_ads_mcp.tool_registry import tool_names

def test_expected_tools_registered():
    names = set(tool_names())
    assert "list_campaigns" in names
    assert "get_insights" in names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_tools.py::test_expected_tools_registered -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/tool_registry.py
def tool_names():
    return [
        "list_ad_accounts",
        "get_ad_account",
        "list_campaigns",
        "get_campaign",
        "list_adsets",
        "get_adset",
        "list_ads",
        "get_ad",
        "list_ad_creatives",
        "get_ad_creative",
        "get_ad_preview",
        "get_insights",
    ]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_tools.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/server.py src/flin_meta_ads_mcp/tool_registry.py tests/test_server_tools.py
git commit -m "feat: register typed read-only MCP tools"
```

### Task 6: Implement Account and Campaign Read Tools

**Files:**
- Create: `src/flin_meta_ads_mcp/tools/accounts.py`
- Create: `src/flin_meta_ads_mcp/tools/campaigns.py`
- Create: `src/flin_meta_ads_mcp/tools/common.py`
- Create: `tests/tools/test_accounts_and_campaigns.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_accounts_and_campaigns.py
from flin_meta_ads_mcp.tools.common import resolve_ad_account_id

def test_resolve_ad_account_id_prefers_argument():
    assert resolve_ad_account_id("act_123", "act_999") == "act_123"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_accounts_and_campaigns.py::test_resolve_ad_account_id_prefers_argument -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/tools/common.py
def resolve_ad_account_id(ad_account_id: str | None, default_ad_account_id: str | None) -> str:
    resolved = ad_account_id or default_ad_account_id
    if not resolved:
        raise ValueError("ad_account_id is required (argument or META_AD_ACCOUNT_ID)")
    return resolved
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_accounts_and_campaigns.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/tools/accounts.py src/flin_meta_ads_mcp/tools/campaigns.py src/flin_meta_ads_mcp/tools/common.py tests/tools/test_accounts_and_campaigns.py
git commit -m "feat: add account and campaign read tool handlers"
```

### Task 7: Implement AdSet and Ad Read Tools

**Files:**
- Create: `src/flin_meta_ads_mcp/tools/adsets.py`
- Create: `src/flin_meta_ads_mcp/tools/ads.py`
- Create: `tests/tools/test_adsets_and_ads.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_adsets_and_ads.py
def test_list_ads_has_default_limit():
    from flin_meta_ads_mcp.tools.ads import normalize_limit
    assert normalize_limit(None) == 50
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_adsets_and_ads.py::test_list_ads_has_default_limit -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/tools/ads.py
def normalize_limit(limit: int | None) -> int:
    if limit is None:
        return 50
    return max(1, min(200, int(limit)))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_adsets_and_ads.py::test_list_ads_has_default_limit -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/tools/adsets.py src/flin_meta_ads_mcp/tools/ads.py tests/tools/test_adsets_and_ads.py
git commit -m "feat: add adset and ad list/get read tools"
```

### Task 8: Implement Creative and Preview Read Tools

**Files:**
- Create: `src/flin_meta_ads_mcp/tools/creatives.py`
- Create: `src/flin_meta_ads_mcp/tools/previews.py`
- Create: `tests/tools/test_creatives_and_previews.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_creatives_and_previews.py
def test_preview_defaults_to_desktop_feed():
    from flin_meta_ads_mcp.tools.previews import normalize_preview_format
    assert normalize_preview_format(None) == "DESKTOP_FEED_STANDARD"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_creatives_and_previews.py::test_preview_defaults_to_desktop_feed -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/tools/previews.py
def normalize_preview_format(value: str | None) -> str:
    return value or "DESKTOP_FEED_STANDARD"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_creatives_and_previews.py::test_preview_defaults_to_desktop_feed -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/tools/creatives.py src/flin_meta_ads_mcp/tools/previews.py tests/tools/test_creatives_and_previews.py
git commit -m "feat: add ad creative and preview read tools"
```

### Task 9: Implement Insights Tool (Core Reporting)

**Files:**
- Create: `src/flin_meta_ads_mcp/tools/insights.py`
- Create: `tests/tools/test_insights.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_insights.py
import pytest
from flin_meta_ads_mcp.tools.insights import validate_insights_args

def test_insights_requires_level():
    with pytest.raises(ValueError):
        validate_insights_args({})
```

def test_insights_accepts_campaign_level():
    args = validate_insights_args({"level": "campaign"})
    assert args["level"] == "campaign"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_insights.py -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/tools/insights.py
ALLOWED_LEVELS = {"account", "campaign", "adset", "ad"}

def validate_insights_args(args: dict) -> dict:
    level = args.get("level")
    if level not in ALLOWED_LEVELS:
        raise ValueError("level must be one of: account, campaign, adset, ad")
    return args
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_insights.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/tools/insights.py tests/tools/test_insights.py
git commit -m "feat: add insights read tool with validation"
```

### Task 10: Read-Only Guard Enforcement

**Files:**
- Create: `src/flin_meta_ads_mcp/guards.py`
- Create: `tests/test_read_only_guards.py`
- Modify: `src/flin_meta_ads_mcp/server.py`

**Step 1: Write the failing test**

```python
# tests/test_read_only_guards.py
import pytest
from flin_meta_ads_mcp.guards import assert_read_only_tool

def test_rejects_unknown_write_like_tool():
    with pytest.raises(PermissionError):
        assert_read_only_tool("update_campaign")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_read_only_guards.py::test_rejects_unknown_write_like_tool -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# src/flin_meta_ads_mcp/guards.py
READ_ONLY_TOOLS = {
    "list_ad_accounts",
    "get_ad_account",
    "list_campaigns",
    "get_campaign",
    "list_adsets",
    "get_adset",
    "list_ads",
    "get_ad",
    "list_ad_creatives",
    "get_ad_creative",
    "get_ad_preview",
    "get_insights",
}

def assert_read_only_tool(name: str) -> None:
    if name not in READ_ONLY_TOOLS:
        raise PermissionError("Tool is not allowed in strict read-only mode")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_read_only_guards.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/flin_meta_ads_mcp/guards.py src/flin_meta_ads_mcp/server.py tests/test_read_only_guards.py
git commit -m "feat: enforce strict read-only tool allowlist"
```

### Task 11: End-to-End Mock Contract Tests

**Files:**
- Create: `tests/e2e/test_mcp_contract.py`
- Modify: `tests/conftest.py`

**Step 1: Write the failing test**

```python
# tests/e2e/test_mcp_contract.py
def test_list_campaigns_contract_shape(mock_server_client):
    out = mock_server_client.call_tool("list_campaigns", {"ad_account_id": "act_123"})
    assert out["ok"] is True
    assert isinstance(out["data"], list)
    assert "paging" in out and "meta" in out
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_mcp_contract.py -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# tests/conftest.py
import pytest

@pytest.fixture
def mock_server_client():
    class Dummy:
        def call_tool(self, name, args):
            return {"ok": True, "data": [], "paging": {"next_after": None, "has_next": False}, "meta": {"api_version": "v21.0", "request_id": "test"}}
    return Dummy()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/e2e/test_mcp_contract.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/e2e/test_mcp_contract.py tests/conftest.py
git commit -m "test: add contract-level response shape tests"
```

### Task 12: Docs for Public Usage and Troubleshooting

**Files:**
- Modify: `README.md`
- Modify: `.env.example`

**Step 1: Write the failing test**

```python
# tests/test_readme_smoke_section.py
from pathlib import Path

def test_readme_has_smoke_test_section():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "2-Minuten-Smoke-Test" in text
    assert "uvx flin-meta-ads-mcp" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_readme_smoke_section.py -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```markdown
## 2-Minuten-Smoke-Test

1. `list_ad_accounts`
2. `list_campaigns`
3. `get_insights` mit `level=campaign` und `date_preset=last_7d`
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_readme_smoke_section.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md .env.example tests/test_readme_smoke_section.py
git commit -m "docs: add public quickstart and smoke-test guide"
```

### Task 13: CI, Build, and Release Automation

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`

**Step 1: Write the failing test**

```python
# tests/test_ci_files_exist.py
from pathlib import Path

def test_ci_workflows_present():
    assert Path(".github/workflows/ci.yml").exists()
    assert Path(".github/workflows/release.yml").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ci_files_exist.py -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e .[dev]
      - run: pytest -q
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ci_files_exist.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/release.yml tests/test_ci_files_exist.py
git commit -m "ci: add test and release workflows for PyPI distribution"
```

### Task 14: Final Verification Checklist

**Files:**
- Modify: `README.md` (badge/version/examples)
- Modify: `pyproject.toml` (final dependency and script sanity)

**Step 1: Write the failing test**

```python
# tests/test_package_metadata.py
from pathlib import Path

def test_project_name_matches_public_command():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "flin-meta-ads-mcp"' in text
    assert "flin-meta-ads-mcp" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_package_metadata.py -v`  
Expected: FAIL until final metadata is complete.

**Step 3: Write minimal implementation**

```toml
[project]
name = "flin-meta-ads-mcp"
version = "0.1.0"

[project.scripts]
flin-meta-ads-mcp = "flin_meta_ads_mcp.server:main"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_package_metadata.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml README.md tests/test_package_metadata.py
git commit -m "chore: finalize metadata and release-ready docs"
```

## Release Commands (after all tasks pass)

Run:

```bash
python -m pip install -U pip
pip install -e .[dev]
ruff check .
mypy src
pytest -q
python -m build
```

Publish:

```bash
python -m pip install twine
twine check dist/*
twine upload dist/*
```

Post-publish smoke test:

```bash
uvx flin-meta-ads-mcp --help
```
