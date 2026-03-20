<<<<<<< HEAD
# flin-meta-ads-mcp
=======
# flin-meta-ads-mcp

`flin-meta-ads-mcp` is a public, strict read-only MCP server for Meta Ads. It is designed to be installed with `uvx` and loaded into Claude with minimal setup.

## What it does

- Lists and reads Meta Ads accounts
- Reads campaigns, ad sets, ads, and creatives
- Gets ad previews
- Fetches insights for account, campaign, ad set, and ad levels
- Stays read-only in `v0.1.0`

## Scope for `v0.1.0`

This release is strictly read-only.

That means:

- No create, update, pause, resume, or delete actions
- No OAuth flow or token refresh
- No generic Graph API proxy

## Install

Install and run from PyPI:

```bash
uvx flin-meta-ads-mcp
```

Test the latest GitHub code before a PyPI release:

```bash
uvx --from git+https://github.com/flin-agency/flin-meta-ads-mcp.git flin-meta-ads-mcp
```

## Claude config

Add this to your Claude MCP config:

```json
{
  "mcpServers": {
    "flin-meta-ads-mcp": {
      "command": "uvx",
      "args": ["flin-meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "EAA...",
        "META_GRAPH_API_VERSION": "v21.0"
      }
    }
  }
}
```

## Environment variables

Required:

- `META_ACCESS_TOKEN`: Meta access token with read permissions

Optional:

- `META_GRAPH_API_VERSION`: Graph API version, default `v21.0`
- `META_TIMEOUT_SECONDS`: request timeout, default `30`
- `META_MAX_RETRIES`: retry count for transient failures, default `3`
- `RUN_LIVE_META_TESTS`: set to `1` to enable live integration tests

Ad account selection:

- If the token has exactly one accessible ad account, the server resolves it automatically.
- If the token has multiple accessible ad accounts, pass `ad_account_id` in the tool call.

## 2-minute smoke test

Use these first three tool calls to confirm the server is working:

1. `list_ad_accounts`
2. `list_campaigns`
3. `get_insights` with `level=campaign` and `date_preset=last_7d`

Example flow in Claude:

```text
Call list_ad_accounts
Call list_campaigns
Call get_insights with level=campaign and date_preset=last_7d
```

If the first call works but later calls fail, the issue is usually permissions or ad account scope.

If `list_campaigns` returns a selection request, call it again with one of the suggested `ad_account_id` values.

## Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Token missing | `META_ACCESS_TOKEN` is not set | Add the env var and restart Claude |
| Token invalid | Expired or wrong token | Generate a valid Meta read token |
| Permission denied | Missing `ads_read` or account access | Grant the token access to the ad account |
| Ambiguous ad account | Token can access multiple ad accounts | Pass `ad_account_id` per tool call |
| Rate limit errors | Meta API throttling | Retry later or reduce the number of insight calls |

## Development

Local development quickstart:

```bash
python -m pip install -e ".[dev]"
pytest -q
ruff check .
mypy src
```

If you want to run live Meta API tests:

```bash
RUN_LIVE_META_TESTS=1 pytest -q
```

## Release

Create and push a release tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

After release, users can run:

```bash
uvx flin-meta-ads-mcp
```

## Notes

- Use only ad accounts you are allowed to access
- This server is intended for analysis and reporting, not mutation
- Public users should treat `META_ACCESS_TOKEN` as a secret and supply it through environment variables only
>>>>>>> origin/codex/flin-meta-ads-mcp-v0-1-0
