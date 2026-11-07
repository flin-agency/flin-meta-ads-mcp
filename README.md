# flin-meta-ads-mcp

Read-only Meta Ads analysis in Claude: accounts, campaigns, ads, images and insights.

## Claude Desktop on macOS — installable package

**Apple Silicon (M1 or newer).** Download the
[desktop package](https://github.com/flin-agency/flin-meta-ads-mcp/releases/latest/download/flin-meta-ads-mcp.mcpb).
[Versioned packages and SHA-256 checksums](https://github.com/flin-agency/flin-meta-ads-mcp/releases/latest)
are also available.
No separate Python, uv, Homebrew or manual JSON setup is required. Intel desktop
packages are not produced. The developer installation below remains available.

1. Download the `.mcpb`, then open Claude **Settings → Extensions → Advanced settings
   → Install Extension…** (Extensions may be under Desktop app).
2. Enter **Meta App ID** and **App Secret** from your administrator/password manager
   in extension settings. Alternatively, enter an **Access Token** with `ads_read`.
   Default ad account and Business Login configuration ID are optional. Never put
   secrets in chat.
3. For browser login, call `start_meta_login`, open its login link and approve
   access with your Facebook/Meta account. The administrator must allow
   `http://localhost:8765/callback` in the Meta app. An existing token skips login.
4. Call `connection_status`, then `connection_status` with `check_live=true` to
   verify Meta access (server 0.1.17 or newer). The default call is local only:
   `auth_status=unknown` with a token is expected until a live check. On older
   servers, use `get_meta_auth_status`, then `list_ad_accounts` for a real check.
5. Call `list_ad_accounts`, select the intended account, then `list_campaigns`.
   A successful connection alone does not establish permission for every account.

Disable an older duplicate manual server entry after migration. Keep its credentials
until the new installation works. SHA-256 files accompany versioned downloads.
Packages are not Apple Developer ID signed/notarized; managed extension policy may
block installation. Do not disable macOS protections.

### Versions, updates and offline use

Claude's **extension version** describes the installed package. The
`connection_status.server_version` field identifies the **running server**.
Launcher 0.1.17 additionally reports `extension_version` and `runtime_source`:
`cached` is a prepared PyPI environment, `bundled` the included fallback.

Each extension start prepares updates from official PyPI in the background.
Successful updates activate at the **next normal extension/Claude start**, never
inside a running conversation. Settings and saved login remain in place. Without
internet, the last prepared server or bundled fallback still starts; Meta data
requests themselves need internet. The first background download can take minutes.

**One-time package migration:** 0.1.14 lacks automatic updates. Packages 0.1.15–0.1.16
have automatic updates but need one replacement with 0.1.17 or newer to acquire the
new compatibility bound and runtime-source reporting. Routine server updates then
need no new MCPB import. Changes to the launcher or settings UI can need a new import.

The new launcher accepts stable, non-yanked versions **>=0.1.15 and <0.2.0**.
The compatibility contract is the existing CLI, `META_*` settings, saved-login JSON
and MCP tool inputs/status responses. The updater checks those tool contracts and
a real credential-free MCP connection before atomic activation. A new minor/major
version requires review and potentially a new package; arbitrary jumps are not
assumed compatible. Pre-releases are excluded.

[Support and manual fallback](SUPPORT.md) explains recovery without deleting login.
[Privacy](PRIVACY.md) covers data flow, storage, revocation and cleanup.
[Security](SECURITY.md) links the detailed review. Browser login uses an unencrypted,
owner-only local credentials file, distinct from Claude's sensitive settings.

## What it does

- Lists and reads Meta Ads accounts
- Reads campaigns, ad sets, ads, ad images, and creatives
- Downloads ad images as embedded files with `download_ad_image`
- Gets ad previews (including `preview_url` links)
- Fetches insights for account, campaign, ad set, and ad levels
- Stays read-only in `v0.1.x`

## Download image files

Call `download_ad_image` with a fresh `url` from `list_ad_images`, `get_ad_image`,
or an image URL from `get_ad_creative`:

```json
{"url": "https://scontent.example.fbcdn.net/path/to/image.jpg?signed_query=..."}
```

The connector fetches the image and returns metadata (`filename`, `mime_type`,
`size_bytes`) plus a direct MCP image preview and an embedded binary resource containing the actual file.
The consuming app does not need to fetch the external image URL, so its external
image-domain allowlist is not involved. Saving or displaying the attachment
requires the app to support MCP embedded binary resources; the resource URI is
an identifier, not a hosted download link or a local filesystem path.

Supported formats: JPEG, PNG, GIF, and WebP, up to 5 MiB. Downloads use HTTPS
Meta CDN subdomains (`fbcdn.net`, `fbsbx.com`), validate every redirect, and never
send the Meta Graph access token to the CDN. Expired URLs require a fresh lookup.
No image files are retained on the connector's disk. Existing image metadata
tools keep their current behavior. Restart the connector after installing the
updated code so the new tool is discovered.

## Scope for `v0.1.x`

This release is strictly read-only.

That means:

- No create, update, pause, resume, or delete actions
- No automatic background token refresh; rerun browser login when access expires or is revoked
- No generic Graph API proxy

## Developer installation

Install and run the latest published PyPI release:

```bash
uvx flin-meta-ads-mcp
```

Install and refresh to the newest published release:

```bash
uvx --refresh flin-meta-ads-mcp
```

Run the latest GitHub code (main branch):

```bash
uvx --refresh --from git+https://github.com/flin-agency/flin-meta-ads-mcp.git flin-meta-ads-mcp
```

## Manual Claude configuration

### First start without an access token (v0.1.12 and later)

Configure the App ID and App Secret; no access token is needed to start the MCP server:

```json
{
  "mcpServers": {
    "flin-meta-ads-mcp": {
      "command": "uvx",
      "args": ["--refresh", "flin-meta-ads-mcp@latest"],
      "env": {
        "META_APP_ID": "YOUR_NUMERIC_APP_ID",
        "META_APP_SECRET": "YOUR_APP_SECRET"
      }
    }
  }
}
```

Restart Claude and ask it to sign you in to Meta. It can call `start_meta_login`
and show you a browser link. After approving access, ask it to check
`get_meta_auth_status`. Once the status is `ready`, the Ads tools work immediately
without restarting Claude. The saved login is also reused on subsequent starts.

The server remains connected when credentials are missing or expired. Ads calls
then return login instructions instead of crashing the connection. If only the
App Secret is configured, `start_meta_login` can accept your public App ID as
`app_id`; never pass the App Secret in chat. An App Secret alone cannot identify
the app for browser login.

The in-chat flow uses the local callback `http://localhost:8765/callback` and
waits for up to three minutes without blocking MCP initialization. Your Meta app
must allow that redirect and grant `ads_read`. For apps requiring HTTPS, use the
terminal login's `--manual` flow described below. Multiple simultaneous login
requests in one server reuse the same pending link; if another process has the
callback port open, finish that login or select another configured redirect port.

### Browser login (v0.1.11 and later)

You can sign in to Meta instead of manually generating and copying an access token.

1. In your Meta app, enable Facebook Login (or Facebook Login for Business) and
   the `ads_read` permission. Copy the **App ID** and **App Secret / App-Geheimcode**
   from **App settings > Basic**.
2. Configure the OAuth redirect to match `http://localhost:8765/callback` for local
   development. Meta's localhost HTTP exception is for development apps; use a
   registered HTTPS redirect with `--manual` if your app requires HTTPS. Development
   apps require the signing-in user to have an app role. Public use may require App Review.
3. Start the login:

   ```bash
   uvx --refresh flin-meta-ads-mcp login
   ```

   Enter the App ID and App Secret when prompted. The secret input is hidden.
   Complete the Facebook login and permission approval in your browser.
   The command exchanges the authorization code for a user token, requests a
   long-lived token, and verifies `ads_read` and ad account access before saving it.
4. Configure your MCP client to use the latest published version:

   ```json
   {
     "mcpServers": {
       "flin-meta-ads-mcp": {
         "command": "uvx",
         "args": ["--refresh", "flin-meta-ads-mcp@latest"]
       }
     }
   }
   ```

   Call `list_ad_accounts`. It loads the saved login automatically, including when
   the server was already running without credentials. Remove any old `META_ACCESS_TOKEN`
   from its configuration and restart the MCP client after changing that configuration:
   an explicitly configured token takes precedence over the saved login.

The token and App Secret are stored in
`~/.config/flin-meta-ads-mcp/credentials.json`, with owner-only file permissions
on macOS/Linux. This is a local secret file, not an encrypted keychain. Keep it
out of source control. Set `META_AUTH_FILE` in both the login shell and the MCP
configuration to use another location. Both processes must run as the same OS user
or have access to the same credentials file. Delete that file to remove the local
login; revoke the app in Meta to invalidate its remote access.

For Facebook Login for Business, set `META_LOGIN_CONFIG_ID` to a configuration
that issues **user access tokens** and grants `ads_read`. The configuration controls
permissions instead of the login URL's scope. This flow does not support business
integration system user token configurations.

If the browser does not open, follow the printed link. Use `--no-browser` to only
print the link, `--timeout 300` to allow more time, or `--redirect-uri` to change
the local port (and match the Meta app configuration). For a registered HTTPS
redirect you control:

```bash
uvx --refresh flin-meta-ads-mcp login --manual --redirect-uri https://your-domain.example/meta/callback
```

After Meta redirects, paste the full address from the browser into the hidden
terminal prompt. The destination must preserve the authorization code and state
in the URL. No callback service is hosted by this package for HTTPS.

See [Meta's manual login flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/)
and [long-lived user tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/).

### Manual access token

Stable (latest published PyPI release, refreshed):

```json
{
  "mcpServers": {
    "flin-meta-ads-mcp": {
      "command": "uvx",
      "args": ["--refresh", "flin-meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "EAA...",
        "META_GRAPH_API_VERSION": "v21.0"
      }
    }
  }
}
```

Latest GitHub code (main branch, refreshed):

```json
{
  "mcpServers": {
    "flin-meta-ads-mcp": {
      "command": "uvx",
      "args": [
        "--refresh",
        "--from",
        "git+https://github.com/flin-agency/flin-meta-ads-mcp.git",
        "flin-meta-ads-mcp"
      ],
      "env": {
        "META_ACCESS_TOKEN": "EAA...",
        "META_GRAPH_API_VERSION": "v21.0"
      }
    }
  }
}
```

## Environment variables

Authentication (choose one):

- Run `flin-meta-ads-mcp login` once to save a browser login, or
- Set `META_ACCESS_TOKEN` to a Meta access token with read permissions

Optional:

- `META_APP_ID`: App ID for browser login (otherwise prompted)
- `META_LOGIN_CONFIG_ID`: optional Facebook Login for Business user-token configuration
- `META_REDIRECT_URI`: browser login callback, default `http://localhost:8765/callback`
- `META_AUTH_FILE`: override the saved credentials path; set consistently for login and server
- `META_APP_SECRET`: App Secret (App-Geheimcode) of the app that issued the access token; enables automatic `appsecret_proof` signing
- `META_GRAPH_API_VERSION`: Graph API version, default `v21.0`
- `META_TIMEOUT_SECONDS`: request timeout, default `30`
- `META_MAX_RETRIES`: retry count for transient failures, default `3`
- `META_DEFAULT_AD_ACCOUNT_ID`: optional fallback ad account (e.g. `act_123...`) used when a tool call omits `ad_account_id`
- `RUN_LIVE_META_TESTS`: set to `1` to enable live integration tests

Ad account selection:

- If the token has exactly one accessible ad account, the server resolves it automatically.
- If `META_DEFAULT_AD_ACCOUNT_ID` is set, the server uses it when `ad_account_id` is omitted.
- If the token has multiple accessible ad accounts, pass `ad_account_id` in the tool call.

### App Secret (App-Geheimcode)

If your Meta app requires App Secret Proof, add `META_APP_SECRET` alongside the
access token in your MCP server's `env` configuration:

```json
"env": {
  "META_ACCESS_TOKEN": "EAA...",
  "META_APP_SECRET": "YOUR_APP_SECRET",
  "META_GRAPH_API_VERSION": "v21.0"
}
```

Find the App Secret in your Meta app dashboard under **App settings > Basic**.
Use a user or system user access token issued for the same app, with `ads_read`
and access to the relevant ad accounts. The App Secret alone cannot replace
the access token.

The server computes an HMAC-SHA256 `appsecret_proof` for every Graph API request,
following [Meta's Business SDK](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/session.py).
The raw App Secret is not sent in requests. Omitting `META_APP_SECRET` (or leaving
it empty) keeps token-only authentication. Restart the MCP client after changing
the configuration. Environment variables must be supplied by the MCP client or
shell; the server does not automatically load `.env` files.

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
| Login missing | No saved login or `META_ACCESS_TOKEN` | Run `flin-meta-ads-mcp login`, then restart the MCP client |
| Login expired | Saved user token expired or was revoked | Run login again and restart the MCP client |
| Redirect rejected | Redirect does not match the Meta app settings, or HTTPS is required | Match the URI exactly; use a registered HTTPS URI with `--manual` for live apps |
| Token invalid | Expired or wrong token | Generate a valid Meta read token |
| Missing or invalid `appsecret_proof` | App requires a proof, or secret and token belong to different apps | Set `META_APP_SECRET` to the secret of the app that issued the token, then restart the MCP client |
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

Keep `pyproject.toml` and `packaging/manifest.json` equal and push a matching `vX.Y.Z`
tag. The single Release workflow runs tests and builds the Apple Silicon bundle,
publishes PyPI, verifies the real PyPI updater and launch, then publishes the MCPB
and checksums. Each release includes the versioned filename plus the identical
`flin-meta-ads-mcp.mcpb` alias. Never complete a failed release with only an MCPB.
README download links must point to an already published asset.

Checks distinguish Linux tests, native Apple Silicon package startup outside the
source tree, and real customer-account access. Automated tests use synthetic
credentials and do not establish live Meta account access. See
[release validation](docs/release-validation.md) for the required evidence.

## Notes

- Use only ad accounts you are allowed to access
- This server is intended for analysis and reporting, not mutation
- Treat access tokens, App Secrets and the saved credentials file as secrets; use the hidden login prompt or environment variables, never chat messages or source code
