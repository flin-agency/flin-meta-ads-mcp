# Support

1. Ask Claude to call `connection_status` (server 0.1.17 or newer). It reports the
   running server version and local setup without network access or login. A local
   token gives `auth_status=unknown`, not proof that Meta accepted it.
2. To check Meta access, explicitly call `connection_status` with `check_live=true`.
   This makes one read of the ad-account endpoint, returns no account details and
   creates no ads or charges. An empty accessible-account list is reported in the
   next step. Select the intended account with `list_ad_accounts` afterwards.
3. Missing configuration: obtain App ID/App Secret or an `ads_read` token from your
   administrator/password manager. Expired/revoked browser login: use
   `start_meta_login`, open its link and check again. A configured access token must
   be replaced/removed in settings before browser login can take precedence.

## Updates and offline fallback

The extension version shown in Claude is the package version; `server_version` is
what actually runs. Launchers from 0.1.17 also report `extension_version` and
`runtime_source` (`cached` or `bundled`). A bundled runtime is the offline fallback,
not proof of an error. `connection_status` never checks whether PyPI has an update.

At each start the launcher prepares compatible stable 0.1.x updates in the
background. They activate at the **next** normal start; allow the first download
time to finish. Network/install/probe failure keeps the cached or bundled server.
Launcher/UI changes need a one-time package import: replace 0.1.16 or older to
acquire the 0.1-series boundary and runtime-source reporting. Routine server
updates afterwards need no package import and preserve settings/saved login.

If a prepared server fails to start, close Claude completely and rename
`~/Library/Application Support/flin-meta-ads-mcp/desktop/active.json` to
`active.json.disabled`; the next start uses the bundled fallback. This leaves
credentials and old environments intact; an online updater may prepare a new one.
Do not delete credentials to troubleshoot package updates.

Report bugs at [GitHub Issues](https://github.com/flin-agency/flin-meta-ads-mcp/issues).
Include macOS/Claude versions, chip type, extension version, safe status fields and
a redacted error. Never include tokens, App Secrets, account IDs/names or ad data.
Automated Linux checks, native Apple Silicon package checks and a real Meta account
test are separate evidence. A passing package check does not prove customer access.
